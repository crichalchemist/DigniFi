# Forms Step 3a2 (Drawing Engine) Implementation Plan, Part 4 of 4

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Print every court form through one engine. Each widget gets its own value, drawn with the template's own layout, and the page is flattened, so the packet has no fillable fields left. A letter the form's font can't print, or a value too long for its box even at 6 pt, is refused in plain words, and the dashboard links the refusal to the step or page that fixes it. Extra rows continue on copies of a form's extra page or on an attached sheet (proven on synthetic schemas). Generate All checks without drawing; Download draws.

**Architecture:** `apps/forms/services/widgets.py` addresses every template widget by page and index tag, so a binding can name one widget of a shared name (`<full name>@<page>:<tag>`). `PDFFormFiller.check()` plans each widget from cached widget maps and fonts without opening a PDF: the letters its font prints, the size its value fits at (mirroring pypdf 6.13.1's layout, `text_fit.py`), and where to fix a refusal (`RULE_FIXES`, `fix_for`). `fill()` runs `check()`, builds each planned widget's appearance with pypdf, removes the widgets that never print, bakes with PyMuPDF and nulls `/AcroForm`. `field_values` stores parts (`{"version": 2, "parts": [...]}`): the form, its continuation copies and its attached sheet. The tests read what is printed on the page (`read_drawn`). Each of the 9 tasks is one commit, and every task boundary passes every gate.

**This part:** Task 9. It starts where Part 3 ends, with Tasks 1–8 committed on this branch. The other parts: Part 1 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part1.md`, Tasks 1–4), Part 2 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part2.md`, Tasks 5–6), Part 3 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part3.md`, Tasks 7–8). The plan is split only to stay under the repository's 500 KB file limit. Run all parts as one execution: one ledger for Tasks 1–9, and the whole-branch final review only after Task 9, because each part's patches expect each file exactly as the earlier tasks leave it.

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

Check that Part 3 is in place: Task 8's commit is on this branch. Review fixes may have added commits after it.

```bash
set -eo pipefail
git log --format=%s 4690d12..HEAD | grep -Fx "feat(forms): link each refusal on the dashboard to its fix; no retry" >/dev/null
echo "Part 3 is in place"
```

Expected: `Part 3 is in place`. If the block fails instead, Task 8 isn't committed: finish Part 3 first.

Check the baseline before Task 9:

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

Expected: `2797 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  420 passed (420)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

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

### Task 9: What the whole-branch review found: composed letters, and the gaps across tasks

_Built and verified as commit `54410ef` on `plan/forms-step3a2`._

**Files:**

- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/management/commands/time_packet.py`
- Modify: `backend/apps/forms/schema.py`
- Modify: `backend/apps/forms/services/pdf_filler.py`
- Modify: `backend/apps/forms/tests/test_attached_sheets.py`
- Modify: `backend/apps/forms/tests/test_check.py`
- Modify: `backend/apps/forms/tests/test_checks.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier1.py`
- Modify: `backend/apps/forms/tests/test_printed_page.py`
- Modify: `backend/apps/forms/tests/test_rule_fixes.py`
- Modify: `backend/apps/forms/tests/test_time_packet.py`
- Modify: `docs/superpowers/specs/2026-10-16-forms-step3-design.md`
- Modify: `frontend/src/pages/FormDashboard.tsx`
- Modify: `frontend/src/pages/__tests__/FormDashboard.test.tsx`
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`

**Interfaces:**

- Consumes:
  - In `backend/apps/forms/services/pdf_filler.py` (Tasks 2, 5 and 7):
    - `_as_printed(text: str) -> str`: a tab and every Unicode space separator (Zs) as a plain space, format characters (Cf) left out (R36). It is the one way into the letter rules: `PDFFormFiller.check` passes each text or combo value through it before `_refused_letter` and `fit()` (so `Planned.value`, the text the drawing prints, is its text), and `sheets._check`, `sheets._lines` and `sheets.prints_whole` call it too; startup's sheet title and label checks (`schema.py`) go through `prints_whole`.
    - `_refused_letter(text: str, prints: Callable[[str], bool], comb: bool = False) -> str | None`: the first letter the font can't print, or a control character other than a line break.
    - `_source(schema: FormSchema, key: str, widget: TemplateWidget) -> tuple[str, dict[str, str]]`: a refusal's box label and fix, from the binding that produced the key (its `label` and `fix_for(field)`); a key no binding produced gets the field index row's label and `{}`.
    - `check()` plans full names before widget keys, `for key in sorted(reached, key=lambda key: "@" in key)`, so a widget's own key wins over its full name.
    - `class UnprintableLetter(Exception)` with `letter`, `label`, `step` and `page`; `str()` is the spec §4.5 sentence.
  - `load_index(template_filename)` (`apps/forms/field_index.py`): each full name's index rows, with `page`, `tag` and `label`.
  - In `backend/apps/forms/management/commands/time_packet.py` (Task 5): `python manage.py time_packet --session <id> [--budget-generate 5] [--budget-download 3]`, which runs Generate All's checks and every packet form's download in one rolled-back transaction, and raises four `CommandError`s, each chained `from exc`: `No session <id>.`, `The session was refused: <type>`, and `<form> was refused: <type>` in the check loop and in the download loop. It imports `_generate_and_persist(session, form_type, user)`, `_prepare(session)` and `_resolve(form_type, session) -> dict` from `apps/forms/views.py`.
  - From `apps/forms/views.py`: `generate_all` returns a filed form untouched in `generated` (DIG-155); `download` draws a filed form's stored `field_values` when it has them (`filed = generated_form.status == "filed" and bool(generated_form.field_values)`), and otherwise prepares and resolves the form from the intake; `class IntakeNotFinished(Exception)` has `page = "/intake"`.
  - `GeneratedForm` (`apps/forms/models.py`): `session`, `form_type`, `status` (`"generated"` or `"filed"`), `generated_by` and `field_values` (encrypted JSON text, `""` when nothing was stored).
  - `class IncomeNotSplit(ValueError)` (`apps/eligibility/cmi.py`) with the class attribute `step = "income_info"`; `class PreconditionMissing(Exception)` (`apps/forms/registry.py`), raised in three places in `registry.py` with `step="debtor_info"` or `step="review"`.
  - In `backend/apps/forms/schema.py`, `validate_schema` (Tasks 6 and 7): for each repeat group, `rows` (every slot field of the group) and `mapped` (the slots `fill_resolver._unmapped` doesn't skip; a box whose `choices` is `{}` is unmapped), and Task 7's sheet-group rules, which read `mapped`.
  - `RULE_FIXES` and `DERIVATIONS` (`apps/forms/services/derivations.py`), `fix_for(field: FieldSpec) -> dict[str, str]` (`fill_resolver.py`), `get_all_form_types()` and `load_schema(form_type)`. `settings.BASE_DIR` is `backend/` (`config/settings/base.py`).
  - From Task 8: `frontend/src/constants/wizardSteps.ts` (`WIZARD_STEPS`, each entry with `key: '<key>'`); in `FormDashboard.tsx`, `PAGE_LINK_LABELS` (keys `'/intake'`, `'/fee-waiver'`, `'/sofa'` and `'/documents'`), the `formRefusals` state with `setFormRefusals` and `setFormRefusal(formType, refusal | undefined)`, and `handleGenerateAll`, whose success path cleared the refusal of each form in `response.generated` and whose `catch` sets `setGenerateAllRefusal(refusalOf(err, ERROR_GENERIC))`; in `IntakeWizard.tsx`, `linkedStep` and the session read's `.then`, and `updateCurrentStep` from `useIntake()` (`frontend/src/context/IntakeContext.tsx`), which sends nothing while the context holds no session.
  - For the tests:
    - `test_check.py`: `_plan(form_type, values)` (the planned widgets of the one form part), `_widgets(form_type, full_name)` (the name's drawn widgets) and `LAST_NAME = "Debtor1.Last name"`.
    - `test_attached_sheets.py`: the `session` fixture (Maria Torres's completed intake, with the synthetic Schedule A/B sheet group `ab_line_3`), `creditor_payments(session, count, names=None)` (`conftest.py`), `MAKES`, `_drawn(session)` (Schedule A/B's parts and drawn PDF), `_spec()`, and `read_sheets(pdf_bytes, spec)` and `read_drawn(form_type, pdf_bytes, parts)` (`pdf_readback.py`).
    - `test_form_views.py`: `api_client` and `session_with_debtor`.
    - `test_time_packet.py`: the `session` fixture (a completed intake with no means test and no forms).
    - `test_checks.py`: `_text(pdf_field, page, tag)` (a constant text binding of one widget), `_community_property_boxes(d)`, `_AB = "schedule_a_b: group 'ab_line_3'"` and the cases of `test_a_sheet_that_cannot_print_its_rows_whole_is_reported`.
    - `test_oracle_tier1.py`: `_box_fill(form_type, position)` (`@cache`), `_drawn(form_type, values)` and `_fields(form_type, types)`.
    - `test_printed_page.py`: `_template(form_type)` and `_cut_off(form_type, values)` (each box whose value reads back other than whole).
    - `FormDashboard.test.tsx`, in the describe "when a form’s Generate or Download is refused": `cardOf(label)`, `downloads(...responses)` (answers Form 101's downloads in turn), `refused(body, status = 422)`, `generateAll()` (opens Generate All and confirms the UPL notice), `LETTER`, `INCOME_NOT_SPLIT` and `GENERATED` (Form 101, generated, id 1).
    - `IntakeWizard.test.tsx`, in the describe "IntakeWizard session re-read": `savedAs(saved)` (serves the session and counts `update_step` calls in the returned `{ count }`) and `sessionAtStep8`; the file already imports `IntakeProvider`, `useIntake`, `MemoryRouter`, `Routes`, `Route` and `useNavigate`.
- Produces:
  - `_as_printed(text)` composes the text (`unicodedata.normalize("NFC", text)`) before the space, format and control-character rules: still the one entry for `check()`, the drawing and the sheets.
  - `_source` gives a binding with an empty label the field index row's label and the binding's own fix.
  - `time_packet` skips a filed form in its Generate All loop, in its download loop draws a filed form's stored `field_values` (`json.loads`) when it has them, and prints `filed` in the check column; each of its four `CommandError`s is raised `from None`.
  - E007, for a sheet group: the column rule and the unprinted rule read every slot (`rows`), and two new messages, `group '<group>': a box slot fills '<box>' on row <n>, and a sheet can't tick a box` and `group '<group>': no sheet column prints '<box>' on row <n>, a slot of the group that binds no list`.
  - `FormDashboard.tsx`: when Generate All answers with its lists, `setFormRefusals({})`.
  - `test_rule_fixes.py`: `FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"`, `_wizard_steps()`, `_pages()`, `_precondition_steps()` and the test `test_every_fix_is_a_step_or_page_the_dashboard_links`, which skips where `FRONTEND` isn't a directory.
  - The new and changed tests listed in Step 1.
  - `CLAUDE.md`: "Forms need a completed intake", "GenerateAll vs single", "Schemas are checked at startup", "`field_values`, not `form_data`" and the Architecture PDF line. The umbrella spec's SPIKE row (`docs/superpowers/specs/2026-10-16-forms-step3-design.md`).
  - Where the commit differs from tasks.md: the Interfaces table's Task 9 row names only `_as_printed`, while the commit also changes `_source`, `time_packet`'s check column and its filed-form download, E007's messages and the dashboard's clearing (all in tasks.md's T9 bullets except the stored-values download, which the m5 bullet doesn't mention). Fix round 1 (R72) goes past the T9 bullets: the m12 column rule reads every slot too, the m18 test also reads the exceptions' own targets, `time_packet` has a test for a filed form stored without values, and a dashboard test pins that a refusal of the whole call leaves the cards'. The m6 wording changes three `CLAUDE.md` gotchas, not the two the bullet names.

**Decisions already made in this task:**

_Why a task of its own:_

- **R71: the whole-branch review's fixes are Task 9, one commit on Task 8.** The review of Tasks 1–8 together (findings F1–F3 and m1–m18) found them after each task had been reviewed and approved alone. Folding each fix back into the task it belongs to (Tasks 2, 3, 5, 7 and 8) would change those commits, and every later section would need checking again. As a task of its own, each earlier commit stays exactly as it was reviewed. The cost is a task that mixes unrelated fixes, so its steps are grouped by what each fix changes.

_Letters (F1, spec §4.3):_

- **R71 (F1): `_as_printed` composes the text (Unicode NFC) first, and only there.** A letter typed as a base letter and a combining mark (e and U+0301, as text pasted from a macOS file name or some PDFs arrives) was refused at the mark. Form 101 was then a 422 for a letter it prints, quoting a lone accent: "The court form can't print the letter “́” in “First name”. Change it to a letter without the mark." Composing in `_as_printed` reaches every letter rule at once: `check()`, the drawing (which prints `fit()`'s text) and the sheets (`sheets._check`, `_lines` and `prints_whole`) take the same composed text, so what is checked, measured and drawn can't drift apart. A comb box counts composed letters: the review drew a decomposed "é1ñ2" in Schedule D's four-cell `account number@1:T32` as four cells. The stored values don't change: the views store `build_parts`' values as the intake holds them.
- **NFC, not NFKC.** NFKC also rewrites compatibility characters that the font prints as they are. The review's NFKC mutant fails the every-letter tests that already existed (`test_check_agrees_with_the_drawing_on_every_letter` and the sheets' letter check).
- **NFC changes no letter that already printed.** The review read the 255 letters that all 17 templates' `/Helv` prints: NFC changes none of them, none is a combining mark, and no two of them compose. So the every-letter tests' expectations stand.
- **Six canonical singletons now print (accepted).** NFC maps six single code points that the font refuses alone to a letter it prints: U+037E (Greek question mark) to ";", U+0387 (Greek ano teleia) to "·", U+1FEF (Greek varia) to the grave accent U+0060, U+1FFD (Greek oxia) to "´", U+212A (Kelvin sign) to "K" and U+212B (Ångström sign) to "Å". `check()` now accepts them and prints the equivalent. Unicode counts each pair as the same character, and the two draw the same glyph, so the controller and the review accepted this on a sworn form.
- **A mark no letter takes is still refused at the mark.** n with U+0308 (n̈) has no composed form, so U+0308 is refused itself, with the letter sentence. That sentence is the owner's to settle (W-1, widened by R71 for review finding m10).
- **What the letter tests draw:** decomposed é, ñ and ü are planned on Form 101 as the composed letter at 10 pt; é and ñ are drawn and read back in every Schedule A/B name box ("José Muñoz") and in its sheet's header; ü is drawn on the sheet ("Citroën Müller"). No test draws a decomposed ü in a form box: planning and drawing take the same text, and `test_check_agrees_with_the_drawing_on_every_letter` ties what `check()` accepts to what the drawing prints (the implementer's call). Through the API, a first name saved decomposed now generates Form 101 (200, where it was 422); the review also saved one through the wizard's PATCH, then Complete and Generate, and got 200.

_A refusal's label (m11):_

- **`_source` falls back to the field index's label when the binding's label is empty, and keeps the binding's fix.** Schedule J binds 20 text boxes with an empty label, so a refusal there read “” for the box. Box `7` now reads "Food and housekeeping supplies", still with `step: "expense_info"` (the review's probe: all 20 name their index label and keep their step). No production binding of the filer's name has an empty label, so a sheet's refused name, which takes the name box's label, can't meet this case.

_Tests that couldn't fail (F2, F3, m1, m2, m17):_

- **F2:** `test_a_widgets_own_key_fills_only_that_widget` plans the values in both orders. With the full name first, as before, dict order gave the expected widgets with or without `check()`'s full-names-first sort.
- **F3:** a new wizard test renders a stub dashboard link (`DashboardLink`, shown once `useIntake().session` is set) and the wizard under one `IntakeProvider`, as App's `IntakeLayout` shares one between `/forms` and `/intake`. It follows the link, waits for the Expenses step, waits 1 s and counts no `update_step`. The four tests that mount the wizard in a fresh provider stay: there `updateCurrentStep` sees no session and sends nothing, so they couldn't see an `update_step` sent through the context, the call Continue makes. The review showed the new test fails under that mutant without the 1 s wait too, and passes without it unmutated.
- **m1:** the cut-off test also draws each drawn combo box's widest option (by Helvetica width) and finds it whole, and asserts that every form has one: the district box (18 combo boxes on the 17 forms).
- **m2:** tier 1's box test checks every ticked drawn widget, of any name, against the values drawn, as spec §8 asks ("the check mark must appear only in that choice's widgets"). `_box_fill` returns the values with the widgets.
- **m17:** the test of a form with a copy and a sheet asserts that the Schedule D sheet's header names Schedule D.

_`time_packet` (m5, m9):_

- **It times what Generate All checks, and draws a filed form from what was filed (m5).** Generate All returns a filed form untouched, so `time_packet` failed on any session with a filed form (`FormIsFiled`) where Generate All succeeds. Its Generate All loop now skips a filed form, and its download loop draws a filed form's stored `field_values` when it has them, otherwise preparing and resolving it from the intake, exactly as `views.download` does (the implementer's call, accepted): skipping the check alone would still fail on a filed form whose current data can't print. The table prints `filed` in the check column.
- **Each `CommandError` is raised `from None` (m9),** all four, "No session" included so one rule holds. A refusal's sentence can quote the filer's letter: chained as `__cause__`, it printed under `--traceback`, and Sentry would send it. `from None` also sets `__suppress_context__`: the review checked that `traceback.print_exception`, `sys.__excepthook__` (what `--traceback` reaches) and Sentry 2.66.1's exception walker then show only the `CommandError`, though `__context__` still holds the refusal, and no backend code reads `__context__`.
- **R72 (review Minor 5):** the filed-form test also stores an unfiled `generated` Form 121 and asserts it is still checked (its check column reads a time), so skipping every stored form fails; a new test draws a filed form stored without values from the intake, so dropping the empty-values guard fails (`json.loads("")`). The review had seen both mutants survive.
- `time_packet` was not run on the seeded personas: this task changes only its filed-form path and its exception chaining, which the tests cover, and a persona session after `seed_demo_data --reset` stores no forms.

