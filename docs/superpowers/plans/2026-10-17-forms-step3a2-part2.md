# Forms Step 3a2 (Drawing Engine) Implementation Plan, Part 2 of 4

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Print every court form through one engine. Each widget gets its own value, drawn with the template's own layout, and the page is flattened, so the packet has no fillable fields left. A letter the form's font can't print, or a value too long for its box even at 6 pt, is refused in plain words, and the dashboard links the refusal to the step or page that fixes it. Extra rows continue on copies of a form's extra page or on an attached sheet (proven on synthetic schemas). Generate All checks without drawing; Download draws.

**Architecture:** `apps/forms/services/widgets.py` addresses every template widget by page and index tag, so a binding can name one widget of a shared name (`<full name>@<page>:<tag>`). `PDFFormFiller.check()` plans each widget from cached widget maps and fonts without opening a PDF: the letters its font prints, the size its value fits at (mirroring pypdf 6.13.1's layout, `text_fit.py`), and where to fix a refusal (`RULE_FIXES`, `fix_for`). `fill()` runs `check()`, builds each planned widget's appearance with pypdf, removes the widgets that never print, bakes with PyMuPDF and nulls `/AcroForm`. `field_values` stores parts (`{"version": 2, "parts": [...]}`): the form, its continuation copies and its attached sheet. The tests read what is printed on the page (`read_drawn`). Each of the 9 tasks is one commit, and every task boundary passes every gate.

**This part:** Tasks 5–6. It starts where Part 1 ends, with Tasks 1–4 committed on this branch. The other parts: Part 1 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part1.md`, Tasks 1–4), Part 3 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part3.md`, Tasks 7–8), Part 4 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part4.md`, Task 9). The plan is split only to stay under the repository's 500 KB file limit. Run all parts as one execution: one ledger for Tasks 1–9, and the whole-branch final review only after Task 9, because each part's patches expect each file exactly as the earlier tasks leave it.

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

Check that Part 1 is in place: Task 4's commit is on this branch. Review fixes may have added commits after it.

```bash
set -eo pipefail
git log --format=%s 4690d12..HEAD | grep -Fx "test(forms): prove what the printed page shows, widget by widget" >/dev/null
echo "Part 1 is in place"
```

Expected: `Part 1 is in place`. If the block fails instead, Task 4 isn't committed: finish Part 1 first.

Check the baseline before Task 5:

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

### Task 5: Generate checks, Download draws, values stored as parts, and the timing command

_Built and verified as commit `467e49b` on `plan/forms-step3a2`._

**Files:**

- Create: `backend/apps/forms/management/commands/time_packet.py`
- Create: `backend/apps/forms/tests/test_time_packet.py`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/models.py`
- Modify: `backend/apps/forms/registry.py`
- Modify: `backend/apps/forms/services/__init__.py`
- Modify: `backend/apps/forms/services/fill_resolver.py`
- Modify: `backend/apps/forms/services/pdf_filler.py`
- Modify: `backend/apps/forms/services/text_fit.py`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_check.py`
- Modify: `backend/apps/forms/tests/test_download_action.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/tests/test_pdf_filler.py`
- Modify: `backend/apps/forms/views.py`
- Modify: `docs/security/deployment.md`

**Interfaces:**

- Consumes:
  - From Task 2, `backend/apps/forms/services/pdf_filler.py`:
    - `PDFFormFiller.check(self, form_type: str, values: dict) -> tuple[PlannedPart, ...]`. Before this task it plans `values` as one `{key: value}` and returns one part, `PlannedPart({"kind": "form", "values": values}, widgets)`.
    - `@dataclass(frozen=True) class Planned` (`widget`, `value`, `size`) and `@dataclass(frozen=True) class PlannedPart` (`part: dict`, `widgets: tuple[Planned, ...]`).
    - `UnprintableLetter` and `ValueTooLong`, each with `step: str | None` and `page: str | None`, and `str(exc)` the filer's sentence.
  - From Task 2, `backend/apps/forms/services/text_fit.py`: `font_for(template_filename: str, font_name: str) -> Font` (`@lru_cache`), `fit(widget: TemplateWidget, font: Font, text: str) -> tuple[str, float] | None`, `wrap(font: Font, text: str, size: float, width: float) -> list[str] | None` and `_width(font, reverse_cmap, text, size)`. Both `fit()` and `wrap()` call pypdf's `font._get_typographic_maps()` (pinned by G12) on every call. This task changes both signatures.
  - From Task 3: `PDFFormFiller.fill(self, form_type: str, values: dict) -> bytes`, which clones the template, raises `TemplateHasNoForm` when it has no `/AcroForm`, runs `check()`, draws each planned widget and bakes the page; and `read_drawn(form_type: str, pdf_bytes: bytes) -> list[DrawnWidget]` (`backend/apps/forms/tests/pdf_readback.py`), which since Task 4 refuses a PDF that was never baked.
  - `resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]` (`backend/apps/forms/services/fill_resolver.py`), a form's `{key: value}`.
  - In `backend/apps/forms/registry.py`: `FORM_REGISTRY[form_type].applies(session)` and `.requires(session)` (raises `PreconditionMissing`), `packet(session) -> list[str]` in filing order, and `build_field_values(form_type: str, session: IntakeSession) -> dict[str, str]`.
  - `load_schema(form_type)` (`apps.forms.schema`), with `template_filename` and `template_version`; `settings.PDF_FORMS_DIRECTORY`.
  - In `backend/apps/forms/views.py`:
    - `_prepare(session: IntakeSession) -> None`: refuses an unfinished intake (`IntakeNotFinished`) and works the means test out again.
    - `_failure(form_type: str | None, exc: Exception) -> tuple[dict, int]`: a refusal's 422 body, `{form_type, error}` plus the exception's `step` or `page` when it has one, or a 500 logged by type only.
    - `_fill(form_type, session) -> tuple[dict[str, str], bytes]` (raises `NotInPacket` when the form doesn't apply), `_store(generated_form, values)` and `_generate_and_persist(session, form_type, user) -> GeneratedForm` (raises `FormIsFiled` for a filed form), which this task replaces or changes.
    - Generate All runs each packet form in its own savepoint and collects each refusal into `errors` as `{form_type, error, step?, page?}`.
  - `GeneratedForm` (`backend/apps/forms/models.py`): `field_values`, an `EncryptedTextField` holding JSON text, and `status` (`generated`, `downloaded`, `filed`).
  - For the tests: `test_form_views.py`'s `user`, `api_client`, `session_with_debtor` (a completed intake whose filer is "Jane Doe") and `_filed_form`; `apps/forms/tests/conftest.py`'s `api_client_authed` and `generated_form_factory` (a Form 121 row for a completed intake whose filer is Maria Torres); `test_download_action.py`'s `_download`, `_printed` and `_rename_filer`; `test_api_readback.py`'s `_comparable`; the `seed_demo_data` command and its `demo_<persona>` users.
- Produces:
  - `parts_of(values: dict) -> list[dict]` in `pdf_filler.py`: a dict whose `"version"` is 2 gives its `parts`; any other dict is one `{"kind": "form", "values": values}`.
  - `PDFFormFiller.check()` takes a parts document or a plain `{key: value}` and returns one `PlannedPart` per part of `parts_of(values)`, each planned by the new `_plan(self, form_type: str, values: dict) -> tuple[Planned, ...]` (the old body). `fill()` takes either shape and draws the planned widgets of every part, keyed by (page, tag), so a later part's widget replaces an earlier one's (review finding 6, parked for Task 6).
  - `resolve_parts(schema: FormSchema, session: IntakeSession) -> dict` in `fill_resolver.py`: `{"version": 2, "parts": [{"kind": "form", "values": resolve(schema, session)}]}`.
  - `build_parts(form_type: str, session: IntakeSession) -> dict` in `registry.py`: the same `requires` check as `build_field_values`, then `resolve_parts`. `build_field_values` is unchanged (R20).
  - In `text_fit.py` (R51, R52), replacing Task 2's two signatures:
    - `reverse_cmap_for(template_filename: str, font_name: str) -> dict[str, str]`, `@lru_cache(maxsize=64)`, beside `font_for`;
    - `fit(widget: TemplateWidget, template_filename: str, text: str) -> tuple[str, float] | None`, which takes the box's font from `widget.font` through `font_for` and `reverse_cmap_for`;
    - `wrap(font: Font, reverse_cmap: dict[str, str], text: str, size: float, width: float) -> list[str] | None`.
  - In `views.py`: `_resolve(form_type: str, session: IntakeSession) -> dict` replaces `_fill`: it raises `NotInPacket` when the form doesn't apply, then returns `build_parts`. `_store(generated_form, document: dict)` stores the document. `_generate_and_persist` runs `check()` and never draws. Download draws, and on a filed form's refusal drops `step` and `page` from the body (R46).
  - `python manage.py time_packet --session <id> [--budget-generate 5] [--budget-download 3]` (`backend/apps/forms/management/commands/time_packet.py`):
    - `requires_system_checks = []`, so the caches are cold when it starts.
    - It imports `_generate_and_persist`, `_prepare` and `_resolve` from `apps.forms.views`, so renaming one breaks the command.
    - It prints one row per packet form, under the header `form`, `check s`, `download s`, `PDF KB`, `template KB`, then `Generate All: <s> s (budget <b> s)` and `Downloads: <s> s in all; the slowest, <form>, <s> s (budget <b> s each)`.
    - It raises `CommandError` with `No session <id>.`, `The session was refused: <exception type>`, `<form type> was refused: <exception type>`, or the budgets missed, joined by `; `: `Generate All took <s> s, over its <b> s budget` and `the download of <form type> took <s> s, over its <b> s budget`.
  - `GeneratedForm.field_values`'s comment describes both stored shapes. No migration.
  - New tests: `test_generate_all_checks_without_drawing` and `test_each_generate_names_the_step_that_fixes_a_letter_the_form_cannot_print` (`test_form_views.py`); `test_a_filed_form_downloads_exactly_what_was_filed`, `test_a_form_filed_before_3a2_still_downloads` (the renamed `test_filed_form_prints_what_was_filed`), `test_a_filed_form_whose_values_cannot_print_is_refused_without_a_step_or_page` and `test_a_template_with_no_form_is_explained_in_plain_words` (`test_download_action.py`); `_comparable_document` (`test_api_readback.py`); and `test_time_packet.py`'s four tests.
  - Where the commit differs from tasks.md's Interfaces table: the `time_packet` row says it "prints each form's check and draw times and the totals"; it prints each form's check time and download time (preparation, resolve and draw, R53) and the PDF and template sizes. Everything else matches the table, including the T5 `text_fit` row added by R52.

**Decisions already made in this task:**

_What Generate, Generate All, Regenerate and Download do (spec §6, §7):_

- **Generate, Generate All and Regenerate check without drawing.** `_generate_and_persist` resolves the form's parts (`_resolve`, which is `build_parts` behind the packet check), runs `check()` and stores the document. They drew every form only to throw the PDF away, and drawing takes most of a form's time (DIG-137). A letter the form can't print or a value too long for its box is still a 422, or a Generate All `errors` entry, with the `step` or `page` that fixes it, because `check()` raises the same exceptions `fill()` raised through it.
- **Download draws.** An unfiled form is prepared, resolved, drawn by `fill()` (which checks first) and its document stored again. A filed form draws its stored JSON, whichever shape it holds: `fill()` reads it through `parts_of`.
  - A filed form with an empty `field_values` is still resolved once and kept, as before this task (`test_filed_form_without_a_snapshot_is_resolved_once_and_kept`). So the R46 refusal below can't happen for it.
- **R46: a filed form whose stored values `check()` refuses downloads as a 422 with the refusal's sentence and no `step` or `page`.** No step changes what was filed. The view pops both keys for any refusal on the filed branch; only `UnprintableLetter` and `ValueTooLong` carry one there. Production v31 predates `field_values` (spec §6), so it holds no such row. `main`, which self-hosters run, has stored values since forms step 1, so a self-hoster's filed form can; whether it keeps this 422 is open for the owner (R73).
- **R47: the bake takes no lock.** PyMuPDF isn't thread-safe, and after this task only Download bakes. Production runs sync gunicorn workers, one request per process. `CLAUDE.md` now says the server must stay on sync workers with no `--threads` unless the bake gets a lock.
- **Stored shape.** `field_values` holds `{"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}`, built by `registry.build_parts()` through `fill_resolver.resolve_parts()`; Tasks 6 and 7 add copy and sheet parts. A form filed before 3a2 holds `{full name: value}`, which `parts_of` reads as one form part. The column stays an encrypted text field, so no migration (the implementer's `makemigrations --check`: no changes).
- **Both registry functions stay (R20).** `build_parts` is the path the views take; `build_field_values` still returns the form's `{key: value}` for `seed_demo_data` and the tests. The registry and services docstrings and `CLAUDE.md` say so (review finding 4).
- **The commit ends with `Refs DIG-137`,** the ticket spec §7 names for Generate All, download and timing.

_The tests the change breaks, and the new ones:_

- **R14 and R53(c): five `fill` patches on Generate now patch `check`,** which Generate calls: `test_filler_fault_is_a_500_logged_by_type_only` (2 cases), `test_a_refused_letter_or_length_names_where_to_fix_it` (2, Task 2's) and `test_unexpected_failure_points_the_filer_to_no_step_or_page`, a site R14's list missed. Each keeps what it proved. Four `build_field_values` patches now patch `build_parts`, two in `test_form_views.py` and two in `test_download_action.py`. Every test that read the stored values reads the form part of the stored document.
  - The parent's `fill()` calls `check()`, so these retargeted tests pass against the parent's views too (Step 6). Step 11 shows that each one bites: with `check()` skipped in `_generate_and_persist`, all five go red, and so does the letter test below.
- **R53(b) and review finding 14: the "template with no form" sentence is proved through Download only.** `TemplateHasNoForm` is raised only while drawing, so since 3a2 only Download can meet one. Generate's `template_has_no_form` parametrize case, which patched `check()` with an exception only `fill()` raises, is dropped along with its import; the parametrize keeps one case, `unmapped_choice`, so its test id stays. `test_a_template_with_no_form_is_explained_in_plain_words` patches `fill()` on Download; it passes on the parent too, and went red in the implementer's run with the sentence removed from `_FAILURE_SENTENCES` (a 500). The controller amended its comment to "Only drawing raises TemplateHasNoForm, so since 3a2 only Download can meet one": `check()` reads the template too, through the cached widget map and fonts.
- **`test_generate_all_checks_without_drawing`** patches `fill` with a mock that counts calls (a boundary: drawing), runs Generate, Generate All and Regenerate, and requires no call, three 200s, no `errors`, and every stored document equal to `build_parts`. Step 6 shows it red against the parent's views.
- **`test_each_generate_names_the_step_that_fixes_a_letter_the_form_cannot_print`** gives the filer the invented surname "Wąsowicz". Generate is a 422 with `step: "debtor_info"` and the sentence "The court form can't print the letter “ą” in “Last name”. Change it to a letter without the mark." (spec §4.5, as the code spells it), and nothing is stored.
  - **Generate All refuses the whole packet,** since every packet form prints the surname: the same `step`, each sentence about “ą”, one entry per packet form, `generated == []`. The implementer's first version asserted that the forms without the surname were kept, which was vacuous because there are none; it was fixed before review.
  - **Regenerate (review finding 11, a gap since before 3a2)** refuses a form generated before the change with the same body and leaves the row as `("generated", "")`. Regenerate shares `_generate_and_persist` with Generate, so no one-line mutation separates them: the fix round's three-edit mutation that makes only Regenerate skip `check()` went red at the Regenerate 422 assertion, where the review had found the suite green (99 passed).
  - "ą" never reaches the log (G6). The fix round kept the name `test_generate_and_generate_all_…`; the re-review noted it omits Regenerate, and the controller renamed it `test_each_generate_names_the_step_that_fixes_a_letter_the_form_cannot_print`.
- **`test_a_filed_form_downloads_exactly_what_was_filed`:** Regenerate, mark filed (both asserted 200, review finding 15), then the filer's first name changes to "Marisol"; Download prints "Maria" and the row keeps its status and stored document. The stored document must equal `{"version": 2, "parts": [{"kind": "form", "values": ANY}]}` (review finding 13): `ANY` is `unittest.mock`'s matcher, not a mock, and the printed page proves the values. The fix round's reds: Download ignoring the filed document (`{'Marisol'} == {'Maria'}`), the filed branch storing the current answers again (the final compare), and the part losing its `kind` (the shape compare).
- **`test_a_form_filed_before_3a2_still_downloads`** is `test_filed_form_prints_what_was_filed` renamed, with a comment: a row in the shape stored before 3a2 still downloads (spec §6). It passes on the parent commit, which only had that shape; Step 12 shows it red when `parts_of` reads every dict as a parts document.
- **`test_a_filed_form_whose_values_cannot_print_is_refused_without_a_step_or_page`** (R46; renamed in the fix round from an ungrammatical name, review finding 5) stores a v2 document whose first name is "Wąsowicz" on a filed Form 121 and requires exactly `{form_type, error}`. Step 13 shows it red with the pops removed.
- **`test_api_readback.py`** compares each stored document with `build_parts` through `_comparable_document`, which applies `_comparable` to each part's values.
- **`test_check.py` and `test_pdf_filler.py`** follow R52: `fit()` takes template filenames, and the G12 pin also asserts that `reverse_cmap_for("form_b121.pdf", "/Helv")` equals the map pypdf's own `_get_typographic_maps()` builds, still calling pypdf's real method.

_`time_packet` (spec §7, R13, R53):_

- **It runs the views' own helpers** (`_prepare`, `_generate_and_persist`, `_resolve`) inside one `transaction.atomic()` that ends with `transaction.set_rollback(True)`, so it times the request's code and writes nothing (R13). Each form's check runs in its own savepoint, as in Generate All.
- **Generate All's time** runs from before `_prepare` to the last form's check and store. **Each download's time** is `_prepare`, `_resolve` and `fill()`: the real Download request prepares first (R53(a)), which is stricter than tasks.md's "build_parts + fill" and costs a few tens of ms (Form 121's whole download is 0.06 s, the implementer's run).
- **Cold caches.** The system checks would build all 17 templates' widget maps first, so `requires_system_checks = []`. The implementer's `probe_cold.py` found `template_widgets`, `load_schema`, `load_index` and `font_for` all at `currsize=0` at the top of `handle()`.
  - The limit: Django imports the command, and with it the views, pypdf and PyMuPDF, before the clock starts, and a woken worker pays those imports on its first request. The implementer measured, at a load near 15, 0.67–0.89 s for `django.setup()` and 0.49–0.55 s to import the forms views and the URLconf; about 0.5 s more on the worst Generate All (2.93 s) stays under 5 s.
- **It reports and judges the first run of a fresh process,** with no warm repeat, as an Eco dyno meets its first request after waking. Budgets default to 5 s for Generate All and 3 s for each download; the budgets are judged after the transaction ends. The deploy step runs it on the Eco dyno with 15 s each, half of Heroku's 30 s router timeout (spec §7).
- **A refusal fails it naming only the exception's type** (G6): a refusal's sentence can quote the filer's letter. That holds for the session as a whole (review findings 2 and 7: `_prepare` and `packet` sit in a `try` that turns any exception into `The session was refused: <type>`) and for one form. The whole-session `except Exception` also catches a database error and calls it a refusal; the re-review accepted it, since the type still shows the cause and nothing of the filer's leaks. A filed form in the session would fail it with `FormIsFiled`; the personas have none.
- **The test fixture's surname is "Okafor".** "Dvořák", a G2 example, is refused on Form 101 (ř), which made the command fail loudly, as designed.
- **`test_time_packet_writes_nothing` proves a draw (review finding 1, Important).** It parses each printed row and requires one row per packet form and every PDF and template size above 0 KB. With the download loop calling `check()` instead of `fill()`, `len(pdf)` is 1 and the PDF prints as 0 KB, so it fails (Step 10); before the fix round both tests stayed green under that mutation.
- **It writes nothing on Postgres either.** The implementer's `probe_pg_writes_nothing.py` ran it on Priya's session in the development database with the command's transaction outermost, as on the dyno: the session's `GeneratedForm` rows stayed 0, though Generate creates 15 inside the run, and the totals stayed at 2,004 forms and 191 means tests.

_Speed and size (R41, R51, R52):_

- **R51(a), taken: pypdf's typographic maps are built once per font.** `reverse_cmap_for(template_filename, font_name)` is an `lru_cache(maxsize=64)` beside `font_for`, keyed by template filename and font name (G11). pypdf's `Font._get_typographic_maps()` builds them again on every call, which was most of `check()`'s time on a long value.
  - **R52: the interface.** A pypdf `Font` doesn't know its template and isn't hashable, so a cache keyed by (template, font name) can't be reached from `fit(widget, font, text)`. `fit()` takes the template filename and looks up the box's font (`widget.font`, the font `check()` already passed) and its map itself; `wrap()` takes the map. Every caller loses an argument it could get wrong. Rejected: shadowing `_get_typographic_maps` on the cached `Font` (obscure, and it would change what the G12 pin calls) and a cache keyed by `id(font)` (not G11). If wrong, Task 7's sheets can't call `fit()` with a font from outside a template; they measure Helvetica their own way.
  - **Measured by the implementer, in one process, interleaved:** the cut-off test on Form 107 and Schedule A/B took 24.0 s and 23.9 s with the cache, against 35.1 s and 33.9 s with the maps rebuilt on every call, about 31% less. The backend suite with coverage took 621 s before the cache at a 1-minute load near 6, and 575 s after it near 3.3; the load came from other desktop processes, so that pair mixes the cache with the machine. The fix round's gates took 1,343 s at a load of 15–20, from load, not code.
- **R51(b), not taken: `fill()` still clones each template from its file,** not from a reader parsed once. R51 takes it only if `time_packet` or the suite needs it, and every budget held (Step 16).
- **R41 (amended): `fill()` keeps `tobytes()` without `garbage` or `deflate`;** the spec sets no size limit, and `time_packet` prints each PDF's size beside its template's so the cost is on record. The implementer's runs: a drawn form is 1.05 to 2.2 times its template (Form 101 972 KB against 703; Form 107 793 against 378; A/B 572 against 309; G 123 against 56), a packet 4.7–5.2 MB against 2.8–3.2 MB.

_Review outcome (R54) and what stays parked:_

- **The review (15 findings, 1 Important) and R54:** fixed 1, 2 and 7, 3, 4, 5, 8, 11, 13, 14 and 15, each with a red proof (the fix round's 10 mutations all went red). The re-review approved.
- **Parked 6: `check()` and `fill()` treat every part as the form's own pages.** `fill()` merges every part's planned widgets by (page, tag), so a second part silently replaces the first, and a part with no `values` (a sheet) or a v2 document with no `parts` is a `KeyError`, a 500. This task stores only one form part, and Task 6 rewrites `fill()` for copies; Task 6's text carries it: `check()` refuses a part whose kind it doesn't know, and `fill()` never merges a copy's widgets into the form's.
- **Parked 9: each download's time leaves out `_store` and `save()`,** and Generate All's leaves out the delete of rows outside the packet and the serializer. Milliseconds against margins of 2 s or more; the commit body says "preparation, resolve and draw".
- **Parked 10 (pre-existing, a ticket candidate): Download's full `save()` can undo a concurrent `mark_filed`.** Download loads the row, draws for about a second, then saves every field; a `mark_filed` committed in that window goes back to `downloaded` and its stored document is replaced, which breaks DIG-155. `_generate_and_persist` has the same check-then-save window. It needs two tabs, or a Generate All alongside. The parent's Download had the same save, and this task shortens Generate's window.
- **Parked 12: the R51 cache has no test.** The G12 pin proves the cached map is pypdf's, not that it is cached: removing `@lru_cache` leaves the suite green. A call-count spy would test implementation, not outcome, and this plan's text reproduces the cache exactly.

_Left as found:_

- **The "6 failed, 73 errors" run on the first commit was the launch, not the code.** The implementer started the gates in the background from a ctx-mode sandbox call; the run inherited the sandbox's `TMPDIR`, which ctx-mode deleted mid-run, so every later `tmp_path` user errored and 6 `test_processor.py` tests that write through `tempfile` failed. Deleting a run's `TMPDIR` mid-run reproduced it, and the same commit passed with a lasting `TMPDIR`. Start long runs from a plain shell.
- **`seed_demo_data` prints each persona's demo password on stdout.** The timing step drops those lines.
- **Frontend timing flakes under load (pre-existing):** at 1-minute loads of 15–127, two or three SOFAStep and FormDashboard tests ran past the 5 s per-test timeout in the fix round's runs, and one SOFAStep run saved "2" for a typed "24000". No frontend file changed in this task; the controller's rerun at a load near 5 passed 397 of 397.
- **Three backend files fail `black --check`** (`apps/documents/apps.py`, `apps/users/serializers.py`, `manage.py`), untouched since the branch's base (Task 4's note).

- [ ] **Step 1: Write the tests**

```python file=backend/apps/forms/tests/test_time_packet.py
"""
time_packet times one session's Generate All and each form's download (spec §7, DIG-137).

It runs on the Eco dyno before a deploy, against a real filer's database, so it must
leave every row as it found it, and a budget it misses must say which.
"""

from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.districts.models import District
from apps.eligibility.models import MeansTest
from apps.forms.models import GeneratedForm
from apps.forms.registry import packet
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    """A completed intake with no means test and no forms yet, so any row it wrote would show."""
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    session = IntakeSession.objects.create(
        user=User.objects.create_user(username="timed", password="pw"),
        district=District.objects.get(code="ilnd"),
        status="completed",
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Ana",
        last_name="Okafor",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
    return session


def test_time_packet_writes_nothing(session):
    out = StringIO()

    call_command(
        "time_packet", session=session.id, budget_generate=600, budget_download=600, stdout=out
    )

    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)
    # It timed every form of the packet, which the means test it worked out decided: one
    # row each of form, check s, download s, PDF KB and template KB.
    printed = out.getvalue()
    assert "Generate All: " in printed
    form_types = packet(session)
    rows = [line.split() for line in printed.splitlines()]
    timed = {row[0]: row[1:] for row in rows if row and row[0] in form_types}
    assert set(timed) == set(form_types)
    # Each download drew its form: a check alone makes no PDF, which prints as 0 KB.
    assert all(
        float(pdf_kb) > 0 and float(template_kb) > 0 for _, _, pdf_kb, template_kb in timed.values()
    )


def test_time_packet_refuses_an_unfinished_intake_and_writes_nothing(session):
    session.status = "in_progress"
    session.save()

    with pytest.raises(CommandError) as refused:
        call_command("time_packet", session=session.id, stdout=StringIO())

    assert str(refused.value) == "The session was refused: IntakeNotFinished"
    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)


def test_time_packet_refusal_writes_nothing_and_keeps_the_filers_letter_out(session):
    # An invented surname: ą is outside the court form's font, which would print "?".
    debtor = session.debtor_info
    debtor.last_name = "Wąsowicz"
    debtor.save()

    with pytest.raises(CommandError) as refused:
        call_command("time_packet", session=session.id, stdout=StringIO())

    # The type only: a refusal's sentence quotes the filer's letter.
    message = str(refused.value)
    assert message == "form_101 was refused: UnprintableLetter"
    assert "ą" not in message
    assert "Wąsowicz" not in message
    # Even the means test it worked out before the refusal is rolled back.
    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)


def test_time_packet_names_the_budget_it_missed(session):
    with pytest.raises(CommandError) as missed:
        call_command(
            "time_packet",
            session=session.id,
            budget_generate=0,
            budget_download=0,
            stdout=StringIO(),
        )

    assert "Generate All took " in str(missed.value)
    assert "the download of form_101 took " in str(missed.value)
    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)
```

`time_packet` runs on the Eco dyno against real filers' rows, so its tests require that it leaves every row as it found it, times a real draw of every packet form, refuses as a whole or per form naming only the exception's type, and names a missed budget.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index 6a59505..8e20c9a 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -26,7 +26,7 @@ from rest_framework.test import APIClient
 from apps.districts.models import District
 from apps.eligibility.models import MeansTest
 from apps.forms.models import GeneratedForm
-from apps.forms.registry import build_field_values, packet
+from apps.forms.registry import build_parts, packet
 from apps.forms.schema import load_schema
 from apps.intake.management.commands.seed_demo_data import PERSONAS
 from apps.intake.models import IncomeInfo, IntakeSession
@@ -154,6 +154,16 @@ def _comparable(form_type, values):
     return fixed, {group: sorted(group_rows) for group, group_rows in groups.items()}


+def _comparable_document(form_type, document):
+    """A form's parts document, each part's values made comparable as _comparable does."""
+    return {
+        **document,
+        "parts": [
+            {**part, "values": _comparable(form_type, part["values"])} for part in document["parts"]
+        ],
+    }
+
+
 def _amount(text):
     try:
         return Decimal(text)
@@ -175,8 +185,11 @@ def test_forms_built_through_the_api_print_what_the_seeded_forms_print(persona):
         form.form_type: json.loads(form.field_values)
         for form in GeneratedForm.objects.filter(session_id=session_id)
     }
-    assert {form_type: _comparable(form_type, values) for form_type, values in stored.items()} == {
-        form_type: _comparable(form_type, build_field_values(form_type, seeded))
+    assert {
+        form_type: _comparable_document(form_type, document)
+        for form_type, document in stored.items()
+    } == {
+        form_type: _comparable_document(form_type, build_parts(form_type, seeded))
         for form_type in packet(seeded)
     }
     # Form 103B prints take-home pay and the non-cash answer, but no form prints the two
@@ -188,5 +201,6 @@ def test_forms_built_through_the_api_print_what_the_seeded_forms_print(persona):
     # prints her own figures: her monthly income on line 1 and her childcare on line 21.
     assert ("form_122a2" in stored) == (persona == "priya")
     if persona == "priya":
-        amounts = [_amount(value) for value in stored["form_122a2"].values()]
+        (part,) = stored["form_122a2"]["parts"]
+        amounts = [_amount(value) for value in part["values"].values()]
         assert any(amount is not None and amount > 0 for amount in amounts)
diff --git a/backend/apps/forms/tests/test_check.py b/backend/apps/forms/tests/test_check.py
index 9accf73..ce58cc7 100644
--- a/backend/apps/forms/tests/test_check.py
+++ b/backend/apps/forms/tests/test_check.py
@@ -31,7 +31,7 @@ from apps.forms.services.pdf_filler import (
     UnprintableLetter,
     ValueTooLong,
 )
-from apps.forms.services.text_fit import MIN_SIZE, fit, font_for
+from apps.forms.services.text_fit import MIN_SIZE, fit
 from apps.forms.services.widgets import field_of, template_widgets, widget_for

 LAST_NAME = "Debtor1.Last name"  # Form 101 page 1: derived last_name, label "Last name"
@@ -317,11 +317,12 @@ def test_a_value_pypdf_would_print_below_6_pt_is_refused():
 def test_branches_no_template_has():
     # No template has a multi-line auto-size box or a comb box without a MaxLen.
     (lines,) = _widgets("schedule_a_b", OTHER_PROPERTY)
-    font = font_for(load_schema("schedule_a_b").template_filename, lines.font)
-    assert fit(dataclasses.replace(lines, size=0.0), font, "A canoe") == ("A canoe", 12.0)
+    template = load_schema("schedule_a_b").template_filename
+    assert fit(dataclasses.replace(lines, size=0.0), template, "A canoe") == ("A canoe", 12.0)
     (cells,) = _widgets("form_121", SSN)
     uncounted = dataclasses.replace(cells, max_len=None)
-    assert fit(uncounted, font, "900-12-3456-78") == ("900-12-3456-78", cells.size)
+    template = load_schema("form_121").template_filename
+    assert fit(uncounted, template, "900-12-3456-78") == ("900-12-3456-78", cells.size)


 # ── Which widgets a key fills ─────────────────────────────────────────
diff --git a/backend/apps/forms/tests/test_download_action.py b/backend/apps/forms/tests/test_download_action.py
index 8552941..ab1a612 100644
--- a/backend/apps/forms/tests/test_download_action.py
+++ b/backend/apps/forms/tests/test_download_action.py
@@ -5,11 +5,12 @@ is filed, and exactly what was filed afterwards (spec §5.5).

 import json
 import logging
-from unittest.mock import patch
+from unittest.mock import ANY, patch

 from django.urls import reverse

 from apps.forms.services.fill_resolver import RepeatOverflow
+from apps.forms.services.pdf_filler import PDFFormFiller, TemplateHasNoForm
 from apps.forms.tests.pdf_readback import read_drawn


@@ -54,10 +55,32 @@ def test_unfiled_form_prints_the_filers_current_answers(api_client_authed, gener

     assert _printed(response, "Debtor1.First name") == {"Marisol"}
     form.refresh_from_db()
-    assert json.loads(form.field_values)["Debtor1.First name"] == "Marisol"
+    (part,) = json.loads(form.field_values)["parts"]
+    assert part["values"]["Debtor1.First name"] == "Marisol"


-def test_filed_form_prints_what_was_filed(api_client_authed, generated_form_factory):
+def test_a_filed_form_downloads_exactly_what_was_filed(api_client_authed, generated_form_factory):
+    form = generated_form_factory(status="generated")
+    regenerate = reverse("generated-forms-regenerate", kwargs={"pk": form.pk})
+    mark_filed = reverse("generated-forms-mark-filed", kwargs={"pk": form.pk})
+    assert api_client_authed.post(regenerate).status_code == 200
+    assert api_client_authed.post(mark_filed).status_code == 200
+    form.refresh_from_db()
+    filed = form.field_values
+    # Spec §6's parts document: a version and the form's own part.
+    assert json.loads(filed) == {"version": 2, "parts": [{"kind": "form", "values": ANY}]}
+    _rename_filer(form, "Marisol")  # the filer's later edit
+
+    response = _download(api_client_authed, form)
+
+    assert response.status_code == 200
+    assert _printed(response, "Debtor1.First name") == {"Maria"}
+    form.refresh_from_db()
+    assert (form.status, form.field_values) == ("filed", filed)
+
+
+def test_a_form_filed_before_3a2_still_downloads(api_client_authed, generated_form_factory):
+    # Filed in the shape stored before 3a2: {full name: value}, with no parts.
     form = generated_form_factory(status="filed")
     form.field_values = json.dumps({"Debtor1.First name": "Maria"})
     form.save()
@@ -70,6 +93,27 @@ def test_filed_form_prints_what_was_filed(api_client_authed, generated_form_fact
     assert form.status == "filed"


+def test_a_filed_form_whose_values_cannot_print_is_refused_without_a_step_or_page(
+    api_client_authed, generated_form_factory
+):
+    # Only a development or test database can hold one (spec §6). No step changes what was
+    # filed, so the refusal names none (R46).
+    form = generated_form_factory(status="filed")
+    form.field_values = json.dumps(
+        {"version": 2, "parts": [{"kind": "form", "values": {"Debtor1.First name": "Wąsowicz"}}]}
+    )
+    form.save()
+
+    response = _download(api_client_authed, form)
+
+    assert response.status_code == 422
+    assert response.data == {
+        "form_type": "form_121",
+        "error": "The court form can't print the letter “ą” in “Debtor 1 first name”. "
+        "Change it to a letter without the mark.",
+    }
+
+
 def test_filed_form_without_a_snapshot_is_resolved_once_and_kept(
     api_client_authed, generated_form_factory
 ):
@@ -79,7 +123,8 @@ def test_filed_form_without_a_snapshot_is_resolved_once_and_kept(

     assert _printed(response, "Debtor1.First name") == {"Maria"}
     form.refresh_from_db()
-    assert json.loads(form.field_values)["Debtor1.First name"] == "Maria"
+    (part,) = json.loads(form.field_values)["parts"]
+    assert part["values"]["Debtor1.First name"] == "Maria"


 def test_a_letter_the_form_cannot_print_refuses_the_download(
@@ -128,7 +173,7 @@ def test_missing_data_is_a_422_with_its_reason(api_client_authed, generated_form
 def test_too_many_rows_is_a_422(api_client_authed, generated_form_factory):
     form = generated_form_factory(status="generated")
     overflow = RepeatOverflow("form_121", "rows", capacity=3, actual=4)
-    with patch("apps.forms.views.build_field_values", side_effect=overflow):
+    with patch("apps.forms.views.build_parts", side_effect=overflow):
         response = _download(api_client_authed, form)
     assert response.status_code == 422
     # No repeat group name or capacity: the filer reads this beside the form's label.
@@ -139,9 +184,23 @@ def test_too_many_rows_is_a_422(api_client_authed, generated_form_factory):
     }


+def test_a_template_with_no_form_is_explained_in_plain_words(
+    api_client_authed, generated_form_factory
+):
+    # Only drawing raises TemplateHasNoForm, so since 3a2 only Download can meet one.
+    form = generated_form_factory(status="generated")
+    with patch.object(PDFFormFiller, "fill", side_effect=TemplateHasNoForm("form_121")):
+        response = _download(api_client_authed, form)
+    assert response.status_code == 422
+    assert response.data == {
+        "form_type": "form_121",
+        "error": "This form's blank court template can't be filled in right now.",
+    }
+
+
 def test_unexpected_failure_logs_only_its_type(api_client_authed, generated_form_factory, caplog):
     form = generated_form_factory(status="generated")
-    with patch("apps.forms.views.build_field_values", side_effect=ValueError("900-11-0001")):
+    with patch("apps.forms.views.build_parts", side_effect=ValueError("900-11-0001")):
         response = _download(api_client_authed, form)
     assert response.status_code == 500
     assert "900-11-0001" not in caplog.text
diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index c1051a5..fa61150 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -31,11 +31,11 @@ from rest_framework.test import APIClient
 from apps.districts.models import District, MedianIncome
 from apps.eligibility.models import MeansTest
 from apps.forms.models import GeneratedForm
+from apps.forms.registry import build_parts, packet
 from apps.forms.services.fill_resolver import UnmappedChoice
 from apps.forms.services.pdf_filler import (
     InvalidFieldValue,
     PDFFormFiller,
-    TemplateHasNoForm,
     UnknownField,
     UnprintableLetter,
     ValueTooLong,
@@ -284,9 +284,7 @@ class TestGenerateEndpoint:
         assert not GeneratedForm.objects.filter(session=session).exists()

     def test_unexpected_failure_logs_only_its_type(self, api_client, session_with_debtor, caplog):
-        with patch(
-            "apps.forms.views.build_field_values", side_effect=ValueError("900-12-3456 leaked")
-        ):
+        with patch("apps.forms.views.build_parts", side_effect=ValueError("900-12-3456 leaked")):
             resp = api_client.post(
                 self.URL,
                 {"session_id": session_with_debtor.id, "form_type": "form_101"},
@@ -303,18 +301,13 @@ class TestGenerateEndpoint:
         "target,exc,error",
         [
             (
-                "apps.forms.views.build_field_values",
+                "apps.forms.views.build_parts",
                 UnmappedChoice("Check Box1"),
                 "One of your answers doesn't match a choice printed on this form, "
                 "so it can't be filled in yet.",
             ),
-            (
-                "apps.forms.views.PDFFormFiller.fill",
-                TemplateHasNoForm("form_101"),
-                "This form's blank court template can't be filled in right now.",
-            ),
         ],
-        ids=["unmapped_choice", "template_has_no_form"],
+        ids=["unmapped_choice"],
     )
     def test_expected_failure_is_explained_in_plain_words(
         self, api_client, session_with_debtor, target, exc, error
@@ -339,7 +332,7 @@ class TestGenerateEndpoint:
     def test_filler_fault_is_a_500_logged_by_type_only(
         self, api_client, session_with_debtor, caplog, exc
     ):
-        with patch.object(PDFFormFiller, "fill", side_effect=exc):
+        with patch.object(PDFFormFiller, "check", side_effect=exc):
             resp = api_client.post(
                 self.URL,
                 {"session_id": session_with_debtor.id, "form_type": "form_101"},
@@ -382,7 +375,7 @@ class TestGenerateEndpoint:
         self, api_client, session_with_debtor, caplog, exc, refusal
     ):
         caplog.set_level(logging.DEBUG)
-        with patch.object(PDFFormFiller, "fill", side_effect=exc):
+        with patch.object(PDFFormFiller, "check", side_effect=exc):
             resp = api_client.post(
                 self.URL,
                 {"session_id": session_with_debtor.id, "form_type": "form_101"},
@@ -400,7 +393,7 @@ class TestGenerateEndpoint:
         # Only a refusal names where the filer fixes it; nothing they enter fixes a fault.
         fault = RuntimeError("page 3 could not be written")
         fault.step, fault.page = "debtor_info", 3
-        with patch.object(PDFFormFiller, "fill", side_effect=fault):
+        with patch.object(PDFFormFiller, "check", side_effect=fault):
             resp = api_client.post(
                 self.URL,
                 {"session_id": session_with_debtor.id, "form_type": "form_101"},
@@ -485,7 +478,8 @@ class TestGenerateAllEndpoint:
         assert json.loads(form.field_values) == {"Debtor 1": "Jane Doe"}
         # The forms not yet filed are resolved from the current answers.
         petition = GeneratedForm.objects.get(session=session_with_debtor, form_type="form_101")
-        assert json.loads(petition.field_values)["Debtor1.First name"] == "Janet"
+        (part,) = json.loads(petition.field_values)["parts"]
+        assert part["values"]["Debtor1.First name"] == "Janet"

     def test_missing_session_id(self, api_client):
         resp = api_client.post(self.URL, {}, format="json")
@@ -513,7 +507,8 @@ class TestRegenerateEndpoint:
         assert resp.data["message"] == "Form regenerated successfully"

         form.refresh_from_db()
-        assert json.loads(form.field_values)["Debtor 1"] == "Jane Doe"
+        (part,) = json.loads(form.field_values)["parts"]
+        assert part["values"]["Debtor 1"] == "Jane Doe"

     def test_filed_form_keeps_what_was_filed(self, api_client, session_with_debtor, user):
         form = _filed_form(session_with_debtor, user, "form_106dec", {"Debtor 1": "Jane Doe"})
@@ -538,6 +533,86 @@ class TestRegenerateEndpoint:
         assert resp.status_code == status.HTTP_404_NOT_FOUND


+# ── Generate, Generate All and Regenerate check; only Download draws (spec §7) ──
+
+
+@pytest.mark.django_db
+def test_generate_all_checks_without_drawing(api_client, session_with_debtor):
+    # Drawing takes most of a form's time, so a packet's Generate All only checks what each
+    # form prints, and stays inside its budget (DIG-137). Download draws.
+    session = session_with_debtor
+    with patch.object(PDFFormFiller, "fill") as fill:
+        generate = api_client.post(
+            "/api/forms/generate/",
+            {"session_id": session.id, "form_type": "form_101"},
+            format="json",
+        )
+        generate_all = api_client.post(
+            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
+        )
+        regenerate = api_client.post(f"/api/forms/{generate.data['form']['id']}/regenerate/")
+
+    assert fill.call_count == 0
+    assert [r.status_code for r in (generate, generate_all, regenerate)] == [200, 200, 200]
+    assert generate_all.data["errors"] == []
+    # Each form keeps the parts it was checked with, which its download draws.
+    stored = GeneratedForm.objects.filter(session=session)
+    assert stored.count() == generate_all.data["total_generated"]
+    for form in stored:
+        assert json.loads(form.field_values) == build_parts(form.form_type, session)
+
+
+@pytest.mark.django_db
+def test_each_generate_names_the_step_that_fixes_a_letter_the_form_cannot_print(
+    api_client, session_with_debtor, user, caplog
+):
+    # An invented surname: ą is outside the court form's font, which would print "?".
+    session = session_with_debtor
+    debtor = session.debtor_info
+    debtor.last_name = "Wąsowicz"
+    debtor.save()
+    caplog.set_level(logging.DEBUG)
+
+    generate = api_client.post(
+        "/api/forms/generate/", {"session_id": session.id, "form_type": "form_101"}, format="json"
+    )
+    generate_all = api_client.post(
+        "/api/forms/generate_all/", {"session_id": session.id}, format="json"
+    )
+
+    refusal = {
+        "form_type": "form_101",
+        "error": "The court form can't print the letter “ą” in “Last name”. "
+        "Change it to a letter without the mark.",
+        "step": "debtor_info",
+    }
+    assert generate.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
+    assert generate.data == refusal
+    # Every form of the packet prints the surname, so Generate All refuses each the same way.
+    errors = generate_all.data["errors"]
+    assert refusal in errors
+    assert {error["step"] for error in errors} == {"debtor_info"}
+    assert all(
+        error["error"].startswith("The court form can't print the letter “ą” in “")
+        for error in errors
+    )
+    assert sorted(error["form_type"] for error in errors) == sorted(packet(session))
+    assert generate_all.data["generated"] == []
+    assert not GeneratedForm.objects.filter(session=session).exists()
+
+    # Regenerate refuses a form generated before the change the same way, and keeps it.
+    form = GeneratedForm.objects.create(
+        session=session, form_type="form_101", status="generated", generated_by=user
+    )
+    regenerate = api_client.post(f"/api/forms/{form.id}/regenerate/")
+
+    assert regenerate.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
+    assert regenerate.data == refusal
+    form.refresh_from_db()
+    assert (form.status, form.field_values) == ("generated", "")
+    assert "ą" not in caplog.text
+
+
 # ── Status Transition Endpoints ───────────────────────────────────────


@@ -1040,8 +1115,9 @@ def test_filed_form_survives_leaving_the_packet(api_client, session_with_debtor)
     printed = {}
     for w in read_drawn("form_122a2", download.content):
         printed.setdefault(w.full_name, set()).add(w.value)
+    (part,) = filed_values["parts"]
     typed = {
-        name: value for name, value in filed_values.items() if value and not value.startswith("/")
+        name: value for name, value in part["values"].items() if value and not value.startswith("/")
     }
     assert "Jane Doe" in typed.values()
     assert {name: printed.get(name) for name in typed} == {
diff --git a/backend/apps/forms/tests/test_pdf_filler.py b/backend/apps/forms/tests/test_pdf_filler.py
index cb34b80..c419496 100644
--- a/backend/apps/forms/tests/test_pdf_filler.py
+++ b/backend/apps/forms/tests/test_pdf_filler.py
@@ -26,7 +26,7 @@ from apps.forms.services.pdf_filler import (
     TemplateHasNoForm,
     UnknownField,
 )
-from apps.forms.services.text_fit import font_for
+from apps.forms.services.text_fit import font_for, reverse_cmap_for
 from apps.forms.services.widgets import parse_key, template_widgets
 from apps.forms.tests.pdf_readback import read_drawn

@@ -103,6 +103,8 @@ def test_text_is_measured_with_pinned_pypdf_font_internals():
     font = font_for("form_b121.pdf", "/Helv")  # Font.from_font_resource
     assert isinstance(font, Font)
     reverse_cmap, _ = font._get_typographic_maps()
+    # check() measures by the map pypdf builds, kept once per font (R51).
+    assert reverse_cmap_for("form_b121.pdf", "/Helv") == reverse_cmap
     assert font.get_text_width(reverse_cmap["W"]) == 944  # Helvetica's W
     assert font.can_encode("é") and not font.can_encode("ą")
     bbox = font.font_descriptor.bbox
PATCH
```

The view tests require that Generate, Generate All and Regenerate never draw and store what `build_parts` builds, that a letter the form can't print is refused with its step through all three, that a filed form downloads exactly what was filed in either stored shape, and that a filed form's refusal names no step or page. Every test that patched `fill` on Generate patches `check`, and every read of a stored row reads its form part. `test_check.py` and `test_pdf_filler.py` call `fit()` with template filenames and pin the cached map to pypdf's.

- [ ] **Step 2: Run the tests and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE --continue-on-collection-errors apps/forms/tests/test_form_views.py apps/forms/tests/test_download_action.py apps/forms/tests/test_api_readback.py apps/forms/tests/test_check.py apps/forms/tests/test_pdf_filler.py apps/forms/tests/test_time_packet.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `11 failed, 44 passed` and `3 errors in`, with `ERROR apps/forms/tests/test_form_views.py`, `CommandError: Unknown command: 'time_packet'`, `AttributeError: 'str' object has no attribute '_get_typographic_maps'`, `test_a_filed_form_whose_values_cannot_print_is_refused_without_a_step_or_page - assert 500 == 422` and `test_unfiled_form_prints_the_filers_current_answers - KeyError: 'parts'`.

`--continue-on-collection-errors` runs the other modules while three can't be imported: `test_form_views.py` and `test_api_readback.py` import `build_parts`, and `test_pdf_filler.py` imports `reverse_cmap_for`. Step 6 shows the view tests' own failures once those names exist.

- All 4 `time_packet` tests fail: the command doesn't exist.
- `test_check.py`'s `test_branches_no_template_has` hands `fit()` a template filename where the parent's `fit()` wants a `Font`.
- 6 of `test_download_action.py`'s 13 fail: the stored values have no `parts`, a v2 document is no `{name: value}` the parent can check (500), and the parent's views have no `build_parts` to patch. The 7 that pass include the renamed pre-3a2 download and the template-with-no-form test, which hold on the parent too; Step 12 shows what the first one guards.

- [ ] **Step 3: Build pypdf's typographic maps once per font**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/text_fit.py b/backend/apps/forms/services/text_fit.py
index f04dd9a..d101be8 100644
--- a/backend/apps/forms/services/text_fit.py
+++ b/backend/apps/forms/services/text_fit.py
@@ -34,6 +34,16 @@ def font_for(template_filename: str, font_name: str) -> Font:
     return Font.from_font_resource(reader.root_object["/AcroForm"]["/DR"]["/Font"][font_name])


+@lru_cache(maxsize=64)
+def reverse_cmap_for(template_filename: str, font_name: str) -> dict[str, str]:
+    """
+    The font's map from each character to the glyph pypdf measures it by, built once:
+    pypdf's Font._get_typographic_maps() builds it again on every call (R51).
+    """
+    reverse_cmap, _ = font_for(template_filename, font_name)._get_typographic_maps()
+    return reverse_cmap
+
+
 def printable(font: Font, letter: str) -> bool:
     """The font's encoding has the letter: pypdf draws it, not "?" or another glyph (R7)."""
     return font.can_encode(letter)
@@ -56,14 +66,16 @@ def _leading(font: Font) -> float:
     return (bbox[3] - bbox[1]) / 1000


-def wrap(font: Font, text: str, size: float, width: float) -> list[str] | None:
+def wrap(
+    font: Font, reverse_cmap: dict[str, str], text: str, size: float, width: float
+) -> list[str] | None:
     """
     One paragraph broken at spaces into lines no wider than width at size, each line
     taking as many words as fit. Spaces are kept as typed, except one at each break.
+    reverse_cmap is the font's, from reverse_cmap_for().

     Returns None when a word is wider than width.
     """
-    reverse_cmap, _ = font._get_typographic_maps()
     lines: list[str] = []
     line: str | None = None
     for word in text.split(" "):
@@ -91,15 +103,17 @@ def _sizes(start: float) -> list[float]:
     return [size for size in sizes if size >= MIN_SIZE]


-def fit(widget: TemplateWidget, font: Font, text: str) -> tuple[str, float] | None:
+def fit(widget: TemplateWidget, template_filename: str, text: str) -> tuple[str, float] | None:
     """
     The text as the box will draw it and the size to draw it at: the box's own size,
-    or the first 0.5 pt step below it at which the text fits, down to 6 pt.
+    or the first 0.5 pt step below it at which the text fits, down to 6 pt. The box's
+    font is the one its /DA names in the template.

     A line break starts a new line in a multi-line box and is a space in any other
     box. Returns None when the text fits at no size.
     """
-    reverse_cmap, _ = font._get_typographic_maps()
+    font = font_for(template_filename, widget.font)
+    reverse_cmap = reverse_cmap_for(template_filename, widget.font)
     field_width = widget.width - 4 * widget.margin
     paragraphs = text.splitlines()
     text = "\n".join(paragraphs) if widget.multiline else " ".join(paragraphs)
@@ -126,7 +140,9 @@ def fit(widget: TemplateWidget, font: Font, text: str) -> tuple[str, float] | No
             if _width(font, reverse_cmap, text, size) <= field_width:
                 return text, size
             continue
-        wrapped = [wrap(font, paragraph, size, field_width) for paragraph in paragraphs]
+        wrapped = [
+            wrap(font, reverse_cmap, paragraph, size, field_width) for paragraph in paragraphs
+        ]
         if None in wrapped:
             continue
         lines = [line for paragraph in wrapped for line in paragraph]
PATCH
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -314,7 +314,7 @@
             letter = _refused_letter(widget, font, text)
             if letter is not None:
                 raise UnprintableLetter(form_type, letter, *_source(schema, key, widget))
-            fitted = fit(widget, font, text)
+            fitted = fit(widget, schema.template_filename, text)
             if fitted is None:
                 raise ValueTooLong(form_type, *_source(schema, key, widget))
             planned.append(Planned(widget, *fitted))
PATCH
```

`reverse_cmap_for` builds a font's character-to-glyph map once and keeps it, keyed by template filename and font name, beside `font_for`. `fit()` now takes the template filename and looks up the box's font and its map itself; `wrap()` takes the map from `fit()`. `check()`'s one call to `fit()` passes its schema's template filename.

- [ ] **Step 4: Run the measuring tests**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_check.py apps/forms/tests/test_pdf_filler.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `79 passed`.

That is `test_check.py`'s 38 tests, among them the one Step 2 showed failing, and `test_pdf_filler.py`'s 41, whose pin now compares the cached map with pypdf's.

- [ ] **Step 5: Store a form's values as parts, and plan each part**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/registry.py b/backend/apps/forms/registry.py
index 8077e7a..bbcdc9e 100644
--- a/backend/apps/forms/registry.py
+++ b/backend/apps/forms/registry.py
@@ -4,7 +4,9 @@ The Chapter 7 packet: which forms a filer needs, and what each needs first (spec
 Each form_type maps to applies(session), which says whether the form is part
 of this filer's packet and never raises, and requires(session), which raises
 PreconditionMissing when data the form can't be filled without is absent.
-build_field_values() is the one path from a session to a form's printed values.
+build_parts() is the path the views take from a session to a form's printed values: the
+parts document they check, store and draw. build_field_values() returns the form's
+{key: value}.
 FORM_REGISTRY is in filing order.
 """

@@ -14,7 +16,7 @@ from dataclasses import dataclass

 from apps.eligibility.cmi import is_above_median
 from apps.forms.schema import load_schema
-from apps.forms.services.fill_resolver import resolve
+from apps.forms.services.fill_resolver import resolve, resolve_parts
 from apps.intake.models import IntakeSession

 _SSN = re.compile(r"\d{3}-\d{2}-\d{4}|\d{9}")
@@ -133,3 +135,16 @@ def build_field_values(form_type: str, session: IntakeSession) -> dict[str, str]
     """
     FORM_REGISTRY[form_type].requires(session)
     return resolve(load_schema(form_type), session)
+
+
+def build_parts(form_type: str, session: IntakeSession) -> dict:
+    """
+    The parts a form prints for this session, as GeneratedForm.field_values stores them:
+    {"version": 2, "parts": [...]} (spec §6).
+
+    Raises:
+        KeyError: form_type is not registered.
+        PreconditionMissing: the form needs data the session lacks.
+    """
+    FORM_REGISTRY[form_type].requires(session)
+    return resolve_parts(load_schema(form_type), session)
diff --git a/backend/apps/forms/services/__init__.py b/backend/apps/forms/services/__init__.py
index 15aaa26..a821d90 100644
--- a/backend/apps/forms/services/__init__.py
+++ b/backend/apps/forms/services/__init__.py
@@ -1,5 +1,7 @@
 """
 Form services: the schema-driven fill engine (fill_resolver, derivations) and the PDF filler.

-A form's printed values come from apps.forms.registry.build_field_values().
+The views take a form's printed values from apps.forms.registry.build_parts(), as the parts
+document they check, store and draw; apps.forms.registry.build_field_values() returns the
+form's {key: value}.
 """
diff --git a/backend/apps/forms/services/fill_resolver.py b/backend/apps/forms/services/fill_resolver.py
index f5ffd16..c99ea69 100644
--- a/backend/apps/forms/services/fill_resolver.py
+++ b/backend/apps/forms/services/fill_resolver.py
@@ -229,3 +229,11 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
                     out[_key(f)] = emitted

     return out
+
+
+def resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
+    """
+    The form's values as the parts it prints, in printing order (spec §6):
+    {"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}.
+    """
+    return {"version": 2, "parts": [{"kind": "form", "values": resolve(schema, session)}]}
PATCH
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -131,6 +131,16 @@

     part: dict  # the part as given: {"kind": "form", "values": {...}}
     widgets: tuple[Planned, ...]
+
+
+def parts_of(values: dict) -> list[dict]:
+    """
+    The parts a form's values hold: a parts document's own, {"version": 2, "parts": [...]}
+    (spec §6), or any other dict, such as a form filed before 3a2, as one form part.
+    """
+    if values.get("version") == 2:
+        return values["parts"]
+    return [{"kind": "form", "values": values}]


 def _source(schema: FormSchema, key: str, widget: TemplateWidget) -> tuple[str, dict[str, str]]:
@@ -250,15 +260,17 @@

         Args:
             form_type: a registered form type; its schema names the template.
-            values: {key: value}. A key is a full name, which fills every drawn widget
-                of that name, or "<full name>@<page>:<tag>", which fills that one
-                widget and wins over the full name there. A value is text, a combo's
-                option, or a box's export state such as "/Chapter 7".
+            values: a parts document, {"version": 2, "parts": [...]}, whose form part
+                holds {key: value}, or {key: value} alone (parts_of). A key is a full
+                name, which fills every drawn widget of that name, or
+                "<full name>@<page>:<tag>", which fills that one widget and wins over
+                the full name there. A value is text, a combo's option, or a box's
+                export state such as "/Chapter 7".

         Returns:
-            One part, holding every widget a key fills in page and tag order: a text
-            or combo box with its text as drawn and its size, a box with its state or
-            "/Off".
+            One planned part per part, each holding every widget a key fills in page
+            and tag order: a text or combo box with its text as drawn and its size, a
+            box with its state or "/Off".

         Raises:
             UnknownField: a key names no drawn widget, or is neither form of key.
@@ -266,6 +278,12 @@
             UnprintableLetter: a letter the box can't print.
             ValueTooLong: a value too long for its box even at 6 pt.
         """
+        return tuple(
+            PlannedPart(part, self._plan(form_type, part["values"])) for part in parts_of(values)
+        )
+
+    def _plan(self, form_type: str, values: dict) -> tuple[Planned, ...]:
+        """What each widget one part's {key: value} fills prints, as check() describes."""
         schema = load_schema(form_type)
         by_name: dict[str, list[TemplateWidget]] = {}
         for widget in template_widgets(schema.template_filename):
@@ -318,7 +336,7 @@
             if fitted is None:
                 raise ValueTooLong(form_type, *_source(schema, key, widget))
             planned.append(Planned(widget, *fitted))
-        return (PlannedPart({"kind": "form", "values": values}, tuple(planned)),)
+        return tuple(planned)

     def fill(self, form_type: str, values: dict) -> bytes:
         """
@@ -341,8 +359,11 @@
         writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
         if "/AcroForm" not in writer.root_object:
             raise TemplateHasNoForm(form_type)
-        (part,) = self.check(form_type, values)
-        planned = {(p.widget.page, p.widget.tag): p for p in part.widgets}
+        planned = {
+            (p.widget.page, p.widget.tag): p
+            for part in self.check(form_type, values)
+            for p in part.widgets
+        }
         acro_form = writer.root_object["/AcroForm"].get_object()

         for number, page in enumerate(writer.pages, start=1):
PATCH
```

`resolve_parts` wraps a form's resolved values as the one form part of a version-2 document, and `build_parts` returns it after the same precondition check as `build_field_values`. `parts_of` reads either stored shape, so `check()` plans each part through `_plan` (the old body) and `fill()` draws the widgets of every part.

- [ ] **Step 6: Watch the view tests fail against the views that still draw**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_form_views.py apps/forms/tests/test_download_action.py apps/forms/tests/test_api_readback.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `18 failed, 58 passed`, with `test_generate_all_checks_without_drawing - AssertionError: assert 16 == 0`, `KeyError: 'parts'`, `does not have the attribute 'build_parts'` and `test_a_filed_form_whose_values_cannot_print_is_refused_without_a_step_or_page - AssertionError: assert {'error': 'Th...'debtor_info'}`.

The modules import now, and the views still draw and store a plain `{key: value}`:

- Generate, Generate All and Regenerate called `fill()` 16 times (one form, a 14-form packet, one form).
- Every read of a stored row's `parts` fails (`KeyError`), in the view tests, the download tests and all 6 personas of `test_api_readback.py`.
- The tests that patch `build_parts` find no such name in the views.
- The filed form's refusal now comes back as a 422, but with `step: "debtor_info"`, which R46 drops.

The 58 that pass include the letter test and the five retargeted Generate tests: the parent's `fill()` runs `check()`, so a refusal already comes back with its step. Step 11 shows they fail once Generate stops checking.

- [ ] **Step 7: Check on Generate, draw on Download**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/models.py b/backend/apps/forms/models.py
index 328ad9b..e2e8b56 100644
--- a/backend/apps/forms/models.py
+++ b/backend/apps/forms/models.py
@@ -62,8 +62,10 @@ class GeneratedForm(models.Model):
     # JSON. Nothing reads or writes it; its column is dropped one release later.
     form_data = models.JSONField(default=dict, help_text="Unused; see field_values")

-    # The values the form printed, as encrypted JSON {full name: value}. The API
-    # never returns it; download fills a filed form from it.
+    # The values the form prints, as encrypted JSON: a parts document,
+    # {"version": 2, "parts": [{"kind": "form", "values": {key: value}}, ...]}, or, for
+    # a form filed before 3a2, {full name: value}, read as one form part. The API never
+    # returns it; download draws a filed form from it.
     field_values = EncryptedTextField(blank=True, default="", help_text="Encrypted JSON")

     # Schema / template version (reproducibility)
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
index 46ebf11..ee8ef02 100644
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -1,9 +1,10 @@
 """
 API views for bankruptcy form generation.

-One path fills every form: registry.build_field_values() resolves a session's
-values, PDFFormFiller fills the template, and the values are kept as an
-encrypted snapshot (GeneratedForm.field_values) that the API never returns.
+One path fills every form: registry.build_parts() resolves a session's values,
+PDFFormFiller checks that the template can print them, and they are kept as an
+encrypted parts document (GeneratedForm.field_values) that the API never returns.
+Generate, Generate All and Regenerate only check; Download draws (spec §7).
 """

 import json
@@ -29,7 +30,7 @@ from .models import GeneratedForm
 from .registry import (
     FORM_REGISTRY,
     PreconditionMissing,
-    build_field_values,
+    build_parts,
     get_all_form_types,
     packet,
 )
@@ -188,31 +189,31 @@ def _prepare(session: IntakeSession) -> None:
     _recalculate_means_test(session)


-def _fill(form_type: str, session: IntakeSession) -> tuple[dict[str, str], bytes]:
-    """Resolve a form that applies to this filer and fill its template. _prepare() runs first."""
+def _resolve(form_type: str, session: IntakeSession) -> dict:
+    """The parts a form that applies to this filer prints. _prepare() runs first."""
     if not FORM_REGISTRY[form_type].applies(session):
         raise NotInPacket()
-    values = build_field_values(form_type, session)
-    return values, PDFFormFiller().fill(form_type, values)
+    return build_parts(form_type, session)


-def _store(generated_form: GeneratedForm, values: dict[str, str]) -> None:
-    generated_form.field_values = json.dumps(values)
+def _store(generated_form: GeneratedForm, document: dict) -> None:
+    generated_form.field_values = json.dumps(document)
     generated_form.template_version = load_schema(generated_form.form_type).template_version


 def _generate_and_persist(session: IntakeSession, form_type: str, user) -> GeneratedForm:
-    """Fill the form (which proves it fills) and keep its values as the snapshot.
+    """Check that the form prints its values, without drawing it, and keep them (spec §7).

     _prepare() runs first.
     """
     if GeneratedForm.objects.filter(session=session, form_type=form_type, status="filed").exists():
         raise FormIsFiled()
-    values, _ = _fill(form_type, session)
+    document = _resolve(form_type, session)
+    PDFFormFiller().check(form_type, document)
     generated_form, _ = GeneratedForm.objects.get_or_create(
         session=session, form_type=form_type, defaults={"generated_by": user}
     )
-    _store(generated_form, values)
+    _store(generated_form, document)
     generated_form.status = "generated"
     generated_form.generated_by = user
     generated_form.save()
@@ -242,7 +243,7 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
       POST /api/forms/generate/              Generate a single form
       POST /api/forms/generate_all/          Generate every form in the packet
       POST /api/forms/{id}/regenerate/       Regenerate an existing form
-      GET  /api/forms/{id}/download/         Fill and stream the PDF
+      GET  /api/forms/{id}/download/         Draw and stream the PDF
       POST /api/forms/{id}/mark_downloaded/
       POST /api/forms/{id}/mark_filed/
     """
@@ -452,26 +453,32 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
     @action(detail=True, methods=["get"])
     def download(self, request, pk=None):
         """
-        Fill the official AO template and stream it.
+        Draw the official AO template and stream it.

-        A form not yet filed is resolved fresh, so the filer always downloads
-        their current answers, and its snapshot is refreshed. A filed form
-        fills from its snapshot, so it matches what was filed, even after it
-        has left the packet (DIG-155).
+        A form not yet filed is resolved, checked and drawn fresh, so the filer always
+        downloads their current answers, and its parts are stored again. A filed form
+        draws its stored parts, or its values stored before 3a2, so it matches what was
+        filed, even after it has left the packet (DIG-155).
         """
         generated_form = self.get_object()
         form_type = generated_form.form_type
         session = generated_form.session
+        filed = generated_form.status == "filed" and bool(generated_form.field_values)

         try:
-            if generated_form.status == "filed" and generated_form.field_values:
+            if filed:
                 pdf_bytes = PDFFormFiller().fill(form_type, json.loads(generated_form.field_values))
             else:
                 _prepare(session)
-                values, pdf_bytes = _fill(form_type, session)
-                _store(generated_form, values)
+                document = _resolve(form_type, session)
+                pdf_bytes = PDFFormFiller().fill(form_type, document)
+                _store(generated_form, document)
         except Exception as exc:
             body, code = _failure(form_type, exc)
+            if filed:
+                # No step or page changes the values a form was filed with (R46).
+                body.pop("step", None)
+                body.pop("page", None)
             return Response(body, status=code)

         if generated_form.status == "generated":
PATCH
```

`_resolve` replaces `_fill`: it refuses a form outside the packet and returns `build_parts`, and draws nothing. `_generate_and_persist` checks that document and stores it, so Generate, Generate All and Regenerate never draw. Download draws: an unfiled form is prepared, resolved, drawn and stored again, and a filed form draws its stored JSON in either shape. A refusal on the filed branch loses its `step` and `page` (R46). The model's comment describes both stored shapes; the column is unchanged, so there is no migration.

- [ ] **Step 8: Add the timing command**

```python file=backend/apps/forms/management/commands/time_packet.py
"""
time_packet: how long one session's Generate All and each form's download take (spec §7).

    python manage.py time_packet --session <id> [--budget-generate 5] [--budget-download 3]

It runs the views' own code: Generate All's preparation and each packet form's check,
then each form's download, which prepares, resolves and draws the form again. It times
the first run of a fresh process, every cache cold, as a dyno meets its first request
after waking, and judges it against the budgets (DIG-137). Everything runs in one
transaction that is rolled back, so it writes nothing (R13).
"""

import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.forms.registry import packet
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.views import _generate_and_persist, _prepare, _resolve
from apps.intake.models import IntakeSession


class Command(BaseCommand):
    help = "Time one session's Generate All and each form's download. Writes nothing."
    # The system checks build every template's widget map, which would warm the caches a
    # dyno's first request meets cold.
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--session", type=int, required=True, help="the IntakeSession id")
        parser.add_argument(
            "--budget-generate", type=float, default=5.0, help="seconds for Generate All"
        )
        parser.add_argument(
            "--budget-download", type=float, default=3.0, help="seconds for each download"
        )

    def handle(self, *args, **options):
        try:
            session = IntakeSession.objects.get(id=options["session"])
        except IntakeSession.DoesNotExist as exc:
            raise CommandError(f"No session {options['session']}.") from exc

        checks, downloads = {}, {}
        with transaction.atomic():
            started = time.perf_counter()
            try:
                _prepare(session)
                form_types = packet(session)
            except Exception as exc:
                raise CommandError(f"The session was refused: {type(exc).__name__}") from exc
            for form_type in form_types:
                form_started = time.perf_counter()
                try:
                    with transaction.atomic():  # a savepoint per form, as Generate All has
                        _generate_and_persist(session, form_type, session.user)
                except Exception as exc:
                    # The type only: a refusal's sentence can quote the filer's letter.
                    raise CommandError(f"{form_type} was refused: {type(exc).__name__}") from exc
                checks[form_type] = time.perf_counter() - form_started
            generate_all = time.perf_counter() - started

            for form_type in form_types:
                form_started = time.perf_counter()
                try:
                    _prepare(session)
                    pdf = PDFFormFiller().fill(form_type, _resolve(form_type, session))
                except Exception as exc:
                    raise CommandError(f"{form_type} was refused: {type(exc).__name__}") from exc
                downloads[form_type] = (time.perf_counter() - form_started, len(pdf))
            transaction.set_rollback(True)  # write nothing (R13)

        self.stdout.write(
            f"{'form':<16}{'check s':>9}{'download s':>12}{'PDF KB':>9}{'template KB':>13}"
        )
        for form_type in form_types:
            seconds, size = downloads[form_type]
            template = Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
            self.stdout.write(
                f"{form_type:<16}{checks[form_type]:>9.2f}{seconds:>12.2f}"
                f"{size / 1024:>9.0f}{template.stat().st_size / 1024:>13.0f}"
            )
        slowest = max(downloads, key=lambda form_type: downloads[form_type][0])
        self.stdout.write(
            f"Generate All: {generate_all:.2f} s (budget {options['budget_generate']:g} s)\n"
            f"Downloads: {sum(s for s, _ in downloads.values()):.2f} s in all; the slowest, "
            f"{slowest}, {downloads[slowest][0]:.2f} s (budget {options['budget_download']:g} s each)"
        )

        missed = []
        if generate_all > options["budget_generate"]:
            missed.append(
                f"Generate All took {generate_all:.2f} s, over its "
                f"{options['budget_generate']:g} s budget"
            )
        missed += [
            f"the download of {form_type} took {seconds:.2f} s, over its "
            f"{options['budget_download']:g} s budget"
            for form_type, (seconds, _) in downloads.items()
            if seconds > options["budget_download"]
        ]
        if missed:
            raise CommandError("; ".join(missed) + ".")
```

The command runs the views' own helpers inside one transaction that it rolls back: Generate All's preparation and each packet form's check and store, each in a savepoint, then each form's download (prepare, resolve, draw). `requires_system_checks = []` keeps every cache cold, as on a dyno's first request after waking. It prints one row per form and the totals, then fails naming every budget missed. A refusal, of the whole session or of one form, fails it naming only the exception's type.

- [ ] **Step 9: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_form_views.py apps/forms/tests/test_download_action.py apps/forms/tests/test_api_readback.py apps/forms/tests/test_check.py apps/forms/tests/test_pdf_filler.py apps/forms/tests/test_time_packet.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `159 passed`.

That is the six files: `test_form_views.py` 57, `test_download_action.py` 13, `test_api_readback.py` 6, `test_check.py` 38, `test_pdf_filler.py` 41 and `test_time_packet.py` 4.

- [ ] **Step 10: Watch the timing test fail when a download only checks**

```bash
set -eo pipefail
cp backend/apps/forms/management/commands/time_packet.py backend/apps/forms/management/commands/time_packet.py.keep
trap 'mv backend/apps/forms/management/commands/time_packet.py.keep backend/apps/forms/management/commands/time_packet.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/management/commands/time_packet.py b/backend/apps/forms/management/commands/time_packet.py
--- a/backend/apps/forms/management/commands/time_packet.py
+++ b/backend/apps/forms/management/commands/time_packet.py
@@ -68,7 +68,7 @@
                 form_started = time.perf_counter()
                 try:
                     _prepare(session)
-                    pdf = PDFFormFiller().fill(form_type, _resolve(form_type, session))
+                    pdf = PDFFormFiller().check(form_type, _resolve(form_type, session))
                 except Exception as exc:
                     raise CommandError(f"{form_type} was refused: {type(exc).__name__}") from exc
                 downloads[form_type] = (time.perf_counter() - form_started, len(pdf))
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_time_packet.py::test_time_packet_writes_nothing -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_time_packet_writes_nothing - assert False`.

Here each download only checks the form. `check()` returns a tuple of planned parts, whose length, 1, prints as 0 KB, so the test's "every PDF above 0 KB" fails (review finding 1). The block restores `time_packet.py` from the copy it kept, pass or fail; each mutation block below does the same with its file.

- [ ] **Step 11: Watch the Generate tests fail when Generate stores without checking**

```bash
set -eo pipefail
cp backend/apps/forms/views.py backend/apps/forms/views.py.keep
trap 'mv backend/apps/forms/views.py.keep backend/apps/forms/views.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -209,7 +209,6 @@
     if GeneratedForm.objects.filter(session=session, form_type=form_type, status="filed").exists():
         raise FormIsFiled()
     document = _resolve(form_type, session)
-    PDFFormFiller().check(form_type, document)
     generated_form, _ = GeneratedForm.objects.get_or_create(
         session=session, form_type=form_type, defaults={"generated_by": user}
     )
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_form_views.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `6 failed, 51 passed`, with `assert 200 == 500` and `assert 200 == 422`.

Here `_generate_and_persist` stores the document without checking it. The five retargeted Generate tests (their patched `check()` is never called) and the letter test all get a 200 where they want a refusal.

- [ ] **Step 12: Watch the pre-3a2 download fail when every dict is read as parts**

```bash
set -eo pipefail
cp backend/apps/forms/services/pdf_filler.py backend/apps/forms/services/pdf_filler.py.keep
trap 'mv backend/apps/forms/services/pdf_filler.py.keep backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -138,7 +138,7 @@
     The parts a form's values hold: a parts document's own, {"version": 2, "parts": [...]}
     (spec §6), or any other dict, such as a form filed before 3a2, as one form part.
     """
-    if values.get("version") == 2:
+    if True:
         return values["parts"]
     return [{"kind": "form", "values": values}]

PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_download_action.py::test_a_form_filed_before_3a2_still_downloads -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_a_form_filed_before_3a2_still_downloads - pymupdf.FileDataError: Failed to open stream`.

Here `parts_of` reads every dict as a parts document. A row stored before 3a2 has no `parts`, so its download is a 500, and the test's read-back can't open the reply as a PDF.

- [ ] **Step 13: Watch a filed form's refusal fail when it keeps its step**

```bash
set -eo pipefail
cp backend/apps/forms/views.py backend/apps/forms/views.py.keep
trap 'mv backend/apps/forms/views.py.keep backend/apps/forms/views.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -477,8 +477,7 @@
             body, code = _failure(form_type, exc)
             if filed:
                 # No step or page changes the values a form was filed with (R46).
-                body.pop("step", None)
-                body.pop("page", None)
+                pass
             return Response(body, status=code)

         if generated_form.status == "generated":
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_download_action.py::test_a_filed_form_whose_values_cannot_print_is_refused_without_a_step_or_page -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `AssertionError: assert {'error': 'Th...'debtor_info'}`.

Here a filed form's refusal keeps the `step` its binding names, and the filer would be sent to a step that can't change what was filed (R46).

- [ ] **Step 14: Say in the docs what Generate and Download do, and how to time a packet before deploying**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 29aab59..9ae6cc6 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -29,16 +29,16 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. It reads the median table in force on today's real date, not the tests' pinned one, and when none is (from November 1, 2026 until the November table is loaded) it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, so even `--reset` leaves the existing personas. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
 - **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
 - **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so are income not entered by source (`IncomeNotSplit`), no median table in force on the fill date (`NoTableInForce`, which logs the table, the date and the district), and a letter the form's font can't print (`UnprintableLetter`) or a value too long for its box even at 6 pt (`ValueTooLong`), whose sentences name the box; any other failure is a 500 logged by exception type only.
-- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), an Expenses step never saved (no `ExpenseInfo` row), and a scanned debt the filer hasn't confirmed (a `DebtInfo` with `is_draft`, step `debts`; see "Document upload sits mid-wizard"). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`), `IntakeNotFinished.page` (`/intake`) and the `step` or `page` of an `UnprintableLetter` or `ValueTooLong`, from the binding that feeds the box (`fix_for` in `fill_resolver.py`); "already filed", "not in your packet" and `NoTableInForce` carry neither, and the key is absent, never null. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must lock the session first (see "Saves lock the session") and call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
+- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), an Expenses step never saved (no `ExpenseInfo` row), and a scanned debt the filer hasn't confirmed (a `DebtInfo` with `is_draft`, step `debts`; see "Document upload sits mid-wizard"). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`), `IntakeNotFinished.page` (`/intake`) and the `step` or `page` of an `UnprintableLetter` or `ValueTooLong`, from the binding that feeds the box (`fix_for` in `fill_resolver.py`); "already filed", "not in your packet", `NoTableInForce` and the download of a filed form whose stored values `check()` refuses carry neither, and the key is absent, never null. The check lives in the views, not in `build_parts` or `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must lock the session first (see "Saves lock the session") and call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
-- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
+- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. Generate, Generate All and Regenerate check without drawing: each resolves the form's parts (`build_parts`), runs `PDFFormFiller.check()` and stores them, so a letter the form can't print or a value too long for its box is a 422, or a Generate All `errors` entry, carrying its `step` or `page`. Download draws: `fill()` bakes with PyMuPDF, which isn't thread-safe, so the server stays on sync gunicorn workers with no `--threads` unless the bake gets a lock. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download draws its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
 - **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. Tiers 1 and 3 read the printed page, not `/V`: `read_drawn` (`apps/forms/tests/pdf_readback.py`) takes a widget's Helvetica text and the template's ZapfDingbats check mark inside its rect, and reads `""` where a box prints only the blank template's own default (the district combos' placeholder, A/B `19.1`–`19.3 % of ownership` "0%", C `page 2` and G `fill 2.6` "2"), so a blank assertion on such a box can't see that default. `read_drawn` refuses a PDF that still has a widget (a `ValueError`, never a listed defect), so it reads only `fill()`'s baked output. The list has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
 - **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, the one function behind all of them; any other error fails the form). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine (`repeat`, `RepeatOverflow` and its 422) stays for later steps; only synthetic tests reach it.
-- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, and the API never returns it. `form_data` is blank; its column is dropped one release after this code is live. A filed form downloads its stored `field_values`; an unfiled one is resolved fresh on every download.
+- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, a parts document in printing order: `{"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}` (`registry.build_parts`). The API never returns it. `form_data` is blank; its column is dropped one release after this code is live. Generate, Generate All and Regenerate store the document they checked; an unfiled form is resolved, checked and drawn fresh on every download, and its document stored again. A filed form draws its stored document, so it prints exactly what was filed. A form filed before forms step 3a2 holds `{full name: value}` with no `version`, which `parts_of` (`pdf_filler.py`) reads as one form part. A filed form whose stored values `check()` refuses downloads as a 422 with the refusal's sentence and no `step` or `page`, since no step changes what was filed.
 - **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
 - **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
 - **CI ruff is pinned** — `ci.yml` installs `ruff==0.8.5`. Unpinned ruff broke CI when new rules shipped.
@@ -84,7 +84,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.

 - **Backend:** Django 5.0 + DRF, Python 3.11, PostgreSQL 15, `encrypted-model-fields` (Fernet PII encryption)
 - **Frontend:** React 19 + Vite 7 + TypeScript, Context API (not Redux), react-router-dom v7
-- **PDF:** pypdf and PyMuPDF draw on the official AO court templates. Each schema in `data/forms/schemas/` binds a field to a widget's full name in the field index (`data/forms/field_index/<template stem>.index.json`). `build_field_values(form_type, session)` checks the form's preconditions and resolves its schema; `PDFFormFiller().check(form_type, values)` plans the widgets each key names (a full name, or `<full name>@<page>:<tag>` for one widget) in the template from `data/forms/pdfs/`, and raises `UnknownField` for any other name; `fill()` runs it, then pypdf builds each planned widget's own appearance and PyMuPDF bakes every remaining widget into the page (the print buttons and the second widget of each stacked pair are removed first), so the PDF it returns can't be filled in a viewer.
+- **PDF:** pypdf and PyMuPDF draw on the official AO court templates. Each schema in `data/forms/schemas/` binds a field to a widget's full name in the field index (`data/forms/field_index/<template stem>.index.json`). `build_parts(form_type, session)`, which the views call, checks the form's preconditions and resolves its schema into the parts document `field_values` stores (`build_field_values` returns the form's `{key: value}` instead); `PDFFormFiller().check(form_type, values)` plans the widgets each key names (a full name, or `<full name>@<page>:<tag>` for one widget) in the template from `data/forms/pdfs/`, and raises `UnknownField` for any other name; `fill()` runs it, then pypdf builds each planned widget's own appearance and PyMuPDF bakes every remaining widget into the page (the print buttons and the second widget of each stacked pair are removed first), so the PDF it returns can't be filled in a viewer.
 - **PDF templates:** 67 official AO court PDFs in `data/forms/pdfs/` (committed). Baked into Heroku image.
 - **Forms:** 17 form types in `apps/forms/registry.py` (`FORM_REGISTRY` / `get_all_form_types()` / `packet(session)`). `generate_all` gives each form its own savepoint.
 - **OCR service:** provider-agnostic. `OCR_PROVIDER` selects `openai` (default, `gpt-4o`, `OPENAI_API_KEY`) or `gemini` (`gemini-2.0-flash`, `GEMINI_API_KEY`); `OCR_MODEL` overrides the model so a model change is a config var, not a deploy. No local model — both call a hosted API directly.
@@ -102,7 +102,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - `apps/intake/management/commands/seed_demo_data.py` — 6 AI personas
 - `apps/eligibility/services/means_test_calculator.py` — `MeansTestCalculator`, which runs and saves `MeansTest.calculate()` (`apps/eligibility/models.py`, where CMI is annualized)
 - `apps/eligibility/cmi.py` — `current_monthly_income` (the one CMI), `IncomeNotSplit`, `is_above_median`
-- `apps/forms/registry.py` — `FORM_REGISTRY` (17 form_type → `PacketForm(applies, requires)`) in filing order, `packet()`, `build_field_values()`
+- `apps/forms/registry.py` — `FORM_REGISTRY` (17 form_type → `PacketForm(applies, requires)`) in filing order, `packet()`, `build_parts()`, `build_field_values()`
 - `apps/forms/services/` — `pdf_filler.py` (`PDFFormFiller`: `check()` plans, `fill()` draws and bakes), `widgets.py` (each template widget by page and tag), `text_fit.py` (letters and fit, as pypdf lays text out), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
 - `apps/forms/field_index.py` + `apps/forms/checks.py` — the field index loader and the schema system check
 - `apps/forms/views.py` — GeneratedFormViewSet (generate, generate_all, download, mark_filed)
diff --git a/docs/security/deployment.md b/docs/security/deployment.md
index 9b8685f..c7e9b03 100644
--- a/docs/security/deployment.md
+++ b/docs/security/deployment.md
@@ -42,6 +42,13 @@ Before deploying to production, complete this checklist:
 - [ ] DDoS protection enabled
 - [ ] WAF configured (if available)

+### Forms step 3: before deploying
+
+- [ ] Run `python manage.py loaddata ilnd_2025_data` right after the release: the districts migration 0003 ends production's existing median row on 2026-03-31.
+- [ ] Reseed the personas with `python manage.py seed_demo_data --reset`.
+- [ ] Count the completed sessions that still hold a draft debt: their forms now leave it off.
+- [ ] Run `python manage.py time_packet --session <id> --budget-generate 15 --budget-download 15` on the Eco dyno for one persona's session. It times Generate All and each download and writes nothing; a missed budget fails the command and names it.
+
 ## Django Settings for Production

 ### Security Settings
PATCH
```

In `CLAUDE.md`:

- "Forms need a completed intake" counts a filed form's refused download among the refusals with no `step` or `page`, and says the completion check lives in the views, not in `build_parts` or `build_field_values`.
- "GenerateAll vs single" says Generate, Generate All and Regenerate check without drawing, and that Download draws with PyMuPDF, which isn't thread-safe, so the server stays on sync gunicorn workers with no `--threads` unless the bake gets a lock (R47).
- "`field_values`, not `form_data`" describes the parts document, the filed redraw, the shape stored before 3a2 and R46's refusal.
- The Architecture's **PDF:** line and the File Map name `build_parts`, which the views call.

`docs/security/deployment.md` gains "Forms step 3: before deploying" after "Security", with tasks.md's four items. The first says the districts migration 0003 ends production's existing median row on 2026-03-31 (the implementer's wording, from PR #26's checklist). The last runs `time_packet` on the Eco dyno with 15 s budgets, half of Heroku's 30 s router timeout.

- [ ] **Step 15: Run every gate**

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

Expected: `2698 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  397 passed (397)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

That is 8 more backend cases than after Task 4: `test_time_packet.py`'s 4, three new tests in `test_download_action.py` (the pre-3a2 download is a rename), and in `test_form_views.py` two new tests less the dropped `template_has_no_form` case. No frontend file changes. Under a heavy load (1-minute load above 15) a SOFAStep or FormDashboard test can run past vitest's 5 s per-test timeout; run vitest again on a quieter machine before suspecting the code. The 25 skips are the Postgres-only tests under sqlite. The next command runs them against the Postgres database named by `DATABASE_URL` in `.claude/forms-step3a2.env`, as CI's "Run the Postgres-only tests" step does.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

This task touches no locking, so they pass unchanged.

- [ ] **Step 16: Time the six personas' packets**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
export DJANGO_SETTINGS_MODULE=config.settings.development
(
  cd backend
  $PY manage.py migrate -v 0
  $PY manage.py loaddata ilnd_2025_data -v 0
  $PY manage.py seed_demo_data --reset | sed '/password/d'
  for persona in maria james priya deshawn sarah andres; do
    if pgrep -fl '[p]ytest|[s]ection_check|[p]laywright|[t]ime_options'; then
      echo "Another run is alive (listed above): wait for it to end, then run this step again." >&2
      exit 1
    fi
    id=$($PY manage.py shell -c "from apps.intake.models import IntakeSession; print(IntakeSession.objects.filter(user__username='demo_$persona').latest('id').id)")
    echo "== $persona, session $id; load: $(uptime | sed 's/.*load averages*: //')"
    $PY manage.py time_packet --session $id
  done
)
echo "All six personas' packets held their budgets."
```

Expected: six tables, each followed by a `Generate All:` line and a `Downloads:` line, then `All six personas' packets held their budgets.`

The timing numbers vary with the machine, so nothing above names one. A missed budget, or a refusal, ends the step at that persona with a line starting `CommandError:` that names the budget missed or the exception's type. The spec's rule is that a miss stops the build and goes back to the owner, and the budget is not moved; a miss on a busy machine is first run again on a quiet one.

How the step runs:

- **The development database.** It migrates, loads the district data and reseeds the six personas, as `.claude/e2e.sh` does, with `config.settings.development` and the `DATABASE_URL` the env file names. The seed's lines that print each persona's demo password are dropped.
- **One persona at a time, each in a fresh process,** so each run meets cold caches. The session id is the persona user's (`demo_maria` … `demo_andres`) newest session.
- **A quiet machine.** Before each run, `pgrep` must find no test run, checker, Playwright or other timing run alive (tasks.md's rule); otherwise the step stops and says so. The brackets in the pattern keep it from matching a shell whose own command line holds the pattern (macOS's `pgrep` skips its own ancestors, Linux's doesn't). Each persona's line prints the load averages for the record.
- **The real date.** `seed_demo_data` reads the median table in force on today's date. From November 1, 2026 until the November table is loaded, it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, and each `time_packet` run fails with `The session was refused: NoTableInForce`.

The implementer's run, measured on this task's code after `seed_demo_data --reset`, each persona in a fresh process with nothing else running (a 1-minute load of 3.9 to 4.7, from other desktop processes):

- Maria, 15 forms: Generate All 2.57 s; slowest download Form 107, 1.28 s; all downloads 5.54 s.
- James, 14 forms: 2.32 s; Form 107, 1.33 s; 5.49 s.
- Priya, 15 forms (the packet with 122A-2): 2.93 s; Form 107, 1.20 s; 5.70 s.
- DeShawn, 15 forms: 2.54 s; Form 107, 1.17 s; 5.32 s.
- Sarah, 15 forms: 2.45 s; Form 107, 1.17 s; 5.33 s.
- Andrés, 14 forms: 2.46 s; Form 107, 1.13 s; 5.00 s.

Every budget held (5 s for Generate All, 3 s for each download), so R51(b)'s parsed-template clone was not taken. These are measurements, not expectations.

- [ ] **Step 17: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 8 passed` and `RUN 2 exit=0: 8 passed`.

Five persona journeys and the SOFA journey press Generate All, which now only checks, and the SOFA journey downloads Form 107, which draws.

These results are the implementer's; this plan's own check doesn't run the journeys. They ran on the task's first commit, 2db99c0, and printed `RUN 1 exit=0: 8 passed (58.7s)` and `RUN 2 exit=0: 8 passed (55.9s)`. The tree committed below differs from it in the Generate All letter test's assertions and in the fix round's changes: the whole-session refusal in `time_packet`, docstrings, `CLAUDE.md` and tests. None of that is on a journey's path, and the journeys were not run again.

- [ ] **Step 18: Commit**

The message is the verified commit's, less one sentence. It claimed that only development and test databases can hold a filed form `check()` refuses, but `main`, which self-hosters run, can too (R73).

```bash
set -eo pipefail
git add \
  backend/apps/forms/management/commands/time_packet.py \
  backend/apps/forms/tests/test_time_packet.py \
  CLAUDE.md \
  backend/apps/forms/models.py \
  backend/apps/forms/registry.py \
  backend/apps/forms/services/__init__.py \
  backend/apps/forms/services/fill_resolver.py \
  backend/apps/forms/services/pdf_filler.py \
  backend/apps/forms/services/text_fit.py \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_check.py \
  backend/apps/forms/tests/test_download_action.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/tests/test_pdf_filler.py \
  backend/apps/forms/views.py \
  docs/security/deployment.md
git commit -F - <<'MSG'
feat(forms): check on Generate, draw on Download, store values as parts

Generate, Generate All and Regenerate drew every form only to throw the
PDF away, and drawing takes most of a form's time. They now resolve the
form's values, run check() and store them, without drawing; a letter the
form can't print or a value too long for its box is still a 422, or a
Generate All errors entry, with the step or page that fixes it. Download
draws: an unfiled form is resolved, checked and drawn fresh and its
values stored again; a filed form draws the values it was filed with.

- GeneratedForm.field_values now holds a parts document,
  {"version": 2, "parts": [{"kind": "form", "values": {...}}]}, built by
  registry.build_parts() through fill_resolver.resolve_parts().
  build_field_values() still returns the form's {key: value}.
  pdf_filler.parts_of() reads either shape, so check() and fill() take a
  parts document or a plain {key: value}, and a form filed before 3a2,
  stored as {full name: value}, still downloads.
- A filed form whose stored values check() refuses downloads as a 422
  with the refusal's sentence and no step or page, since no step
  changes what was filed.
- python manage.py time_packet --session <id> times one session's
  Generate All (its preparation and each form's check and store) and
  each form's download (preparation, resolve and draw), in a fresh
  process with every cache cold, as a dyno meets its first request
  after waking: it runs no system checks, which would build every
  template's widget map first. It prints each form's times and its PDF's
  size beside its template's, writes nothing (one transaction, rolled
  back), and fails naming any budget it missed (5 s for Generate All,
  3 s for each download by default). A refusal, of the whole session
  or of one form, fails it with a CommandError naming only the
  exception's type, since a refusal's sentence can quote the filer's
  letter.
- text_fit builds pypdf's typographic maps once per font, cached by
  template filename and font name beside font_for (reverse_cmap_for):
  pypdf builds them again on every call, which was most of check()'s
  time on a long value. fit() now takes the template filename and
  looks up the box's font and map itself; wrap() takes the map.

time_packet on the six seeded personas, after seed_demo_data --reset,
each in a fresh process with no other test run alive (1-minute load
3.9 to 4.7 from other desktop processes):

  persona   forms  Generate All  slowest download   all downloads
  Maria       15      2.57 s     form_107 1.28 s       5.54 s
  James       14      2.32 s     form_107 1.33 s       5.49 s
  Priya       15      2.93 s     form_107 1.20 s       5.70 s
  DeShawn     15      2.54 s     form_107 1.17 s       5.32 s
  Sarah       15      2.45 s     form_107 1.17 s       5.33 s
  Andrés      14      2.46 s     form_107 1.13 s       5.00 s

Every budget holds, so fill() still clones each template from its file
rather than from a reader parsed once. A drawn form is 1.05 to 2.2
times its template's size (Form 107: 793 KB against 378 KB; a packet:
4.7 to 5.2 MB against 2.8 to 3.2 MB), since fill() keeps tobytes()
without garbage collection; the spec sets no size limit.

The backend suite (pytest with coverage, nothing else running) took
621 s before the map cache, at a 1-minute load near 6, and 575 s after
it, near 3.3; the load comes from other desktop processes, so the pair
mixes the cache with the machine. In one process, interleaved, the
cut-off test on Form 107 and A/B took 24.0 and 23.9 s with the cache
against 35.1 and 33.9 s with pypdf's maps rebuilt on every call.

The Generate tests that patched fill() patch check(), which Generate
now calls, and keep what each proved. TemplateHasNoForm is raised only
while drawing, so a template with no form is explained through Download
alone. The download, Generate All,
Regenerate and read-back tests read the stored parts document; the
read-back compares it with build_parts().

New tests: Generate, Generate All and Regenerate never call fill();
a surname with ą is refused through Generate, Generate All and
Regenerate with its step, and nothing is stored; a filed form downloads
exactly what was filed, stored as the parts document with its version
and kind, and one filed before 3a2 still downloads; a filed form whose
values can't print is refused without a step or page; time_packet
draws every form of the packet (each PDF's size above 0 KB) and writes
nothing, refuses an unfinished intake as a whole, keeps a refused
letter out of its message and writes nothing, and names a missed
budget; the pinned font test checks the cached map is pypdf's.

docs/security/deployment.md gains "Forms step 3: before deploying",
with 3a1's three steps and time_packet on the Eco dyno. CLAUDE.md's
"GenerateAll vs single" says Generate checks, Download draws, and the
server stays on sync workers since PyMuPDF isn't thread-safe;
"field_values, not form_data" describes the parts document, the filed
redraw and the shape stored before 3a2; "Forms need a completed
intake" counts a filed form's refused download among the refusals
with no step or page. CLAUDE.md, the registry and the services package
name build_parts() as the path the views take, beside
build_field_values().

Refs DIG-137
MSG
git status --short
```

### Task 6: Continuation copies

_Built and verified as commit `cc9e5f2` on `plan/forms-step3a2`._

**Files:**

- Create: `backend/apps/forms/tests/test_continuation_copies.py`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/schema.py`
- Modify: `backend/apps/forms/services/fill_resolver.py`
- Modify: `backend/apps/forms/services/pdf_filler.py`
- Modify: `backend/apps/forms/services/widgets.py`
- Modify: `backend/apps/forms/tests/conftest.py`
- Modify: `backend/apps/forms/tests/pdf_readback.py`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_checks.py`
- Modify: `backend/apps/forms/tests/test_download_action.py`
- Modify: `backend/apps/forms/tests/test_fill_resolver.py`
- Modify: `backend/apps/forms/views.py`

**Interfaces:**

- Consumes:
  - From Task 1, `backend/apps/forms/services/widgets.py`: `TemplateWidget` (`full_name`, `page`, `tag`, `kind`, `states`, the property `drawn`), `template_widgets(template_filename: str) -> tuple[TemplateWidget, ...]` (`@lru_cache`, ordered by page then tag), `parse_key(key: str) -> tuple[str, int | None, str | None]` (a malformed key raises `ValueError`) and `widget_for(template_filename, page, annotation, page_top) -> TemplateWidget`.
  - From Tasks 2 and 5, `backend/apps/forms/services/pdf_filler.py`:
    - `PDFFormFiller.check(self, form_type: str, values: dict) -> tuple[PlannedPart, ...]`, which plans every part of `parts_of(values)` as the form's own pages through `_plan(self, form_type: str, values: dict) -> tuple[Planned, ...]`;
    - `Planned` (`widget`, `value`, `size`), `PlannedPart` (`part`, `widgets`), `_draw(writer, page, acro_form, annotation, planned)`;
    - `UnknownField`, `UnprintableLetter` and `ValueTooLong` (each with `step` and `page`), and `TemplateHasNoForm(form_type)`.
  - From Task 3, `PDFFormFiller.fill(self, form_type: str, values: dict) -> bytes`, which since Task 5 keys every part's planned widgets by (page, tag) in one dict and draws them on one clone (review finding 6 of Task 5, parked for this task).
  - From Tasks 3 and 4, `backend/apps/forms/tests/pdf_readback.py`: `DrawnWidget(full_name, page, tag, value, state)` and `read_drawn(form_type: str, pdf_bytes: bytes) -> list[DrawnWidget]`, which refuses a PDF that still has a widget (R49), and its helpers `_characters`, `_text`, `_inside` and `_blank`.
  - From Task 5: `resolve_parts(schema: FormSchema, session: IntakeSession) -> dict` (one form part around `resolve()`), `registry.build_parts(form_type: str, session: IntakeSession) -> dict` and `parts_of(values: dict) -> list[dict]`.
  - In `backend/apps/forms/schema.py`: `FieldSpec` (`pdf_field`, `type`, `source`, `page`, `binding`, `repeat`, `repeat_capacity`, `row`, `legal_review`, `conditional_on`, `choices`, `tag`), `FormSchema(form_type, template_filename, template_version, fields)`, `load_schema(form_type: str) -> FormSchema` (`@lru_cache`) and `validate_schema(schema: FormSchema, derivations: set[str], predicates: set[str]) -> list[tuple[str, str]]`, which `apps/forms/checks.py` turns into `forms.E001`–`E007`.
  - In `backend/apps/forms/services/fill_resolver.py`: `RepeatOverflow` (removed here), `resolve(schema, session) -> dict[str, str]`, `resolve_binding(binding: str, session) -> str | list[str]`, `_section_applies`, `_scalar_value`, `_key(field) -> str`, `_unmapped(field) -> bool` (a box whose `choices` is `{}`) and `_emit(field, value) -> str | None`.
  - In `backend/apps/forms/views.py`: `_FAILURE_SENTENCES`, which maps `RepeatOverflow` to a 422 sentence before this task.
  - For the tests: `test_checks.py`'s `schema_copy` fixture and its `_edit`, `_errors`, `_ids`, `_field`, `_text` and `_row` helpers; `test_fill_resolver.py`'s `session`, `_field` and `_schema`; `test_download_action.py`'s `_download` and `_rename_filer`; `apps/forms/tests/conftest.py`'s `api_client_authed` and `generated_form_factory` (a Form 121 row for Maria Torres's completed intake in the Northern District of Illinois); the `SOFAReport` and `SOFACreditorPayment` models.
- Produces:
  - In `schema.py`: `@dataclass(frozen=True) class PageNumberBoxes` (`page: int`, `this: str | None`, `of: str | None`); `@dataclass(frozen=True) class GroupSpec` (`name: str`, `extra_page: int | None`, `number: str | None`, `number_boxes: dict[int, str]`, `page_numbers: tuple[PageNumberBoxes, ...]`); `FormSchema.groups: dict[str, GroupSpec] = field(default_factory=dict)`, read by `load_schema` from a schema's top-level `"groups"`, `{"<group>": {"extra_page": int, "number": "2.{n}", "number_boxes": {"<slot row>": "<key>"}, "page_numbers": [{"page": int, "this": "<key>" or null, "of": "<key>" or null}]}}`, with the `number_boxes` rows turned into ints. `validate_schema` gains the group rules below and the helpers `_pages_drawn(name, drawn) -> list[int]` and `_drawn_on(key, page, drawn) -> bool`.
  - In `widgets.py`: `page_count(template_filename: str) -> int`, `@lru_cache(maxsize=32)`, keyed by template filename (G11).
  - In `fill_resolver.py`: `resolve_parts(schema, session) -> dict` returns `{"version": 2, "parts": [{"kind": "form", "values": {...}}, *copies]}`, each copy `{"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}}`. `resolve(schema, session)` returns the form part's values, so `build_field_values` keeps its shape. New private helpers: `_cell`, `_number_page`, `_headers` and `_copies`. `RepeatOverflow` is gone.
  - In `pdf_filler.py`: `check()` plans a `copy` part only against the widgets on its `page` (`_plan(self, form_type: str, values: dict, page: int | None = None)`) and raises `ValueError` for a part of any kind but `form` and `copy`. `fill()` draws each copy alone and inserts it after its extra page or the copy before, through the new `_clone(form_type: str, template: str) -> pypdf.PdfWriter` and `_baked(writer, template, widgets: tuple[Planned, ...], only: int | None = None) -> pymupdf.Document`.
  - In `pdf_readback.py`: `read_drawn(form_type: str, pdf_bytes: bytes, parts: list[dict] | None = None) -> list[DrawnWidget]`; `DrawnWidget.copy: int | None = None`, the last field (`None` on the form's own pages). It raises `ValueError` when the PDF's page count isn't the template's plus its copies', also with no `parts`.
  - In `apps/forms/tests/conftest.py`:`_schedule_d_with_group(tmp_path, settings, group, rows, declaration)`; the fixtures `schedule_d_with_copies` (group `d_part_1`) and `schedule_d_part_2_with_copies` (group `d_part_2`), each yielding the schemas directory; and `creditor_payments`, which returns `add(session, count) -> list[SOFACreditorPayment]`.
  - `views.py` loses `RepeatOverflow` and its sentence.
  - New tests: `test_continuation_copies.py`'s eleven cases; in `test_checks.py`, `test_an_untagged_binding_on_a_page_without_its_widget_is_reported`, `test_an_untagged_slot_whose_name_is_drawn_twice_on_its_page_is_reported`, `test_a_group_continued_on_copies_of_its_extra_page_passes`, `test_a_repeat_group_whose_rows_cannot_continue_is_reported` (14 cases), `test_a_repeat_group_whose_capacity_isnt_its_slots_is_reported` (4), `test_a_repeat_group_whose_rows_sit_on_the_wrong_pages_is_reported` (5), `test_a_group_box_that_another_writer_fills_is_reported` (4), `test_a_page_count_box_drawn_on_two_pages_is_one_writer`, `test_an_untagged_group_key_drawn_on_other_pages_is_reported` (3), `test_an_untagged_box_slot_whose_boxes_share_a_state_is_reported`, `test_an_untagged_box_slot_whose_boxes_each_have_their_own_state_passes`, `test_a_second_group_continued_on_copies_is_reported` and `test_a_group_with_no_extra_page_is_not_counted_as_a_second`; in `test_fill_resolver.py`, `test_rows_past_the_slots_go_to_copies_of_the_extra_page` (was `test_repeat_overflow_raises`), `test_a_legal_review_row_prints_neither_in_the_slots_nor_on_a_copy`, `test_a_copy_never_repeats_a_row_from_the_form` and `test_rows_past_the_slots_of_a_group_with_no_extra_page_are_never_dropped`; in `test_download_action.py`, `test_rows_past_the_slots_download_on_a_copy` (was `test_too_many_rows_is_a_422`), `test_a_page_of_guarded_slots_still_takes_its_rows_on_a_copy` (2) and a `with a copy` case of `test_a_filed_form_downloads_exactly_what_was_filed`.
  - Where the commit differs from tasks.md: the table's T6 rows match, but tasks.md's text asks less of startup than the commit does. tasks.md says `extra_page` "must hold at least one of the group's slots"; the commit also requires it to be the page of the group's last slots, and adds every other group rule listed under the decisions below, from the review rounds (R56, R58, R59, R60). tasks.md lists only "Blank, not 0.00" for `CLAUDE.md`; the commit also updates "Schemas are checked at startup" and "`field_values`, not `form_data`". tasks.md says a copy is drawn by "clone the template, keep only that page, draw, remove, bake"; the commit draws the page on a full clone, then PyMuPDF keeps that page and bakes it (same result). The table doesn't name `page_count`, `_clone`, `_baked`, `_plan`'s `page`, the conftest fixtures or `read_drawn`'s page-count refusal.

**Decisions already made in this task:**

_What a group declares, and what startup refuses (spec §5.2; R21, R55, R56, R58, R59, R60):_

- **A group is a declaration in the schema, beside its bindings.** A schema's top-level `"groups"` gives each repeat group its `extra_page`, its entry `number` and `number_boxes`, and its `page_numbers` boxes, read into `GroupSpec` and `PageNumberBoxes`. The page-number boxes stay a declaration of the group and are filled only when the group has copies (R21). Task 7's sheet groups declare no `extra_page`.
- **Startup refuses every group declaration that would print a row wrong, rather than printing it wrong (R56, R58, R59, R60).** A schema author sees the refusal in `manage.py check` and the release, not a filer at Generate. No production schema has a group, so none of these rules can trip production: in every fix round, all 17 production schemas passed (`test_every_registered_form_passes`, 17 of 17, and `manage.py check`). The rules, and the defect each one prevents:
  - forms.E007, a repeat group that isn't declared in `groups`, or names no `extra_page`: its rows past the last slot would have nowhere to go. `resolve_parts` raises a `ValueError` for that case rather than drop a row (R55(4)), a 500 logged by type that startup makes unreachable.
  - E007, an `extra_page` that holds none of the group's slots, or isn't the page of its last slots (review finding 7). Copies of page 1 would print the rows past 2.5 before page 2's 2.3 to 2.5, and with no slot on the extra page a copy has nowhere to put a row (`range()` would step by 0, a 500).
  - E007, a `number` without `{n}` (also when `number_boxes` is declared with no `number`), one whose `format(n=1)` raises anything (`"2.{n}{m}"` a `KeyError`, `"2.{n}{n[0]}"` a `TypeError`), or one that prints the same for `n=1` and `n=2` (`"2.{{n}}"` prints `2.{n}` on every row). Each would be a 500 at Generate or the same number on every row (R58, R59(b)).
  - E007, fields of one group that carry more than one `repeat_capacity` or more than one `conditional_on` (R56): a group applies whole or not at all, and which capacity counted would depend on field order.
  - E007, slot rows (unmapped boxes aside) other than exactly 1 to `repeat_capacity` (defects B and C, review findings 3 and 4). A capacity below the slots printed a row twice, in its slot and again on a copy. One above them printed a row nowhere, silently; that one predates this task, and the first commit body wrongly claimed T6 had stopped it.
  - E007, a slot row whose mapped boxes sit on more than one page (R58): a copy takes a row's boxes from its own page only.
  - E007, rows that go back a page as the row number rises (R58). Rows 1–3 on page 2 and rows 4–5 on page 1 would print 4, 5, 1, 2, 3.
  - E007, an untagged slot binding that would print its row more than once (R59(c), replaced by R60). An untagged binding fills every drawn widget of its name, so a text or combo slot whose name has more than one drawn widget is refused, and so is a checkbox or radio slot whose drawn widgets share an on-state. Schedule I's `Assistance 8f` (two widgets on page 2) and Schedule D's `check 5` (four boxes on page 2, all `/On`) are refused. D's `check 4` (four boxes, four states) passes, since an answer ticks one box. Re-review 3 found that refusing every box with more than one drawn widget would refuse the right untagged spelling of such columns (230 sets of box twins in the templates, D's `check 2` to `check 4` among them). The binding's declared `type` picks the test, since E004 already refuses a type its widgets don't match.
  - E007, a second group with an `extra_page` on one form (defect A; the next bullet). A group with no `extra_page` doesn't count.
  - E003, a `number_boxes` row that isn't a slot row (review finding 9, which used to read "on page None"), and a number or page-number box that is no drawn widget on its row's page or its declared page (R55(3)), which would otherwise be an `UnknownField` 500 at Generate on a copy. A row's page is the page of its mapped boxes only (fix round 4, re-review 3's first Minor): an unmapped box prints nothing, and listed first it let a number box on the wrong page pass.
  - E003, an untagged number box or page-number `this` box whose name has more than one drawn widget, on its own page or another: it would print its number in each. D's page 2 draws `undefined_19` twice (T37 and T63), so the synthetic group tags both. A page count is the same on every page, so an untagged `of` box may print it in each of its widgets.
  - E003, for every binding in a group or not, an untagged binding whose `page` holds no drawn widget of its name (R58; re-review 1's S1 and S2). This task makes a binding's `page` decide which slots and cells a copy holds. In the re-review's probe a page typo dropped a claim of $800.00 from every copy while `check()` passed, and a typo the other way put a key with no widget on the copy's page, a 500 at Generate. Production had 605 fields and none off its page. A null `page` is refused here too, and the group rules skip it rather than compare it with a number (fix round 2: round 1's `max(pages)` crashed `manage.py check` with a `TypeError`).
  - E006 counts every key a group writes as a writer beside the bindings (R59; re-review 2's K1 and K2): each number box, each page-number `this` and each `of`, resolved to the widgets it names, tagged or not. A number box typed as row 3's amount box (K1) lost 300.00 and 600.00 from the page, and the tagged spelling of a bound widget (K2) passed a check of key equality. Two rows naming one number box conflict. One `of` key declared for two pages counts once, since a page count is the same on every page: E/F's `fill_27.1.7` on pages 5 and 6 passes.
- **Every key a group writes has a guard** (fix round 3's table, as fix round 4 left it):
  - a slot cell, tagged: E003's full-name and (page, tag) checks, one page per row, rows in page order, and E006;
  - a slot cell, untagged: E003's full-name and page checks, the twin rule, one page per row, rows in page order, and E006;
  - a number box: E003's slot-row check and its check on the row's mapped page, the untagged multi-widget rule, and E006 against bindings, other boxes and another row's box;
  - a page-number `this` box: E003 on its page, the untagged multi-widget rule, and E006, one writer per (group, page);
  - a page-number `of` box: E003 on its page, and E006, one writer per key;
  - a copy's header (another binding's key): that binding's own E003 checks and E006. A group's own keys never become headers, and `_headers` keeps a key only when it is drawn on the extra page.
    With the capacity, extra-page and page-order rules, every row of a group that applies goes to exactly one slot, on the form or on a copy, and no row lands on a page before an earlier row's. The commit body says so, and fix rounds 2 to 4 re-checked it against the code.
- **One extra-page group per form is 3a2's own limit, not the spec's, and 3c must lift it (R21 as amended by R56; defect A, review findings 1, 2 and 6).** Neither spec says it: spec §5.1 names E/F, with copies of pages 2 and 4, and §5.2 counts every copy. With two overflowing groups on one form, each page count counted one group's copies, copy numbers restarted for each group, and the later group overwrote the form's page-number boxes. Numbering pages across every group's copies goes beyond this task, so startup refuses a second group with an `extra_page` instead (fail loud). Before 3c binds E/F, it must remove the refusal and make page numbering count every group's copies.

_Copies (spec §5.2; R21, R24, R55):_

- **The resolver.** `resolve_parts` fills a group's slots in row order as before. The rows past the last slot go onto copy parts of the extra page: as many to a copy as that page has slot rows, in slot order, the last copy holding what's left. Copies are built after every form value is in, since they repeat its headers. `resolve()` returns the form part's values, so `build_field_values` carries the entry numbers and, with copies, the page numbers too (R55(5)).
- **Entry numbers** go in each slot that holds a row, on the form's own pages and on copies: `number.format(n=<the row's position in the whole group>)`. A slot with no row stays blank and unnumbered, on page 2 with three rows as on the last copy.
- **Page numbers only with a copy (R21).** With at least one copy, a page up to the extra page keeps its number, copy i is the extra page plus i, a later page moves down by the number of copies, and `of` is the template's page count plus the copies. `page_count` reads the template once (`lru_cache` keyed by template filename, G11), and only for a group that has copies and declares page numbers. With no copy, nothing changes (spec §5.2, "No overflow, no change").
- **A copy repeats the form's page headers and nothing else (R24, R55(2)).** It carries a form value whose full name is drawn on the extra page and on another page ("Debtor 1"), never one drawn on one page alone (page 2's total, `undefined_24`), and never a group's own key: a slot, a number box or a page-number box. Without that exclusion, D's `account number` (page 1 T32, page 3 T33) would carry the form's row into the last copy's empty slot, a row printed twice on a sworn form (`test_a_copy_never_repeats_a_row_from_the_form`). A tagged key rides along only when its widget is on the extra page. Where a "last page" total belongs once copies exist is 3c's call (R24).
- **`legal_review` decides which cells print, never which slots exist (R59(a); re-review 2's first Minor).** A copy takes its slot rows from the group's mapped fields on the extra page and its cells from the printed ones, as the form's own slots do. When every slot box on the extra page was `legal_review` and not asked, slots taken from the printed fields left a copy none, so `range()` stepped by 0: a 500 at Generate.
- **`RepeatOverflow` is gone** (spec §5.1), with its 422 sentence. The views' comment no longer says that the classes with fixed sentences have messages naming repeat groups.

_Checking and drawing (Task 5's finding 6; R54, R55):_

- **`check()` plans each part by its kind.** A `form` part plans every page, as before. A `copy` part plans only the widgets on its `page`, so a key with no widget there is `UnknownField`, DigniFi's defect. A part of any other kind raises `ValueError`, a 500 logged by type (R54, R55(4)). The test's unknown kind is "poster", so Task 7's "sheet" never collides with it.
- **`fill()` draws each copy alone and never merges it into the form (Task 5's finding 6).** The form's parts are drawn on one clone, as before. Each copy gets a clone of its own with only its page drawn; PyMuPDF's `select()` keeps that page, `bake()` follows, and `insert_pdf(start_at=…)` puts it right after the extra page or the copy before it. Task 5's `fill()` keyed every part's widgets by (page, tag) in one dict, so a copy's widget silently replaced the form's. `/AcroForm` is set to null once, at the end.
  - The implementer's probe found no MuPDF warning and no `/AcroForm` in a copy's catalog after `select()` and `bake()`, and found that `insert_pdf(start_at=<page count>)` appends, as a copy of a template's last page (C, G and H) needs.
  - Each copy costs a clone, a write and a bake. G14 covers the form's own pages, and tasks.md asks for one clone per copy. No production schema has a group, so no persona's packet pays it.
- **`read_drawn(form_type, pdf_bytes, parts)` reads each copy as the template page it copies.** `_pages` works out each output page's (template page, copy number) itself, not through `fill()`'s code: the template's pages in order, each copy after the last occurrence of its page. The blank form's baseline applies by template page. It refuses a PDF whose page count isn't the template's plus its copies', also with no `parts`, so a copy is never read as page 3 (`test_a_copy_is_never_read_as_another_page`).

_Owner questions, and what 3c must do first (R57, R61, finding 17):_

- **R57, an owner question and a named 3c prerequisite: entry number "2.10" doesn't fit Schedule D's `undefined_12@2:T3`, even at 6 pt.** The box is 15.60 pt wide, 11.60 pt usable. "2.9" fits at 8.0 pt; "2.10" at 6 pt is 11.676 pt. The `undefined_19` boxes (16.86 pt wide, 12.86 usable) fit "2.10" to "2.99" at 6.5 pt and refuse "2.100", and the page-number boxes fit "100" at 7 pt. On the synthetic D, 12 rows put "2.12" in copy 3's first slot. Generate and Download are then a 422 that quotes the box's internal index label, says "Shorten it" and names no step or page, which the filer can't act on (review finding 5, defect D). Each fix is someone else's call: a floor below 6 pt for numbers the engine makes changes the owner's Q2 answer, a different number layout changes what a sworn form shows, and a new refusal sentence is filer prose the spec lacks. It can't happen in 3a2, since only synthetic schemas have groups. **Real Schedule D must not be bound until the owner decides.** The fix round only made `creditor_payments` name a creditor for any count ("Creditor 10" on), so a test can reach 12 rows; no test pins the refusal.
- **R61(1), parked: an untagged box column whose boxes each have their own state, spread over more than one page.** Fix round 4 replaced round 3's "drawn on more than one page" condition rather than adding to it, so such a column passes startup, and one answer would tick one box, perhaps on a page other than the row's. No template has one: the implementer's probe over the 17 templates counted 0 such names, against 42 names drawn on several pages, 73 text or combo names with more than one drawn widget and 3 box names whose boxes share an on-state. A rule for it would be untestable dead code. If a template gains such a name, 3c restores the multi-page condition for boxes.
- **R61(3), RED2, a 3c prerequisite: nothing checks where a number box sits.** Two rows that swap number boxes pass startup, and page 2 then prints 2.5, 2.4, 2.3 from the top (its copy 2.8, 2.7, 2.6). It's new in this task, not pre-existing, so it has no Plane ticket. When 3c binds real groups, group boxes need an audit or tier 2 placement check, as bindings have.
- **Finding 17, parked: two parts of `_headers` have no test.** The tag condition (`tag is None or (at, tag) == (w.page, w.tag)`) and the lines that exclude number and page-number boxes (`own |= …`) can each be removed with every test green: D's real schema has no tagged key, and none of the synthetic group's number or page-number box names is drawn on more than one page. Neither changes anything in 3a2, and this plan's text reproduces both exactly.

_The tests the change breaks, and the new ones:_

- **The broken tests are fixed in this commit.**
  - The two E006 tests of a repeat group on Schedule I now declare their group (`_rows` adds `{"cp": {"extra_page": 2}}`). The one whose first row is untagged is refused by E007 as well, since page 2 draws `Assistance 8f` twice; it still asserts the E006 first, so it still proves that an untagged and a tagged row of one name conflict.
  - `test_repeat_overflow_raises` becomes `test_rows_past_the_slots_go_to_copies_of_the_extra_page`: made-up names on the Form 107 template (R18), four slots, two of them on the extra page, and seven rows give two copies, the last holding one row.
  - `test_too_many_rows_is_a_422` becomes `test_rows_past_the_slots_download_on_a_copy`: six rows download as a 200 whose stored parts hold the copy.
  - `test_push_button_binding_is_reported` now expects E003 with E004: a print button is never drawn, so its page holds no drawn widget of its name, as the tagged case already showed.
  - The "entry-number box for a row no slot has" case names `4_3@2:T13`, a drawn widget nothing else writes, since row 3's own box would now also be two writers (E006).
- **Synthetic schemas over the real templates (R18, R19, G11).** `_schedule_d_with_group` copies the real schemas into `tmp_path`, adds one group's fields to Schedule D with capacity equal to its rows, and points `FORM_SCHEMAS_DIRECTORY` there; both fixtures clear `load_schema`'s cache before and after. `schedule_d_with_copies` is tasks.md's `d_part_1`: `sofa.creditor_payments[].creditor_name` on `Creditors Name` to `Creditors Name_5` and `.total_paid` on `undefined`, `undefined_5`, `undefined_10`, `undefined_14` and `undefined_20`, rows 1–2 on page 1 and 3–5 on page 2, `extra_page` 2, `number` `"2.{n}"`, number boxes 3 → `undefined_12`, 4 → `undefined_19@2:T37`, 5 → `undefined_19@2:T63`, and the page-number boxes of pages 1 to 3 (`fill_27.0`; `fill_27.1.0` and `fill_27.1.1`; `fill_28.1.1` and `fill_28.1.2`). The review matched every one of these names, with its page and tag, against Schedule D's field index. `schedule_d_part_2_with_copies` puts one group on Part 2's six `Name` boxes on page 3, the template's last, as C, G and H continue theirs. The resolver tests build their `FormSchema`s by hand, mostly with made-up names (R18), and `validate_schema` never sees them.
- **The session** is `generated_form_factory().session`: a completed intake for Maria Torres in the Northern District of Illinois, whose real district the district box takes.
- **Cases beyond tasks.md's list:** two copies (nine rows), the only proof of copy numbering, of each copy following the one before and of each copy's own page number; three rows, the only proof that an empty slot isn't numbered; a copy of the template's last page; a letter refused on a copy, naming the SOFA page as on the form (`"Wąsowicz Credit"`, invented); a page of slots that are all `legal_review` (six and eight rows, Download); a copy that plans only its own page; and a part of a kind `check()` doesn't know.
- **`test_a_filed_form_downloads_exactly_what_was_filed` gains a `with a copy` case.** Both cases Regenerate, mark filed, rename the filer and delete the sixth row, so a fresh resolve would print three pages and no copy; the download is read through the filed parts. The stored document's shape is now asserted by its version and its parts' kinds, so `ANY` is gone.
- **`_comparable`'s docstring** no longer claims order-independence across parts (review finding 11): rows go to the form part and its copies by position.

_Review outcome:_

- **Five reviews.** The first found six Important findings, four distinct defects (A, two extra-page groups; B and C, a capacity below or above the slots; D, R57) and 11 Minors. R56 fixed A, B and C at startup and every Minor but 17. Re-review 1 found S1 and S2 (R58), re-review 2 K1, K2 and three Minors (R59), and re-review 3 approved with two Minors, the unmapped box's row page and the same-page twins, which a fresh implementer fixed (R60). Re-review 4 approved with no new findings.
- **The implementer's red proofs:** 61 mutations in six runners, every one red on the final commit. Steps 10 to 13 repeat four of them: Task 5's merge, and the three whose tests pass on the parent commit.

_Left as found:_

- **`data/forms/field_index/audit/form_107.audit.json`** still says, in four `produces` strings, that more than 3 rows raises `RepeatOverflow`. They record what the code did when the audit ran, and no code reads them.
- **`test_download_action.py`'s docstring** cites "spec §5.5", the forms-foundation spec, not 3a2's.
- **An untagged binding fills every drawn widget of its name**, as it has since before this task (`schema.py` says so beside `FieldSpec.tag`). For page headers that is the point; for slots, the twin rule above refuses it.
- **Frontend timing flakes under load (pre-existing).** During the first build's gates, at a 1-minute load near 16, one SOFAStep test ran past vitest's 5 s per-test timeout; alone it passed, and the whole suite then passed 397 of 397. No frontend file changes in this task.

- [ ] **Step 1: Write the tests**

```python file=backend/apps/forms/tests/test_continuation_copies.py
"""
Rows past a repeat group's last slot continue on copies of the page its schema names (3a2
spec §5.2): each copy is drawn alone and goes in right after that page, numbered as the
form asks. 3a2 proves it on a synthetic Schedule D group (§5.4; conftest's
schedule_d_with_copies): Part 1's rows 2.1 and 2.2 on page 1, then three rows on page 2.
"""

import pymupdf
import pytest

from apps.forms.registry import build_parts
from apps.forms.services.pdf_filler import PDFFormFiller, UnknownField, UnprintableLetter
from apps.forms.tests.pdf_readback import read_drawn

NAMES = [
    "Creditors Name",
    "Creditors Name_2",
    "Creditors Name_3",
    "Creditors Name_4",
    "Creditors Name_5",
]
AMOUNTS = ["undefined", "undefined_5", "undefined_10", "undefined_14", "undefined_20"]
ENTRY_NUMBERS = ("undefined_12", "undefined_19")  # page 2's three "2.__" boxes
PAGE_NUMBERS = {
    "fill_27.0": "of",  # page 1 prints "page 1 of ___"
    "fill_27.1.0": "this",
    "fill_27.1.1": "of",
    "fill_28.1.1": "this",
    "fill_28.1.2": "of",
}


@pytest.fixture
def session(generated_form_factory, schedule_d_with_copies):
    """Maria Torres's completed intake in the Northern District of Illinois."""
    return generated_form_factory().session


def _drawn(session):
    """Schedule D's parts for the session, its drawn PDF, and what each widget prints."""
    document = build_parts("schedule_d", session)
    pdf = PDFFormFiller().fill("schedule_d", document)
    return document["parts"], pdf, read_drawn("schedule_d", pdf, document["parts"])


def _printed(drawn, names):
    """(full name, copy) → what it prints, for boxes with one widget on their page."""
    return {(w.full_name, w.copy): w.value for w in drawn if w.full_name in names}


def _entries(drawn):
    """The entry-number boxes, in the order they print."""
    return [w.value for w in drawn if w.full_name in ENTRY_NUMBERS]


def _page_numbers(drawn):
    """Each printed page's page-number boxes, {"this": …, "of": …}, in the order they print."""
    pages = {}
    for w in drawn:
        if w.full_name in PAGE_NUMBERS:
            pages.setdefault((w.page, w.copy), {})[PAGE_NUMBERS[w.full_name]] = w.value
    return list(pages.values())


def test_extra_rows_print_on_copies_of_the_extra_page(session, creditor_payments):
    rows = creditor_payments(session, 6)

    parts, pdf, drawn = _drawn(session)

    assert [(part["kind"], part.get("page"), part.get("number")) for part in parts] == [
        ("form", None, None),
        ("copy", 2, 1),
    ]
    # Read from the pages themselves: the sixth row is on the third of four pages, right
    # after page 2, and Part 2's page comes last.
    pages = pymupdf.open("pdf", pdf)
    assert len(pages) == 4
    assert rows[5].creditor_name in pages[2].get_text()
    assert "Part 2:" in pages[3].get_text()
    assert "Part 2:" not in pages[2].get_text()
    # Rows 1-5 fill the form's own slots, page 2's included; row 6 fills the copy's first.
    names = [row.creditor_name for row in rows]
    assert _printed(drawn, NAMES) == {
        **{(box, None): names[n] for n, box in enumerate(NAMES)},
        ("Creditors Name_3", 1): names[5],
        ("Creditors Name_4", 1): "",
        ("Creditors Name_5", 1): "",
    }
    assert _printed(drawn, AMOUNTS) == {
        **{(box, None): f"{n}00.00" for n, box in enumerate(AMOUNTS, start=1)},
        ("undefined_10", 1): "600.00",
        ("undefined_14", 1): "",
        ("undefined_20", 1): "",
    }


def test_a_copy_repeats_the_page_header_but_not_the_page_total(session, creditor_payments):
    # The filer's name heads every page; page 2's total prints once (R24).
    creditor_payments(session, 6)

    _, _, drawn = _drawn(session)

    assert {(w.page, w.copy, w.value) for w in drawn if w.full_name == "Debtor 1"} == {
        (1, None, "Maria Torres"),
        (2, None, "Maria Torres"),
        (2, 1, "Maria Torres"),
        (3, None, "Maria Torres"),
    }
    assert _printed(drawn, ["undefined_24"]) == {
        ("undefined_24", None): "0.00",
        ("undefined_24", 1): "",
    }


@pytest.mark.parametrize(
    "count, copies, entries, page_numbers",
    [
        (
            6,
            [1],
            ["2.3", "2.4", "2.5", "2.6", "", ""],
            [
                {"of": "4"},
                {"this": "2", "of": "4"},
                {"this": "3", "of": "4"},
                {"this": "4", "of": "4"},
            ],
        ),
        (
            9,
            [1, 2],
            ["2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "", ""],
            [
                {"of": "5"},
                {"this": "2", "of": "5"},
                {"this": "3", "of": "5"},
                {"this": "4", "of": "5"},
                {"this": "5", "of": "5"},
            ],
        ),
    ],
    ids=["one copy", "two copies"],
)
def test_entry_and_page_numbers_continue_on_each_copy(
    session, creditor_payments, count, copies, entries, page_numbers
):
    creditor_payments(session, count)

    parts, _, drawn = _drawn(session)

    assert [part["number"] for part in parts if part["kind"] == "copy"] == copies
    assert _entries(drawn) == entries
    assert _page_numbers(drawn) == page_numbers


@pytest.mark.parametrize(
    "count, entries",
    [(3, ["2.3", "", ""]), (5, ["2.3", "2.4", "2.5"])],
    ids=["a row on page 2", "every slot"],
)
def test_rows_that_fit_the_slots_print_no_copy_and_no_page_number(
    session, creditor_payments, count, entries
):
    creditor_payments(session, count)

    parts, pdf, drawn = _drawn(session)

    assert [part["kind"] for part in parts] == ["form"]
    assert len(pymupdf.open("pdf", pdf)) == 3
    assert _entries(drawn) == entries  # only a slot that holds a row is numbered
    assert _page_numbers(drawn) == [{"of": ""}, {"this": "", "of": ""}, {"this": "", "of": ""}]


def test_a_copy_is_never_read_as_another_page(session, creditor_payments):
    # Read without its parts, the copy would pass for page 3, and page 3 would go unread.
    creditor_payments(session, 6)
    _, pdf, _ = _drawn(session)
    with pytest.raises(ValueError, match="4 pages, but its parts print 3"):
        read_drawn("schedule_d", pdf)


def test_a_copy_of_the_last_page_goes_after_it(
    schedule_d_part_2_with_copies, generated_form_factory, creditor_payments
):
    # C, G and H continue on their last page; here D's Part 2 page, page 3 of 3.
    session = generated_form_factory().session
    rows = creditor_payments(session, 7)

    parts, pdf, drawn = _drawn(session)

    assert [(part["kind"], part.get("page"), part.get("number")) for part in parts] == [
        ("form", None, None),
        ("copy", 3, 1),
    ]
    pages = pymupdf.open("pdf", pdf)
    assert len(pages) == 4
    assert ["Part 2:" in page.get_text() for page in pages] == [False, False, True, True]
    assert rows[6].creditor_name in pages[3].get_text()
    assert _printed(drawn, ["Name"]) == {
        ("Name", None): rows[0].creditor_name,
        ("Name", 1): rows[6].creditor_name,
    }


def test_a_letter_refused_on_a_copy_names_where_to_fix_it(session, creditor_payments):
    # Row 6 prints only on the copy of page 2; its creditor's name comes from the SOFA.
    rows = creditor_payments(session, 6)
    rows[5].creditor_name = "Wąsowicz Credit"
    rows[5].save()
    document = build_parts("schedule_d", session)
    assert "Wąsowicz Credit" not in document["parts"][0]["values"].values()

    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("schedule_d", document)

    assert str(refused.value) == (
        "The court form can't print the letter “ą” in “Creditor's name”. "
        "Change it to a letter without the mark."
    )
    assert (refused.value.step, refused.value.page) == (None, "/sofa")


def test_a_copy_fills_only_the_widgets_on_its_page(schedule_d_with_copies):
    # "Debtor 1" heads pages 1 to 3; on a copy of page 2 it fills page 2's widget alone.
    (_, copy) = PDFFormFiller().check(
        "schedule_d",
        {
            "version": 2,
            "parts": [
                {"kind": "form", "values": {}},
                {"kind": "copy", "page": 2, "number": 1, "values": {"Debtor 1": "Maria Torres"}},
            ],
        },
    )
    assert [(p.widget.page, p.widget.tag) for p in copy.widgets] == [(2, "T1")]

    # Page 1's first creditor box isn't on page 2.
    with pytest.raises(UnknownField):
        PDFFormFiller().check(
            "schedule_d",
            {
                "version": 2,
                "parts": [{"kind": "copy", "page": 2, "number": 1, "values": {NAMES[0]: "x"}}],
            },
        )


def test_a_part_of_a_kind_check_does_not_know_is_refused(schedule_d_with_copies):
    with pytest.raises(ValueError, match="poster"):
        PDFFormFiller().check(
            "schedule_d",
            {"version": 2, "parts": [{"kind": "poster", "values": {"Debtor 1": "Maria Torres"}}]},
        )
```

`test_continuation_copies.py` draws the synthetic Schedule D through `build_parts`, `fill()` and `read_drawn(..., parts)`, and checks the parts, the printed pages and what each box prints:

- six rows put the sixth on a copy of page 2, the third of four pages, while page 2 keeps the third row;
- the copy repeats "Debtor 1" but not page 2's total;
- entry and page numbers run 2.3 to 2.6 and 1 to 4 of 4 with one copy, and 2.3 to 2.9 and 1 to 5 of 5 with two;
- three or five rows print no copy and no page number, and number only the slots that hold a row;
- read without its parts, the four-page PDF is refused;
- a copy of the template's last page goes after it;
- a letter the form can't print, in a row only a copy holds, is refused naming the SOFA page;
- a copy plans only its own page's widgets, and a part of an unknown kind is refused.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/conftest.py b/backend/apps/forms/tests/conftest.py
index 8435163..0fa282d 100644
--- a/backend/apps/forms/tests/conftest.py
+++ b/backend/apps/forms/tests/conftest.py
@@ -15,11 +15,46 @@ from rest_framework.test import APIClient
 from apps.districts.models import District
 from apps.forms.field_index import load_index
 from apps.forms.models import GeneratedForm
+from apps.forms.schema import load_schema
 from apps.forms.services.widgets import template_widgets
-from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
+from apps.intake.models import (
+    DebtorInfo,
+    IncomeInfo,
+    IntakeSession,
+    SOFACreditorPayment,
+    SOFAReport,
+)

 User = get_user_model()

+# A slot's boxes, (box, label, the SOFA creditor payment attribute it prints).
+_NAME = ("Creditor's name", "creditor_name")
+_AMOUNT = ("Amount of claim", "total_paid")
+# Schedule D Part 1's rows as (page, boxes), each a creditor's name and a Column A amount:
+# 2.1 and 2.2 on page 1, then page 2's three rows, which the filer numbers from 2.3.
+_D_PART_1 = [
+    (1, [("Creditors Name", *_NAME), ("undefined", *_AMOUNT)]),
+    (1, [("Creditors Name_2", *_NAME), ("undefined_5", *_AMOUNT)]),
+    (2, [("Creditors Name_3", *_NAME), ("undefined_10", *_AMOUNT)]),
+    (2, [("Creditors Name_4", *_NAME), ("undefined_14", *_AMOUNT)]),
+    (2, [("Creditors Name_5", *_NAME), ("undefined_20", *_AMOUNT)]),
+]
+# Schedule D Part 2's six entries on page 3, the template's last page: each a name.
+_D_PART_2 = [
+    (3, [(box, *_NAME)]) for box in ["Name", "Name_2", "Name_3", "Name_4", "Name_5", "Name_6"]
+]
+_CREDITORS = [
+    "Ashby Auto Credit",
+    "Birchfield Lending",
+    "Corvale Finance",
+    "Dunmere Savings",
+    "Elsworth Credit",
+    "Fenwick Motor Credit",
+    "Glasmere Loans",
+    "Halcott Finance",
+    "Ivyrock Credit",
+]
+

 @pytest.fixture
 def index_copy(tmp_path, settings):
@@ -45,6 +80,104 @@ def index_copy(tmp_path, settings):
     template_widgets.cache_clear()


+def _schedule_d_with_group(tmp_path, settings, group, rows, declaration):
+    """
+    Copy the real schemas into tmp_path and point FORM_SCHEMAS_DIRECTORY there, with a
+    synthetic repeat group on Schedule D: row n's slot is rows[n - 1], (page, boxes), each
+    box bound to that SOFA creditor payment's attribute; the group's declaration is
+    `declaration`. Returns the schemas directory.
+    """
+    schemas = tmp_path / "schemas"
+    shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, schemas)
+    path = schemas / "schedule_d.json"
+    schema = json.loads(path.read_text())
+    for row, (page, boxes) in enumerate(rows, start=1):
+        for pdf_field, label, attr in boxes:
+            schema["fields"].append(
+                {
+                    "pdf_field": pdf_field,
+                    "type": "text",
+                    "source": "asked",
+                    "page": page,
+                    "label": label,
+                    "required": False,
+                    "conditional_on": None,
+                    "value": None,
+                    "rule": None,
+                    "ingest_key": None,
+                    "binding": f"sofa.creditor_payments[].{attr}",
+                    "repeat": group,
+                    "repeat_capacity": len(rows),
+                    "row": row,
+                    "legal_review": False,
+                }
+            )
+    schema["groups"] = {group: declaration}
+    path.write_text(json.dumps(schema))
+    settings.FORM_SCHEMAS_DIRECTORY = schemas
+    return schemas
+
+
+@pytest.fixture
+def schedule_d_with_copies(tmp_path, settings):
+    """
+    A copy of the real schemas whose Schedule D has a synthetic repeat group (3a2 spec
+    §5.4, R18, R19): Part 1's five rows, each a SOFA creditor payment's name and amount,
+    continued on copies of page 2, numbered "2.{n}", with the page-number boxes of pages
+    1 to 3. Yields the schemas directory. The schema cache is cleared before and after,
+    so the synthetic Schedule D never poisons, or is poisoned by, the real one.
+    """
+    declaration = {
+        "extra_page": 2,
+        "number": "2.{n}",
+        "number_boxes": {
+            "3": "undefined_12",
+            "4": "undefined_19@2:T37",
+            "5": "undefined_19@2:T63",
+        },
+        "page_numbers": [
+            {"page": 1, "this": None, "of": "fill_27.0"},
+            {"page": 2, "this": "fill_27.1.0", "of": "fill_27.1.1"},
+            {"page": 3, "this": "fill_28.1.1", "of": "fill_28.1.2"},
+        ],
+    }
+    schemas = _schedule_d_with_group(tmp_path, settings, "d_part_1", _D_PART_1, declaration)
+    load_schema.cache_clear()
+    yield schemas
+    load_schema.cache_clear()
+
+
+@pytest.fixture
+def schedule_d_part_2_with_copies(tmp_path, settings):
+    """
+    As schedule_d_with_copies, but Schedule D's one synthetic group is Part 2's six
+    entries on page 3, continued on copies of that page, the template's last, as C, G
+    and H continue theirs. Yields the schemas directory.
+    """
+    schemas = _schedule_d_with_group(tmp_path, settings, "d_part_2", _D_PART_2, {"extra_page": 3})
+    load_schema.cache_clear()
+    yield schemas
+    load_schema.cache_clear()
+
+
+@pytest.fixture
+def creditor_payments():
+    """add(session, count): that many SOFA creditor payments, each a firm and an amount."""
+
+    def add(session, count):
+        report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
+        return [
+            SOFACreditorPayment.objects.create(
+                report=report,
+                creditor_name=_CREDITORS[n - 1] if n <= len(_CREDITORS) else f"Creditor {n}",
+                total_paid=Decimal(f"{n}00.00"),
+            )
+            for n in range(1, count + 1)
+        ]
+
+    return add
+
+
 @pytest.fixture
 def api_client_authed(db):
     user = User.objects.create_user(username="testuser", password="pw")
diff --git a/backend/apps/forms/tests/pdf_readback.py b/backend/apps/forms/tests/pdf_readback.py
index b7f8c92..2aca871 100644
--- a/backend/apps/forms/tests/pdf_readback.py
+++ b/backend/apps/forms/tests/pdf_readback.py
@@ -5,10 +5,11 @@ Every value prints in Helvetica and every tick is the template's ZapfDingbats ch
 mark, while the templates print their own words in Arial, Wingdings and Times. A
 character belongs to a widget when its centre lies inside the widget's rect from the
 field index: two pairs of boxes overlap by about 2 pt, and a glyph merely touching a
-rect would put a neighbour's tick in it.
+rect would put a neighbour's tick in it. A copy of an extra page is read as the template
+page it copies, found through the form's parts.
 """

-from dataclasses import dataclass
+from dataclasses import dataclass, replace
 from functools import lru_cache
 from io import BytesIO
 from pathlib import Path
@@ -19,7 +20,7 @@ from django.conf import settings
 from pypdf.generic import ArrayObject, NameObject

 from apps.forms.schema import load_schema
-from apps.forms.services.widgets import TemplateWidget, template_widgets, widget_for
+from apps.forms.services.widgets import TemplateWidget, page_count, template_widgets, widget_for

 _BOXES = ("CheckBox", "RadioButton")
 _TEXT_FONT = "Helvetica"
@@ -33,6 +34,7 @@ class DrawnWidget:
     tag: str
     value: str  # the Helvetica text inside the widget's rect; "" when none
     state: str  # a box: its on-state when a check mark is inside, else "/Off"; "" for text
+    copy: int | None = None  # on a copy of an extra page, its number; None on the form's own


 @dataclass(frozen=True)
@@ -83,20 +85,40 @@ def _text(widget: TemplateWidget, characters: list[_Character]) -> str:
     return "".join(text.split()) if widget.comb else text


-def _read(template: str, document: pymupdf.Document) -> list[DrawnWidget]:
-    characters = [_characters(page) for page in document]
-    drawn = []
+def _read(
+    template: str, document: pymupdf.Document, pages: list[tuple[int, int | None]]
+) -> list[DrawnWidget]:
+    """Each page's widgets, read as those of the template page and copy `pages` names for it."""
+    widgets: dict[int, list[TemplateWidget]] = {}
     for widget in template_widgets(template):
-        on_page = characters[widget.page - 1]
-        if widget.kind in _BOXES:
-            ticked = any(c.font == _TICK_FONT and _inside(c, widget.rect) for c in on_page)
-            value, state = "", widget.states[0] if ticked else "/Off"
-        else:
-            value, state = _text(widget, on_page), ""
-        drawn.append(DrawnWidget(widget.full_name, widget.page, widget.tag, value, state))
+        widgets.setdefault(widget.page, []).append(widget)
+    drawn = []
+    for output, (page, copy) in zip(document, pages, strict=True):
+        on_page = _characters(output)
+        for widget in widgets.get(page, []):
+            if widget.kind in _BOXES:
+                ticked = any(c.font == _TICK_FONT and _inside(c, widget.rect) for c in on_page)
+                value, state = "", widget.states[0] if ticked else "/Off"
+            else:
+                value, state = _text(widget, on_page), ""
+            drawn.append(DrawnWidget(widget.full_name, widget.page, widget.tag, value, state, copy))
     return drawn


+def _pages(template: str, parts: list[dict]) -> list[tuple[int, int | None]]:
+    """
+    The template page, and the copy number, each page of the drawn form shows: the
+    template's pages in order, and each copy right after its extra page or the copy of
+    it before.
+    """
+    pages: list[tuple[int, int | None]] = [(p, None) for p in range(1, page_count(template) + 1)]
+    for part in parts:
+        if part["kind"] == "copy":
+            at = max(i for i, (page, _) in enumerate(pages) if page == part["page"]) + 1
+            pages.insert(at, (part["page"], part["number"]))
+    return pages
+
+
 @lru_cache(maxsize=32)
 def _blank(template: str) -> dict[tuple[int, str], str]:
     """
@@ -120,21 +142,28 @@ def _blank(template: str) -> dict[tuple[int, str], str]:
     writer.write(buffer)
     document = pymupdf.open("pdf", buffer.getvalue())
     document.bake(annots=False, widgets=True)
-    return {(w.page, w.tag): w.value for w in _read(template, document) if w.value}
+    pages = [(page, None) for page in range(1, len(document) + 1)]
+    return {(w.page, w.tag): w.value for w in _read(template, document, pages) if w.value}


-def read_drawn(form_type: str, pdf_bytes: bytes) -> list[DrawnWidget]:
+def read_drawn(
+    form_type: str, pdf_bytes: bytes, parts: list[dict] | None = None
+) -> list[DrawnWidget]:
     """
     What the drawn form prints in each widget of its template, one entry per index row
-    in page and tag order. A text box that prints exactly what the blank form prints
-    there reads as "": nothing the template prints passes for a value, so a value equal
-    to that box's blank text reads blank too.
+    in page and tag order. With `parts`, the parts it was drawn from (spec §6), each copy
+    of an extra page follows that page, its widgets read with their copy number. A text
+    box that prints exactly what the blank form prints there reads as "": nothing the
+    template prints passes for a value, so a value equal to that box's blank text reads
+    blank too.

     Raises:
         ValueError: a page still has a widget. MuPDF reads an unbaked widget's appearance
             as text, and a viewer may rebuild it from the field's one value, so only a
             baked page shows what prints. Not an assertion, so a listed defect's xfail
-            never takes a missing bake for that defect.
+            never takes a missing bake for that defect. Also when the PDF has a page
+            count other than the template's and its copies', so no copy is read as
+            another page.
     """
     template = load_schema(form_type).template_filename
     blank = _blank(template)
@@ -142,11 +171,10 @@ def read_drawn(form_type: str, pdf_bytes: bytes) -> list[DrawnWidget]:
     unbaked = [page.number + 1 for page in document if page.first_widget]
     if unbaked:
         raise ValueError(f"the PDF still has widgets on pages {unbaked}: it was never baked")
+    pages = _pages(template, parts or [])
+    if len(document) != len(pages):
+        raise ValueError(f"the PDF has {len(document)} pages, but its parts print {len(pages)}")
     return [
-        (
-            DrawnWidget(w.full_name, w.page, w.tag, "", w.state)
-            if w.value and blank.get((w.page, w.tag)) == w.value
-            else w
-        )
-        for w in _read(template, document)
+        replace(w, value="") if w.value and blank.get((w.page, w.tag)) == w.value else w
+        for w in _read(template, document, pages)
     ]
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index 8e20c9a..c4360cf 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -136,10 +136,12 @@ def _send_through_the_api(persona):

 def _comparable(form_type, values):
     """
-    A form's values, with each repeat group's rows in a fixed order.
+    One part's values, with each repeat group's rows in a fixed order.

     No production schema has a repeat group since step 2 took Form 107's off. Stored rows
-    have no fixed order (DIG-164), so a group a later step binds compares regardless of it.
+    have no fixed order (DIG-164), so within one part a group a later step binds compares
+    regardless of it. Across parts it doesn't: a group past its last slot puts its rows on
+    the form part and its copies by position, so another order moves other rows to a copy.
     Each row keeps its own values together, so an amount that moves to another row differs.
     """
     fixed = dict(values)
diff --git a/backend/apps/forms/tests/test_checks.py b/backend/apps/forms/tests/test_checks.py
index cb4aaea..e4bc623 100644
--- a/backend/apps/forms/tests/test_checks.py
+++ b/backend/apps/forms/tests/test_checks.py
@@ -99,7 +99,8 @@ def test_push_button_binding_is_reported(schema_copy):
         "legal_review": False,
     }
     _edit(schema_copy, "form_101", lambda d: d["fields"].append(print_button))
-    assert _ids("form_101") == ["forms.E004"]
+    # A print button is never drawn, so its page holds no widget that prints (E003).
+    assert _ids("form_101") == ["forms.E003", "forms.E004"]


 def test_checkbox_without_choices_is_reported(schema_copy):
@@ -208,6 +209,14 @@ def test_a_tag_that_isnt_one_of_the_names_widgets_on_its_page_is_reported(schema
     ]


+def test_an_untagged_binding_on_a_page_without_its_widget_is_reported(schema_copy):
+    # Form 121 prints Debtor1.First name on page 1 only.
+    _edit(schema_copy, "form_121", lambda d: _field(d, "Debtor1.First name").update(page=2))
+    assert _errors("form_121") == [
+        ("forms.E003", "form_121: 'Debtor1.First name' has no drawn widget on page 2")
+    ]
+
+
 def test_a_tag_on_the_second_of_a_stacked_pair_is_reported(schema_copy):
     # Schedule D page 2 lays 4_3's T14 over T13; only T13 prints a value.
     _edit(schema_copy, "schedule_d", lambda d: d["fields"].append(_text("4_3", 2, "T14")))
@@ -255,24 +264,487 @@ def _row(tag, row):
     }


+def _rows(*rows):
+    """Add the rows to the schema, and declare their group, continued on page 2."""
+
+    def change(d):
+        d["fields"].extend(rows)
+        d["groups"] = {"cp": {"extra_page": 2}}
+
+    return change
+
+
+_UNTAGGED_SLOT_ON_A_TWIN = (
+    "forms.E007",
+    "schedule_i: repeat group 'cp': 'Assistance 8f' is drawn 2 times, on pages [2], "
+    "so its slot needs a tag",
+)
+
+
 @pytest.mark.parametrize(
-    "first, second",
-    [(("T49", 1), ("T49", 2)), ((None, 1), ("T49", 2))],
+    "first, second, also",
+    [(("T49", 1), ("T49", 2), []), ((None, 1), ("T49", 2), [_UNTAGGED_SLOT_ON_A_TWIN])],
     ids=["two rows tagged to one widget", "an untagged and a tagged row"],
 )
-def test_two_rows_of_a_group_that_would_fill_one_widget_are_reported(schema_copy, first, second):
-    # A box shows one value: the later row would overwrite the earlier one.
-    _edit(schema_copy, "schedule_i", lambda d: d["fields"].extend([_row(*first), _row(*second)]))
+def test_two_rows_of_a_group_that_would_fill_one_widget_are_reported(
+    schema_copy, first, second, also
+):
+    # A box shows one value: the later row would overwrite the earlier one. The untagged row
+    # is also refused on its own, below.
+    _edit(schema_copy, "schedule_i", _rows(_row(*first), _row(*second)))
     assert _errors("schedule_i") == [
-        ("forms.E006", "schedule_i: 'Assistance 8f' is bound 2 times on page 2")
+        ("forms.E006", "schedule_i: 'Assistance 8f' is bound 2 times on page 2"),
+        *also,
     ]


 def test_rows_of_a_group_on_different_widgets_of_one_name_pass(schema_copy):
-    _edit(schema_copy, "schedule_i", lambda d: d["fields"].extend([_row("T36", 1), _row("T49", 2)]))
+    _edit(schema_copy, "schedule_i", _rows(_row("T36", 1), _row("T49", 2)))
     assert _ids("schedule_i") == []


+def test_an_untagged_slot_whose_name_is_drawn_twice_on_its_page_is_reported(schema_copy):
+    # Page 2 draws Assistance 8f twice, and nothing else writes it: row 1 would print in both.
+    row_2 = {**_row(None, 2), "pdf_field": "Other deductions 5h"}  # drawn once, on page 2
+    _edit(schema_copy, "schedule_i", _rows(_row(None, 1), row_2))
+    assert _errors("schedule_i") == [_UNTAGGED_SLOT_ON_A_TWIN]
+
+
+def test_a_group_continued_on_copies_of_its_extra_page_passes(schedule_d_with_copies):
+    assert _errors("schedule_d") == []
+
+
+def _group(change):
+    """Change the synthetic Schedule D group's declaration."""
+    return lambda d: change(d["groups"]["d_part_1"])
+
+
+def _row_3_numbered_on_the_page_of_its_unmapped_box(d):
+    # An unmapped box prints nothing, so row 3 is still on page 2, where undefined_2 isn't.
+    # Listed before the group's other fields, such a box used to decide the row's page.
+    box = {**_text("Contingent", 1, None), "type": "checkbox", "value": None, "choices": {}}
+    box |= {"repeat": "d_part_1", "repeat_capacity": 5, "row": 3}
+    first = next(i for i, f in enumerate(d["fields"]) if f["repeat"] == "d_part_1")
+    d["fields"].insert(first, box)
+    d["groups"]["d_part_1"]["number_boxes"]["3"] = "undefined_2"
+
+
+@pytest.mark.parametrize(
+    "change, error",
+    [
+        (
+            lambda d: d.pop("groups"),
+            ("forms.E007", "schedule_d: repeat group 'd_part_1' isn't declared in groups"),
+        ),
+        (
+            _group(lambda g: g.pop("extra_page")),
+            ("forms.E007", "schedule_d: group 'd_part_1' names no extra_page"),
+        ),
+        (
+            # Page 3 is Part 2's: no row of Part 1 is there.
+            _group(lambda g: g.update(extra_page=3)),
+            ("forms.E007", "schedule_d: group 'd_part_1': extra_page 3 holds none of its slots"),
+        ),
+        (
+            # Page 1's copies would print the rows past 2.5 before page 2's 2.3 to 2.5.
+            _group(lambda g: g.update(extra_page=1)),
+            (
+                "forms.E007",
+                "schedule_d: group 'd_part_1': extra_page 1 isn't the page of its last slots, 2",
+            ),
+        ),
+        (
+            _group(lambda g: g.update(number="2.")),
+            ("forms.E007", "schedule_d: group 'd_part_1': number must contain {n}"),
+        ),
+        (
+            # {m} has no value: numbering the first row would fail at Generate.
+            _group(lambda g: g.update(number="2.{n}{m}")),
+            ("forms.E007", "schedule_d: group 'd_part_1': number '2.{n}{m}' doesn't format"),
+        ),
+        (
+            # A number has no index: this one fails with a TypeError, not a KeyError.
+            _group(lambda g: g.update(number="2.{n}{n[0]}")),
+            ("forms.E007", "schedule_d: group 'd_part_1': number '2.{n}{n[0]}' doesn't format"),
+        ),
+        (
+            _group(lambda g: g.update(number="2.{n[0]}")),
+            ("forms.E007", "schedule_d: group 'd_part_1': number must contain {n}"),
+        ),
+        (
+            # Escaped braces: every row would be numbered "2.{n}".
+            _group(lambda g: g.update(number="2.{{n}}")),
+            (
+                "forms.E007",
+                "schedule_d: group 'd_part_1': number '2.{{n}}' prints the same for every row",
+            ),
+        ),
+        (
+            # Entry-number boxes, and no number to put in them.
+            _group(lambda g: g.pop("number")),
+            ("forms.E007", "schedule_d: group 'd_part_1': number must contain {n}"),
+        ),
+        (
+            # A box nothing else writes (row 3's own box would also be two writers, E006).
+            _group(lambda g: g["number_boxes"].update({"6": "4_3@2:T13"})),
+            (
+                "forms.E003",
+                "schedule_d: group 'd_part_1': '4_3@2:T13' numbers row 6, "
+                "which isn't a slot row",
+            ),
+        ),
+        (
+            # 4_3's T14 is the stacked second of a pair, which never prints.
+            _group(lambda g: g["number_boxes"].update({"3": "4_3@2:T14"})),
+            (
+                "forms.E003",
+                "schedule_d: group 'd_part_1': '4_3@2:T14' is no drawn widget on page 2",
+            ),
+        ),
+        (
+            # Page 1's undefined_2 would number row 3, whose name and amount are on page 2.
+            _row_3_numbered_on_the_page_of_its_unmapped_box,
+            (
+                "forms.E003",
+                "schedule_d: group 'd_part_1': 'undefined_2' is no drawn widget on page 2",
+            ),
+        ),
+        (
+            # Page 2's own "of" box, declared as page 1's.
+            _group(lambda g: g["page_numbers"][0].update({"of": "fill_27.1.1"})),
+            (
+                "forms.E003",
+                "schedule_d: group 'd_part_1': 'fill_27.1.1' is no drawn widget on page 1",
+            ),
+        ),
+    ],
+    ids=[
+        "undeclared",
+        "no extra page",
+        "extra page without a slot",
+        "extra page before its last slots",
+        "number without {n}",
+        "number that doesn't format",
+        "number that indexes n",
+        "number with only an indexed n",
+        "number with escaped braces",
+        "entry-number boxes without a number",
+        "entry-number box for a row no slot has",
+        "entry-number box that never prints",
+        "entry-number box on the page of its row's unmapped box",
+        "page-number box on another page",
+    ],
+)
+def test_a_repeat_group_whose_rows_cannot_continue_is_reported(
+    schedule_d_with_copies, change, error
+):
+    _edit(schedule_d_with_copies, "schedule_d", change)
+    assert _errors("schedule_d") == [error]
+
+
+def _slots(change, first_only=False):
+    """Change every field of the synthetic Schedule D group, or only its first."""
+
+    def apply(d):
+        fields = [f for f in d["fields"] if f["repeat"] == "d_part_1"]
+        for f in fields[:1] if first_only else fields:
+            f.update(change)
+
+    return apply
+
+
+@pytest.mark.parametrize(
+    "change, error",
+    [
+        (
+            # Row 5 would print in its slot on page 2 and again on a copy.
+            _slots({"repeat_capacity": 4}),
+            "repeat group 'd_part_1': its slot rows aren't exactly 1 to its repeat_capacity, 4",
+        ),
+        (
+            # Row 6 would print nowhere: past the last slot, and before the first copy row.
+            _slots({"repeat_capacity": 6}),
+            "repeat group 'd_part_1': its slot rows aren't exactly 1 to its repeat_capacity, 6",
+        ),
+        (
+            # Which capacity counts would hang on the first field left after filtering.
+            _slots({"repeat_capacity": 4}, first_only=True),
+            "repeat group 'd_part_1' has more than one repeat_capacity",
+        ),
+        (
+            # The group would print in part: some of a row's boxes, and not the others.
+            _slots({"conditional_on": "has_creditor_payments"}, first_only=True),
+            "repeat group 'd_part_1' has more than one conditional_on",
+        ),
+    ],
+    ids=[
+        "capacity below the slots",
+        "capacity above the slots",
+        "two capacities",
+        "two conditions",
+    ],
+)
+def test_a_repeat_group_whose_capacity_isnt_its_slots_is_reported(
+    schedule_d_with_copies, change, error
+):
+    _edit(schedule_d_with_copies, "schedule_d", change)
+    assert _errors("schedule_d") == [("forms.E007", f"schedule_d: {error}")]
+
+
+def _slot(box, **change):
+    """Change one field of the synthetic Schedule D group, found by its full name."""
+
+    def apply(d):
+        next(f for f in d["fields"] if f["repeat"] == "d_part_1" and f["pdf_field"] == box).update(
+            change
+        )
+
+    return apply
+
+
+def _amount_of_row_5_on_page_3(d):
+    # Page 3's Name_6 is a drawn widget there, so every page is right: the row spans two.
+    _slot("undefined_20", pdf_field="Name_6", page=3)(d)
+    d["groups"]["d_part_1"]["extra_page"] = 3
+    d["groups"]["d_part_1"]["number_boxes"].pop("5")
+
+
+def _rows_1_to_3_on_page_2(d):
+    # Page 1's two slots take rows 4 and 5, so the form would print 2.4 before 2.1.
+    rows = {"Creditors Name_3": 1, "undefined_10": 1, "Creditors Name_4": 2, "undefined_14": 2}
+    rows |= {"Creditors Name_5": 3, "undefined_20": 3, "Creditors Name": 4, "undefined": 4}
+    rows |= {"Creditors Name_2": 5, "undefined_5": 5}
+    for f in d["fields"]:
+        if f["repeat"] == "d_part_1":
+            f["row"] = rows[f["pdf_field"]]
+    d["groups"]["d_part_1"].pop("number")
+    d["groups"]["d_part_1"]["number_boxes"] = {}
+
+
+@pytest.mark.parametrize(
+    "change, errors",
+    [
+        (
+            # Row 5's amount is a page 2 widget: a copy would print its name and not its amount.
+            _slot("undefined_20", page=1),
+            [
+                ("forms.E003", "schedule_d: 'undefined_20' has no drawn widget on page 1"),
+                (
+                    "forms.E007",
+                    "schedule_d: repeat group 'd_part_1': row 5 is on pages [1, 2], not one",
+                ),
+            ],
+        ),
+        (
+            # Row 2's amount is a page 1 widget: a copy would take row 2's box as one of its own.
+            _slot("undefined_5", page=2),
+            [
+                ("forms.E003", "schedule_d: 'undefined_5' has no drawn widget on page 2"),
+                (
+                    "forms.E007",
+                    "schedule_d: repeat group 'd_part_1': row 2 is on pages [1, 2], not one",
+                ),
+            ],
+        ),
+        (
+            # A null page names no page: reported, not a crash comparing None with a page.
+            _slot("undefined_20", page=None),
+            [("forms.E003", "schedule_d: 'undefined_20' has no drawn widget on page None")],
+        ),
+        (
+            _amount_of_row_5_on_page_3,
+            [
+                (
+                    "forms.E007",
+                    "schedule_d: repeat group 'd_part_1': row 5 is on pages [2, 3], not one",
+                )
+            ],
+        ),
+        (
+            _rows_1_to_3_on_page_2,
+            [
+                (
+                    "forms.E007",
+                    "schedule_d: repeat group 'd_part_1': row 4 is on a page before row 3's",
+                )
+            ],
+        ),
+    ],
+    ids=[
+        "a box declared on the page before its widget's",
+        "a box declared on the page after its widget's",
+        "a box with no page",
+        "a row on two pages",
+        "rows that go back a page",
+    ],
+)
+def test_a_repeat_group_whose_rows_sit_on_the_wrong_pages_is_reported(
+    schedule_d_with_copies, change, errors
+):
+    _edit(schedule_d_with_copies, "schedule_d", change)
+    assert _errors("schedule_d") == errors
+
+
+@pytest.mark.parametrize(
+    "change, name",
+    [
+        # A one-digit typo: row 3's number box written as row 3's own amount box.
+        (_group(lambda g: g["number_boxes"].update({"3": "undefined_10"})), "undefined_10"),
+        # Row 5's amount box by its tagged spelling.
+        (_group(lambda g: g["number_boxes"].update({"5": "undefined_20@2:T65"})), "undefined_20"),
+        # Rows 4 and 5 both number themselves in row 5's box.
+        (_group(lambda g: g["number_boxes"].update({"4": "undefined_19@2:T63"})), "undefined_19"),
+        # Page 2's position written into row 5's amount box.
+        (_group(lambda g: g["page_numbers"][1].update({"this": "undefined_20"})), "undefined_20"),
+    ],
+    ids=[
+        "a number box on a slot's own box",
+        "a number box on a bound widget's tagged spelling",
+        "two rows naming one number box",
+        "a page-number box on a slot's box",
+    ],
+)
+def test_a_group_box_that_another_writer_fills_is_reported(schedule_d_with_copies, change, name):
+    # The later key would overwrite the other's value without a word.
+    _edit(schedule_d_with_copies, "schedule_d", change)
+    assert _errors("schedule_d") == [
+        ("forms.E006", f"schedule_d: {name!r} is bound 2 times on page 2")
+    ]
+
+
+def test_a_page_count_box_drawn_on_two_pages_is_one_writer(schema_copy):
+    # Schedule E/F draws one "of" box, fill_27.1.7, on pages 5 and 6. Every page prints the
+    # same count, so declaring it for both pages can't conflict.
+    def declare(d):
+        d["groups"] = {
+            "e_f": {
+                "extra_page": 6,
+                "page_numbers": [
+                    {"page": 5, "of": "fill_27.1.7"},
+                    {"page": 6, "of": "fill_27.1.7"},
+                ],
+            }
+        }
+
+    _edit(schema_copy, "schedule_e_f", declare)
+    assert _errors("schedule_e_f") == []
+
+
+@pytest.mark.parametrize(
+    "change, error",
+    [
+        (
+            # Case number is drawn on pages 1 to 3: row 1's amount would print on each.
+            _slot("undefined", pdf_field="Case number"),
+            (
+                "forms.E007",
+                "schedule_d: repeat group 'd_part_1': 'Case number' is drawn 3 times, on pages "
+                "[1, 2, 3], so its slot needs a tag",
+            ),
+        ),
+        (
+            # Row 3's number would print on pages 1 and 3 as well.
+            _group(lambda g: g["number_boxes"].update({"3": "Case number"})),
+            (
+                "forms.E003",
+                "schedule_d: group 'd_part_1': 'Case number' is drawn 3 times, on pages "
+                "[1, 2, 3], so it needs a tag",
+            ),
+        ),
+        (
+            # Page 2 draws undefined_19 twice: row 3's number would print in rows 4 and 5's.
+            _group(lambda g: g.update(number_boxes={"3": "undefined_19"})),
+            (
+                "forms.E003",
+                "schedule_d: group 'd_part_1': 'undefined_19' is drawn 2 times, on pages [2], "
+                "so it needs a tag",
+            ),
+        ),
+    ],
+    ids=["a slot", "a number box", "a number box with a twin on its page"],
+)
+def test_an_untagged_group_key_drawn_on_other_pages_is_reported(
+    schedule_d_with_copies, change, error
+):
+    _edit(schedule_d_with_copies, "schedule_d", change)
+    assert _errors("schedule_d") == [error]
+
+
+def _box_slot(pdf_field, row, choices, value):
+    """Add an untagged checkbox slot to the synthetic Schedule D group: row `row`, on page 2."""
+    box = {**_text(pdf_field, 2, None), "type": "checkbox", "value": value, "choices": choices}
+    box |= {"repeat": "d_part_1", "repeat_capacity": 5, "row": row}
+    return lambda d: d["fields"].append(box)
+
+
+def test_an_untagged_box_slot_whose_boxes_share_a_state_is_reported(schedule_d_with_copies):
+    # Row 4's "Who owes the debt?" draws four boxes, each on at /On: one answer would tick all.
+    _edit(schedule_d_with_copies, "schedule_d", _box_slot("check 5", 4, {"true": "/On"}, "true"))
+    assert _errors("schedule_d") == [
+        (
+            "forms.E007",
+            "schedule_d: repeat group 'd_part_1': 'check 5' is drawn 4 times, on pages [2], "
+            "so its slot needs a tag",
+        )
+    ]
+
+
+def test_an_untagged_box_slot_whose_boxes_each_have_their_own_state_passes(
+    schedule_d_with_copies,
+):
+    # Row 3's "Who owes the debt?": each of its four boxes has its own state, so an answer
+    # ticks one of them.
+    choices = {
+        "debtor 1": "/debtor 1",
+        "debtor 2": "/debtor 2",
+        "both": "/Debtor 1 and 2",
+        "another": "/One of debtors and another",
+    }
+    _edit(schedule_d_with_copies, "schedule_d", _box_slot("check 4", 3, choices, "debtor 2"))
+    assert _errors("schedule_d") == []
+
+
+def _part_2(extra_page):
+    """Add a second group to the synthetic Schedule D: Part 2's six names on page 3."""
+
+    def add(d):
+        for row, box in enumerate(["Name", "Name_2", "Name_3", "Name_4", "Name_5", "Name_6"], 1):
+            d["fields"].append(
+                {
+                    **_text(box, 3, None),
+                    "source": "asked",
+                    "value": None,
+                    "binding": "sofa.creditor_payments[].creditor_name",
+                    "repeat": "d_part_2",
+                    "repeat_capacity": 6,
+                    "row": row,
+                }
+            )
+        d["groups"]["d_part_2"] = {} if extra_page is None else {"extra_page": extra_page}
+
+    return add
+
+
+def test_a_second_group_continued_on_copies_is_reported(schedule_d_with_copies):
+    # 3a2 numbers a form's pages counting one group's copies only (R21, R56).
+    _edit(schedule_d_with_copies, "schedule_d", _part_2(extra_page=3))
+    assert _errors("schedule_d") == [
+        (
+            "forms.E007",
+            "schedule_d: groups 'd_part_1' and 'd_part_2' both declare extra_page; "
+            "3a2 continues one group per form on copies",
+        )
+    ]
+
+
+def test_a_group_with_no_extra_page_is_not_counted_as_a_second(schedule_d_with_copies):
+    # Such a group is refused for its own reason (T7's sheet groups will declare a sheet).
+    _edit(schedule_d_with_copies, "schedule_d", _part_2(extra_page=None))
+    assert _errors("schedule_d") == [
+        ("forms.E007", "schedule_d: group 'd_part_2' names no extra_page")
+    ]
+
+
 def test_a_template_that_doesnt_match_its_index_is_reported_not_raised(schema_copy, index_copy):
     def move_a_row_off_its_widget(rows):
         next(row for row in rows if row["page"] == 2)["rect"] = [1, 1, 2, 2]
diff --git a/backend/apps/forms/tests/test_download_action.py b/backend/apps/forms/tests/test_download_action.py
index ab1a612..419d03a 100644
--- a/backend/apps/forms/tests/test_download_action.py
+++ b/backend/apps/forms/tests/test_download_action.py
@@ -5,11 +5,13 @@ is filed, and exactly what was filed afterwards (spec §5.5).

 import json
 import logging
-from unittest.mock import ANY, patch
+from unittest.mock import patch

+import pymupdf
+import pytest
 from django.urls import reverse

-from apps.forms.services.fill_resolver import RepeatOverflow
+from apps.forms.schema import load_schema
 from apps.forms.services.pdf_filler import PDFFormFiller, TemplateHasNoForm
 from apps.forms.tests.pdf_readback import read_drawn

@@ -59,22 +61,46 @@ def test_unfiled_form_prints_the_filers_current_answers(api_client_authed, gener
     assert part["values"]["Debtor1.First name"] == "Marisol"


-def test_a_filed_form_downloads_exactly_what_was_filed(api_client_authed, generated_form_factory):
+@pytest.mark.parametrize(
+    "form_type, parts, box, printed",
+    [
+        ("form_121", ["form"], "Debtor1.First name", {(None, "Maria")}),
+        # Schedule D's sixth row prints on a copy of page 2, under the filer's name.
+        ("schedule_d", ["form", "copy"], "Debtor 1", {(None, "Maria Torres"), (1, "Maria Torres")}),
+    ],
+    ids=["form", "with a copy"],
+)
+def test_a_filed_form_downloads_exactly_what_was_filed(
+    api_client_authed,
+    generated_form_factory,
+    schedule_d_with_copies,
+    creditor_payments,
+    form_type,
+    parts,
+    box,
+    printed,
+):
     form = generated_form_factory(status="generated")
+    form.form_type = form_type
+    form.save()
+    rows = creditor_payments(form.session, 6)
     regenerate = reverse("generated-forms-regenerate", kwargs={"pk": form.pk})
     mark_filed = reverse("generated-forms-mark-filed", kwargs={"pk": form.pk})
     assert api_client_authed.post(regenerate).status_code == 200
     assert api_client_authed.post(mark_filed).status_code == 200
     form.refresh_from_db()
     filed = form.field_values
-    # Spec §6's parts document: a version and the form's own part.
-    assert json.loads(filed) == {"version": 2, "parts": [{"kind": "form", "values": ANY}]}
-    _rename_filer(form, "Marisol")  # the filer's later edit
+    # Spec §6's parts document: a version, the form's own part, then one part per copy.
+    document = json.loads(filed)
+    assert (document["version"], [part["kind"] for part in document["parts"]]) == (2, parts)
+    _rename_filer(form, "Marisol")  # the filer's later edits
+    rows[5].delete()  # Schedule D would now print five rows, and no copy

     response = _download(api_client_authed, form)

     assert response.status_code == 200
-    assert _printed(response, "Debtor1.First name") == {"Maria"}
+    drawn = read_drawn(form_type, response.content, document["parts"])
+    assert {(w.copy, w.value) for w in drawn if w.full_name == box} == printed
     form.refresh_from_db()
     assert (form.status, form.field_values) == ("filed", filed)

@@ -170,20 +196,72 @@ def test_missing_data_is_a_422_with_its_reason(api_client_authed, generated_form
     assert "name and address" in response.data["error"]


-def test_too_many_rows_is_a_422(api_client_authed, generated_form_factory):
+def test_rows_past_the_slots_download_on_a_copy(
+    api_client_authed, generated_form_factory, schedule_d_with_copies, creditor_payments
+):
     form = generated_form_factory(status="generated")
-    overflow = RepeatOverflow("form_121", "rows", capacity=3, actual=4)
-    with patch("apps.forms.views.build_parts", side_effect=overflow):
-        response = _download(api_client_authed, form)
-    assert response.status_code == 422
-    # No repeat group name or capacity: the filer reads this beside the form's label.
-    assert response.data == {
-        "form_type": "form_121",
-        "error": "You have more entries than this form has room for. The extra entries "
-        "need a continuation page, which this app can't make yet.",
+    form.form_type = "schedule_d"
+    form.save()
+    rows = creditor_payments(form.session, 6)
+
+    response = _download(api_client_authed, form)
+
+    assert response.status_code == 200
+    form.refresh_from_db()
+    parts = json.loads(form.field_values)["parts"]
+    assert [part["kind"] for part in parts] == ["form", "copy"]
+    # Page 2's first slot holds the third row; its copy holds the sixth.
+    drawn = read_drawn("schedule_d", response.content, parts)
+    assert {(w.copy, w.value) for w in drawn if w.full_name == "Creditors Name_3"} == {
+        (None, rows[2].creditor_name),
+        (1, rows[5].creditor_name),
     }


+@pytest.mark.parametrize(
+    "count, entries",
+    [
+        (6, ["2.3", "2.4", "2.5", "2.6", "", ""]),
+        (8, ["2.3", "2.4", "2.5", "2.6", "2.7", "2.8"]),
+    ],
+    ids=["one row on the copy", "a full copy"],
+)
+def test_a_page_of_guarded_slots_still_takes_its_rows_on_a_copy(
+    api_client_authed,
+    generated_form_factory,
+    schedule_d_with_copies,
+    creditor_payments,
+    count,
+    entries,
+):
+    # UPL guard: page 2's boxes print only an asked answer, so they print nothing here. The
+    # guard decides which boxes print, never which slots exist: rows past the last slot
+    # still go to the copy's slots, numbered, as rows 3 to 5 do on page 2.
+    path = schedule_d_with_copies / "schedule_d.json"
+    data = json.loads(path.read_text())
+    for f in data["fields"]:
+        if f["repeat"] == "d_part_1" and f["page"] == 2:
+            f.update(source="derived", rule="full_name", legal_review=True)
+    path.write_text(json.dumps(data))
+    load_schema.cache_clear()
+    form = generated_form_factory(status="generated")
+    form.form_type = "schedule_d"
+    form.save()
+    rows = creditor_payments(form.session, count)
+
+    response = _download(api_client_authed, form)
+
+    assert response.status_code == 200
+    form.refresh_from_db()
+    parts = json.loads(form.field_values)["parts"]
+    drawn = read_drawn("schedule_d", response.content, parts)
+    assert [w.value for w in drawn if w.full_name in ("undefined_12", "undefined_19")] == entries
+    text = "".join(page.get_text() for page in pymupdf.open("pdf", response.content))
+    assert rows[0].creditor_name in text  # page 1's boxes aren't guarded
+    guarded = {r.creditor_name for r in rows[2:]} | {str(r.total_paid) for r in rows[2:]}
+    assert [value for value in guarded if value in text] == []
+
+
 def test_a_template_with_no_form_is_explained_in_plain_words(
     api_client_authed, generated_form_factory
 ):
diff --git a/backend/apps/forms/tests/test_fill_resolver.py b/backend/apps/forms/tests/test_fill_resolver.py
index 3bcaa49..750d81f 100644
--- a/backend/apps/forms/tests/test_fill_resolver.py
+++ b/backend/apps/forms/tests/test_fill_resolver.py
@@ -7,12 +7,12 @@ from django.contrib.auth import get_user_model

 from apps.districts.models import District
 from apps.documents.models import IngestedAggregate
-from apps.forms.schema import FieldSpec, FormSchema
+from apps.forms.schema import FieldSpec, FormSchema, GroupSpec
 from apps.forms.services.fill_resolver import (
-    RepeatOverflow,
     UnmappedChoice,
     resolve,
     resolve_binding,
+    resolve_parts,
 )
 from apps.intake.models import (
     DebtorInfo,
@@ -307,28 +307,120 @@ def test_repeat_rows_of_a_shared_name_land_on_their_own_widgets(session):
     }


-def test_repeat_overflow_raises(session):
+def _payments(session, count):
     report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
-    for i in range(4):
+    for i in range(count):
         SOFACreditorPayment.objects.create(
             report=report,
             creditor_name=f"C{i}",
             total_paid=Decimal("1.00"),
         )
-    schema = _schema(
-        [
-            _field(
-                pdf_field="Cred1",
-                source="asked",
-                repeat="cp",
-                repeat_capacity=3,
-                row=1,
-                binding="sofa.creditor_payments[].creditor_name",
-            ),
-        ]
+
+
+def _slots():
+    """Group cp's four slots, one creditor each: Cred1 and Cred2 on page 1, Cred3 and Cred4 on 2."""
+    return [
+        _field(
+            pdf_field=f"Cred{row}",
+            page=1 if row <= 2 else 2,
+            source="asked",
+            repeat="cp",
+            repeat_capacity=4,
+            row=row,
+            binding="sofa.creditor_payments[].creditor_name",
+        )
+        for row in range(1, 5)
+    ]
+
+
+def test_rows_past_the_slots_go_to_copies_of_the_extra_page(session):
+    _payments(session, 7)
+    schema = FormSchema(
+        "form_107",
+        "b_107_0425-form.pdf",
+        "v1",
+        _slots(),
+        groups={"cp": GroupSpec("cp", extra_page=2, number=None, number_boxes={}, page_numbers=())},
     )
-    with pytest.raises(RepeatOverflow):
-        resolve(schema, session)
+
+    # Page 2's two slots take rows 5 and 6 on its first copy, and row 7 on its second.
+    assert resolve_parts(schema, session)["parts"] == [
+        {"kind": "form", "values": {"Cred1": "C0", "Cred2": "C1", "Cred3": "C2", "Cred4": "C3"}},
+        {"kind": "copy", "page": 2, "number": 1, "values": {"Cred3": "C4", "Cred4": "C5"}},
+        {"kind": "copy", "page": 2, "number": 2, "values": {"Cred3": "C6"}},
+    ]
+    assert resolve(schema, session) == {"Cred1": "C0", "Cred2": "C1", "Cred3": "C2", "Cred4": "C3"}
+
+
+def test_a_legal_review_row_prints_neither_in_the_slots_nor_on_a_copy(session):
+    # UPL guard: a legal_review binding fills only from an explicit asked answer, on the
+    # form's own slots and on the copies alike.
+    _payments(session, 7)
+    reviewed = [
+        _field(
+            pdf_field=f"Amt{row}",
+            page=1 if row <= 2 else 2,
+            source="derived",
+            legal_review=True,
+            repeat="cp",
+            repeat_capacity=4,
+            row=row,
+            binding="sofa.creditor_payments[].total_paid",
+        )
+        for row in range(1, 5)
+    ]
+    group = GroupSpec("cp", extra_page=2, number=None, number_boxes={}, page_numbers=())
+    schema = FormSchema("form_107", "b_107_0425-form.pdf", "v1", _slots() + reviewed, {"cp": group})
+
+    parts = resolve_parts(schema, session)["parts"]
+
+    assert [sorted(part["values"]) for part in parts] == [
+        ["Cred1", "Cred2", "Cred3", "Cred4"],
+        ["Cred3", "Cred4"],
+        ["Cred3"],
+    ]
+
+
+def test_a_copy_never_repeats_a_row_from_the_form(session):
+    # Schedule D's Part 2 entry 4 box on page 3 shares its full name with a page 1 box, as
+    # a page header does. A copy of page 3 with one row leaves that slot blank.
+    _payments(session, 7)
+    boxes = [
+        "account number 6",
+        "account number 7",
+        "account number 8",
+        "account number",
+        "account number 10",
+        "account number 11",
+    ]
+    fields = [
+        _field(
+            pdf_field=box,
+            page=3,
+            tag="T33" if box == "account number" else None,
+            source="asked",
+            repeat="notified",
+            repeat_capacity=6,
+            row=row,
+            binding="sofa.creditor_payments[].creditor_name",
+        )
+        for row, box in enumerate(boxes, start=1)
+    ]
+    group = GroupSpec("notified", extra_page=3, number=None, number_boxes={}, page_numbers=())
+    schema = FormSchema("schedule_d", "form_b106d.pdf", "v1", fields, {"notified": group})
+
+    form, copy = resolve_parts(schema, session)["parts"]
+
+    assert form["values"]["account number@3:T33"] == "C3"
+    assert copy["values"] == {"account number 6": "C6"}
+
+
+def test_rows_past_the_slots_of_a_group_with_no_extra_page_are_never_dropped(session):
+    # The startup check refuses such a schema (forms.E007); a row must never vanish.
+    _payments(session, 5)
+    schema = _schema(_slots())
+    with pytest.raises(ValueError, match="names no extra page"):
+        resolve_parts(schema, session)


 def test_legal_review_field_not_filled_without_answer(session):
PATCH
```

- `conftest.py` gains the synthetic Schedule D fixtures (`schedule_d_with_copies`, `schedule_d_part_2_with_copies`) and `creditor_payments`, which adds that many SOFA creditor payments to a session, an invented firm and an amount each.
- `pdf_readback.py` is the oracle, so it changes with the tests: `read_drawn` takes the parts, reads each copy as the template page it copies, and refuses a PDF whose page count its parts don't explain. It imports `page_count`, which Step 3 adds.
- `test_checks.py` gives every group rule a case that it refuses, with the exact message, and the cases that must pass. The two Schedule I group tests declare their group, and the print-button binding now expects E003 as well.
- `test_fill_resolver.py` proves the copies at the resolver, on hand-built schemas, and replaces `test_repeat_overflow_raises`.
- `test_download_action.py` downloads a form with a copy, a filed form with a copy, and a page of guarded slots, and drops the `RepeatOverflow` 422.
- `test_api_readback.py`'s `_comparable` docstring says rows compare regardless of order only within one part.

- [ ] **Step 2: Run the tests and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE --continue-on-collection-errors apps/forms/tests/test_continuation_copies.py apps/forms/tests/test_fill_resolver.py apps/forms/tests/test_download_action.py apps/forms/tests/test_api_readback.py apps/forms/tests/test_checks.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `37 failed, 52 passed` and `3 errors in`, with `ERROR apps/forms/tests/test_continuation_copies.py`, `ERROR apps/forms/tests/test_fill_resolver.py`, `ERROR apps/forms/tests/test_download_action.py`, `test_push_button_binding_is_reported - AssertionError: assert ['forms.E004'] == ['forms.E003', 'forms.E004']` and `test_a_second_group_continued_on_copies_is_reported - assert [] == [('forms.E007...m on copies')]`.

`--continue-on-collection-errors` runs the other modules while three can't be imported: `test_continuation_copies.py` and `test_download_action.py` import `pdf_readback.py`, which needs `widgets.page_count`, and `test_fill_resolver.py` imports `GroupSpec`. Step 5 shows their own failures.

- 37 of `test_checks.py`'s 83 fail: no group rule exists yet, and the print-button binding, the untagged Form 121 binding on page 2 and the "untagged and tagged row" case expect an E003 or an E007 the parent never reports.
- The 52 that pass are `test_api_readback.py`'s 6 personas and 46 of `test_checks.py`. Three of those are new tests that can't fail while nothing refuses a group: `test_a_group_continued_on_copies_of_its_extra_page_passes`, `test_a_page_count_box_drawn_on_two_pages_is_one_writer` and `test_an_untagged_box_slot_whose_boxes_each_have_their_own_state_passes`. Steps 11 to 13 show each one red.

- [ ] **Step 3: Declare repeat groups, and check them at startup**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
index 7c86e1d..1e7b8de 100644
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -9,7 +9,7 @@ from __future__ import annotations

 import hashlib
 import json
-from dataclasses import dataclass
+from dataclasses import dataclass, field
 from functools import lru_cache
 from io import BytesIO
 from pathlib import Path
@@ -18,7 +18,12 @@ import pypdf
 from django.conf import settings

 from apps.forms.field_index import export_state, load_index
-from apps.forms.services.widgets import TemplateMismatch, TemplateWidget, template_widgets
+from apps.forms.services.widgets import (
+    TemplateMismatch,
+    TemplateWidget,
+    parse_key,
+    template_widgets,
+)


 @dataclass(frozen=True)
@@ -65,6 +70,29 @@ class FieldSpec:
     ui: UIFieldSpec | None = None


+@dataclass(frozen=True)
+class PageNumberBoxes:
+    """One template page's page-number boxes: `this` shows its position, `of` the page count."""
+
+    page: int
+    this: str | None  # a values key, or None when the page has no such box
+    of: str | None
+
+
+@dataclass(frozen=True)
+class GroupSpec:
+    """
+    A repeat group's declaration (3a2 spec §5.2): the template page whose copies take the
+    rows past its last slot, and the boxes that number the rows and the pages.
+    """
+
+    name: str
+    extra_page: int | None
+    number: str | None  # the entry number, such as "2.{n}", n the row's position in the group
+    number_boxes: dict[int, str]  # slot row → the key of that slot's entry-number box
+    page_numbers: tuple[PageNumberBoxes, ...]
+
+
 @dataclass(frozen=True)
 class FormSchema:
     """Complete specification for a form, including all fields."""
@@ -73,6 +101,7 @@ class FormSchema:
     template_filename: str
     template_version: str
     fields: list[FieldSpec]
+    groups: dict[str, GroupSpec] = field(default_factory=dict)


 @lru_cache(maxsize=32)
@@ -105,11 +134,26 @@ def load_schema(form_type: str) -> FormSchema:
         ui_spec = UIFieldSpec.from_dict(ui_data) if ui_data else None
         fields.append(FieldSpec(**field_data, ui=ui_spec))

+    groups = {
+        name: GroupSpec(
+            name=name,
+            extra_page=group.get("extra_page"),
+            number=group.get("number"),
+            number_boxes={int(row): key for row, key in group.get("number_boxes", {}).items()},
+            page_numbers=tuple(
+                PageNumberBoxes(page=boxes["page"], this=boxes.get("this"), of=boxes.get("of"))
+                for boxes in group.get("page_numbers", [])
+            ),
+        )
+        for name, group in raw.get("groups", {}).items()
+    }
+
     return FormSchema(
         form_type=raw["form_type"],
         template_filename=raw["template_filename"],
         template_version=raw["template_version"],
         fields=fields,
+        groups=groups,
     )


@@ -153,7 +197,6 @@ def validate_schema(
     for widget in widget_map or ():
         if widget.drawn:
             drawn.setdefault(widget.full_name, []).append(widget)
-    seen: dict[str, list[FieldSpec]] = {}

     for f in schema.fields:
         widgets = index.get(f.pdf_field)
@@ -168,7 +211,13 @@ def validate_schema(
             errors.append(
                 ("E003", f"{f.pdf_field!r} has no drawn widget {f.tag!r} on page {f.page}")
             )
-        seen.setdefault(f.pdf_field, []).append(f)
+        # An untagged binding's page decides which copy rows it fills (3a2 spec §5.2).
+        if (
+            f.tag is None
+            and widget_map is not None
+            and not any(w.page == f.page for w in drawn.get(f.pdf_field, ()))
+        ):
+            errors.append(("E003", f"{f.pdf_field!r} has no drawn widget on page {f.page}"))

         types = {w.type for w in widgets}
         if any(w.basis == "form_control" for w in widgets):
@@ -213,17 +262,204 @@ def validate_schema(
         if f.repeat is not None and not f.repeat_capacity:
             errors.append(("E007", f"repeat group {f.repeat!r} has no repeat_capacity"))

-    for name, bindings in seen.items():
-        # A binding fills every drawn widget of its name, or with a tag only that one. A
-        # widget shows one value, so two bindings that would fill it conflict, rows of
-        # one repeat group included.
+    # Who writes each widget: every binding, and every box a group numbers a row or a page
+    # in. A key fills every drawn widget of its name, or with a tag only that one. A widget
+    # shows one value, so two writers that would fill it conflict, rows of one repeat group
+    # included. A page count is the same on every page: one "of" key is one writer.
+    writers: dict[str, list[tuple[tuple, int | None, str | None]]] = {}
+    for i, f in enumerate(schema.fields):
+        if f.pdf_field in index:  # any other name is reported above (E003)
+            writers.setdefault(f.pdf_field, []).append((("binding", i), f.page, f.tag))
+    for group_name, group in schema.groups.items():
+        boxes = [(("number", group_name, row), key) for row, key in group.number_boxes.items()]
+        for p in group.page_numbers:
+            if p.this:
+                boxes.append((("this", group_name, p.page), p.this))
+            if p.of:
+                boxes.append((("of", p.of), p.of))
+        for writer, key in boxes:
+            try:
+                name, at, tag = parse_key(key)
+            except ValueError:
+                continue  # E003 below reports a key that names no widget
+            writers.setdefault(name, []).append((writer, at, tag))
+    for name, entries in writers.items():
         for widget in drawn.get(name, ()):
-            fills = [
-                b for b in bindings if b.tag is None or (b.page, b.tag) == (widget.page, widget.tag)
-            ]
+            fills = {
+                writer
+                for writer, page, tag in entries
+                if tag is None or (page, tag) == (widget.page, widget.tag)
+            }
             if len(fills) > 1:
                 errors.append(
                     ("E006", f"{name!r} is bound {len(fills)} times on page {widget.page}")
                 )
                 break
+
+    # A repeat group fills its slots, rows 1 to repeat_capacity, and its rows past the last
+    # slot continue on copies of its extra page, the page of its last slots (3a2 spec §5.2).
+    # Each box that numbers a row or a page prints on that row's or page's page.
+    from apps.forms.services.fill_resolver import _unmapped  # here: it imports this module
+
+    slots: dict[str, list[FieldSpec]] = {}
+    for f in schema.fields:
+        if f.repeat is not None:
+            slots.setdefault(f.repeat, []).append(f)
+    for name, rows in slots.items():
+        # A group applies whole or not at all, and its capacity is its slots: a capacity
+        # below them would print a row on the form and on a copy, one above them no row.
+        capacities = {f.repeat_capacity for f in rows}
+        mapped = [f for f in rows if not _unmapped(f)]
+        if len(capacities) > 1:
+            errors.append(("E007", f"repeat group {name!r} has more than one repeat_capacity"))
+        else:
+            (capacity,) = capacities  # None or 0 is reported above, per field
+            if capacity and {f.row for f in mapped} != set(range(1, capacity + 1)):
+                errors.append(
+                    (
+                        "E007",
+                        f"repeat group {name!r}: its slot rows aren't exactly 1 to its "
+                        f"repeat_capacity, {capacity}",
+                    )
+                )
+        if len({f.conditional_on for f in rows}) > 1:
+            errors.append(("E007", f"repeat group {name!r} has more than one conditional_on"))
+        # An untagged binding fills every widget of its name, so a slot whose name is drawn
+        # more than once would print its row in each, or tick each box that shares its state.
+        # A column of boxes that each have their own state ticks only the answer's box.
+        for f in mapped:
+            widgets = drawn.get(f.pdf_field, ())
+            if f.type in ("checkbox", "radio"):
+                states = [s for w in widgets for s in set(w.states)]
+                twinned = len(states) > len(set(states))
+            else:
+                twinned = len(widgets) > 1
+            if f.tag is None and twinned:
+                errors.append(
+                    (
+                        "E007",
+                        f"repeat group {name!r}: {f.pdf_field!r} is drawn {len(widgets)} times, "
+                        f"on pages {_pages_drawn(f.pdf_field, drawn)}, so its slot needs a tag",
+                    )
+                )
+        # A copy takes a row's boxes from one page, and prints rows in row order. A missing
+        # row is reported above, against the capacity, and a missing page by E003.
+        paged = [f for f in mapped if f.row is not None and f.page is not None]
+        row_pages: dict[int, set[int]] = {}
+        for f in paged:
+            row_pages.setdefault(f.row, set()).add(f.page)
+        page_of: dict[int, int] = {}
+        for row, on in sorted(row_pages.items()):
+            if len(on) > 1:
+                errors.append(
+                    ("E007", f"repeat group {name!r}: row {row} is on pages {sorted(on)}, not one")
+                )
+            else:
+                (page_of[row],) = on
+        order = sorted(page_of)
+        for before, after in zip(order, order[1:], strict=False):
+            if page_of[after] < page_of[before]:
+                errors.append(
+                    (
+                        "E007",
+                        f"repeat group {name!r}: row {after} is on a page before row {before}'s",
+                    )
+                )
+        group = schema.groups.get(name)
+        pages = {f.page for f in paged}
+        if group is None:
+            errors.append(("E007", f"repeat group {name!r} isn't declared in groups"))
+        elif group.extra_page is None:
+            errors.append(("E007", f"group {name!r} names no extra_page"))
+        elif group.extra_page not in pages:
+            errors.append(
+                ("E007", f"group {name!r}: extra_page {group.extra_page} holds none of its slots")
+            )
+        elif group.extra_page != max(pages):
+            errors.append(
+                (
+                    "E007",
+                    f"group {name!r}: extra_page {group.extra_page} isn't the page of its "
+                    f"last slots, {max(pages)}",
+                )
+            )
+    # 3a2 numbers a form's pages counting one group's copies only (R21, R56).
+    continued = [
+        repr(name) for name, group in schema.groups.items() if group.extra_page is not None
+    ]
+    if len(continued) > 1:
+        errors.append(
+            (
+                "E007",
+                f"groups {', '.join(continued[:-1])} and {continued[-1]} "
+                f"{'both' if len(continued) == 2 else 'all'} declare extra_page; "
+                "3a2 continues one group per form on copies",
+            )
+        )
+    for name, group in schema.groups.items():
+        if (group.number is not None or group.number_boxes) and "{n}" not in (group.number or ""):
+            errors.append(("E007", f"group {name!r}: number must contain {{n}}"))
+        elif group.number is not None:
+            try:
+                first, second = group.number.format(n=1), group.number.format(n=2)
+            except Exception:  # any way it fails at Generate is a schema error here
+                errors.append(("E007", f"group {name!r}: number {group.number!r} doesn't format"))
+            else:
+                if first == second:  # "2.{{n}}" prints "2.{n}" for every row
+                    errors.append(
+                        (
+                            "E007",
+                            f"group {name!r}: number {group.number!r} prints the same "
+                            "for every row",
+                        )
+                    )
+        if widget_map is None:
+            continue
+        # A row is on its mapped boxes' page: an unmapped box prints nothing, wherever it is.
+        rows = [f for f in slots.get(name, []) if not _unmapped(f)]
+        boxes = []
+        for row, key in group.number_boxes.items():
+            page = next((f.page for f in rows if f.row == row), None)
+            if page is None:
+                errors.append(
+                    ("E003", f"group {name!r}: {key!r} numbers row {row}, which isn't a slot row")
+                )
+            else:
+                boxes.append((key, page))
+        boxes += [(key, p.page) for p in group.page_numbers for key in (p.this, p.of) if key]
+        for key, page in boxes:
+            if not _drawn_on(key, page, drawn):
+                errors.append(
+                    ("E003", f"group {name!r}: {key!r} is no drawn widget on page {page}")
+                )
+        # A row's or a page's number prints in one box: an untagged key whose name has more
+        # than one drawn widget would print it in each. A page count is the same in all.
+        numbered = [*group.number_boxes.values(), *(p.this for p in group.page_numbers if p.this)]
+        for key in numbered:
+            widgets = drawn.get(key, ())  # a tagged key has "@", so it is never a name here
+            if len(widgets) > 1:
+                errors.append(
+                    (
+                        "E003",
+                        f"group {name!r}: {key!r} is drawn {len(widgets)} times, on pages "
+                        f"{_pages_drawn(key, drawn)}, so it needs a tag",
+                    )
+                )
     return errors
+
+
+def _pages_drawn(name: str, drawn: dict[str, list[TemplateWidget]]) -> list[int]:
+    """The pages a full name is drawn on, in order."""
+    return sorted({w.page for w in drawn.get(name, ())})
+
+
+def _drawn_on(key: str, page: int | None, drawn: dict[str, list[TemplateWidget]]) -> bool:
+    """Whether a values key fills a drawn widget on `page`."""
+    try:
+        name, at, tag = parse_key(key)
+    except ValueError:
+        return False
+    return any(
+        w.page == page and (tag is None or (w.page, w.tag) == (at, tag))
+        for w in drawn.get(name, ())
+    )
diff --git a/backend/apps/forms/services/widgets.py b/backend/apps/forms/services/widgets.py
index 5806d7d..1ddfe1b 100644
--- a/backend/apps/forms/services/widgets.py
+++ b/backend/apps/forms/services/widgets.py
@@ -246,6 +246,12 @@ def template_widgets(template_filename: str) -> tuple[TemplateWidget, ...]:
     return tuple(sorted(widgets, key=lambda w: (w.page, int(w.tag[1:]))))


+@lru_cache(maxsize=32)
+def page_count(template_filename: str) -> int:
+    """How many pages the template has."""
+    return len(pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template_filename).pages)
+
+
 def widget_for(
     template_filename: str, page: int, annotation: DictionaryObject, page_top: float
 ) -> TemplateWidget:
PATCH
```

`load_schema` reads a schema's top-level `groups` into `GroupSpec` and `PageNumberBoxes`, with each `number_boxes` row as an int; `FormSchema.groups` is empty by default. `validate_schema` gains, in order:

- E003 for an untagged binding whose page holds no drawn widget of its name;
- E006's writers: every binding, and every number box, page-number `this` and page-number `of`, so two writers of one widget conflict;
- for each repeat group, E007's capacity, condition, twin, one-page and page-order rules, then its declaration and extra-page rules. `_unmapped` is imported inside the function, since `fill_resolver` imports this module;
- E007 for a second group with an `extra_page`, and the `number` rules;
- E003 for each number and page-number box, through the new helpers `_drawn_on` and `_pages_drawn`.

`widgets.page_count` reads a template's page count once per template. The resolver and the read-back use it.

- [ ] **Step 4: Run the startup tests**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_checks.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `83 passed`.

That includes `test_every_registered_form_passes`: all 17 production schemas pass the new rules.

- [ ] **Step 5: Watch the copy tests fail while rows past the last slot still raise**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_continuation_copies.py apps/forms/tests/test_fill_resolver.py apps/forms/tests/test_download_action.py apps/forms/tests/test_api_readback.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `19 failed, 38 passed`, with `RepeatOverflow: schedule_d: repeat group 'd_part_1' has 6 rows but template holds 5`, `test_rows_that_fit_the_slots_print_no_copy_and_no_page_number[a row on page 2] - AssertionError: assert ['', '', ''] == ['2.3', '', '']`, `test_rows_past_the_slots_download_on_a_copy - assert 422 == 200` and `test_a_part_of_a_kind_check_does_not_know_is_refused - Failed: DID NOT RAISE <class 'ValueError'>`.

The modules import now. The resolver still raises `RepeatOverflow` one row past the last slot, which Download turns into its 422, and numbers no slot. `check()` still plans a copy part on every page of the form, and an unknown kind as the form.

- [ ] **Step 6: Continue rows past the last slot on copies of the extra page**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/fill_resolver.py b/backend/apps/forms/services/fill_resolver.py
index c99ea69..10bad0f 100644
--- a/backend/apps/forms/services/fill_resolver.py
+++ b/backend/apps/forms/services/fill_resolver.py
@@ -3,31 +3,19 @@ Fill resolver — turns a FormSchema + IntakeSession into {pdf_field: str}, or,
 binding with a tag, {"<pdf_field>@<page>:<tag>": str}.

 Source priority is encoded per-field in the schema (constant/derived/asked/
-ingested/signature). This module resolves ``binding`` references; resolve()
-(Task 8) orchestrates dispatch, conditional sections, and repeat groups.
+ingested/signature). This module resolves ``binding`` references; resolve_parts()
+orchestrates dispatch, conditional sections, and repeat groups, whose rows past the
+last slot continue on copies of an extra page, and resolve() returns its form part.
 """

 from __future__ import annotations

-from apps.forms.schema import FieldSpec, FormSchema
+from apps.forms.schema import FieldSpec, FormSchema, GroupSpec, PageNumberBoxes
 from apps.forms.services.derivations import DERIVATIONS, PREDICATES, RULE_FIXES
+from apps.forms.services.widgets import TemplateWidget, page_count, parse_key, template_widgets
 from apps.intake.models import FormAnswer, IntakeSession


-class RepeatOverflow(Exception):
-    """A bound collection exceeded its template's pre-printed row capacity."""
-
-    def __init__(self, form_type: str, group: str, capacity: int, actual: int):
-        self.form_type = form_type
-        self.group = group
-        self.capacity = capacity
-        self.actual = actual
-        super().__init__(
-            f"{form_type}: repeat group {group!r} has {actual} rows but template "
-            f"holds {capacity}. A continuation attachment is required."
-        )
-
-
 class UnmappedChoice(Exception):
     """A checkbox or radio answer has no export state in its binding's choices."""

@@ -164,7 +152,121 @@ def _emit(field: FieldSpec, value: str | None) -> str | None:
     return str(value)


+def _cell(
+    field: FieldSpec,
+    position: int | None,
+    columns: dict[str, str | list[str]],
+    session: IntakeSession,
+    ingested_cache: dict,
+) -> str | None:
+    """What a repeat group's binding prints for the row at `position` (from 1) in the group."""
+    if not field.binding:
+        return _emit(field, _scalar_value(field, session, ingested_cache=ingested_cache))
+    vals = columns.get(_key(field))
+    if isinstance(vals, list) and position and position <= len(vals):
+        return _emit(field, str(vals[position - 1]))
+    return None
+
+
+def _number_page(values: dict[str, str], boxes: PageNumberBoxes, position: int, total: int) -> None:
+    """A page's position in the form, and the form's page count, in its page-number boxes."""
+    if boxes.this:
+        values[boxes.this] = str(position)
+    if boxes.of:
+        values[boxes.of] = str(total)
+
+
+def _headers(schema: FormSchema, form: dict[str, str], page: int) -> dict[str, str]:
+    """
+    The form's values a copy of `page` repeats: those of a box whose full name prints on
+    `page` and on another page too, such as "Debtor 1" and "Case number" (R24). Never a
+    box that prints on one page alone, such as a page total, and never a group's own box.
+    """
+    drawn: dict[str, list[TemplateWidget]] = {}
+    for widget in template_widgets(schema.template_filename):
+        if widget.drawn:
+            drawn.setdefault(widget.full_name, []).append(widget)
+    own = {_key(f) for f in schema.fields if f.repeat is not None}
+    for group in schema.groups.values():
+        own |= set(group.number_boxes.values())
+        own |= {key for boxes in group.page_numbers for key in (boxes.this, boxes.of) if key}
+    headers = {}
+    for key, value in form.items():
+        name, at, tag = parse_key(key)
+        widgets = drawn.get(name, [])
+        here = [
+            w for w in widgets if w.page == page and (tag is None or (at, tag) == (w.page, w.tag))
+        ]
+        if key not in own and here and any(w.page != page for w in widgets):
+            headers[key] = value
+    return headers
+
+
+def _copies(
+    schema: FormSchema,
+    group: GroupSpec,
+    fields: list[FieldSpec],
+    printed: list[FieldSpec],
+    columns: dict[str, str | list[str]],
+    capacity: int,
+    actual: int,
+    form: dict[str, str],
+    session: IntakeSession,
+    ingested_cache: dict,
+) -> list[dict]:
+    """
+    The copies of the group's extra page that print its rows past `capacity` (spec §5.2):
+    each holds as many rows as that page has slots, in the slots' order, numbers them as
+    the group does, and repeats the form's page headers. With copies, every page-number
+    box counts them, the form's own (written into `form`) included (R21). The group's
+    `fields` decide its slots and `printed` the cells that print, as on the form's pages.
+    """
+    page = group.extra_page
+    slots = sorted({f.row for f in fields if f.page == page and f.row})
+    positions = list(range(capacity + 1, actual + 1))
+    copies = []
+    for start in range(0, len(positions), len(slots)):
+        values: dict[str, str] = {}
+        # The last copy may hold fewer rows than the page has slots.
+        for row, position in zip(slots, positions[start : start + len(slots)], strict=False):
+            for f in printed:
+                if f.row == row and f.page == page:
+                    emitted = _cell(f, position, columns, session, ingested_cache)
+                    if emitted is not None:
+                        values[_key(f)] = emitted
+            if row in group.number_boxes:
+                values[group.number_boxes[row]] = group.number.format(n=position)
+        copies.append({"kind": "copy", "page": page, "number": len(copies) + 1, "values": values})
+
+    if group.page_numbers:
+        total = page_count(schema.template_filename) + len(copies)
+        for boxes in group.page_numbers:
+            # Copy n prints right after page `page`, as page `page` + n of the form.
+            position = boxes.page if boxes.page <= page else boxes.page + len(copies)
+            _number_page(form, boxes, position, total)
+            if boxes.page == page:
+                for copy in copies:
+                    _number_page(copy["values"], boxes, page + copy["number"], total)
+    headers = _headers(schema, form, page)
+    for copy in copies:
+        copy["values"] = {**headers, **copy["values"]}
+    return copies
+
+
 def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
+    """The values the form's own pages print: resolve_parts()'s form part."""
+    return resolve_parts(schema, session)["parts"][0]["values"]
+
+
+def resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
+    """
+    The form's values as the parts it prints, in printing order (spec §6):
+    {"version": 2, "parts": [{"kind": "form", "values": {key: value}}, *copies]}.
+
+    A repeat group fills its slots in row order. Rows past its last slot continue on
+    copies of the extra page its declaration names (spec §5.2), each
+    {"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}}.
+    """
     out: dict[str, str] = {}

     from apps.documents.models import IngestedAggregate
@@ -197,7 +299,7 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
             out[_key(f)] = emitted

     # Repeat groups. An unmapped box is dropped before any lookup, so its binding
-    # is never resolved and never counts toward RepeatOverflow (spec §5.1).
+    # is never resolved and never counts as a row (spec §5.1).
     groups: dict[str, list[FieldSpec]] = {}
     for f in schema.fields:
         if f.repeat is None or _unmapped(f):
@@ -205,6 +307,8 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
         if _section_applies(f, session, answer_cache=_form_answers):
             groups.setdefault(f.repeat, []).append(f)

+    copies: list[dict] = []
+    overflowing = []
     for group_name, fields in groups.items():
         capacity = fields[0].repeat_capacity or 0
         resolved_cols = {_key(f): resolve_binding(f.binding, session) for f in fields if f.binding}
@@ -212,28 +316,35 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
             (len(v) for v in resolved_cols.values() if isinstance(v, list)),
             default=0,
         )
+        # UPL guard, as above
+        printed = [f for f in fields if not (f.legal_review and f.source != "asked")]
+        for f in printed:
+            emitted = _cell(f, f.row, resolved_cols, session, _ingested_cache)
+            if emitted is not None:
+                out[_key(f)] = emitted
+        group = schema.groups.get(group_name)
+        if group is not None:
+            for row, key in group.number_boxes.items():
+                if row <= min(actual, capacity):
+                    out[key] = group.number.format(n=row)
         if actual > capacity:
-            raise RepeatOverflow(schema.form_type, group_name, capacity, actual)
-        for f in fields:
-            if f.legal_review and f.source != "asked":
-                continue
-            if f.binding:
-                vals = resolved_cols.get(_key(f))
-                if isinstance(vals, list) and f.row and f.row <= len(vals):
-                    emitted = _emit(f, str(vals[f.row - 1]))
-                    if emitted is not None:
-                        out[_key(f)] = emitted
-            else:
-                emitted = _emit(f, _scalar_value(f, session, ingested_cache=_ingested_cache))
-                if emitted is not None:
-                    out[_key(f)] = emitted
-
-    return out
-
-
-def resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
-    """
-    The form's values as the parts it prints, in printing order (spec §6):
-    {"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}.
-    """
-    return {"version": 2, "parts": [{"kind": "form", "values": resolve(schema, session)}]}
+            if group is None or group.extra_page is None:
+                # The startup check refuses such a schema (forms.E007); never drop a row.
+                raise ValueError(f"{schema.form_type}: group {group_name!r} names no extra page")
+            overflowing.append((group, fields, printed, resolved_cols, capacity, actual))
+
+    # Copies once the form's own values are all in: they repeat its page headers.
+    for group, fields, printed, resolved_cols, capacity, actual in overflowing:
+        copies += _copies(
+            schema,
+            group,
+            fields,
+            printed,
+            resolved_cols,
+            capacity,
+            actual,
+            out,
+            session,
+            _ingested_cache,
+        )
+    return {"version": 2, "parts": [{"kind": "form", "values": out}, *copies]}
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
index ee8ef02..f5b89f5 100644
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -36,7 +36,7 @@ from .registry import (
 )
 from .schema import load_schema
 from .serializers import GeneratedFormSerializer
-from .services.fill_resolver import RepeatOverflow, UnmappedChoice
+from .services.fill_resolver import UnmappedChoice
 from .services.pdf_filler import (
     PDFFormFiller,
     TemplateHasNoForm,
@@ -66,16 +66,12 @@ class IntakeNotFinished(Exception):
 # (registry.py, eligibility/cmi.py, districts/dated_tables.py, which logs its own
 # refusal), and so do UnprintableLetter and ValueTooLong (pdf_filler.py), which name the
 # letter and the box. Every other class gets a fixed sentence, because their messages
-# name form keys, repeat groups and PDF widgets. None names the form: the dashboard shows
+# name form keys and PDF widgets. None names the form: the dashboard shows
 # its label beside the error.
 _FAILURE_SENTENCES = {
     IntakeNotFinished: "Finish your intake before preparing your forms.",
     NotInPacket: "This form isn't part of your packet, based on the answers you've given.",
     FormIsFiled: "This form is marked as filed, so it keeps the answers it was filed with.",
-    RepeatOverflow: (
-        "You have more entries than this form has room for. The extra entries need a "
-        "continuation page, which this app can't make yet."
-    ),
     UnmappedChoice: (
         "One of your answers doesn't match a choice printed on this form, "
         "so it can't be filled in yet."
PATCH
```

`resolve_parts` now holds `resolve()`'s body, and `resolve()` returns its form part. Each group's slots fill as before, through `_cell`, and each slot that holds a row gets its entry number. A group whose rows pass its last slot is kept aside, and once every form value is in, `_copies` puts its remaining rows on copy parts of the extra page. It numbers each row, writes the page numbers on the form part and on each copy (`_number_page`), and adds the form's page headers to each copy (`_headers`). A group that overflows with no extra page raises `ValueError` instead of dropping its rows. `RepeatOverflow` goes, with its import and its 422 sentence in the views.

- [ ] **Step 7: Watch the copy tests fail while drawing still merges every part into the form**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_continuation_copies.py apps/forms/tests/test_fill_resolver.py apps/forms/tests/test_download_action.py apps/forms/tests/test_api_readback.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `12 failed, 45 passed`, with `ValueError: the PDF has 3 pages, but its parts print 4`, `ValueError: the PDF has 3 pages, but its parts print 5` and `test_a_copy_fills_only_the_widgets_on_its_page - AssertionError: assert [(1, 'T1'), (...'), (3, 'T1')] == [(2, 'T1')]`.

The resolver's tests and the refused letter on a copy pass now. Task 5's `fill()` still draws every part's widgets onto the form's own three pages, so `read_drawn` finds no page for the copies and refuses the PDF; and `check()` still plans a copy on every page.

- [ ] **Step 8: Plan each copy on its own page, and draw it alone**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
index 758d737..03dc977 100644
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -251,6 +251,49 @@ def _draw(
         field[NameObject("/V")] = original


+def _clone(form_type: str, template: str) -> pypdf.PdfWriter:
+    """A fresh copy of the template to draw on."""
+    writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
+    if "/AcroForm" not in writer.root_object:
+        raise TemplateHasNoForm(form_type)
+    return writer
+
+
+def _baked(
+    writer: pypdf.PdfWriter, template: str, widgets: tuple[Planned, ...], only: int | None = None
+) -> pymupdf.Document:
+    """
+    Draw the planned widgets on a clone of the template, and bake every page, or with
+    `only`, that one page alone: the widgets that don't print are removed, each planned
+    widget gets its own appearance, and PyMuPDF bakes every widget left into its page.
+    """
+    planned = {(p.widget.page, p.widget.tag): p for p in widgets}
+    acro_form = writer.root_object["/AcroForm"].get_object()
+
+    for number, page in enumerate(writer.pages, start=1):
+        if "/Annots" not in page or (only is not None and number != only):
+            continue
+        kept = ArrayObject()
+        for annot in page["/Annots"]:
+            annotation = annot.get_object()
+            if annotation.get("/Subtype") == "/Widget":
+                widget = widget_for(template, number, annotation, float(page.mediabox.top))
+                if not widget.drawn:
+                    continue
+                if (number, widget.tag) in planned:
+                    _draw(writer, page, acro_form, annotation, planned[(number, widget.tag)])
+            kept.append(annot)
+        page[NameObject("/Annots")] = kept
+
+    buffer = BytesIO()
+    writer.write(buffer)
+    document = pymupdf.open("pdf", buffer.getvalue())
+    if only is not None:
+        document.select([only - 1])
+    document.bake(annots=False, widgets=True)
+    return document
+
+
 class PDFFormFiller:
     """Fill AO court PDF templates with field values and return bytes."""

@@ -260,8 +303,9 @@ class PDFFormFiller:

         Args:
             form_type: a registered form type; its schema names the template.
-            values: a parts document, {"version": 2, "parts": [...]}, whose form part
-                holds {key: value}, or {key: value} alone (parts_of). A key is a full
+            values: a parts document, {"version": 2, "parts": [...]}, or {key: value}
+                alone (parts_of). A form part's {key: value} fills the form's own pages;
+                a copy part's fills only the widgets on its extra `page`. A key is a full
                 name, which fills every drawn widget of that name, or
                 "<full name>@<page>:<tag>", which fills that one widget and wins over
                 the full name there. A value is text, a combo's option, or a box's
@@ -273,35 +317,47 @@ class PDFFormFiller:
             box with its state or "/Off".

         Raises:
-            UnknownField: a key names no drawn widget, or is neither form of key.
+            UnknownField: a key names no drawn widget (on a copy's page, for a copy), or
+                is neither form of key.
             InvalidFieldValue: a box state or combo option the template lacks.
             UnprintableLetter: a letter the box can't print.
             ValueTooLong: a value too long for its box even at 6 pt.
+            ValueError: a part of a kind other than "form" and "copy".
         """
-        return tuple(
-            PlannedPart(part, self._plan(form_type, part["values"])) for part in parts_of(values)
-        )
+        planned = []
+        for part in parts_of(values):
+            if part["kind"] == "form":
+                widgets = self._plan(form_type, part["values"])
+            elif part["kind"] == "copy":
+                widgets = self._plan(form_type, part["values"], page=part["page"])
+            else:
+                raise ValueError(f"{form_type}: no part of kind {part['kind']!r}")
+            planned.append(PlannedPart(part, widgets))
+        return tuple(planned)

-    def _plan(self, form_type: str, values: dict) -> tuple[Planned, ...]:
-        """What each widget one part's {key: value} fills prints, as check() describes."""
+    def _plan(self, form_type: str, values: dict, page: int | None = None) -> tuple[Planned, ...]:
+        """
+        What each widget one part's {key: value} fills prints, as check() describes: on
+        any page of the form, or with `page`, on that page alone.
+        """
         schema = load_schema(form_type)
         by_name: dict[str, list[TemplateWidget]] = {}
         for widget in template_widgets(schema.template_filename):
-            if widget.drawn:
+            if widget.drawn and (page is None or widget.page == page):
                 by_name.setdefault(widget.full_name, []).append(widget)

         reached: dict[str, list[TemplateWidget]] = {}
         unknown = []
         for key in values:
             try:
-                name, page, tag = parse_key(key)
+                name, at, tag = parse_key(key)
             except ValueError:
                 unknown.append(key)
                 continue
             reached[key] = [
                 widget
                 for widget in by_name.get(name, ())
-                if tag is None or (widget.page, widget.tag) == (page, tag)
+                if tag is None or (widget.page, widget.tag) == (at, tag)
             ]
             if not reached[key]:
                 unknown.append(key)
@@ -345,7 +401,9 @@ class PDFFormFiller:
         check() plans every widget first. pypdf then builds each planned widget's own
         appearance at its planned size; the widgets the template doesn't print and the
         second widget of each stacked pair are removed; and PyMuPDF bakes every other
-        widget into its page. An unfilled widget prints as the blank form shows it.
+        widget into its page. An unfilled widget prints as the blank form shows it. Each
+        copy of an extra page is drawn alone, on a clone of the template of its own, and
+        goes in right after that page, or after the copy of it before (spec §5.2).

         Args:
             form_type: a registered form type; its schema names the template.
@@ -353,37 +411,22 @@ class PDFFormFiller:

         Raises:
             TemplateHasNoForm: the template has no /AcroForm.
-            UnknownField, InvalidFieldValue, UnprintableLetter, ValueTooLong: as check().
+            UnknownField, InvalidFieldValue, UnprintableLetter, ValueTooLong, ValueError:
+                as check().
         """
         template = load_schema(form_type).template_filename
-        writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
-        if "/AcroForm" not in writer.root_object:
-            raise TemplateHasNoForm(form_type)
-        planned = {
-            (p.widget.page, p.widget.tag): p
-            for part in self.check(form_type, values)
-            for p in part.widgets
-        }
-        acro_form = writer.root_object["/AcroForm"].get_object()
-
-        for number, page in enumerate(writer.pages, start=1):
-            if "/Annots" not in page:
+        writer = _clone(form_type, template)
+        planned = self.check(form_type, values)
+        form = tuple(p for part in planned if part.part["kind"] == "form" for p in part.widgets)
+        document = _baked(writer, template, form)
+        shown = list(range(1, len(document) + 1))  # the template page each page shows
+        for part in planned:
+            if part.part["kind"] != "copy":
                 continue
-            kept = ArrayObject()
-            for annot in page["/Annots"]:
-                annotation = annot.get_object()
-                if annotation.get("/Subtype") == "/Widget":
-                    widget = widget_for(template, number, annotation, float(page.mediabox.top))
-                    if not widget.drawn:
-                        continue
-                    if (number, widget.tag) in planned:
-                        _draw(writer, page, acro_form, annotation, planned[(number, widget.tag)])
-                kept.append(annot)
-            page[NameObject("/Annots")] = kept
-
-        buffer = BytesIO()
-        writer.write(buffer)
-        document = pymupdf.open("pdf", buffer.getvalue())
-        document.bake(annots=False, widgets=True)
+            page = part.part["page"]
+            copy = _baked(_clone(form_type, template), template, part.widgets, page)
+            at = max(i for i, template_page in enumerate(shown) if template_page == page) + 1
+            document.insert_pdf(copy, start_at=at)
+            shown.insert(at, page)
         document.xref_set_key(document.pdf_catalog(), "AcroForm", "null")
         return document.tobytes()
PATCH
```

`check()` plans a `form` part on every page, a `copy` part only on its own page (`_plan`'s new `page`), and refuses any other kind. `fill()` moves its draw-and-bake loop into `_baked`, and the template clone into `_clone`. It draws the form's parts on one clone as before, then each copy on a clone of its own: only the copy's page is drawn, PyMuPDF keeps that page and bakes it, and `insert_pdf` puts it right after the extra page or the copy before it. `/AcroForm` is set to null once, at the end.

- [ ] **Step 9: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_continuation_copies.py apps/forms/tests/test_fill_resolver.py apps/forms/tests/test_download_action.py apps/forms/tests/test_api_readback.py apps/forms/tests/test_checks.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `140 passed`.

That is `test_continuation_copies.py` 11, `test_fill_resolver.py` 24, `test_download_action.py` 16, `test_api_readback.py` 6 and `test_checks.py` 83.

- [ ] **Step 10: Watch the copy tests fail when the form also draws its copies' widgets**

```bash
set -eo pipefail
cp backend/apps/forms/services/pdf_filler.py backend/apps/forms/services/pdf_filler.py.keep
trap 'mv backend/apps/forms/services/pdf_filler.py.keep backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -417,7 +417,7 @@
         template = load_schema(form_type).template_filename
         writer = _clone(form_type, template)
         planned = self.check(form_type, values)
-        form = tuple(p for part in planned if part.part["kind"] == "form" for p in part.widgets)
+        form = tuple(p for part in planned for p in part.widgets)
         document = _baked(writer, template, form)
         shown = list(range(1, len(document) + 1))  # the template page each page shows
         for part in planned:
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_continuation_copies.py apps/forms/tests/test_download_action.py::test_rows_past_the_slots_download_on_a_copy -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `5 failed, 7 passed`, with `test_extra_rows_print_on_copies_of_the_extra_page - AssertionError`, `test_entry_and_page_numbers_continue_on_each_copy[one copy] - AssertionError: assert ['2.6', '2.4'` and `test_rows_past_the_slots_download_on_a_copy - AssertionError`.

Here the form's own pages also draw every copy's widgets, as Task 5's `fill()` did, while each copy is still drawn and inserted. Page 2's first slot then prints the sixth row and "2.6" where the third row and "2.3" belong (Task 5's finding 6). The block restores `pdf_filler.py` from the copy it kept, pass or fail; each mutation block below does the same with its file.

- [ ] **Step 11: Watch the synthetic group fail startup when groups aren't read**

```bash
set -eo pipefail
cp backend/apps/forms/schema.py backend/apps/forms/schema.py.keep
trap 'mv backend/apps/forms/schema.py.keep backend/apps/forms/schema.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -145,7 +145,7 @@
                 for boxes in group.get("page_numbers", [])
             ),
         )
-        for name, group in raw.get("groups", {}).items()
+        for name, group in {}.items()
     }

     return FormSchema(
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_checks.py::test_a_group_continued_on_copies_of_its_extra_page_passes -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_a_group_continued_on_copies_of_its_extra_page_passes - assert [('forms.E007...d in groups')] == []`.

Here `load_schema` ignores `groups`, so the synthetic group is undeclared. The test proves that conftest's synthetic Schedule D is a schema startup accepts.

- [ ] **Step 12: Watch E/F's page count fail when each page's count box is its own writer**

```bash
set -eo pipefail
cp backend/apps/forms/schema.py backend/apps/forms/schema.py.keep
trap 'mv backend/apps/forms/schema.py.keep backend/apps/forms/schema.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -276,7 +276,7 @@
             if p.this:
                 boxes.append((("this", group_name, p.page), p.this))
             if p.of:
-                boxes.append((("of", p.of), p.of))
+                boxes.append((("of", p.page), p.of))
         for writer, key in boxes:
             try:
                 name, at, tag = parse_key(key)
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_checks.py::test_a_page_count_box_drawn_on_two_pages_is_one_writer -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_a_page_count_box_drawn_on_two_pages_is_one_writer - assert [('forms.E006...s on page 5')] == []`.

Here E006 counts one writer per page an `of` key is declared for, so E/F's `fill_27.1.7`, declared for pages 5 and 6, conflicts with itself.

- [ ] **Step 13: Watch a column of boxes with their own states fail when a box slot counts widgets**

```bash
set -eo pipefail
cp backend/apps/forms/schema.py backend/apps/forms/schema.py.keep
trap 'mv backend/apps/forms/schema.py.keep backend/apps/forms/schema.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -331,7 +331,7 @@
             widgets = drawn.get(f.pdf_field, ())
             if f.type in ("checkbox", "radio"):
                 states = [s for w in widgets for s in set(w.states)]
-                twinned = len(states) > len(set(states))
+                twinned = len(widgets) > 1
             else:
                 twinned = len(widgets) > 1
             if f.tag is None and twinned:
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_checks.py::test_an_untagged_box_slot_whose_boxes_each_have_their_own_state_passes -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_an_untagged_box_slot_whose_boxes_each_have_their_own_state_passes - assert [('forms.E007...needs a tag')] == []`.

Here an untagged box slot is refused whenever its name has more than one drawn widget, which refuses Schedule D's `check 4`, four boxes with four states, where one answer ticks one box (re-review 3).

- [ ] **Step 14: Say in the docs what a group declares and what startup refuses**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 9ae6cc6..ea8c6b2 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -34,11 +34,11 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
 - **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. Generate, Generate All and Regenerate check without drawing: each resolves the form's parts (`build_parts`), runs `PDFFormFiller.check()` and stores them, so a letter the form can't print or a value too long for its box is a 422, or a Generate All `errors` entry, carrying its `step` or `page`. Download draws: `fill()` bakes with PyMuPDF, which isn't thread-safe, so the server stays on sync gunicorn workers with no `--threads` unless the bake gets a lock. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download draws its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
-- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
+- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. For repeat groups, E007 refuses one not declared in the schema's `groups`, an `extra_page` that isn't the page of the group's last slots, a `number` without `{n}` (also when only `number_boxes` is set), one that `format(n=1)` can't fill or that prints the same for `n=1` and `n=2`, a second group with an `extra_page` on one form (3a2's limit), fields that differ in `repeat_capacity` or `conditional_on` or whose slot rows aren't exactly 1 to `repeat_capacity`, a slot row whose boxes sit on more than one page, rows that go back a page as the row number rises, and an untagged slot binding that would print its row more than once: a text or combo one whose name has more than one drawn widget, or a checkbox or radio one whose drawn widgets share an on-state (a column whose boxes each have their own state, such as Schedule D's `check 4`, passes); E003 refuses a number box for a row that isn't a slot row, a number or page-number box that is no drawn widget on its row's or page's page, an untagged number or page-number `this` box whose name has more than one drawn widget, and any untagged binding whose `page` holds no drawn widget of its name (a copy picks its rows' boxes by `page`); and E006 counts each group box (`number_boxes` values and `page_numbers` `this` and `of`, one `of` key once) as a writer beside the bindings. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. Tiers 1 and 3 read the printed page, not `/V`: `read_drawn` (`apps/forms/tests/pdf_readback.py`) takes a widget's Helvetica text and the template's ZapfDingbats check mark inside its rect, and reads `""` where a box prints only the blank template's own default (the district combos' placeholder, A/B `19.1`–`19.3 % of ownership` "0%", C `page 2` and G `fill 2.6` "2"), so a blank assertion on such a box can't see that default. `read_drawn` refuses a PDF that still has a widget (a `ValueError`, never a listed defect), so it reads only `fill()`'s baked output. The list has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
-- **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, the one function behind all of them; any other error fails the form). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine (`repeat`, `RepeatOverflow` and its 422) stays for later steps; only synthetic tests reach it.
-- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, a parts document in printing order: `{"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}` (`registry.build_parts`). The API never returns it. `form_data` is blank; its column is dropped one release after this code is live. Generate, Generate All and Regenerate store the document they checked; an unfiled form is resolved, checked and drawn fresh on every download, and its document stored again. A filed form draws its stored document, so it prints exactly what was filed. A form filed before forms step 3a2 holds `{full name: value}` with no `version`, which `parts_of` (`pdf_filler.py`) reads as one form part. A filed form whose stored values `check()` refuses downloads as a 422 with the refusal's sentence and no `step` or `page`, since no step changes what was filed.
+- **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, the one function behind all of them; any other error fails the form). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine stays for later steps, and only synthetic tests reach it: a repeat group (`repeat`) is declared in the schema's top-level `groups` with the `extra_page` that continues it (forms.E007 refuses a group without one), and rows past its last slot print on copies of that page, each a `copy` part drawn alone and put in right after the page or the copy before it, numbered by the group's `number` and `page_numbers` boxes. `RepeatOverflow` is gone.
+- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, a parts document in printing order: `{"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}` (`registry.build_parts`). The API never returns it. Each copy of an extra page follows the form part as a part of its own, `{"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}}`. `form_data` is blank; its column is dropped one release after this code is live. Generate, Generate All and Regenerate store the document they checked; an unfiled form is resolved, checked and drawn fresh on every download, and its document stored again. A filed form draws its stored document, so it prints exactly what was filed. A form filed before forms step 3a2 holds `{full name: value}` with no `version`, which `parts_of` (`pdf_filler.py`) reads as one form part. A filed form whose stored values `check()` refuses downloads as a 422 with the refusal's sentence and no `step` or `page`, since no step changes what was filed.
 - **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
 - **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
 - **CI ruff is pinned** — `ci.yml` installs `ruff==0.8.5`. Unpinned ruff broke CI when new rules shipped.
PATCH
```

In `CLAUDE.md`:

- "Schemas are checked at startup" lists the group rules: E007's, E003's and E006's counting of group boxes.
- "Blank, not 0.00, on the forms" says a repeat group is declared in `groups` with the `extra_page` that continues it, that rows past its last slot print on copies of that page drawn alone and numbered, and that `RepeatOverflow` is gone.
- "`field_values`, not `form_data`" gives the copy part's shape.

- [ ] **Step 15: Run every gate**

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

Expected: `2753 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  397 passed (397)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

That is 55 more backend cases than after Task 5: the 38 new items in `test_checks.py`, `test_continuation_copies.py`'s 11, 3 more in `test_fill_resolver.py` and 3 more in `test_download_action.py`. No frontend file changes. Under a heavy load (1-minute load above 15) a SOFAStep or FormDashboard test can run past vitest's 5 s per-test timeout; run vitest again on a quieter machine before suspecting the code. The 25 skips are the Postgres-only tests under sqlite. The next command runs them against the Postgres database named by `DATABASE_URL` in `.claude/forms-step3a2.env`, as CI's "Run the Postgres-only tests" step does.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

This task touches no locking, so they pass unchanged.

- [ ] **Step 16: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_continuation_copies.py \
  CLAUDE.md \
  backend/apps/forms/schema.py \
  backend/apps/forms/services/fill_resolver.py \
  backend/apps/forms/services/pdf_filler.py \
  backend/apps/forms/services/widgets.py \
  backend/apps/forms/tests/conftest.py \
  backend/apps/forms/tests/pdf_readback.py \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_checks.py \
  backend/apps/forms/tests/test_download_action.py \
  backend/apps/forms/tests/test_fill_resolver.py \
  backend/apps/forms/views.py
git commit -F - <<'MSG'
feat(forms): continue rows past a group's last slot on copies of its extra page

A repeat group used to stop at its template's printed slots: one row
more raised RepeatOverflow, a 422 saying the app couldn't make a
continuation page. The court forms that have an extra page (D, E/F, G,
H, C) ask the filer to copy it, so rows past the last slot now print on
copies of that page (3a2 spec §5.2). No production schema has a repeat
group yet; 3a2 proves it on synthetic Schedule D groups (§5.4).

- A schema declares its groups in a top-level "groups":
  {"<group>": {"extra_page": int, "number": "2.{n}",
  "number_boxes": {"<slot row>": "<key>"},
  "page_numbers": [{"page": int, "this": key, "of": key}]}}, read into
  FormSchema.groups as GroupSpec and PageNumberBoxes.
- The startup check (forms.E007) refuses, for a repeat group:
  - one that isn't declared, or names no extra_page;
  - an extra_page that isn't the page of the group's last slots;
  - a number without {n}, also when only number_boxes is set, one
    whose format(n=1) raises anything ("2.{n}{m}", "2.{n}{n[0]}"), or
    one that prints the same for n=1 and n=2 ("2.{{n}}");
  - fields with more than one repeat_capacity or conditional_on, so a
    group applies whole or not at all;
  - slot rows (unmapped boxes aside) other than exactly 1 to
    repeat_capacity, since a capacity below the slots would print a row
    twice and one above them would print a row nowhere;
  - a slot row whose boxes sit on more than one page, since a copy
    takes a row's boxes from its own page only;
  - rows that go back a page as the row number rises (R58);
  - an untagged slot binding that would print its row more than once: a
    text or combo one whose name has more than one drawn widget, or a
    checkbox or radio one whose drawn widgets share an on-state, so that
    one answer ticks them all (R59, R60). A column whose boxes each have
    their own state, such as Schedule D's "check 4", ticks only the
    answer's box, so it passes;
  - a second group with an extra_page on one form: 3a2 numbers pages
    counting one group's copies (R21, R56), and 3c lifts the limit.
  forms.E003 refuses a number box for a row that isn't a slot row, a
  number or page-number box that is no drawn widget on its row's or
  page's page, an untagged number or page-number "this" box whose name
  has more than one drawn widget (it would print its number in each),
  and, for every binding, an untagged one whose page holds no drawn
  widget of its name (a tagged one's page and tag were already
  checked). T6 makes a binding's page decide which slots a copy holds,
  so a page typo would otherwise drop a cell or fail Generate. A null
  page is refused this way too, not compared with a number.
  forms.E006 counts every key a group writes, each number box and each
  page-number "this" and "of", as a writer of the widgets it names
  beside the bindings, so a group box on a bound widget (by either
  spelling) or on another box is refused, two rows naming one box
  included. A page count is the same on every page, so one "of" key
  declared for two pages counts once.
- resolve_parts() fills a group's slots in row order as before. Rows
  past the last slot go onto copy parts, {"kind": "copy", "page",
  "number", "values"}, as many to a copy as the extra page has slot
  rows, in the same slot order. legal_review decides which of a slot's
  boxes print, never which slots exist, on copies as on the form's own
  pages. Each slot holding a row, on the form's own pages and on
  copies, gets its entry number ("2.{n}", n the row's position in the
  whole group). With at least one copy, every page-number box counts
  the copies: a page up to the extra page keeps its number, copy i is
  the extra page plus i, a later page moves down by the number of
  copies, and "of" is the page count with the copies (R21). A copy
  repeats the form's page headers, the boxes whose full name also
  prints on another page ("Debtor 1"), but never a box that prints on
  one page alone, such as page 2's total (R24), and never a group's own
  box, so an empty slot on the last copy stays blank. Because startup
  requires the capacity to be the slots, the extra page to hold at
  least one slot and be the page of the last slots, each binding's page
  to draw its widget, each slot row to sit on one page and the rows to
  run forward in page order, every row of a group that applies goes to
  exactly one slot, on the form or on a copy, and no row lands on a
  page before an earlier row's. Rows past the slots of a group with no
  extra page, which startup refuses, raise a ValueError rather than
  vanish. resolve() returns the form part's values, so
  build_field_values() keeps its shape.
- check() plans a copy part only against the widgets on its page, and
  refuses a part of a kind it doesn't know (ValueError). fill() draws
  the form's parts on one clone as before, then each copy alone: a
  clone of its own, its page drawn, the rest dropped, baked, and put in
  right after the extra page or the copy before it. A copy's widgets
  are never merged into the form's, which T5's fill() did (R54).
- RepeatOverflow is gone, with its 422 sentence in the views.
- read_drawn(form_type, pdf_bytes, parts) reads each copy as the
  template page it copies; DrawnWidget gains copy (None on the form's
  own pages). It refuses a PDF whose page count isn't the template's
  plus its copies', so a copy can never be read as another page.

The tests the change breaks are fixed here: the two E006 tests of a
repeat group on Schedule I declare their group, and the one whose first
row is untagged is refused by E007 as well, since page 2 draws that
row's name twice; test_repeat_overflow_raises
becomes test_rows_past_the_slots_go_to_copies_of_the_extra_page (seven
rows, two slots on the extra page: two copies, the last holding one
row); the download test of the RepeatOverflow sentence becomes a
download of six rows, a 200 whose stored parts hold the copy; and the
untagged print-button binding on Form 101 is now refused by E003 as
well as E004, as a tagged one already was.

New tests, over conftest's synthetic Schedule D (the real schema plus a
group on Part 1's five rows, bound to SOFA creditor payments, continued
on page 2; R18, R19), and a second fixture whose one group is Part 2's
six entries on page 3, the template's last:
- six rows put the sixth on one copy of page 2, read from the third of
  four pages, while page 2 keeps the third row;
- the copy repeats "Debtor 1" but not page 2's total;
- entry and page numbers run 2.3 to 2.6 and 1 to 4 of 4 with one copy,
  and 2.3 to 2.9 and 1 to 5 of 5 with two;
- three or five rows print no copy and no page number, and number only
  the slots that hold a row;
- a copy of the last page goes after it;
- a letter the form can't print in a row that only a copy holds is
  refused naming the SOFA page, as on the form;
- a filed form with a copy downloads exactly what was filed, after the
  filer's rename and a deleted row;
- with every page-2 slot box legal_review and not asked, six and eight
  rows download (no 500) with the rows numbered in their slots on page
  2 and the copy, and no guarded name or amount printed anywhere;
- a copy plans only its own page's widgets, and a part of an unknown
  kind is refused;
- the startup check passes the synthetic group and refuses each broken
  declaration, each number that can't number rows, each capacity or
  condition that differs from the slots, a second group with an extra
  page (one with none isn't counted), a slot box declared on the page
  before or after its widget's or on no page, a row on two pages with
  every page right, rows that go back a page, a number box on a slot's
  box or on a bound widget's tagged spelling, two rows naming one
  number box, a page-number box on a slot's box, a number box on the
  page of an unmapped box of its row rather than its row's own, an
  untagged slot or number box whose name is drawn on several pages, an
  untagged number box or text slot whose name is drawn twice on its own
  page, and an untagged box slot whose boxes share one state (Schedule
  D's "check 5"); E/F's one "of" box drawn on pages 5 and 6 passes, and
  so does an untagged slot on D's "check 4", four boxes with four
  states; outside any group, an untagged binding on a page without its
  widget is refused;
- a copy never repeats a row from the form, a legal_review row prints
  neither in the slots nor on a copy, and a group with no extra page
  never drops a row.
The creditor_payments test helper names a creditor for any count.

CLAUDE.md: "Blank, not 0.00" describes copies, and RepeatOverflow is
gone; "Schemas are checked at startup" lists the group rules;
"field_values, not form_data" gives the copy part's shape.
MSG
git status --short
```