_The dashboard (m8):_

- **Generate All's answer replaces every card's refusal:** when it answers with `{generated, errors}`, `setFormRefusals({})` clears them all. Before, only the forms in `generated` lost theirs, so a form Generate All refused again showed the same words and link on its card and in the list. The lists now hold every checked form's current refusal. A filed form, which Generate All returns unchecked, shows none until its next Download (Task 8's accepted call; R72 corrected the wording that said every form).
- **A refusal of Generate All's whole call leaves the cards' refusals as they are** (the implementer's call, pinned by a test under R72): an unfinished intake, income not entered by source or no median table in force means no form was checked, so it says nothing about the cards.
- **R72 accepted one duplicate (review Minor 1).** A card's refused Download of an unfiled form can itself be a refusal of the session, such as `IncomeNotSplit`. Generate All then refuses the whole call for the same reason, so the sentence and its "Go to Income" link show twice, on the card and above the cards. Both are current and correct, and nothing misleads.

_Startup's sheet rules (m12):_

- **E007 refuses, in a sheet group, every slot no column prints, bound or not, and every box slot, bound or not, mapped or not.** The rows past the slots print only what a column prints, so such a slot's value would be lost from every row past the slots. The unprinted rule now reads every slot of the group (`rows`), not only the slots mapped to a state (`mapped`), and a new loop refuses each slot with no binding: a box slot ("a box slot fills '<box>' on row <n>, and a sheet can't tick a box") and a text or combo slot, such as a constant or a derived value ("no sheet column prints '<box>' on row <n>, a slot of the group that binds no list"). A bound slot is still reported once per binding (the existing "a box slot" case binds four boxes to one list and expects one error); an unbound one is reported per slot, naming its box and row.
- **R72 (review Minor 3): the column rule reads every slot too,** so a box not yet mapped, bound to the list a column prints, is refused ("sheet column 'Make' binds a box's answer, which a sheet can't tick"). In the first build it passed, though `CLAUDE.md` and the commit body already said any box slot.
- No production schema has a group. The review's probe found that the 17 production schemas and the four synthetic group schemas in `conftest.py` still pass.

_One list of steps and pages (m18):_

- **`test_rule_fixes.py` reads the step keys from `frontend/src/constants/wizardSteps.ts` and the pages from `PAGE_LINK_LABELS` in `FormDashboard.tsx`** (plus `/ask/<form type>`), not from a hand copy, so a step or a route renamed on either side fails the backend suite: otherwise the dashboard would drop the link and the filer would be told to try again. The check moves out of `test_every_refusal_names_where_to_fix_it` into its own test, `test_every_fix_is_a_step_or_page_the_dashboard_links`, which covers every fix a refusal can carry: each rule's (`RULE_FIXES`, which names only step keys and `/fee-waiver`), `fix_for` of every text or combo binding on the 17 forms (an answer's `/ask/` page, the pay stub's `/documents`), one synthetic SOFA list binding (`/sofa`; no production schema binds one), and, since R72 (review Minor 4), the targets the exceptions name: `PreconditionMissing`'s `step` wherever the backend raises it, `IncomeNotSplit.step` and `IntakeNotFinished.page`. Before R72, renaming the `review` step or `/intake` passed.
- **The raise sites are read from the code with `ast`:** every non-test, non-migration module under `backend/apps`, so a new place that raises `PreconditionMissing` is checked too. A `step` that isn't a string constant fails the test ("a step this test can't read"), and so does a scan that finds none.
- **The new test skips, saying why, where `frontend/src` is absent.** Compose's backend container mounts only `./backend` (and the data), so `docker compose exec backend python -m pytest`, as `CLAUDE.md` gives it, would otherwise fail. CI's backend job checks out the whole repository and runs pytest with `-rs`, so the skip can't hide a failure there; the gates' 25 skips are all Postgres-only tests. Any later backend test that reads the frontend must skip there too.
- The readers are regular expressions on single-quoted TypeScript. The review found that double quotes make both read nothing, and the test then fails rather than passing empty.

_Docs:_

- **m6 is docs only.** A filed form whose stored values `check()` refuses for a letter or a length downloads as a 422 with no `step` or `page`; any other refusal of a filed form (a key or a box state the template no longer has) stays a 500, since it means a template changed under a filed form, an operations problem (R46 as R71 narrowed it). `CLAUDE.md` said every refusal; three gotchas made that claim, "Forms need a completed intake", "GenerateAll vs single" and "`field_values`, not `form_data`", and all three are narrowed. Comparing `template_version` on the filed path is a ticket candidate.
- **m13, m14 and m15.** The Architecture PDF line says every push button (Print, Reset, Save As and Add Attachment) is removed before the bake, not only the print buttons: the final review counted 67 undrawn widgets, all of them those four buttons. "`field_values`, not `form_data`" says `check()` and `fill()` take a sheet's title, columns and rows from its part, and the schema gives only the template and, for a refusal, its fix and the name box's label. The umbrella spec's SPIKE row says the engine method was "replaced by 3a2's §3 (engine) and §8 (oracle)": the suggested "3a2's spec §3" was one character wider than the table's column, so dropping "spec" keeps the diff to one line with no re-padding.
- F1, m8 and m12 each change the gotcha that describes them: "GenerateAll vs single" (composing, and when a card's refusal clears) and "Schemas are checked at startup" (the sheet list).

_Not here:_

- **m7 is parked for 3b and 3c (R71):** `resolve_parts` resolves each slot binding with its own unordered query and pairs a row's cells by position. It predates 3a2, and no production schema has a group; it is a ticket candidate and a prerequisite before 3b or 3c binds real rows.
- **m10 and m16 are the owner's (R71):** the letter sentence for a letter with no mark (W-1, now including n̈), and the README, which still says pypdf alone makes the PDFs. README hunks need the owner's yes, so `README.md` is untouched.
- m3 and m4 (the stored errata diff, and the errata items' citations of Task 8's first commit) are the controller's records, not code.

_What was checked:_

- Every new or changed test was shown red, on the parent or under a mutation: 31 of 31 mutants red on this commit (25 on the first build, six more in fix round 1), in `.claude/plan3a2-work/t09/mutate.py`. The review ran its own: composing only in the check, drawing a form box or a sheet line uncomposed, NFD and NFKC (each red), an `update_step` sent 300 ms after the read (red), and all eight ways of chaining the four `CommandError`s (red). Steps 7 to 13, 16, 19, 22 and 23 run 15 of them.
- The commit ends with `Refs DIG-137`, the ticket for `time_packet` and Generate All's budget.

- [ ] **Step 1: Write the tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_attached_sheets.py b/backend/apps/forms/tests/test_attached_sheets.py
index 0ec1ad2..8890831 100644
--- a/backend/apps/forms/tests/test_attached_sheets.py
+++ b/backend/apps/forms/tests/test_attached_sheets.py
@@ -9,6 +9,7 @@ page 3.

 import json
 import re
+import unicodedata
 from io import BytesIO, StringIO
 from pathlib import Path

@@ -268,6 +269,29 @@ def test_the_sheet_prints_every_letter_the_form_prints(session, creditor_payment
     assert "Łucja Kıłıç" in text and "Łada Niva ł ı" in text


+def test_letters_typed_with_their_marks_apart_print_whole_on_the_form_and_the_sheet(
+    session, creditor_payments
+):
+    # é typed as e and U+0301 (pasted from a file name, say) is checked, measured and drawn
+    # as é, the one letter the font prints, on the form's boxes and on its sheet alike.
+    debtor = session.debtor_info
+    debtor.first_name = unicodedata.normalize("NFD", "José")
+    debtor.last_name = unicodedata.normalize("NFD", "Muñoz")
+    debtor.save()
+    creditor_payments(session, 5, [*MAKES[:4], unicodedata.normalize("NFD", "Citroën Müller")])
+
+    parts, pdf = _drawn(session)
+
+    (sheet,) = read_sheets(pdf, _spec())
+    assert (sheet.header[0], sheet.rows) == (
+        "José Muñoz",
+        (("3.5", "Citroën Müller", "500.00"),),
+    )
+    name_boxes = {f.pdf_field for f in load_schema("schedule_a_b").fields if f.rule == "full_name"}
+    printed = [w.value for w in read_drawn("schedule_a_b", pdf, parts) if w.full_name in name_boxes]
+    assert printed and set(printed) == {"José Muñoz"}
+
+
 def test_a_name_neither_the_form_nor_the_sheet_can_print_is_refused_on_the_form(
     session, creditor_payments
 ):
@@ -455,3 +479,10 @@ def test_a_form_with_a_copy_and_a_sheet_prints_the_sheet_last(
     }
     (sheet,) = read_sheets(pdf, sheet_spec(document["parts"][2]))
     assert sheet.rows == (("2.6", "Kia", "600.00"), ("2.7", "Saab", "700.00"))
+    # Headed with Schedule D's own title, not another form's
+    assert sheet.header == (
+        "Maria Torres",
+        "Official Form 106D, Schedule D: Creditors Who Have Claims Secured by Property "
+        "(attached sheet)",
+        "Case number (if known)",
+    )
diff --git a/backend/apps/forms/tests/test_check.py b/backend/apps/forms/tests/test_check.py
index fe4022b..fc721ef 100644
--- a/backend/apps/forms/tests/test_check.py
+++ b/backend/apps/forms/tests/test_check.py
@@ -12,6 +12,7 @@ metrics, so "the first size that fits" isn't checked against check()'s own arith

 import dataclasses
 import re
+import unicodedata
 from pathlib import Path

 import pymupdf
@@ -123,6 +124,35 @@ def test_a_letter_the_form_cannot_print_is_refused(last_name, letter):
     )


+@pytest.mark.parametrize("last_name", ["Varée", "Peñalta", "Grünholt"])
+def test_a_letter_typed_as_a_letter_and_its_mark_prints_as_the_one_letter(last_name):
+    # Text pasted from a file name or some PDFs, or typed with combining marks, holds é as
+    # e and U+0301: the form prints it as é, the one letter its font has.
+    decomposed = unicodedata.normalize("NFD", last_name)
+    assert len(decomposed) == len(last_name) + 1
+    (planned,) = _plan("form_101", {LAST_NAME: decomposed})
+    assert (planned.value, planned.size) == (last_name, 10.0)
+
+
+def test_a_letter_typed_with_its_marks_apart_is_refused_as_the_whole_letter():
+    # ễ is e with two marks: the form can't print ễ, so the refusal names ễ, not a mark.
+    with pytest.raises(UnprintableLetter) as refused:
+        PDFFormFiller().check("form_101", {LAST_NAME: unicodedata.normalize("NFD", "Nguyễn")})
+    assert refused.value.letter == "ễ"
+    assert str(refused.value) == (
+        "The court form can't print the letter “ễ” in “Last name”. "
+        "Change it to a letter without the mark."
+    )
+
+
+def test_a_mark_no_letter_takes_is_refused_at_the_mark():
+    # No single letter is n with a diaeresis, so the mark stays apart and is refused itself
+    # (the sentence for it is the owner's, W-1).
+    with pytest.raises(UnprintableLetter) as refused:
+        PDFFormFiller().check("form_101", {LAST_NAME: "Mun\N{COMBINING DIAERESIS}oz"})
+    assert refused.value.letter == "\N{COMBINING DIAERESIS}"
+
+
 @pytest.mark.parametrize(
     "space", ["\t", "\N{NO-BREAK SPACE}", "\N{THIN SPACE}", "\N{NARROW NO-BREAK SPACE}"]
 )
@@ -174,6 +204,18 @@ def test_a_refusal_names_the_box_as_its_binding_does():
         assert (unbound.value.label, unbound.value.step, unbound.value.page) == (label, None, None)


+def test_a_box_whose_binding_has_no_label_is_named_by_its_index_row():
+    # Schedule J's amount boxes are bound with an empty label; a refusal names the box as
+    # the field index does, never as “”, and still links to the step its rule reads.
+    with pytest.raises(UnprintableLetter) as refused:
+        PDFFormFiller().check("schedule_j", {"7": "Wąsowicz"})
+    assert (refused.value.label, refused.value.step, refused.value.page) == (
+        "Food and housekeeping supplies",
+        "expense_info",
+        None,
+    )
+
+
 # ── Fit ───────────────────────────────────────────────────────────────


@@ -335,9 +377,17 @@ def test_a_widgets_own_key_fills_only_that_widget():
     first, second = _widgets("schedule_i", "Assistance 8f")
     planned = _plan("schedule_i", {first.key: "SNAP"})
     assert [(p.widget, p.value) for p in planned] == [(first, "SNAP")]
-    # It wins over its full name, which still fills the name's other widget.
-    planned = _plan("schedule_i", {"Assistance 8f": "Housing aid", second.key: "SNAP"})
-    assert [(p.widget, p.value) for p in planned] == [(first, "Housing aid"), (second, "SNAP")]
+    # It wins over its full name, which still fills the name's other widget, whichever key
+    # comes first.
+    for values in (
+        {"Assistance 8f": "Housing aid", second.key: "SNAP"},
+        {second.key: "SNAP", "Assistance 8f": "Housing aid"},
+    ):
+        planned = _plan("schedule_i", values)
+        assert [(p.widget, p.value) for p in planned] == [
+            (first, "Housing aid"),
+            (second, "SNAP"),
+        ]


 def test_a_full_name_fills_every_drawn_widget_but_never_a_stacked_one():
diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index fa61150..6542127 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -17,6 +17,7 @@ Covers:

 import json
 import logging
+import unicodedata
 from datetime import date
 from decimal import Decimal
 from unittest.mock import patch
@@ -613,6 +614,23 @@ def test_each_generate_names_the_step_that_fixes_a_letter_the_form_cannot_print(
     assert "ą" not in caplog.text


+@pytest.mark.django_db
+def test_a_name_saved_with_its_marks_apart_generates_form_101(api_client, session_with_debtor):
+    # The intake keeps a name as typed, so é can arrive as e and U+0301: the form prints é,
+    # never a refusal that quotes a lone accent.
+    debtor = session_with_debtor.debtor_info
+    debtor.first_name = unicodedata.normalize("NFD", "José")
+    debtor.save()
+
+    response = api_client.post(
+        "/api/forms/generate/",
+        {"session_id": session_with_debtor.id, "form_type": "form_101"},
+        format="json",
+    )
+
+    assert response.status_code == status.HTTP_200_OK, response.data
+
+
 # ── Status Transition Endpoints ───────────────────────────────────────


PATCH
```

The letters and the refusal's label:

- `test_check.py`: decomposed "Varée", "Peñalta" and "Grünholt" plan as the composed name at 10 pt; decomposed "Nguyễn" is refused naming ễ, in the spec sentence; "Mun" + U+0308 + "oz" is refused at U+0308; Schedule J's box `7`, whose binding has an empty label, is refused as "Food and housekeeping supplies" with `step: "expense_info"`. `test_a_widgets_own_key_fills_only_that_widget` plans its values in both orders (F2).
- `test_attached_sheets.py`: a decomposed "José Muñoz" prints in every Schedule A/B name box and in the sheet's header, and a decomposed fifth make, "Citroën Müller", prints whole on the sheet. The copy-and-sheet test also asserts the Schedule D sheet's header (m17).
- `test_form_views.py`: a first name saved decomposed generates Form 101 (200).

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_oracle_tier1.py b/backend/apps/forms/tests/test_oracle_tier1.py
index 717ee0c..98bba8d 100644
--- a/backend/apps/forms/tests/test_oracle_tier1.py
+++ b/backend/apps/forms/tests/test_oracle_tier1.py
@@ -97,13 +97,16 @@ def _text_fill(form_type):

 @cache
 def _box_fill(form_type, position):
-    """Fill the position-th choice of every mapped box at once; boxes share no widgets."""
+    """
+    Fill the position-th choice of every mapped box at once; boxes share no widgets.
+    Returns the values drawn, and what each drawn widget prints with them.
+    """
     values = {}
     for f in _fields(form_type, ("checkbox", "radio")):
         keys = sorted(f.choices or {})
         if position < len(keys):
             values[f.pdf_field] = f.choices[keys[position]]
-    return _drawn(form_type, values)
+    return values, _drawn(form_type, values)


 _TEXT_KINDS = ("Text", "ComboBox")
@@ -238,14 +241,19 @@ def test_checkbox_ticks_only_the_widgets_for_its_answer(form_type, pdf_field, ca
         for w in template_widgets(template)
         if w.full_name == pdf_field and w.drawn and state in w.states
     )
-    own = [
-        w
-        for w in _box_fill(form_type, sorted(field.choices).index(case))
-        if w.full_name == pdf_field
-    ]
+    values, drawn = _box_fill(form_type, sorted(field.choices).index(case))
+    own = [w for w in drawn if w.full_name == pdf_field]
     ticked = [w for w in own if w.state == state]
     assert len(ticked) == expected, f"no_widget: {len(ticked)} of {expected} widgets show {state}"
     assert all(w.state == "/Off" for w in own if w.state != state), "spill: another option is on"
+    # The check mark appears only in the widgets of the choices drawn (spec §8), never in a
+    # widget of another name.
+    stray = sorted(
+        (w.full_name, w.page, w.tag)
+        for w in drawn
+        if w.state not in ("", "/Off") and values.get(w.full_name) != w.state
+    )
+    assert stray == [], f"spill: a tick also prints in {stray}"


 def test_every_checkbox_binding_maps_its_answers_to_a_box():
diff --git a/backend/apps/forms/tests/test_printed_page.py b/backend/apps/forms/tests/test_printed_page.py
index a7e216f..06b51c8 100644
--- a/backend/apps/forms/tests/test_printed_page.py
+++ b/backend/apps/forms/tests/test_printed_page.py
@@ -520,8 +520,8 @@ def test_no_value_is_ever_cut_off(form_type):
     # The longest value check() lets through prints whole, every character inside its box,
     # and one letter or line more is refused, never drawn cut off (spec §9). A short value
     # at the box's own size stays inside too: there R38's 37 boxes hang Ç's cedilla up to
-    # 0.108 pt under the rect, as the template always has. (Combo boxes take only their
-    # own options, so they have no boundary to probe.)
+    # 0.108 pt under the rect, as the template always has. A combo box takes only its own
+    # options, so it has no boundary to probe: it prints its widest whole.
     boxes = [w for w in template_widgets(_template(form_type)) if w.drawn and w.kind == "Text"]
     boundaries = {}  # boxes alike in every measure check() takes share a boundary
     just, over, short = {}, {}, {}
@@ -537,6 +537,17 @@ def test_no_value_is_ever_cut_off(form_type):
     assert [key for key in over if _fits(form_type, key, over[key])] == []
     assert _cut_off(form_type, just) == []
     assert _cut_off(form_type, short) == []
+    # Every form has its district box, which lists every district.
+    widest = {
+        w.key: max(
+            (o for o in w.options if o.strip()),
+            key=lambda o: pymupdf.get_text_length(o, fontname="helv", fontsize=10),
+        )
+        for w in template_widgets(_template(form_type))
+        if w.drawn and w.kind == "ComboBox"
+    }
+    assert widest
+    assert _cut_off(form_type, widest) == []


 # ── A capital's mark on a multi-line box's first line ─────────────────
PATCH
```

- `test_printed_page.py`: the cut-off test draws each drawn combo box's widest option and finds it whole, and asserts each form has one (m1).
- `test_oracle_tier1.py`: `_box_fill` returns the values it drew with the drawn widgets, and the box test asserts that no drawn widget of any name shows a state other than the one its name was given (m2).

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_time_packet.py b/backend/apps/forms/tests/test_time_packet.py
index b5ec53b..7239ddb 100644
--- a/backend/apps/forms/tests/test_time_packet.py
+++ b/backend/apps/forms/tests/test_time_packet.py
@@ -5,6 +5,8 @@ It runs on the Eco dyno before a deploy, against a real filer's database, so it
 leave every row as it found it, and a budget it misses must say which.
 """

+import json
+import traceback
 from datetime import date
 from decimal import Decimal
 from io import StringIO
@@ -17,12 +19,17 @@ from django.core.management.base import CommandError
 from apps.districts.models import District
 from apps.eligibility.models import MeansTest
 from apps.forms.models import GeneratedForm
-from apps.forms.registry import packet
+from apps.forms.registry import build_parts, packet
 from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()


+def _printed_with_traceback(error):
+    """What --traceback prints for the error: every exception chained to it, too."""
+    return "".join(traceback.format_exception(error))
+
+
 @pytest.fixture
 def session(db):
     """A completed intake with no means test and no forms yet, so any row it wrote would show."""
@@ -77,9 +84,19 @@ def test_time_packet_refuses_an_unfinished_intake_and_writes_nothing(session):
         call_command("time_packet", session=session.id, stdout=StringIO())

     assert str(refused.value) == "The session was refused: IntakeNotFinished"
+    # Nothing chained: --traceback prints only the command's own error.
+    assert (refused.value.__cause__, refused.value.__suppress_context__) == (None, True)
     assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)


+def test_time_packet_names_a_session_it_cannot_find(db):
+    with pytest.raises(CommandError) as refused:
+        call_command("time_packet", session=404, stdout=StringIO())
+
+    assert str(refused.value) == "No session 404."
+    assert (refused.value.__cause__, refused.value.__suppress_context__) == (None, True)
+
+
 def test_time_packet_refusal_writes_nothing_and_keeps_the_filers_letter_out(session):
     # An invented surname: ą is outside the court form's font, which would print "?".
     debtor = session.debtor_info
@@ -94,10 +111,103 @@ def test_time_packet_refusal_writes_nothing_and_keeps_the_filers_letter_out(sess
     assert message == "form_101 was refused: UnprintableLetter"
     assert "ą" not in message
     assert "Wąsowicz" not in message
+    # Not even chained to it, where --traceback, or Sentry, would print it.
+    assert refused.value.__cause__ is None
+    assert "ą" not in _printed_with_traceback(refused.value)
     # Even the means test it worked out before the refusal is rolled back.
     assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)


+def _file(session, form_type, values):
+    return GeneratedForm.objects.create(
+        session=session,
+        form_type=form_type,
+        status="filed",
+        generated_by=session.user,
+        field_values=json.dumps(values),
+    )
+
+
+def _timed(session, out):
+    """Each packet form's row of the table: check s, download s, PDF KB and template KB."""
+    rows = [line.split() for line in out.getvalue().splitlines()]
+    timed = {row[0]: row[1:] for row in rows if row and row[0] in packet(session)}
+    assert set(timed) == set(packet(session))
+    return timed
+
+
+def test_time_packet_times_a_session_with_a_filed_form_and_draws_what_was_filed(session):
+    # Generate All returns a filed form untouched, and its download draws what was filed.
+    filed = _file(session, "form_101", build_parts("form_101", session))
+    # A form generated, not filed, is checked again, as Generate All checks it.
+    generated = GeneratedForm.objects.create(
+        session=session,
+        form_type="form_121",
+        status="generated",
+        generated_by=session.user,
+        field_values=json.dumps(build_parts("form_121", session)),
+    )
+    # Since filing, the filer's email became one Form 101, the one form that prints it,
+    # can't print: drawn from the intake, Form 101 would be refused.
+    debtor = session.debtor_info
+    debtor.email = "ana.wąs@example.org"
+    debtor.save()
+    out = StringIO()
+
+    call_command(
+        "time_packet", session=session.id, budget_generate=600, budget_download=600, stdout=out
+    )
+
+    timed = _timed(session, out)
+    check, _, pdf_kb, _ = timed["form_101"]
+    assert (check, float(pdf_kb) > 0) == ("filed", True)
+    assert float(timed["form_121"][0]) >= 0  # a time, not "filed"
+    assert sorted(GeneratedForm.objects.values_list("id", "status", "field_values")) == sorted(
+        [
+            (filed.id, "filed", filed.field_values),
+            (generated.id, "generated", generated.field_values),
+        ]
+    )
+    assert MeansTest.objects.count() == 0
+
+
+def test_time_packet_draws_a_filed_form_stored_without_values_from_the_intake(session):
+    # As the download view does: a filed form whose values were never stored is resolved
+    # from the intake and drawn.
+    filed = GeneratedForm.objects.create(
+        session=session,
+        form_type="form_101",
+        status="filed",
+        generated_by=session.user,
+        field_values="",
+    )
+    out = StringIO()
+
+    call_command(
+        "time_packet", session=session.id, budget_generate=600, budget_download=600, stdout=out
+    )
+
+    check, _, pdf_kb, _ = _timed(session, out)["form_101"]
+    assert (check, float(pdf_kb) > 0) == ("filed", True)
+    assert list(GeneratedForm.objects.values_list("id", "status", "field_values")) == [
+        (filed.id, "filed", "")
+    ]
+    assert MeansTest.objects.count() == 0
+
+
+def test_time_packet_keeps_the_filers_letter_out_of_a_filed_forms_refusal(session):
+    # Values filed before 3a2 were never checked; their download refuses a letter.
+    _file(session, "form_101", {"Debtor1.Last name": "Wąsowicz"})
+
+    with pytest.raises(CommandError) as refused:
+        call_command("time_packet", session=session.id, stdout=StringIO())
+
+    assert str(refused.value) == "form_101 was refused: UnprintableLetter"
+    assert refused.value.__cause__ is None
+    assert "ą" not in _printed_with_traceback(refused.value)
+    assert MeansTest.objects.count() == 0
+
+
 def test_time_packet_names_the_budget_it_missed(session):
     with pytest.raises(CommandError) as missed:
         call_command(
PATCH
```

`time_packet`: a session with a filed Form 101 times, its row reading `filed` and its PDF drawn from what was filed (the filer's email has since become one Form 101 can't print), while an unfiled Form 121 is still checked and nothing is written; a filed form stored without values is drawn from the intake; a filed form's refusal keeps the filer's letter out of the error and its chain; a session it can't find is named, chained to nothing; and the two existing refusal tests assert that nothing is chained (`__cause__` is `None`, and `--traceback` would print no "ą").

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_checks.py b/backend/apps/forms/tests/test_checks.py
index 370b508..a0b4718 100644
--- a/backend/apps/forms/tests/test_checks.py
+++ b/backend/apps/forms/tests/test_checks.py
@@ -799,6 +799,14 @@ def _community_property_boxes(d):
         )


+def _unmapped_community_property_boxes(d):
+    # Not yet mapped to a state, so they tick nothing for now; once mapped, they would.
+    _community_property_boxes(d)
+    for f in d["fields"]:
+        if f["repeat"] == "ab_line_3" and f["type"] == "checkbox":
+            f["choices"] = {}
+
+
 def _a_column_of_boxes(d):
     _community_property_boxes(d)
     columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
@@ -812,6 +820,18 @@ def _a_column_of_boxes(d):
     )


+def _ab_slot(**binding):
+    """Add a slot to row 1 of the synthetic Schedule A/B group, filled as `binding` says."""
+
+    def change(d):
+        d["fields"].append(
+            {**_text(None, 2, None), "repeat": "ab_line_3", "repeat_capacity": 4, "row": 1}
+            | binding
+        )
+
+    return change
+
+
 def _another_lists_column(d):
     columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
     columns[0]["width"] = 200
@@ -921,6 +941,54 @@ _AB = "schedule_a_b: group 'ab_line_3'"
                 "and a sheet can't tick a box",
             ),
         ),
+        (
+            # A box in the Make column's list, its answer not yet mapped to a state: once
+            # mapped, it would tick a box the sheet doesn't have.
+            _ab_slot(
+                pdf_field="Check if this is community property see",
+                type="checkbox",
+                source="asked",
+                value=None,
+                choices={},
+                binding="sofa.creditor_payments[].creditor_name",
+            ),
+            (
+                "forms.E007",
+                f"{_AB}: sheet column 'Make' binds a box's answer, which a sheet can't tick",
+            ),
+        ),
+        (
+            _unmapped_community_property_boxes,
+            (
+                "forms.E007",
+                f"{_AB}: a box slot binds 'sofa.creditor_payments[].dates_of_payments', "
+                "and a sheet can't tick a box",
+            ),
+        ),
+        (
+            # A box ticked for every row, bound to nothing: still no box on the sheet.
+            _ab_slot(
+                pdf_field="Check if this is community property see",
+                type="checkbox",
+                value="yes",
+                choices={"true": "/On"},
+            ),
+            (
+                "forms.E007",
+                f"{_AB}: a box slot fills 'Check if this is community property see' on row 1, "
+                "and a sheet can't tick a box",
+            ),
+        ),
+        (
+            # A value DigniFi works out (the filer's name, in row 1's model box): no column
+            # holds it, so a fifth row would lose it.
+            _ab_slot(pdf_field="3 2", source="derived", value=None, rule="full_name"),
+            (
+                "forms.E007",
+                f"{_AB}: no sheet column prints '3 2' on row 1, a slot of the group that "
+                "binds no list",
+            ),
+        ),
         (
             # "Line 3.5" is 35.58 pt at 10 pt, wider than the 32 pt inside the line column's
             # padding: it would print on two lines.
@@ -967,6 +1035,10 @@ _AB = "schedule_a_b: group 'ab_line_3'"
         "a column of boxes",
         "a slot with no column",
         "a box slot",
+        "a box slot not yet mapped, in a column",
+        "a box slot not yet mapped",
+        "a constant box slot",
+        "a derived slot",
         "a first line wider than the line column",
         "two columns with one label",
         "a label wider than its column",
PATCH
```

Four new cases of `test_a_sheet_that_cannot_print_its_rows_whole_is_reported`, on the synthetic Schedule A/B sheet group, each with its exact message: a box not yet mapped in the list the Make column prints; the four community-property boxes not yet mapped; a constant box; and a derived text slot (the filer's name in row 1's model box).

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_rule_fixes.py b/backend/apps/forms/tests/test_rule_fixes.py
index cbf73b8..c0eb31c 100644
--- a/backend/apps/forms/tests/test_rule_fixes.py
+++ b/backend/apps/forms/tests/test_rule_fixes.py
@@ -7,25 +7,65 @@ A constant links nowhere: a constant that can't print is DigniFi's defect, and
 test_check.py's test_every_constant_prints keeps every constant printable.
 """

+import ast
+import re
+
 import pytest
+from django.conf import settings

+from apps.eligibility.cmi import IncomeNotSplit
 from apps.forms.registry import get_all_form_types
 from apps.forms.schema import FieldSpec, load_schema
 from apps.forms.services.derivations import DERIVATIONS, RULE_FIXES
 from apps.forms.services.fill_resolver import fix_for
-
-# The keys of WIZARD_STEPS in frontend/src/constants/wizardSteps.ts: what /intake?step= opens.
-WIZARD_STEPS = {
-    "debtor_info",
-    "income_info",
-    "expense_info",
-    "assets",
-    "debts",
-    "contracts",
-    "codebtors",
-    "review",
-}
-PAGES = {"/fee-waiver", "/documents", "/sofa"} | {f"/ask/{ft}" for ft in get_all_form_types()}
+from apps.forms.views import IntakeNotFinished
+
+FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"
+
+
+def _wizard_steps():
+    """
+    The keys of WIZARD_STEPS in frontend/src/constants/wizardSteps.ts: what /intake?step=
+    opens.
+    """
+    steps = (FRONTEND / "constants" / "wizardSteps.ts").read_text()
+    return set(re.findall(r"key: '(\w+)'", steps))
+
+
+def _pages():
+    """
+    The pages the forms dashboard links a refusal to: PAGE_LINK_LABELS in
+    frontend/src/pages/FormDashboard.tsx, and each form's questions page, /ask/<form type>.
+    """
+    dashboard = (FRONTEND / "pages" / "FormDashboard.tsx").read_text()
+    labels = re.search(r"const PAGE_LINK_LABELS[^{]*\{(.*?)\};", dashboard, re.DOTALL)[1]
+    return set(re.findall(r"'(/[^']*)':", labels)) | {f"/ask/{ft}" for ft in get_all_form_types()}
+
+
+def _precondition_steps():
+    """
+    The step each PreconditionMissing(...) in the backend's code names, read from its source,
+    so a new place that raises one is checked too.
+    """
+    steps, unread = set(), []
+    for path in (settings.BASE_DIR / "apps").rglob("*.py"):
+        if {"tests", "migrations"} & set(path.parts):
+            continue
+        for node in ast.walk(ast.parse(path.read_text())):
+            if not (
+                isinstance(node, ast.Call)
+                and getattr(node.func, "id", None) == "PreconditionMissing"
+            ):
+                continue
+            step = next((k.value for k in node.keywords if k.arg == "step"), None)
+            if step is None and len(node.args) > 1:
+                step = node.args[1]
+            if isinstance(step, ast.Constant):
+                steps.add(step.value)
+            elif step is not None:
+                unread.append(f"{path.name}:{node.lineno}")
+    assert unread == [], "a step this test can't read"
+    return steps


 def _field(source, rule=None, binding=None, ingest_key=None, value=None):
@@ -59,8 +99,35 @@ def test_every_refusal_names_where_to_fix_it():
     for rule, fix in RULE_FIXES.items():
         assert rule in DERIVATIONS, rule
         assert len(fix) <= 1, rule
-        for kind, target in fix.items():
-            assert target in {"step": WIZARD_STEPS, "page": PAGES}[kind], rule
+
+
+def test_every_fix_is_a_step_or_page_the_dashboard_links():
+    # Read from the frontend itself, so a step key or a route renamed on either side fails
+    # here: the dashboard would otherwise drop the link and tell the filer to try again.
+    if not FRONTEND.is_dir():
+        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
+    targets = {"step": _wizard_steps(), "page": _pages()}
+    # Every fix a refusal can carry: each rule's, each text or combo binding's on the forms
+    # (an answer's questions page, a scan's), a SOFA list's, which no form binds yet, and
+    # each one an exception names itself: a missing precondition's, wherever it is raised,
+    # income not entered by source and an unfinished intake.
+    preconditions = _precondition_steps()
+    assert preconditions  # Forms 101 and 121 need a debtor and an SSN
+    fixes = [
+        *RULE_FIXES.values(),
+        *(
+            fix_for(f)
+            for form_type in get_all_form_types()
+            for f in load_schema(form_type).fields
+            if f.type in ("text", "choice")
+        ),
+        fix_for(_field("asked", binding="sofa.creditor_payments[].creditor_name")),
+        *({"step": step} for step in preconditions),
+        {"step": IncomeNotSplit.step},
+        {"page": IntakeNotFinished.page},
+    ]
+    unlinked = [fix for fix in fixes for kind, target in fix.items() if target not in targets[kind]]
+    assert unlinked == []


 @pytest.mark.parametrize(
PATCH
```

`test_rule_fixes.py` reads the step keys and pages from the frontend's own files, and checks every fix a refusal can carry against them in a test of its own, which skips where the frontend's source isn't.

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/FormDashboard.test.tsx b/frontend/src/pages/__tests__/FormDashboard.test.tsx
index 7a8a04f..954c42e 100644
--- a/frontend/src/pages/__tests__/FormDashboard.test.tsx
+++ b/frontend/src/pages/__tests__/FormDashboard.test.tsx
@@ -1055,6 +1055,59 @@ describe('FormDashboard', () => {
       expect(within(card).queryByRole('link')).not.toBeInTheDocument();
     });

+    it('shows a form’s refusal once, in Generate All’s list, when Generate All refuses it again', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({
+            generated: [],
+            errors: [{ form_type: 'form_101', error: LETTER, step: 'debtor_info' }],
+            total_generated: 0,
+            total_errors: 1,
+          })
+        )
+      );
+      downloads(refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }));
+
+      renderFormDashboard();
+      const card = await cardOf(GENERATED);
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+      await within(card).findByText(LETTER);
+
+      await generateAll();
+      await screen.findByText(/1 form could not be generated/);
+
+      // A list item reads "<form>: <refusal>", so the words are matched within it
+      const shown = screen.getAllByText(LETTER, { exact: false });
+      expect(shown).toHaveLength(1);
+      expect(shown[0].closest('li')).not.toBeNull();
+      expect(screen.getAllByRole('link', { name: 'Go to Your Information' })).toHaveLength(1);
+    });
+
+    // A refusal of the whole call checked no form, so it says nothing about the card's
+    it('keeps a form’s refusal when Generate All is refused as a whole', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({ error: INCOME_NOT_SPLIT, step: 'income_info' }, { status: 422 })
+        )
+      );
+      downloads(refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }));
+
+      renderFormDashboard();
+      const card = await cardOf(GENERATED);
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+      await within(card).findByText(LETTER);
+
+      await generateAll();
+
+      const wholeCall = await screen.findByRole('alert');
+      expect(within(wholeCall).getByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
+      expect(within(card).getByText(LETTER)).toBeInTheDocument();
+      expect(within(card).getByRole('link', { name: 'Go to Your Information' })).toHaveAttribute(
+        'href',
+        '/intake?step=debtor_info'
+      );
+    });
+
     it('clears a form’s refusal once it is marked filed', async () => {
       downloads(refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }));

diff --git a/frontend/src/pages/__tests__/IntakeWizard.test.tsx b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
index f9e3bbd..70c7a5a 100644
--- a/frontend/src/pages/__tests__/IntakeWizard.test.tsx
+++ b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
@@ -894,6 +894,42 @@ describe('IntakeWizard session re-read', { timeout: 15_000 }, () => {
     expect(stepUpdates.count).toBe(0);
   });

+  /** The forms dashboard's link to a step, shown once the shared session has loaded */
+  function DashboardLink() {
+    const { session } = useIntake();
+    const navigate = useNavigate();
+    return session ? (
+      <button type="button" onClick={() => navigate('/intake?step=expense_info')}>
+        Go to Expenses
+      </button>
+    ) : null;
+  }
+
+  // The dashboard and the wizard share one IntakeProvider (App's IntakeLayout): the session is
+  // already loaded when a link opens the wizard, so an update_step sent through the context, as
+  // Continue sends it, would reach the server
+  it('opens the step a dashboard link names, the session already loaded, without moving the filer’s saved place', async () => {
+    const stepUpdates = savedAs({ ...sessionAtStep8, status: 'completed' });
+    localStorage.setItem('current_session_id', '1');
+    render(
+      <MemoryRouter initialEntries={['/forms']}>
+        <IntakeProvider>
+          <Routes>
+            <Route path="/intake" element={<IntakeWizard />} />
+            <Route path="/forms" element={<DashboardLink />} />
+          </Routes>
+        </IntakeProvider>
+      </MemoryRouter>
+    );
+
+    await userEvent.click(await screen.findByRole('button', { name: 'Go to Expenses' }));
+
+    expect(await screen.findByRole('heading', { name: 'Expenses', level: 2 })).toBeInTheDocument();
+    // Long enough for a request sent as the step opened to reach the server
+    await new Promise((resolve) => setTimeout(resolve, 1000));
+    expect(stepUpdates.count).toBe(0);
+  });
+
   // A refresh then opens the saved step, and Back leaves the wizard rather than reopening the link
   it('drops the step from the address once it has opened it, without a new history entry', async () => {
     const stepUpdates = savedAs({ ...sessionAtStep8, status: 'completed' });
PATCH
```

- `FormDashboard.test.tsx`: a card refused on Download, then Generate All refusing the same form, shows the refusal and its link once, in the list (m8); and a refusal of Generate All's whole call leaves the card's refusal and its link (R72).
- `IntakeWizard.test.tsx`: the wizard opens the step a dashboard link names, under the provider the dashboard shares, without an `update_step` (F3).

- [ ] **Step 2: Run the tests and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs apps/forms/tests/test_check.py apps/forms/tests/test_attached_sheets.py apps/forms/tests/test_form_views.py::test_a_name_saved_with_its_marks_apart_generates_form_101 apps/forms/tests/test_time_packet.py apps/forms/tests/test_checks.py apps/forms/tests/test_rule_fixes.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `17 failed, 185 passed`, with `test_a_letter_typed_as_a_letter_and_its_mark_prints_as_the_one_letter[Var\xe9e] - apps.forms.services.pdf_filler.UnprintableLetter: The court form can't print the letter “́” in “Last name”.`, `test_a_box_whose_binding_has_no_label_is_named_by_its_index_row - AssertionError: assert ('', 'expense_info', None) == ('Food and ho...e_info', None)`, `test_time_packet_times_a_session_with_a_filed_form_and_draws_what_was_filed - django.core.management.base.CommandError: form_101 was refused: FormIsFiled`, `test_time_packet_names_a_session_it_cannot_find - AssertionError: assert (DoesNotExist...xist.'), True) == (None, True)` and `test_a_sheet_that_cannot_print_its_rows_whole_is_reported[a derived slot] - assert [] == [('forms.E007...nds no list')]`.

- **Letters and the label, 7 failures:** the three decomposed names are refused at their mark (U+0301, U+0303, U+0308), quoting the lone mark; decomposed "Nguyễn" is refused at U+0302, not at ễ; the A/B name and sheet test is refused at the mark in "Debtor 1"; and the API's Generate of Form 101 is a 422 quoting the mark in "First name". The empty-label test reads `''` for the label (its step, `expense_info`, is already right).
- **`time_packet`, 6 of 8:** the three tests that assert nothing is chained find the exception they replace as `__cause__` (`IntakeNotFinished`, `DoesNotExist`, `UnprintableLetter`), and the three filed-form tests stop at `form_101 was refused: FormIsFiled`, since the command checks a filed form as Generate All never does.
- **Startup, 4 of 107:** the four new sheet-group cases pass startup here (`assert [] == [...]`).
- **Five new or changed tests pass on the parent:** `test_a_mark_no_letter_takes_is_refused_at_the_mark` (this check already refuses a lone U+0308), `test_a_widgets_own_key_fills_only_that_widget` (the full-names-first sort is already there), `test_a_form_with_a_copy_and_a_sheet_prints_the_sheet_last` (the D sheet is already titled right), and in `test_rule_fixes.py` the new `test_every_fix_is_a_step_or_page_the_dashboard_links` (Task 8's frontend already has every target) and `test_every_refusal_names_where_to_fix_it`, which only lost an assertion to it. Steps 7, 9, 12 and 23 show the first four fail against a wrong version of the code. The cut-off test and tier 1's box test aren't run here: both pass on the parent, they draw every form, and Steps 10 and 11 show each fail.

```bash
set -eo pipefail
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx src/pages/__tests__/IntakeWizard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  1 failed | 107 passed (108)`, with `shows a form’s refusal once, in Generate All’s list, when Generate All refuses it again` and `AssertionError: expected [ <li><a …(3)></a></li>, <p></p> ] to have a length of 1 but got 2`.

The form's refusal shows twice, in Generate All's list and still on its card. The other two new tests pass on the parent: a refusal of the whole call already leaves the cards' refusals (Step 19 shows that test fail when it doesn't), and the wizard already sends no `update_step` for a linked step (Step 13 shows the new test fail when it does, through the context).

- [ ] **Step 3: Compose the text before the letter rules**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -164,13 +164,15 @@

 def _as_printed(text: str) -> str:
     """
-    The text with every space (a tab, or any Unicode space separator) as a plain space,
-    and format characters such as a soft hyphen left out: the template's font has no
-    glyph for them, and draws U+00A0 as € (R34, R36).
+    The text composed (NFC), so a letter typed as a base letter and a combining mark, such
+    as e and U+0301, is the one letter é the font prints; then with every space (a tab, or
+    any Unicode space separator) as a plain space, and format characters such as a soft
+    hyphen left out: the template's font has no glyph for them, and draws U+00A0 as €
+    (R34, R36).
     """
     return "".join(
         " " if letter == "\t" or unicodedata.category(letter) == "Zs" else letter
-        for letter in text
+        for letter in unicodedata.normalize("NFC", text)
         if unicodedata.category(letter) != "Cf"
     )

PATCH
```

`_as_printed` now reads `unicodedata.normalize("NFC", text)`, so e and U+0301 reach the space, format and control rules, the letter check, `fit()` and the drawing as the one letter é. A letter the font can't print is then refused as the whole letter, and a mark no letter takes stays apart and is refused itself.

- [ ] **Step 4: Run the letter tests**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k 'one_letter or whole_letter or mark_no_letter or marks_apart' apps/forms/tests/test_check.py apps/forms/tests/test_attached_sheets.py apps/forms/tests/test_form_views.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `7 passed, 114 deselected`.

The seven letter tests of Step 1 pass: the three decomposed names, ễ refused as itself, the lone mark, the A/B name and sheet, and Form 101's Generate through the API. The empty-label test still fails until Step 5, so this run leaves it out.

- [ ] **Step 5: Name a box by its index label when its binding has none**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -148,18 +148,22 @@
     """
     The box's label and where the filer fixes its value, from the binding that produced
     the key. A key no binding produced (a test's, the oracle's) gets the index row's
-    label and no fix.
+    label and no fix; a binding with an empty label, the index row's label and its fix.
     """
     name, page, tag = parse_key(key)
+    fix: dict[str, str] = {}
     for field in schema.fields:
         if field.pdf_field == name and field.tag == tag and (tag is None or field.page == page):
-            return field.label, fix_for(field)
+            if field.label:
+                return field.label, fix_for(field)
+            fix = fix_for(field)
+            break
     row = next(
         row
         for row in load_index(schema.template_filename)[name]
         if (row.page, row.tag) == (widget.page, widget.tag)
     )
-    return row.label, {}
+    return row.label, fix


 def _as_printed(text: str) -> str:
PATCH
```

When the binding that produced the key has an empty label, `_source` keeps its fix and takes the label from the field index row of the refused widget.

- [ ] **Step 6: Run the check tests**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs apps/forms/tests/test_check.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `45 passed`.

That is all of `test_check.py`, six new tests among them.

- [ ] **Step 7: Watch the lone-mark test fail when a lone mark is dropped**

```bash
set -eo pipefail
cp backend/apps/forms/services/pdf_filler.py backend/apps/forms/services/pdf_filler.py.keep
trap 'mv backend/apps/forms/services/pdf_filler.py.keep backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -177,7 +177,7 @@
     return "".join(
         " " if letter == "\t" or unicodedata.category(letter) == "Zs" else letter
         for letter in unicodedata.normalize("NFC", text)
-        if unicodedata.category(letter) != "Cf"
+        if unicodedata.category(letter) not in ("Cf", "Mn")
     )


PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k mark_no_letter apps/forms/tests/test_check.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 44 deselected`, with `test_a_mark_no_letter_takes_is_refused_at_the_mark - Failed: DID NOT RAISE <class 'apps.forms.services.pdf_filler.UnprintableLetter'>`.

Here `_as_printed` drops a nonspacing mark (Mn) left over after composing, as it drops a format character, so "Mun" + U+0308 + "oz" prints as "Munoz": a name the filer never typed. The block restores `pdf_filler.py` from the copy it kept, pass or fail; each mutation block below does the same with its file.

- [ ] **Step 8: Watch the label test fail when the index label comes without the binding's step**

```bash
set -eo pipefail
cp backend/apps/forms/services/pdf_filler.py backend/apps/forms/services/pdf_filler.py.keep
trap 'mv backend/apps/forms/services/pdf_filler.py.keep backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -156,7 +156,7 @@
         if field.pdf_field == name and field.tag == tag and (tag is None or field.page == page):
             if field.label:
                 return field.label, fix_for(field)
-            fix = fix_for(field)
+            fix = {}
             break
     row = next(
         row
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k no_label apps/forms/tests/test_check.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 44 deselected`, with `test_a_box_whose_binding_has_no_label_is_named_by_its_index_row - AssertionError: assert ('Food and ho...', None, None) == ('Food and ho...e_info', None)`.

Here a binding with an empty label gets the index row's label but no fix, as a key no binding produced does, so the dashboard would offer no link to Expenses. On the parent the test failed on the label alone; this shows it also holds the step.

- [ ] **Step 9: Watch the own-key test fail when keys are planned in the order given**

```bash
set -eo pipefail
cp backend/apps/forms/services/pdf_filler.py backend/apps/forms/services/pdf_filler.py.keep
trap 'mv backend/apps/forms/services/pdf_filler.py.keep backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -385,7 +385,7 @@

         # Full names first, so a widget's own key overrides its name's.
         filled_by: dict[TemplateWidget, str] = {}
-        for key in sorted(reached, key=lambda key: "@" in key):
+        for key in reached:
             for widget in reached[key]:
                 filled_by[widget] = key

PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k own_key apps/forms/tests/test_check.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 44 deselected`, with `test_a_widgets_own_key_fills_only_that_widget - AssertionError: assert [(TemplateWid...Housing aid')] == [(TemplateWid...1.0), 'SNAP')]`.

Here `check()` plans the keys in the order the values hold them, so with the widget's own key first, its full name, planned after it, overwrites it: both of Schedule I's `Assistance 8f` widgets print "Housing aid". Before this task the test listed the full name first, and this passed (review finding F2).

- [ ] **Step 10: Watch the cut-off test fail when a combo box prints too large for its box**

```bash
set -eo pipefail
cp backend/apps/forms/services/pdf_filler.py backend/apps/forms/services/pdf_filler.py.keep
trap 'mv backend/apps/forms/services/pdf_filler.py.keep backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -406,7 +406,7 @@
             fitted = fit(widget, schema.template_filename, text)
             if fitted is None:
                 raise ValueTooLong(form_type, *_source(schema, key, widget))
-            planned.append(Planned(widget, *fitted))
+            planned.append(Planned(widget, *(fitted if widget.kind != 'ComboBox' else (fitted[0], 14.0))))
         return tuple(planned)

     def fill(self, form_type: str, values: dict) -> bytes:
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k 'cut_off and form_101' apps/forms/tests/test_printed_page.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 94 deselected`, with `test_no_value_is_ever_cut_off[form_101] - AssertionError: assert [('Bankruptcy...ight', 1.889)] == []`.

Here every combo box is drawn at 14 pt, and Form 101's district box prints its widest option 1.889 pt past its right edge. Before this task the cut-off test drew only text boxes, and this passed (review finding m1).

- [ ] **Step 11: Watch tier 1's box test fail when a tick spills into another name's widget**

```bash
set -eo pipefail
cp backend/apps/forms/services/pdf_filler.py backend/apps/forms/services/pdf_filler.py.keep
trap 'mv backend/apps/forms/services/pdf_filler.py.keep backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -407,6 +407,9 @@
             if fitted is None:
                 raise ValueTooLong(form_type, *_source(schema, key, widget))
             planned.append(Planned(widget, *fitted))
+        spare = [w for w in template_widgets(schema.template_filename) if w.drawn and w.kind == 'CheckBox' and w not in filled_by]
+        if spare and any(p.widget.kind == 'CheckBox' and p.value != '/Off' for p in planned):
+            planned.append(Planned(spare[0], spare[0].states[0], None))
         return tuple(planned)

     def fill(self, form_type: str, values: dict) -> bytes:
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k 'ticks_only and form_101' apps/forms/tests/test_oracle_tier1.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `40 failed, 921 deselected`, with `test_checkbox_ticks_only_the_widgets_for_its_answer[form_101:Check Box26:yes] - AssertionError: spill: a tick also prints in [('Check Box1', 1, 'T3')]`.

Here `check()` also ticks the first drawn checkbox no value fills whenever it ticks one, so every box case on Form 101 prints a stray tick in `Check Box1` or `Check Box2`, another name's widget. Before this task the test looked only at the widgets of the box's own name, and this passed (review finding m2).

- [ ] **Step 12: Watch the Schedule D sheet test fail when every sheet takes Schedule A/B's title**

```bash
set -eo pipefail
cp backend/apps/forms/services/sheets.py backend/apps/forms/services/sheets.py.keep
trap 'mv backend/apps/forms/services/sheets.py.keep backend/apps/forms/services/sheets.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/sheets.py b/backend/apps/forms/services/sheets.py
--- a/backend/apps/forms/services/sheets.py
+++ b/backend/apps/forms/services/sheets.py
@@ -171,7 +171,7 @@
     columns carry no binding: the part holds their cells.
     """
     return SheetSpec(
-        part["title"],
+        "Official Form 106A/B, Schedule A/B: Property",
         tuple(SheetColumn(column["label"], "", column["width"]) for column in part["columns"]),
     )

PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k sheet_last apps/forms/tests/test_attached_sheets.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 17 deselected`, with `test_a_form_with_a_copy_and_a_sheet_prints_the_sheet_last - AssertionError: assert ('Maria Torre...r (if known)') == ('Maria Torre...r (if known)')`.

Here `sheet_spec` heads every sheet with Schedule A/B's title, so Schedule D's sheet names the wrong form. Before this task only A/B's sheet title was asserted, and this passed (review finding m17).

- [ ] **Step 13: Watch the shared-provider test fail when the wizard moves the saved step through the context**

```bash
set -eo pipefail
cp frontend/src/pages/IntakeWizard.tsx frontend/src/pages/IntakeWizard.tsx.keep
trap 'mv frontend/src/pages/IntakeWizard.tsx.keep frontend/src/pages/IntakeWizard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -194,6 +194,7 @@
             { replace: true }
           );
         }
+        if (linkedStep !== undefined) void updateCurrentStep(linkedStep).catch(() => {});
         if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
         if (fresh.income_info) setIncomeData(hydrateAmounts(fresh.income_info, INCOME_FIELDS));
         if (fresh.expense_info) setExpenseData(hydrateAmounts(fresh.expense_info, EXPENSE_FIELDS));
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/IntakeWizard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  1 failed | 58 passed (59)`, with `opens the step a dashboard link names, the session already loaded, without moving the filer’s saved place` and `AssertionError: expected 1 to be +0 // Object.is equality`.

Here the wizard saves the linked step as the filer's place through the context's `updateCurrentStep`, the call Continue makes, which would also set a completed intake back to in progress. Only the new test sees it: the four linked-step tests that mount the wizard in a fresh provider still pass, since there the context has no session when the read returns and sends nothing (review finding F3).

- [ ] **Step 14: Time a session with a filed form, and chain no refusal to the command's error**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/management/commands/time_packet.py b/backend/apps/forms/management/commands/time_packet.py
index ddb82bd..fd2d6e9 100644
--- a/backend/apps/forms/management/commands/time_packet.py
+++ b/backend/apps/forms/management/commands/time_packet.py
@@ -4,12 +4,15 @@ time_packet: how long one session's Generate All and each form's download take (
     python manage.py time_packet --session <id> [--budget-generate 5] [--budget-download 3]

 It runs the views' own code: Generate All's preparation and each packet form's check,
-then each form's download, which prepares, resolves and draws the form again. It times
-the first run of a fresh process, every cache cold, as a dyno meets its first request
-after waking, and judges it against the budgets (DIG-137). Everything runs in one
-transaction that is rolled back, so it writes nothing (R13).
+then each form's download, which prepares, resolves and draws the form again. A filed
+form isn't checked, as Generate All returns it untouched, and its download draws what was
+filed, as the download view does. It times the first run of a fresh process, every cache
+cold, as a dyno meets its first request after waking, and judges it against the budgets
+(DIG-137). Everything runs in one transaction that is rolled back, so it writes nothing
+(R13).
 """

+import json
 import time
 from pathlib import Path

@@ -17,6 +20,7 @@ from django.conf import settings
 from django.core.management.base import BaseCommand, CommandError
 from django.db import transaction

+from apps.forms.models import GeneratedForm
 from apps.forms.registry import packet
 from apps.forms.schema import load_schema
 from apps.forms.services.pdf_filler import PDFFormFiller
@@ -40,10 +44,12 @@ class Command(BaseCommand):
         )

     def handle(self, *args, **options):
+        # Each CommandError is raised `from None`: --traceback, or Sentry, would otherwise
+        # print the exception it replaces, whose sentence can quote the filer's letter.
         try:
             session = IntakeSession.objects.get(id=options["session"])
-        except IntakeSession.DoesNotExist as exc:
-            raise CommandError(f"No session {options['session']}.") from exc
+        except IntakeSession.DoesNotExist:
+            raise CommandError(f"No session {options['session']}.") from None

         checks, downloads = {}, {}
         with transaction.atomic():
@@ -52,25 +58,36 @@ class Command(BaseCommand):
                 _prepare(session)
                 form_types = packet(session)
             except Exception as exc:
-                raise CommandError(f"The session was refused: {type(exc).__name__}") from exc
+                raise CommandError(f"The session was refused: {type(exc).__name__}") from None
+            filed = {
+                form.form_type: form
+                for form in GeneratedForm.objects.filter(session=session, status="filed")
+            }
             for form_type in form_types:
+                if form_type in filed:
+                    continue  # Generate All returns a filed form untouched
                 form_started = time.perf_counter()
                 try:
                     with transaction.atomic():  # a savepoint per form, as Generate All has
                         _generate_and_persist(session, form_type, session.user)
                 except Exception as exc:
                     # The type only: a refusal's sentence can quote the filer's letter.
-                    raise CommandError(f"{form_type} was refused: {type(exc).__name__}") from exc
+                    raise CommandError(f"{form_type} was refused: {type(exc).__name__}") from None
                 checks[form_type] = time.perf_counter() - form_started
             generate_all = time.perf_counter() - started

             for form_type in form_types:
                 form_started = time.perf_counter()
                 try:
-                    _prepare(session)
-                    pdf = PDFFormFiller().fill(form_type, _resolve(form_type, session))
+                    if form_type in filed and filed[form_type].field_values:
+                        # As the download view: a filed form draws what was filed
+                        values = json.loads(filed[form_type].field_values)
+                    else:
+                        _prepare(session)
+                        values = _resolve(form_type, session)
+                    pdf = PDFFormFiller().fill(form_type, values)
                 except Exception as exc:
-                    raise CommandError(f"{form_type} was refused: {type(exc).__name__}") from exc
+                    raise CommandError(f"{form_type} was refused: {type(exc).__name__}") from None
                 downloads[form_type] = (time.perf_counter() - form_started, len(pdf))
             transaction.set_rollback(True)  # write nothing (R13)

@@ -80,8 +97,9 @@ class Command(BaseCommand):
         for form_type in form_types:
             seconds, size = downloads[form_type]
             template = Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
+            check = f"{checks[form_type]:.2f}" if form_type in checks else "filed"
             self.stdout.write(
-                f"{form_type:<16}{checks[form_type]:>9.2f}{seconds:>12.2f}"
+                f"{form_type:<16}{check:>9}{seconds:>12.2f}"
                 f"{size / 1024:>9.0f}{template.stat().st_size / 1024:>13.0f}"
             )
         slowest = max(downloads, key=lambda form_type: downloads[form_type][0])
PATCH
```

`time_packet` reads the session's filed forms. Its Generate All loop skips them, as `generate_all` returns them untouched; its download loop draws a filed form's stored values when it has them, as `views.download` does, and otherwise prepares and resolves the form. The check column reads `filed` for a filed form. Each `CommandError` is raised `from None`, so nothing chained to it can print the filer's letter.

- [ ] **Step 15: Run the time_packet tests**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs apps/forms/tests/test_time_packet.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `8 passed`.

- [ ] **Step 16: Watch the filed-form tests fail when every stored form is skipped, or empty values are read**

```bash
set -eo pipefail
cp backend/apps/forms/management/commands/time_packet.py backend/apps/forms/management/commands/time_packet.py.keep
trap 'mv backend/apps/forms/management/commands/time_packet.py.keep backend/apps/forms/management/commands/time_packet.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/management/commands/time_packet.py b/backend/apps/forms/management/commands/time_packet.py
--- a/backend/apps/forms/management/commands/time_packet.py
+++ b/backend/apps/forms/management/commands/time_packet.py
@@ -61,7 +61,7 @@
                 raise CommandError(f"The session was refused: {type(exc).__name__}") from None
             filed = {
                 form.form_type: form
-                for form in GeneratedForm.objects.filter(session=session, status="filed")
+                for form in GeneratedForm.objects.filter(session=session)
             }
             for form_type in form_types:
                 if form_type in filed:
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs apps/forms/tests/test_time_packet.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 7 passed`, with `test_time_packet_times_a_session_with_a_filed_form_and_draws_what_was_filed - ValueError: could not convert string to float: 'filed'`.

Here `time_packet` treats every stored form as filed, so on a session that has run Generate All it would check nothing and report a Generate All of almost no time, and the budget (DIG-137) would pass without being measured. The unfiled Form 121's row reads `filed` where the test wants a time.

```bash
set -eo pipefail
cp backend/apps/forms/management/commands/time_packet.py backend/apps/forms/management/commands/time_packet.py.keep
trap 'mv backend/apps/forms/management/commands/time_packet.py.keep backend/apps/forms/management/commands/time_packet.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/management/commands/time_packet.py b/backend/apps/forms/management/commands/time_packet.py
--- a/backend/apps/forms/management/commands/time_packet.py
+++ b/backend/apps/forms/management/commands/time_packet.py
@@ -79,7 +79,7 @@
             for form_type in form_types:
                 form_started = time.perf_counter()
                 try:
-                    if form_type in filed and filed[form_type].field_values:
+                    if form_type in filed:
                         # As the download view: a filed form draws what was filed
                         values = json.loads(filed[form_type].field_values)
                     else:
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs apps/forms/tests/test_time_packet.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 7 passed`, with `test_time_packet_draws_a_filed_form_stored_without_values_from_the_intake - django.core.management.base.CommandError: form_101 was refused: JSONDecodeError`.

Here a filed form stored without values is read as stored values, and `json.loads("")` refuses it, where the download view resolves it from the intake. The review saw both of these mutants pass before fix round 1 (R72, review Minor 5).

- [ ] **Step 17: Let Generate All's answer replace every card's refusal**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
index 438306f..19a3b84 100644
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -143,7 +143,9 @@ export function FormDashboard() {
   const [generationErrors, setGenerationErrors] = useState<GenerateAllError[]>([]);
   const [generateAllRefusal, setGenerateAllRefusal] = useState<Refusal | null>(null);
   // Each form's last refused Generate or Download, until its own Generate or Download next
-  // succeeds, Generate All returns it in `generated` (a filed form included), or it is marked filed
+  // succeeds, Generate All answers (its lists then hold every checked form's current refusal; a
+  // filed form, which it returns unchecked, shows none until its next Download), or it is marked
+  // filed. A refusal of Generate All's whole call leaves them.
   const [formRefusals, setFormRefusals] = useState<Partial<Record<FormType, Refusal>>>({});
   const [dischargeData, setDischargeData] = useState<DebtClassification[]>([]);

@@ -209,9 +211,9 @@ export function FormDashboard() {
     try {
       const response = await api.forms.generateAll(session.id);
       setForms(response.generated);
-      // Every form Generate All returns in `generated` loses its card's refusal, a filed form
-      // included, which Generate All returns untouched
-      response.generated.forEach((form) => setFormRefusal(form.form_type, undefined));
+      // Generate All's answer replaces every card's refusal: a form it refused again is in its
+      // list, so the same words and link don't show twice, and an older refusal can't stay
+      setFormRefusals({});
       setGenerationErrors(response.errors);
       trackEvent('form_generated', { form_type: 'all', session_id: session.id });
       setShowSurvey(true);
PATCH
```

When Generate All answers with `{generated, errors}`, every card's refusal clears, and its list holds the current ones. A refusal of the whole call leaves the cards' as they are. The state's comment says how long a card's refusal lasts.

- [ ] **Step 18: Run the dashboard and wizard tests**

```bash
set -eo pipefail
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx src/pages/__tests__/IntakeWizard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: `Test Files  2 passed (2)` and `Tests  108 passed (108)`.

- [ ] **Step 19: Watch the whole-call test fail when a refusal of the whole call clears the cards**

```bash
set -eo pipefail
cp frontend/src/pages/FormDashboard.tsx frontend/src/pages/FormDashboard.tsx.keep
trap 'mv frontend/src/pages/FormDashboard.tsx.keep frontend/src/pages/FormDashboard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -219,6 +219,7 @@
       setShowSurvey(true);
     } catch (err) {
       setGenerateAllRefusal(refusalOf(err, ERROR_GENERIC));
+      setFormRefusals({});
     }
     // Generate All works the means test out again, so the packet may have changed
     try {
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  1 failed | 48 passed (49)`, with `keeps a form’s refusal when Generate All is refused as a whole` and `TestingLibraryElementError: Unable to find an element with the text: The court form can't print the letter “ą” in “Last name”. Change it to a letter without the mark.`.

Here a refusal of the whole call also clears every card's refusal, though it checked no form, and Form 101's card loses its refusal and its link. The review saw this mutant pass every dashboard test before fix round 1 (R72, review Minor 6).

- [ ] **Step 20: Refuse at startup every sheet-group slot no column prints, and every box slot**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
index d6ea926..269bc66 100644
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -406,9 +406,10 @@ def validate_schema(
         elif group.sheet is not None:
             # The rows a sheet prints are the slots' rows: a column of another list would
             # print rows that aren't the group's, or leave some of them out. A cell prints
-            # its slot's text, and a box's answer is a state, which a sheet can't tick.
+            # its slot's text, and a box's answer is a state, which a sheet can't tick, mapped
+            # to one yet or not.
             for column in group.sheet.columns:
-                bound = [f for f in mapped if f.binding == column.binding]
+                bound = [f for f in rows if f.binding == column.binding]
                 if not bound:
                     errors.append(
                         (
@@ -426,12 +427,14 @@ def validate_schema(
                         )
                     )
             # And every slot's value prints in a column, or the rows past the slots would
-            # drop it: a text or combo slot needs a column of its binding, and a box slot
-            # can't continue at all. (A sheet with no columns is reported as such below.)
+            # drop it: a text or combo slot needs a column of its binding, so one with no
+            # binding (a constant, a derived value) can't continue, and a box slot can't
+            # continue at all, bound or not. (A sheet with no columns is reported as such
+            # below.)
             columns = {column.binding for column in group.sheet.columns}
-            unprinted = {f.binding for f in mapped if f.binding} - columns if columns else set()
+            unprinted = {f.binding for f in rows if f.binding} - columns if columns else set()
             for binding in sorted(unprinted):
-                if any(f.type in ("checkbox", "radio") for f in mapped if f.binding == binding):
+                if any(f.type in ("checkbox", "radio") for f in rows if f.binding == binding):
                     errors.append(
                         (
                             "E007",
@@ -447,6 +450,25 @@ def validate_schema(
                             "which a slot of the group binds",
                         )
                     )
+            for f in rows if columns else ():
+                if f.binding:
+                    continue
+                if f.type in ("checkbox", "radio"):
+                    errors.append(
+                        (
+                            "E007",
+                            f"group {name!r}: a box slot fills {f.pdf_field!r} on row {f.row}, "
+                            "and a sheet can't tick a box",
+                        )
+                    )
+                else:
+                    errors.append(
+                        (
+                            "E007",
+                            f"group {name!r}: no sheet column prints {f.pdf_field!r} on row "
+                            f"{f.row}, a slot of the group that binds no list",
+                        )
+                    )
         elif group.extra_page is None:
             errors.append(("E007", f"group {name!r} names neither an extra_page nor a sheet"))
         elif group.extra_page not in pages:
PATCH
```

In a sheet group, the column rule and the unprinted rule read every slot (`rows`), mapped to a state or not, and a new loop refuses each slot with no binding: a box slot, since a sheet has no box to tick, and a text or combo slot, since no column can print a value no list holds.

- [ ] **Step 21: Run the startup tests**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs apps/forms/tests/test_checks.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `107 passed`.

That is all of `test_checks.py`, the four new sheet-group cases among them. So are the 17 cases of `test_every_registered_form_passes`: the production schemas still pass, since none has a group.

- [ ] **Step 22: Watch the column case fail when the column rule reads only mapped slots**

```bash
set -eo pipefail
cp backend/apps/forms/schema.py backend/apps/forms/schema.py.keep
trap 'mv backend/apps/forms/schema.py.keep backend/apps/forms/schema.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -409,7 +409,7 @@
             # its slot's text, and a box's answer is a state, which a sheet can't tick, mapped
             # to one yet or not.
             for column in group.sheet.columns:
-                bound = [f for f in rows if f.binding == column.binding]
+                bound = [f for f in mapped if f.binding == column.binding]
                 if not bound:
                     errors.append(
                         (
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k cannot_print_its_rows_whole apps/forms/tests/test_checks.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 21 passed, 85 deselected`, with `test_a_sheet_that_cannot_print_its_rows_whole_is_reported[a box slot not yet mapped, in a column] - assert [] == [('forms.E007... can't tick")]`.

Here the column rule sees only slots mapped to a state, as before fix round 1, so a box not yet mapped in the list the Make column prints passes startup. The other three new cases are still refused, by the unprinted rule and the new loop (R72, review Minor 3).

- [ ] **Step 23: Watch the frontend-reading test fail when a step or a page is renamed on one side**

```bash
set -eo pipefail
cp frontend/src/constants/wizardSteps.ts frontend/src/constants/wizardSteps.ts.keep
trap 'mv frontend/src/constants/wizardSteps.ts.keep frontend/src/constants/wizardSteps.ts' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/constants/wizardSteps.ts b/frontend/src/constants/wizardSteps.ts
--- a/frontend/src/constants/wizardSteps.ts
+++ b/frontend/src/constants/wizardSteps.ts
@@ -5,7 +5,7 @@
 export const WIZARD_STEPS = [
   { number: 1, label: 'Your Information', key: 'debtor_info' },
   { number: 2, label: 'Income', key: 'income_info' },
-  { number: 3, label: 'Expenses', key: 'expense_info' },
+  { number: 3, label: 'Expenses', key: 'expenses' },
   { number: 4, label: 'Assets', key: 'assets' },
   { number: 5, label: 'Amounts Owed', key: 'debts' },
   { number: 6, label: 'Contracts & Leases', key: 'contracts' },
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k dashboard_links apps/forms/tests/test_rule_fixes.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 22 deselected`, with `test_every_fix_is_a_step_or_page_the_dashboard_links - AssertionError: assert [{'step': 'ex...e_info'}, ...] == []`.

Here the wizard's Expenses step is renamed in `wizardSteps.ts` alone, and every rule and binding that sends the filer to `expense_info` would lose its link.

```bash
set -eo pipefail
cp frontend/src/constants/wizardSteps.ts frontend/src/constants/wizardSteps.ts.keep
trap 'mv frontend/src/constants/wizardSteps.ts.keep frontend/src/constants/wizardSteps.ts' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/constants/wizardSteps.ts b/frontend/src/constants/wizardSteps.ts
--- a/frontend/src/constants/wizardSteps.ts
+++ b/frontend/src/constants/wizardSteps.ts
@@ -10,5 +10,5 @@
   { number: 5, label: 'Amounts Owed', key: 'debts' },
   { number: 6, label: 'Contracts & Leases', key: 'contracts' },
   { number: 7, label: 'Codebtors', key: 'codebtors' },
-  { number: 8, label: 'Review & Results', key: 'review' },
+  { number: 8, label: 'Review & Results', key: 'results' },
 ];
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k dashboard_links apps/forms/tests/test_rule_fixes.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 22 deselected`, with `test_every_fix_is_a_step_or_page_the_dashboard_links - AssertionError: assert [{'step': 'review'}] == []`.

```bash
set -eo pipefail
cp frontend/src/pages/FormDashboard.tsx frontend/src/pages/FormDashboard.tsx.keep
trap 'mv frontend/src/pages/FormDashboard.tsx.keep frontend/src/pages/FormDashboard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -52,7 +52,7 @@
  * intake's own words, and "Go to" with each other page's heading (step 3a2 spec §4.5, ruling R22)
  */
 const PAGE_LINK_LABELS: Record<string, string> = {
-  '/intake': 'Finish your intake',
+  '/finish': 'Finish your intake',
   '/fee-waiver': 'Go to Filing Fee Waiver Application',
   '/sofa': 'Go to Statement of Financial Affairs',
   '/documents': 'Go to Upload your documents',
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k dashboard_links apps/forms/tests/test_rule_fixes.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 22 deselected`, with `test_every_fix_is_a_step_or_page_the_dashboard_links - AssertionError: assert [{'page': '/intake'}] == []`.

Here the Review step's key and the `/intake` page are renamed on the frontend. Only an exception names either: `PreconditionMissing(…, step="review")` in `registry.py` and `IntakeNotFinished.page`. Both renames passed before fix round 1 (R72, review Minor 4).

```bash
set -eo pipefail
cp frontend/src/pages/FormDashboard.tsx frontend/src/pages/FormDashboard.tsx.keep
trap 'mv frontend/src/pages/FormDashboard.tsx.keep frontend/src/pages/FormDashboard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -54,7 +54,7 @@
 const PAGE_LINK_LABELS: Record<string, string> = {
   '/intake': 'Finish your intake',
   '/fee-waiver': 'Go to Filing Fee Waiver Application',
-  '/sofa': 'Go to Statement of Financial Affairs',
+  '/statement': 'Go to Statement of Financial Affairs',
   '/documents': 'Go to Upload your documents',
 };

PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs -k dashboard_links apps/forms/tests/test_rule_fixes.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 22 deselected`, with `test_every_fix_is_a_step_or_page_the_dashboard_links - AssertionError: assert [{'page': '/sofa'}] == []`.

Here `/sofa` is renamed in `PAGE_LINK_LABELS`. Only the test's synthetic SOFA list binding names it, since no production schema binds a `sofa.` list yet; a check of `RULE_FIXES` alone would have passed.

- [ ] **Step 24: Watch the frontend-reading test skip, saying why, where the frontend's source isn't**

```bash
set -eo pipefail
mv frontend/src frontend/src.away
trap 'mv frontend/src.away frontend/src' EXIT
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfEs apps/forms/tests/test_rule_fixes.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR|SKIPPED) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `the frontend's source isn't here (compose's backend mounts backend/ only)` and `22 passed, 1 skipped`.

With `frontend/src` moved away, as in compose's backend container (which mounts `./backend` and `./data` only), the new test skips and `-rs` prints why; the other 22 tests of the file run. The block puts `frontend/src` back when it ends.

- [ ] **Step 25: Say in the docs what changed**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 1abf2bb..67f93d4 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -29,16 +29,16 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. It reads the median table in force on today's real date, not the tests' pinned one, and when none is (from November 1, 2026 until the November table is loaded) it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, so even `--reset` leaves the existing personas. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
 - **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
 - **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so are income not entered by source (`IncomeNotSplit`), no median table in force on the fill date (`NoTableInForce`, which logs the table, the date and the district), and a letter the form's font can't print (`UnprintableLetter`) or a value too long for its box even at 6 pt (`ValueTooLong`), whose sentences name the box; any other failure is a 500 logged by exception type only.
-- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), an Expenses step never saved (no `ExpenseInfo` row), and a scanned debt the filer hasn't confirmed (a `DebtInfo` with `is_draft`, step `debts`; see "Document upload sits mid-wizard"). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`), `IntakeNotFinished.page` (`/intake`) and the `step` or `page` of an `UnprintableLetter` or `ValueTooLong`, from the binding that feeds the box (`fix_for` in `fill_resolver.py`); "already filed", "not in your packet", `NoTableInForce` and the download of a filed form whose stored values `check()` refuses carry neither, and the key is absent, never null. The check lives in the views, not in `build_parts` or `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must lock the session first (see "Saves lock the session") and call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
+- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), an Expenses step never saved (no `ExpenseInfo` row), and a scanned debt the filer hasn't confirmed (a `DebtInfo` with `is_draft`, step `debts`; see "Document upload sits mid-wizard"). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`), `IntakeNotFinished.page` (`/intake`) and the `step` or `page` of an `UnprintableLetter` or `ValueTooLong`, from the binding that feeds the box (`fix_for` in `fill_resolver.py`); "already filed", "not in your packet", `NoTableInForce` and the download of a filed form whose stored values hold a letter or a length `check()` refuses carry neither, and the key is absent, never null. The check lives in the views, not in `build_parts` or `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must lock the session first (see "Saves lock the session") and call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
-- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. Generate, Generate All and Regenerate check without drawing: each resolves the form's parts (`build_parts`), runs `PDFFormFiller.check()` and stores them, so a letter the form can't print or a value too long for its box is a 422, or a Generate All `errors` entry, carrying its `step` or `page`. The browser sends Generate All once (`apiFetchOnce`, never `withRetry`), and the dashboard links each refusal it shows (the packet list's, Generate All's whole-call refusal, a Generate All `errors` entry, or a card's refused Generate or Download, whose body `downloadForm` reads after its one token refresh) to its fix: a `step` to `/intake?step=<key>`, a `page` to that page, "Finish your intake" at most once. A card's refusal stays until its own Generate or Download next succeeds, Generate All returns that form in `generated` (a filed form included, which it returns untouched), or the form is marked filed. Download draws: `fill()` bakes with PyMuPDF, which isn't thread-safe, so the server stays on sync gunicorn workers with no `--threads` unless the bake gets a lock. Generate calls PyMuPDF too, without drawing: `check()` measures an attached sheet's text with PyMuPDF's `Font` (`sheets.plan_sheet`), and so does the startup check. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download draws its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
-- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. For repeat groups, E007 refuses one not declared in the schema's `groups`, one that names neither or both of an `extra_page` and a `sheet`, an `extra_page` that isn't the page of the group's last slots, a `number` without `{n}` (also when only `number_boxes` or a `sheet` is set), one that `format(n=1)` can't fill or that prints the same for `n=1` and `n=2`, a second group with an `extra_page` on one form (3a2's limit), fields that differ in `repeat_capacity` or `conditional_on` or whose slot rows aren't exactly 1 to `repeat_capacity`, a slot row whose boxes sit on more than one page, rows that go back a page as the row number rises, and an untagged slot binding that would print its row more than once: a text or combo one whose name has more than one drawn widget, or a checkbox or radio one whose drawn widgets share an on-state (a column whose boxes each have their own state, such as Schedule D's `check 4`, passes); for a `sheet`, E007 also refuses no columns, columns wider than 504 pt (7 in) with the 36 pt line column, a column whose binding isn't a `sofa.<collection>[].<attr>` list or isn't one of the group's slot bindings, or that any box slot binds, a slot binding no column prints (the rows past the slots would drop it), any other box slot (a sheet has no box to tick), a first sheet line (`number` for the row past the slots) that doesn't print whole on one line of the 36 pt line column, two columns with one label, a label or title the sheet can't print whole (a letter the form's template can't print, or a word wider than its column or the page), and `page_numbers` (a sheet group has no copies); E003 refuses a number box for a row that isn't a slot row, a number or page-number box that is no drawn widget on its row's or page's page, an untagged number or page-number `this` box whose name has more than one drawn widget, and any untagged binding whose `page` holds no drawn widget of its name (a copy picks its rows' boxes by `page`); and E006 counts each group box (`number_boxes` values and `page_numbers` `this` and `of`, one `of` key once) as a writer beside the bindings. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
+- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. Generate, Generate All and Regenerate check without drawing: each resolves the form's parts (`build_parts`), runs `PDFFormFiller.check()` and stores them, so a letter the form can't print or a value too long for its box is a 422, or a Generate All `errors` entry, carrying its `step` or `page`. `check()` composes the text first (NFC, in `pdf_filler._as_printed`, which the sheets use too), so a letter typed as a letter and a combining mark, such as e and U+0301, is checked and printed as the one letter é. The browser sends Generate All once (`apiFetchOnce`, never `withRetry`), and the dashboard links each refusal it shows (the packet list's, Generate All's whole-call refusal, a Generate All `errors` entry, or a card's refused Generate or Download, whose body `downloadForm` reads after its one token refresh) to its fix: a `step` to `/intake?step=<key>`, a `page` to that page, "Finish your intake" at most once. A card's refusal stays until its own Generate or Download next succeeds, Generate All answers with its `generated` and `errors` (which then hold every checked form's current refusal, so none shows twice; a filed form, which Generate All returns unchecked, shows none until its next Download; a refusal of the whole call leaves the cards' as they are), or the form is marked filed. Download draws: `fill()` bakes with PyMuPDF, which isn't thread-safe, so the server stays on sync gunicorn workers with no `--threads` unless the bake gets a lock. Generate calls PyMuPDF too, without drawing: `check()` measures an attached sheet's text with PyMuPDF's `Font` (`sheets.plan_sheet`), and so does the startup check. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download draws its stored `field_values` without the packet check, and a letter or a length in them that `check()` refuses is a 422 with no `step` or `page`, any other refusal of them a 500; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
+- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. For repeat groups, E007 refuses one not declared in the schema's `groups`, one that names neither or both of an `extra_page` and a `sheet`, an `extra_page` that isn't the page of the group's last slots, a `number` without `{n}` (also when only `number_boxes` or a `sheet` is set), one that `format(n=1)` can't fill or that prints the same for `n=1` and `n=2`, a second group with an `extra_page` on one form (3a2's limit), fields that differ in `repeat_capacity` or `conditional_on` or whose slot rows aren't exactly 1 to `repeat_capacity`, a slot row whose boxes sit on more than one page, rows that go back a page as the row number rises, and an untagged slot binding that would print its row more than once: a text or combo one whose name has more than one drawn widget, or a checkbox or radio one whose drawn widgets share an on-state (a column whose boxes each have their own state, such as Schedule D's `check 4`, passes); for a `sheet`, E007 also refuses no columns, columns wider than 504 pt (7 in) with the 36 pt line column, a column whose binding isn't a `sofa.<collection>[].<attr>` list or isn't one of the group's slot bindings, or that any box slot binds, a slot no column prints, bound or not, a constant or a derived one included (the rows past the slots would drop it), any box slot, bound or not (a sheet has no box to tick), a first sheet line (`number` for the row past the slots) that doesn't print whole on one line of the 36 pt line column, two columns with one label, a label or title the sheet can't print whole (a letter the form's template can't print, or a word wider than its column or the page), and `page_numbers` (a sheet group has no copies); E003 refuses a number box for a row that isn't a slot row, a number or page-number box that is no drawn widget on its row's or page's page, an untagged number or page-number `this` box whose name has more than one drawn widget, and any untagged binding whose `page` holds no drawn widget of its name (a copy picks its rows' boxes by `page`); and E006 counts each group box (`number_boxes` values and `page_numbers` `this` and `of`, one `of` key once) as a writer beside the bindings. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. Tiers 1 and 3 read the printed page, not `/V`: `read_drawn` (`apps/forms/tests/pdf_readback.py`) takes a widget's Helvetica text and the template's ZapfDingbats check mark inside its rect, and reads `""` where a box prints only the blank template's own default (the district combos' placeholder, A/B `19.1`–`19.3 % of ownership` "0%", C `page 2` and G `fill 2.6` "2"), so a blank assertion on such a box can't see that default. `read_drawn` refuses a PDF that still has a widget (a `ValueError`, never a listed defect), so it reads only `fill()`'s baked output. The list has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
 - **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, the one function behind all of them; any other error fails the form). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine stays for later steps, and only synthetic tests reach it: a repeat group (`repeat`) is declared in the schema's top-level `groups` with the `extra_page` that continues it or the `sheet` that takes its rows (forms.E007 refuses a group with neither or both). Rows past its last slot print on copies of that page, each a `copy` part drawn alone and put in right after the page or the copy before it, numbered by the group's `number` and `page_numbers` boxes, or on an attached sheet (`apps/forms/services/sheets.py`): plain US Letter pages after the form's pages and copies, each headed by the filer's name, the form's title with "(attached sheet)" and a blank "Case number (if known)", with every row labelled by its `number` under the group's columns, in Helvetica at 10 pt. PyMuPDF draws its Helvetica in WinAnsiEncoding, so `draw_sheet()` writes each letter's code in the templates' own `/Helv` encoding (`sheets._DIFFERENCES`, which all 17 templates share and a test pins) and gives every sheet page's font that `/Encoding`: a sheet prints exactly the forms' letters, Ł, ł and ı included, and refuses the rest with the forms' own check (`text_fit.printable` on the form's `/Helv`, which also refuses □, the template's `/.notdef`). A sheet's pages are not counted in the form's page numbers. A total adds up every row, the copies' and the sheet's included. `RepeatOverflow` is gone.
-- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, a parts document in printing order: `{"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}` (`registry.build_parts`). The API never returns it. Each copy of an extra page follows the form part as a part of its own, `{"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}}`, and each attached sheet follows the copies, `{"kind": "sheet", "group": <group>, "title": <its title>, "columns": [{"label": str, "width": <points>}], "name": <the filer's full name>, "rows": [{"line": "3.5", "cells": [<one per column>]}]}`; `check()` and `fill()` draw a sheet part from its own title and columns (`sheets.sheet_spec`), never the schema's, so a filed sheet prints exactly what was filed whatever its schema says later. `form_data` is blank; its column is dropped one release after this code is live. Generate, Generate All and Regenerate store the document they checked; an unfiled form is resolved, checked and drawn fresh on every download, and its document stored again. A filed form draws its stored document, so it prints exactly what was filed. A form filed before forms step 3a2 holds `{full name: value}` with no `version`, which `parts_of` (`pdf_filler.py`) reads as one form part. A filed form whose stored values `check()` refuses downloads as a 422 with the refusal's sentence and no `step` or `page`, since no step changes what was filed.
+- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, a parts document in printing order: `{"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}` (`registry.build_parts`). The API never returns it. Each copy of an extra page follows the form part as a part of its own, `{"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}}`, and each attached sheet follows the copies, `{"kind": "sheet", "group": <group>, "title": <its title>, "columns": [{"label": str, "width": <points>}], "name": <the filer's full name>, "rows": [{"line": "3.5", "cells": [<one per column>]}]}`; `check()` and `fill()` take a sheet part's title, columns and rows from the part (`sheets.sheet_spec`), never from the schema, so a filed sheet prints exactly what was filed whatever its schema says later: the schema gives only the template whose letters the check uses and, for a refusal, its fix and the name box's label. `form_data` is blank; its column is dropped one release after this code is live. Generate, Generate All and Regenerate store the document they checked; an unfiled form is resolved, checked and drawn fresh on every download, and its document stored again. A filed form draws its stored document, so it prints exactly what was filed. A form filed before forms step 3a2 holds `{full name: value}` with no `version`, which `parts_of` (`pdf_filler.py`) reads as one form part. A filed form whose stored values hold a letter or a length `check()` refuses downloads as a 422 with the refusal's sentence and no `step` or `page`, since no step changes what was filed; any other refusal of them (a template changed under the filed form) is a 500.
 - **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
 - **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
 - **CI ruff is pinned** — `ci.yml` installs `ruff==0.8.5`. Unpinned ruff broke CI when new rules shipped.
@@ -84,7 +84,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.

 - **Backend:** Django 5.0 + DRF, Python 3.11, PostgreSQL 15, `encrypted-model-fields` (Fernet PII encryption)
 - **Frontend:** React 19 + Vite 7 + TypeScript, Context API (not Redux), react-router-dom v7
-- **PDF:** pypdf and PyMuPDF draw on the official AO court templates. Each schema in `data/forms/schemas/` binds a field to a widget's full name in the field index (`data/forms/field_index/<template stem>.index.json`). `build_parts(form_type, session)`, which the views call, checks the form's preconditions and resolves its schema into the parts document `field_values` stores (`build_field_values` returns the form's `{key: value}` instead); `PDFFormFiller().check(form_type, values)` plans the widgets each key names (a full name, or `<full name>@<page>:<tag>` for one widget) in the template from `data/forms/pdfs/`, and raises `UnknownField` for any other name; `fill()` runs it, then pypdf builds each planned widget's own appearance and PyMuPDF bakes every remaining widget into the page (the print buttons and the second widget of each stacked pair are removed first), so the PDF it returns can't be filled in a viewer.
+- **PDF:** pypdf and PyMuPDF draw on the official AO court templates. Each schema in `data/forms/schemas/` binds a field to a widget's full name in the field index (`data/forms/field_index/<template stem>.index.json`). `build_parts(form_type, session)`, which the views call, checks the form's preconditions and resolves its schema into the parts document `field_values` stores (`build_field_values` returns the form's `{key: value}` instead); `PDFFormFiller().check(form_type, values)` plans the widgets each key names (a full name, or `<full name>@<page>:<tag>` for one widget) in the template from `data/forms/pdfs/`, and raises `UnknownField` for any other name; `fill()` runs it, then pypdf builds each planned widget's own appearance and PyMuPDF bakes every remaining widget into the page (every push button, Print, Reset, Save As and Add Attachment, and the second widget of each stacked pair are removed first), so the PDF it returns can't be filled in a viewer.
 - **PDF templates:** 67 official AO court PDFs in `data/forms/pdfs/` (committed). Baked into Heroku image.
 - **Forms:** 17 form types in `apps/forms/registry.py` (`FORM_REGISTRY` / `get_all_form_types()` / `packet(session)`). `generate_all` gives each form its own savepoint.
 - **OCR service:** provider-agnostic. `OCR_PROVIDER` selects `openai` (default, `gpt-4o`, `OPENAI_API_KEY`) or `gemini` (`gemini-2.0-flash`, `GEMINI_API_KEY`); `OCR_MODEL` overrides the model so a model change is a config var, not a deploy. No local model — both call a hosted API directly.
diff --git a/docs/superpowers/specs/2026-10-16-forms-step3-design.md b/docs/superpowers/specs/2026-10-16-forms-step3-design.md
index 3e905bd..fd571fd 100644
--- a/docs/superpowers/specs/2026-10-16-forms-step3-design.md
+++ b/docs/superpowers/specs/2026-10-16-forms-step3-design.md
@@ -756,7 +756,7 @@ Every owner answer, controller ruling, ticket and counsel item maps to exactly o
 | CORR.valid_through | 3a1 | `valid_through` per table; irregular tables guarded only by the runbook; tests pin the fill date                                   |
 | CORR.J3            | 3e2 | Schedule J line 3 asked in the form's words on the Expenses step (owner confirmed)                                                 |
 | CORR.J45           | 3c  | A homeowner's J line 4 mortgage payment and J line 5 from the debts linked to "my home"; 3e2 does not ask line 5 (owner confirmed) |
-| SPIKE              | 3a2 | The engine method (PyMuPDF `insert_text` plus `delete_widget`; exact-clip oracle), replaced by 3a2's spec §3                       |
+| SPIKE              | 3a2 | The engine method (PyMuPDF `insert_text` plus `delete_widget`; exact-clip oracle), replaced by 3a2's §3 (engine) and §8 (oracle)   |
 | DIG-273            | 3a1 | The id round-trip for assets and debts, and the `useAutoSave` baseline                                                             |
 | DIG-274            | 3a1 | The median fix                                                                                                                     |
 | DIG-275            | 3h  | Line 35's past-due amount ÷ 60 in the one calculator                                                                               |
PATCH
```

In `CLAUDE.md`:

- "Forms need a completed intake", "GenerateAll vs single" and "`field_values`, not `form_data`": a filed form's download is a 422 with no `step` or `page` when its stored values hold a letter or a length `check()` refuses; any other refusal of it is a 500 (m6).
- "GenerateAll vs single": the letter check composes the text first (NFC, in `_as_printed`, which the sheets use too); a card's refusal clears when Generate All answers with its lists, a filed form's until its next Download, and a refusal of the whole call leaves them.
- "Schemas are checked at startup": a sheet group refuses every slot no column prints, bound or not, and any box slot, bound or not.
- "`field_values`, not `form_data`": `check()` and `fill()` take a sheet's title, columns and rows from its part; the schema gives only the template and, for a refusal, its fix and the name box's label (m14).
- The Architecture PDF line: every push button (Print, Reset, Save As and Add Attachment) is removed before the bake (m13).

The umbrella spec's SPIKE row now points to 3a2's §3 (engine) and §8 (oracle) (m15).

- [ ] **Step 26: Run every gate**

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

Expected: `2814 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  423 passed (423)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

That is 17 more backend cases than after Task 8: six in `test_check.py`, four in `test_time_packet.py`, four in `test_checks.py`, and one each in `test_attached_sheets.py`, `test_form_views.py` and `test_rule_fixes.py`. Vitest gains three tests, two on the dashboard and one in the wizard. The 25 skips are the Postgres-only tests under sqlite; the new frontend-reading test runs here, since the checkout has `frontend/src`. Under a heavy load (1-minute load above 15) a SOFAStep or FormDashboard test can run past vitest's 5 s per-test timeout; run vitest again on a quieter machine before suspecting the code. The next command runs the Postgres-only tests against the database named by `DATABASE_URL` in `.claude/forms-step3a2.env`.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

This task touches no locking, so they pass unchanged.

- [ ] **Step 27: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 8 passed` and `RUN 2 exit=0: 8 passed`.

Every journey that prepares forms runs `check()`, and with it `_as_printed`; five persona journeys (Andrés, DeShawn, James, Maria and Sarah) and the SOFA journey press Generate All, whose answer now clears the cards' refusals.

These results are the implementer's; this plan's own check doesn't run the journeys. They ran on the task's first commit, 80c9fac (`RUN 1 exit=0: 8 passed (1.2m)`, `RUN 2 exit=0: 8 passed (1.3m)`). The tree committed below differs from 80c9fac in production code only in `schema.py`'s sheet column rule (`mapped` to `rows`), a startup rule for groups, which no production schema has, and in a comment in `FormDashboard.tsx`; the rest is tests and `CLAUDE.md` (R72). The controller read that delta, and the journeys were not run again.

- [ ] **Step 28: Commit**

```bash
set -eo pipefail
git add \
  CLAUDE.md \
  backend/apps/forms/management/commands/time_packet.py \
  backend/apps/forms/schema.py \
  backend/apps/forms/services/pdf_filler.py \
  backend/apps/forms/tests/test_attached_sheets.py \
  backend/apps/forms/tests/test_check.py \
  backend/apps/forms/tests/test_checks.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/tests/test_oracle_tier1.py \
  backend/apps/forms/tests/test_printed_page.py \
  backend/apps/forms/tests/test_rule_fixes.py \
  backend/apps/forms/tests/test_time_packet.py \
  docs/superpowers/specs/2026-10-16-forms-step3-design.md \
  frontend/src/pages/FormDashboard.tsx \
  frontend/src/pages/__tests__/FormDashboard.test.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx
git commit -F - <<'MSG'
fix(forms): check composed letters, and close the branch review's gaps

The whole-branch review of forms step 3a2 found a filer blocked by a
letter the court form prints, tests that pass with their behaviour
broken, and docs that say more than the code does (ruling R71).

- A letter typed as a base letter and a combining mark (e and U+0301,
  as text pasted from a file name or some PDFs holds it) is checked,
  measured and drawn as the one letter é. pdf_filler._as_printed
  composes the text (NFC) before its space, format and control rules,
  and check(), the drawing and an attached sheet all read the text
  through it. A name saved that way used to make Form 101 a 422 that
  quoted a lone accent and asked the filer to drop it; it now prints.
  A letter the form can't print is refused as the whole letter (ễ, not
  its mark); a mark no letter takes (n and U+0308) is still refused at
  the mark, in the sentence the owner is to settle (W-1).
- A refusal of a box whose binding has an empty label (Schedule J's
  amounts) names the box by its field-index label, never as “”, and
  keeps its binding's step.
- time_packet times what Generate All checks: it skips a filed form,
  which Generate All returns untouched, and draws a filed form's
  download from what was filed, as the download view does, so a
  session with a filed form can be timed; the table shows "filed" for
  its check. Each CommandError is raised from None, so --traceback or
  Sentry can't print the refusal it replaces, whose sentence can quote
  the filer's letter.
- Generate All's answer replaces every card's refusal on the forms
  dashboard: a form it refuses again shows its words and link once, in
  its list, and a card can't keep an older refusal beside it. A filed
  form, which Generate All returns unchecked, shows none until its next
  Download. A refusal of the whole call leaves the cards' as they are.
- Startup check E007 refuses, in a group continued on an attached
  sheet, every slot no column prints, bound or not (a constant or a
  derived slot, which the sheet's rows would drop), and every box slot,
  bound or not, mapped or not, its column's included: a sheet has no
  box to tick.

Tests:
- decomposed é, ñ and ü plan as the composed letter; decomposed ễ is
  refused naming ễ; n and U+0308 is refused at the mark; a name and a
  sheet cell typed decomposed print whole on Schedule A/B's boxes and
  on its sheet; through the API, a first name saved decomposed
  generates Form 101 (a 200, where it was a 422).
- A widget's own key wins over its full name whichever key comes first
  (the old dict order passed with the full-names-first sort removed).
- The wizard opens the step a dashboard link names without sending
  update_step when the shared provider already holds the session, as
  it does when the dashboard links there (the cold-provider tests
  couldn't see a call through the context).
- The cut-off test draws every drawn combo box's widest option and
  finds it whole (the district box on every form).
- Tier 1's box test checks every ticked widget of any name against the
  values drawn, not only the box's own widgets (spec §8).
- time_packet: a session with a filed form times, its row reading
  "filed", and its download draws what was filed (Form 101's current
  email can't print), while a form generated but not filed is still
  checked; a filed form stored without values is drawn from the
  intake; a filed form's refusal keeps the filer's letter out of the
  error and its chain; the existing refusal tests assert nothing is
  chained; a session it can't find is named.
- A Schedule J amount box's refusal is named by its index label.
- E007: a constant box slot, a derived text slot, a box slot not yet
  mapped, and one not yet mapped in the list a column prints, in A/B's
  synthetic sheet group, are each refused.
- test_rule_fixes reads the step keys from wizardSteps.ts and the pages
  from FormDashboard.tsx's PAGE_LINK_LABELS (plus /ask/<form type>)
  instead of a hand copy, and checks every fix a refusal can carry
  against them: each rule's, each text binding's, a SOFA list's, and
  the targets the exceptions name, PreconditionMissing's step at every
  place the code raises it (read with ast), IncomeNotSplit.step and
  IntakeNotFinished.page. So a step or route renamed on one side fails.
  It skips, saying why, where the frontend's source isn't (compose's
  backend container). That check moves out of
  test_every_refusal_names_where_to_fix_it into its own test.
- The Schedule D sheet test asserts the sheet's header names Schedule D.
- Generate All refusing a form whose card shows the same refusal shows
  it once, in its list; a refusal of Generate All's whole call leaves a
  card's refusal and its link.

CLAUDE.md: the letter check composes text first; a card's refusal
clears when Generate All answers (a filed form's until its next
Download); a filed form's download is a 422 with
no step or page for a letter or a length, and any other refusal of it a
500; E007's sheet list names every slot no column prints and every box
slot; check() and fill() take a sheet's title, columns and rows from its
part, the schema giving only the template and a refusal's fix and name
label; every push button (Print, Reset, Save As, Add Attachment) is
removed before the bake. The umbrella spec's SPIKE row points to 3a2's
§3 (engine) and §8 (oracle).

Refs DIG-137
MSG
git status --short
```
