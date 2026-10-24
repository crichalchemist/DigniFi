# Forms Step 3a2 (Drawing Engine) Implementation Plan, Part 3 of 4

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Print every court form through one engine. Each widget gets its own value, drawn with the template's own layout, and the page is flattened, so the packet has no fillable fields left. A letter the form's font can't print, or a value too long for its box even at 6 pt, is refused in plain words, and the dashboard links the refusal to the step or page that fixes it. Extra rows continue on copies of a form's extra page or on an attached sheet (proven on synthetic schemas). Generate All checks without drawing; Download draws.

**Architecture:** `apps/forms/services/widgets.py` addresses every template widget by page and index tag, so a binding can name one widget of a shared name (`<full name>@<page>:<tag>`). `PDFFormFiller.check()` plans each widget from cached widget maps and fonts without opening a PDF: the letters its font prints, the size its value fits at (mirroring pypdf 6.13.1's layout, `text_fit.py`), and where to fix a refusal (`RULE_FIXES`, `fix_for`). `fill()` runs `check()`, builds each planned widget's appearance with pypdf, removes the widgets that never print, bakes with PyMuPDF and nulls `/AcroForm`. `field_values` stores parts (`{"version": 2, "parts": [...]}`): the form, its continuation copies and its attached sheet. The tests read what is printed on the page (`read_drawn`). Each of the 9 tasks is one commit, and every task boundary passes every gate.

**This part:** Tasks 7–8. It starts where Part 2 ends, with Tasks 1–6 committed on this branch. The other parts: Part 1 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part1.md`, Tasks 1–4), Part 2 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part2.md`, Tasks 5–6), Part 4 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part4.md`, Task 9). The plan is split only to stay under the repository's 500 KB file limit. Run all parts as one execution: one ledger for Tasks 1–9, and the whole-branch final review only after Task 9, because each part's patches expect each file exactly as the earlier tasks leave it.

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

Check that Part 2 is in place: Task 6's commit is on this branch. Review fixes may have added commits after it.

```bash
set -eo pipefail
git log --format=%s 4690d12..HEAD | grep -Fx "feat(forms): continue rows past a group's last slot on copies of its extra page" >/dev/null
echo "Part 2 is in place"
```

Expected: `Part 2 is in place`. If the block fails instead, Task 6 isn't committed: finish Part 2 first.

Check the baseline before Task 7:

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

### Task 7: Attached sheets

_Built and verified as commit `17ea5e4` on `plan/forms-step3a2`._

**Files:**

- Create: `backend/apps/forms/services/sheets.py`
- Create: `backend/apps/forms/tests/test_attached_sheets.py`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/schema.py`
- Modify: `backend/apps/forms/services/fill_resolver.py`
- Modify: `backend/apps/forms/services/pdf_filler.py`
- Modify: `backend/apps/forms/services/text_fit.py`
- Modify: `backend/apps/forms/tests/conftest.py`
- Modify: `backend/apps/forms/tests/pdf_readback.py`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_check.py`
- Modify: `backend/apps/forms/tests/test_checks.py`
- Modify: `backend/apps/forms/tests/test_download_action.py`
- Modify: `backend/apps/forms/tests/test_pdf_filler.py`
- Modify: `backend/apps/forms/tests/test_printed_page.py`

**Interfaces:**

- Consumes:
  - From Task 6, `backend/apps/forms/schema.py`: `GroupSpec(name, extra_page, number, number_boxes, page_numbers)`, `PageNumberBoxes(page, this, of)`, `FormSchema.groups: dict[str, GroupSpec]`, `load_schema(form_type: str) -> FormSchema` (`@lru_cache`) and `validate_schema(schema: FormSchema, derivations: set[str], predicates: set[str]) -> list[tuple[str, str]]`, with Task 6's group rules. Before this task E007 refuses a group with no `extra_page` as "names no extra_page".
  - From Tasks 2, 5 and 6, `backend/apps/forms/services/pdf_filler.py`:
    - `_as_printed(text: str) -> str` (a tab and every space separator as a plain space, format characters dropped);
    - `_refused_letter(widget: TemplateWidget, font: Font, text: str) -> str | None`, whose signature changes here;
    - `UnprintableLetter(form_type, letter, label, fix)` and `ValueTooLong(form_type, label, fix)`, each with `step` and `page` taken from `fix`;
    - `PlannedPart(part, widgets)`, `parts_of(values: dict) -> list[dict]`, `_clone(form_type, template)` and `_baked(writer, template, widgets, only=None)`;
    - `PDFFormFiller.check(self, form_type, values) -> tuple[PlannedPart, ...]`, which plans `form` and `copy` parts and refuses any other kind with `ValueError: <form>: no part of kind '<kind>'`;
    - `PDFFormFiller.fill(self, form_type, values) -> bytes`, which draws the form's parts on one clone and each copy alone, then sets `/AcroForm` to null.
  - From Tasks 2 and 5, `backend/apps/forms/services/text_fit.py`: `font_for(template_filename: str, font_name: str) -> Font` (cached) and `printable(font: Font, letter: str) -> bool` (`font.can_encode(letter)` before this task).
  - From Tasks 2 and 6, `backend/apps/forms/services/fill_resolver.py`:
    - `resolve_parts(schema, session) -> dict`, which returns the form part and its copies. A group that overflows with no `extra_page` raises `ValueError: <form>: group '<group>' names no extra page`.
    - `_cell(field, position, columns, session, ingested_cache) -> str | None`, a slot's text for one row.
    - `fix_for(field: FieldSpec) -> dict[str, str]`, the spec §4.5 fix for a binding: `{"page": "/sofa"}` for a `sofa.…` binding.
  - From Task 2, `backend/apps/forms/services/derivations.py`: `DERIVATIONS["full_name"](session) -> str` and `RULE_FIXES["full_name"] == {"step": "debtor_info"}`.
  - From Task 6, `backend/apps/forms/tests/pdf_readback.py`: `read_drawn(form_type, pdf_bytes, parts=None) -> list[DrawnWidget]`, which refuses a PDF whose page count isn't the template's plus its copies'.
  - For the tests:
    - `apps/forms/tests/conftest.py`'s `_schedule_d_with_group(tmp_path, settings, group, rows, declaration)` (renamed here), `schedule_d_with_copies`, `schedule_d_part_2_with_copies`, `creditor_payments` (`add(session, count)`) and `generated_form_factory` (a Form 121 row for Maria Torres's completed intake in the Northern District of Illinois);
    - `test_checks.py`'s `_edit` and `_errors`;
    - `test_download_action.py`'s `_download`;
    - `test_printed_page.py`'s `_LETTERS` (Task 4's character set) and `_no_anti_aliasing`.
- Produces:
  - In `schema.py`:
    - `@dataclass(frozen=True) class SheetColumn` (`label: str`, `binding: str`, `width: float`) and `@dataclass(frozen=True) class SheetSpec` (`title: str`, `columns: tuple[SheetColumn, ...]`).
    - `GroupSpec.sheet: SheetSpec | None = None`, the last field. `load_schema` reads a group's `"sheet": {"title": str, "columns": [{"label": str, "binding": "sofa.<collection>[].<attr>", "width": <points>}]}` through `_sheet(sheet: dict) -> SheetSpec`, each width as a float.
    - `validate_schema` gains the sheet rules listed under the decisions below, through `_sheet_errors(name: str, group: GroupSpec, template: str) -> list[tuple[str, str]]` and `_LIST_BINDING` (`re.compile(r"sofa\.\w+\[\]\.\w+")`). The "no extra page" message becomes "names neither an extra_page nor a sheet".
  - New `backend/apps/forms/services/sheets.py`:
    - `draw_sheet(spec: SheetSpec, part: dict) -> bytes` and `plan_sheet(form_type: str, spec: SheetSpec, part: dict) -> None`, which raises `UnprintableLetter`, `ValueTooLong`, or `ValueError` for a line that doesn't fit the line column;
    - `sheet_spec(part: dict) -> SheetSpec`, the part's own title and columns, each column's binding `""`;
    - `inner_width(width: float) -> float`, `prints_whole(text: str, width: float, template: str) -> bool` and `fits_line_column(line: str, template: str) -> bool`, which startup uses too;
    - the constants `PAGE` (612.0, 792.0), `MARGIN` 54.0, `WIDTH` 504.0, `LINE_WIDTH` 36.0, `PAD` 2.0, `SIZE` 10.0 and `LEADING` (13.74 pt).
  - In `fill_resolver.py`: `resolve_parts` returns `{"version": 2, "parts": [form, *copies, *sheets]}`. A sheet part is `{"kind": "sheet", "group": <group>, "title": str, "columns": [{"label": str, "width": float}], "name": <the filer's full name>, "rows": [{"line": "3.5", "cells": [<one per column>]}]}`, built by the new `_sheet(group, fields, printed, columns, capacity, actual, session, ingested_cache) -> dict`.
  - In `pdf_filler.py`:
    - `_refused_letter(text: str, prints: Callable[[str], bool], comb: bool = False) -> str | None`. Its one caller, `_plan`, passes `partial(printable, font)` and `widget.comb`.
    - `check()` plans a `sheet` part through `plan_sheet` with no widgets, and refuses a part of any kind but `form`, `copy` and `sheet`.
    - `fill()` appends each sheet after the form's pages and copies.
    - The import `from pypdf._font import Font` goes.
  - In `text_fit.py`: `printable(font, letter)` is `font.can_encode(letter) and letter != adobe_glyphs["/.notdef"]`, so □ (U+25A1) is never printable. `pypdf._codecs.adobe_glyphs` is a new pypdf internal, pinned in `test_pdf_filler.py`.
  - In `pdf_readback.py`:
    - `read_drawn(form_type, pdf_bytes, parts=None)` reads the template's pages and its copies, and leaves the pages after them to `read_sheets`. It raises `ValueError` unless every later page is a sheet page ("(attached sheet)" in its text), with at least one such page per sheet part and none without one.
    - New `@dataclass(frozen=True) class SheetPage` (`header`, `labels`, `rows`, `lines`, `ink`, `crossing`, `overlapping`) and `read_sheets(pdf_bytes: bytes, spec: SheetSpec) -> list[SheetPage]`.
  - In `apps/forms/tests/conftest.py`:
    - `_with_group(tmp_path, settings, form_type, group, rows, declaration)` replaces `_schedule_d_with_group`. It copies the real schemas only once per test and adds a group beside any added before.
    - New fixtures `schedule_a_b_with_sheet` (group `ab_line_3`) and `schedule_d_with_a_copy_and_a_sheet` (groups `d_part_2` on copies, `d_part_1` on a sheet), each yielding the schemas directory.
    - `creditor_payments` returns `add(session, count, names=None)`.
  - Where the commit differs from tasks.md:
    - The Interfaces table's sheet-part row was updated for R63 and matches the commit.
    - Its `sheets.py` row names only `draw_sheet` and `plan_sheet`. The commit also produces `sheet_spec`, `inner_width`, `prints_whole`, `fits_line_column` and the layout constants, which startup and the read-back use.
    - tasks.md's T2 text defines `printable` as `font.can_encode(letter)`; it now also refuses □. The table never named `_refused_letter`, whose signature changes here.
    - tasks.md's text says `read_drawn` "skips" sheet pages; it refuses a PDF whose later pages aren't all sheet pages.
    - tasks.md's text gives the refusal's fix as "(`/sofa`)". The commit takes it from `fix_for` on the slot behind the column (R65), which is `/sofa` for today's columns.
    - tasks.md lists two `CLAUDE.md` gotchas (the File Map and "Blank, not 0.00"). The commit also updates "Schemas are checked at startup", "`field_values`, not `form_data`" and "GenerateAll vs single".
    - tasks.md's E007 list has three rules: one of `extra_page` and `sheet`, the 504 pt width, and list bindings. The commit has every rule listed under the decisions below, several of them from the review rounds (R64, R66).
    - G12's list of pypdf internals lacks `pypdf._codecs.adobe_glyphs`, which `text_fit.py` now imports.

**Decisions already made in this task:**

_What a sheet group declares, and what startup refuses (spec §5.3; R56, R64, R65, R66):_

- **A sheet group declares `number` and `sheet`, never `extra_page`.** `sheet` holds the title the sheet's header prints and the columns of the group's row, each a label, a `sofa.<collection>[].<attr>` list binding and a width in points. `load_schema` reads it into `SheetSpec` and `SheetColumn`, and `GroupSpec.sheet` is the last field, defaulted to `None`, so Task 6's groups load unchanged.
- **Startup refuses every sheet declaration that can't print every row whole, rather than printing it wrong.** As in Task 6 (R56, R58 to R60), a schema author sees the refusal in `manage.py check` and the release, not a filer at Generate. No production schema has a group, so none of these rules can trip production: `test_every_registered_form_passes` passes all 17 schemas. Each rule, and the defect it prevents:
  - E007, a group that names neither or both of an `extra_page` and a `sheet`: its rows past the last slot would have nowhere, or two places, to go. `resolve_parts` still raises a `ValueError` for an overflow with neither, which startup makes unreachable.
  - E007, a sheet group without `{n}` in its `number`, or with no `number` at all: each sheet row is labelled with the form line it continues, and `None.format` would be a 500 at Generate.
  - E007, a first sheet line, `number.format(n=capacity + 1)`, that doesn't print whole on one line of the line column (review findings 7, 8 and 12). `"Line 3.{n}"` gives "Line 3.5", 35.58 pt against the column's 32 pt inside its padding. It passed startup, and every Generate with a fifth row was then a 500. The rule uses the same `fits_line_column` as `plan_sheet`: the letters, then one line.
  - E007, `page_numbers` on a sheet group: Task 6 fills them only for a group with copies (R21), and a sheet group has none, so they would never print.
  - E007, a sheet with no columns, or with columns wider than the 504 pt (7 in) between its margins once the 36 pt line column is added. The synthetic A/B is exactly 36 + 300 + 168 = 504; the test's 301 is refused at 505.
  - E007, a column whose binding isn't a `sofa.<collection>[].<attr>` list (`_LIST_BINDING`, a full match). 3a2 has no other list source (R19), and 3b and 3c add theirs.
  - E007, a column whose binding no mapped slot of the group binds: it would print another list's rows, not the group's.
  - E007, a column that any box slot binds: a box's answer is a state, such as `/On`, and a sheet has no box to tick. (Review finding 15: the first commit's words said "only box slots"; the code always said any, and the words now match.)
  - E007, a slot binding that no column prints (review finding 2). Each row past the slots would silently lose that value. A box slot with no column gets its own message ("a box slot binds …, and a sheet can't tick a box"), so every box slot in a sheet group is refused once. Slots with no binding (derived or constant) are left out; guarded slots count. The rule is skipped for a sheet with no columns, which has its own message.
  - E007, two columns with one label (R66). A label names one column, to the filer and to a refusal's fix (`sheets._fixes`, below). In the re-review's probe, a derived value column also labelled "Make" sent a Make refusal to `debtor_info` instead of `/sofa`.
  - E007, a label that doesn't print whole inside its column's padding, or a column 4 pt wide or less, which leaves no room: a letter the form's template can't print, or a word wider than the column.
  - E007, a title that doesn't print whole, with " (attached sheet)" added, across the 504 pt.
  - Task 6's slot rules hold for a sheet group's slots too: capacity equal to the slot rows, one page per slot row, rows in page order, the untagged-twin rule, group boxes as E006 writers and E003 on number boxes. They run before the extra-page branch. Two cases prove the capacity and page-order rules on the sheet group.
  - Only the extra page's own rules leave a sheet group alone: "the page of the last slots", and the one group with an `extra_page` per form. `test_a_group_continued_on_an_attached_sheet_is_not_counted_as_a_second` adds a sheet group on D's Part 2 beside its copied Part 1, and startup passes it (R56).
- **R65(2), parked: only the first sheet line is checked at startup.** A later line outgrows the 32 pt only from n = 10000 for `"3.{n}"`: "3.9999" is 30.58 pt, and "3.10000" is 36.14. `plan_sheet` checks every line with the same helper and raises `ValueError` for a wider one, a 500 logged by type, as Task 6's unknown part kind is.

_The sheet part (spec §5.3, §6; R23, R63):_

- **`resolve_parts` puts the rows past a sheet group's slots into one part, after the form part and its copies.**
  - Each row's `line` is `number.format(n=<the row's position in the whole group>)`, "3.5" for the fifth vehicle.
  - Each cell is that column's binding for the row, through `_cell` on the group's first slot of that binding, the slot's own text conversion (`_emit`), so a cell prints as the slot would.
  - `name` is `DERIVATIONS["full_name"](session)`, for the header (R23).
- **R63: a sheet part stores its title and its columns' labels and widths, and `check()` and `fill()` draw it from those, never from the live schema.** `sheets.sheet_spec(part)` builds the `SheetSpec`, each column's binding `""`, since the part holds the cells.
  - Why (review finding 3): the first build drew a filed sheet under the live schema. After a schema edit that passes startup, a filed form was then a 500 (a renamed group, or an added column), a permanent 422 (a narrowed column), or new labels. That breaks spec §6's "exactly what was filed" (DIG-155). Step 17 shows each.
  - `test_a_filed_sheet_prints_what_was_filed_whatever_its_schema_says_later` proves it. It files A/B with six vehicles, then renames the group, adds a column, narrows one, or changes the title and a label, each passing `validate_form`. Every page's words and their boxes then match the first download. Bytes can't be compared: the implementer's probe found that two fills of the same values differ only in the trailer's second `/ID` string.
  - This amends the Interfaces sheet-part row (R23). It is also a spec errata item: §6's example sheet part gains `title` and `columns`.
  - No reader is needed for a sheet part without `title` and `columns`: 3a2 isn't deployed, and no production schema has a group.
- **The UPL guard blanks a column, never a row (R59(a)).** A column prints blank when any slot binding it is guarded (`legal_review` and not asked); the row's line and its other cells still print, as on the form and its copies.

_Letters (R62; review findings 1, 10, 11, 14):_

- **R62: the sheet's Helvetica takes the templates' own `/Encoding`, and its letter check is the forms' `printable()`, so the forms and the sheet print the same letters.**
  - All 17 templates' `/Helv` (a base-14 Helvetica, not embedded) share one `/Encoding`. Its `/Differences` array has 140 elements: 128 glyph names, set at 12 starting codes. A probe over the 17 schemas' templates found one distinct array.
  - `sheets._DIFFERENCES` holds it as PDF tokens. `_CODES` is pypdf's own reverse map for a font resource built from it, the map pypdf uses to encode a form's text. `_encoded()` writes each letter's code in that encoding, and after drawing, `draw_sheet` sets every sheet page's font `/Encoding` to it with `xref_set_key`.
  - `plan_sheet` refuses a letter with `text_fit.printable` on the form's own `/Helv` (`font_for(template, "/Helv")`), through `_as_printed` and `_refused_letter`, exactly as `check()` does for a box. That set is 255 characters: the encoding's 256 codes, less □.
  - Why: spec §5.3 says the sheet follows "the same rules as the form". The first build drew in PyMuPDF's WinAnsiEncoding, which refused 13 letters the forms print (Ł ł ı ˘ ˇ ˙ ˚ ˛ ˝ ⁄ − ﬁ ﬂ). Its refusal then blamed "Debtor 1" for Ł, a box that prints Ł.
  - `test_the_sheet_prints_in_the_templates_own_encoding` pins it. Every template's `/Helv` is `/Type1` `/Helvetica` with no `/BaseEncoding`, its `/Differences` equal `_DIFFERENCES`, and pypdf's map for it equals the sheet's. Both pages of a two-page sheet then carry that `/Encoding`.
  - The sheet's font has no `/Widths`, as the templates' `/Helv` has none, so a viewer advances each glyph by Helvetica's own metrics. Of the letters the sheet accepts, only ⁄ measures differently in PyMuPDF's `Font` (278) and pypdf's AFM (167). The sheet measures it wider than a viewer draws it, so it is never cut off.
  - The implementer's mutation "only the first page's font gets the encoding" is equivalent, so it was dropped: PyMuPDF draws every page of a sheet in one font object.
- **□ (U+25A1) is refused everywhere (review finding 11, pre-existing since Task 2).** pypdf reads the templates' `/.notdef`, at code 173, as □, so `can_encode` accepted it, and a form drew code 173, which reads back as a soft hyphen. `printable` now leaves out `adobe_glyphs["/.notdef"]`, so the forms' check and the sheet's both refuse it. `test_check.py`'s `Nowak□` case proves it on a form. `test_pdf_filler.py` pins `adobe_glyphs["/.notdef"] == "□"`, a library constant that only a pypdf change can turn red. `printable` has two production callers, `pdf_filler._plan` and `sheets._prints` (the agreement test's `_template_letters` calls it too), and no other letter changes: the forms suite passes.
- **`_refused_letter(text, prints, comb=False)` takes the font's check as a function**, so the sheet reuses `check()`'s letter handling: line breaks aren't letters (G15), control characters are refused, and `( ) \` in a comb box. `_plan`, its one caller, passes `partial(printable, font)` and `widget.comb`. The now unused `Font` import goes from `pdf_filler.py`, and `test_pdf_filler.py` still pins `Font` itself.
- **The filer's name is checked too, as a guard (R65(3)).** `plan_sheet` refuses a name it can't print across the page, labelled with the form's own `full_name` binding's label ("Debtor 1" on A/B) and fixed at `RULE_FIXES["full_name"]` (`debtor_info`). With no such binding, the label falls back to the title with " (attached sheet)". 16 of the 17 schemas bind `full_name`; Form 121, which has no sheet, doesn't.
  - Through `check()` the guard can't be reached: the form's own name box, in the same font, refuses first. `test_a_name_neither_the_form_nor_the_sheet_can_print_is_refused_on_the_form` shows the sentence with and without a sheet ("Maria Wąsowicz", with five vehicles and then four).
  - `test_a_name_the_sheet_cannot_print_is_refused_where_the_name_is_entered` calls `plan_sheet` alone.
- **R65(1): a sheet refusal's fix comes from the schema's column of the same label.** `sheets._fixes` maps each of the schema's columns' labels to its binding. It finds the group's slot with that binding and returns `fix_for(slot)`, or `{}` for a label the schema no longer declares. The first build hard-coded `/sofa` (review finding 9).
  - The lookup matters only for an unfiled form, whose part was just built from that schema. A filed form's refusal drops `step` and `page` (R46).
  - R66's unique labels mean no column can take another's fix.
  - Today's columns are SOFA lists, so their refusals name `/sofa`.
- **Generate now calls PyMuPDF too, without drawing (review finding 16).** `plan_sheet` measures text with `pymupdf.Font("helv").text_length`, and so does startup (`prints_whole`). Production stays on sync gunicorn workers (R47), so nothing changes there. `CLAUDE.md`'s "GenerateAll vs single" says so.
- **Widths come from `pymupdf.Font("helv").text_length` on the Unicode text.** `pymupdf.get_text_length(text, "helv")`, in PyMuPDF 1.27.2.3, measures every WinAnsi letter at 0x80–0x9F (’ “ ” – — … € • Š Œ ž …) at 2.78 pt at 10 pt, whatever the letter. It passes a cp1252 code where the font lookup takes a Unicode character. It is pre-existing in the library, and DigniFi doesn't call it.

_Drawing a sheet (spec §5.3):_

- **The page:**
  - US Letter (612 × 792 pt) with 0.75 in (54 pt) margins, so 504 pt between them; Helvetica at 10 pt, left-aligned.
  - A line is PyMuPDF's own Helvetica line, ascender to descender: `LEADING` 13.74 pt, with the baseline 10.75 pt below the line's top. Every character's box then stays inside its line, its column and the margins.
- **Layout judgment calls beyond the spec** (the implementer's; the reviews accepted them):
  - The line column is 36 pt. "3.9999" fits inside its padding, and 504 − 36 = 468 pt is left for the group's columns.
  - Each cell's text keeps 2 pt (`PAD`) from each side of its column. Rows are 6 pt apart.
  - The blank line for the case number is 180 pt (2.5 in), starting 4 pt after its label.
  - A rule runs under the column labels.
  - The header's name line is the name alone, and the line column's label is blank: the spec gives no words for either ("Debtor 1" isn't printed).
- **Sheet pages are not counted in a form's page numbers.** Spec §5.2 numbers each page "with the copies counted", and §5.3 appends a sheet "right after its form", with no registry entry, schema or field index. That is also why E007 refuses `page_numbers` on a sheet group.
- **A cell wraps at its spaces, and a line break starts a new line** (G15's `splitlines()`, as in a multi-line box). A row never splits across pages, and the sheet runs to as many pages as its rows need. Every page repeats the header and the labels.
  - `draw_sheet` raises `ValueError` if a row taller than a page reaches it unchecked, rather than looping or cutting it.
  - A letter drawn without the check prints "?", as pypdf prints one on a form. The agreement test draws refused letters through the real `draw_sheet` this way.
- **An empty line isn't drawn (review finding 13).** For an empty line, PyMuPDF's `insert_text` swallows a `ValueError` and writes a traceback to stdout, once per blank cell in production. The guarded-column test points `pymupdf._g_out_log` at a `StringIO` and asserts it stays empty. `capsys` can't see that log, since PyMuPDF binds `sys.stdout` when it is imported.
- **Each line goes to `insert_text` as a one-item list.** `insert_text` splits a string at NEL (0x85), and 0x85 is "–" in the templates' encoding.
- **`fill()` appends each sheet after the form's pages and its copies (review finding 6).** `test_a_form_with_a_copy_and_a_sheet_prints_the_sheet_last` proves the order on Schedule D, with Part 2 on copies of page 3 and Part 1 on a sheet. The parts are `form, copy, sheet`, and only the fifth of five pages is a sheet page.

_Plan and draw share their arithmetic (review findings 4, 5 and 19; R66):_

- **`inner_width(width)`, the column's width less 2 pt on each side, is the one cell width.** `plan_sheet`'s cells, `draw_sheet`'s cells and labels, `fits_line_column` and E007's label rule all use it.
- **`_room(spec, header)` is the one page room.** It is `792 − 54 − _rows_top(spec, header)`, where `_rows_top` is the top margin plus the header's lines, a blank line and the labels' lines, then a 6 pt gap. `plan_sheet`'s height test uses it, and so does `draw_sheet`'s page break, which counts the height its rows have taken from the page's first row.
- **Why:** in the first build each side worked out its own. A word between 296 and 300 pt, or a row one line too tall, passed Generate and was then a 500 at Download.
- **The boundary tests**, each figure measured with `pymupdf.Font("helv").text_length` at 10 pt:
  - The Make column is 300 pt, 296 inside its padding. "W"×31 + "i" (294.86 pt) prints whole, and "W"×31 + "ii" (297.08 pt) is refused by `check()` naming "Make" (`test_a_word_as_wide_as_its_cell_prints_and_a_wider_one_is_refused`).
  - A Make cell of 44 typed lines prints on one sheet page, and 45 are refused (`test_a_row_as_tall_as_a_page_prints_and_a_taller_one_is_refused`). 44 = ⌊(792 − 54 − 128.70) / 13.74⌋. 128.70 = 54 + 5 × 13.74 + 6: three header lines, a blank line and one label line, since "Current value of the portion you own" is 161.19 pt, one line inside its 164.
  - The padding test's row 3.5, "W"×30 + " i i" (293.2 pt), prints from 92 to 385.2 pt in the Make column (90 to 390), and a third i, which would end at 390.2, starts the next line.
  - Row 3.6, "W"×31 + " i" (297.64 pt), would end at 389.64: inside the column but past its padding. It wraps before the i (re-review 1's B03, R66).

_Reading a sheet in the tests:_

- **`read_drawn` refuses a sheet page read as a form page.** Sheet pages are told apart by "(attached sheet)" in their text. A probe found it on none of the 222 pages of the 67 templates.
  - Without parts, an 11-page A/B with a sheet gives "the PDF has 11 pages, but its parts print 10".
  - A drawing missing the sheet its parts have gives "… print 10 and 1 attached sheet(s)".
- **`read_sheets(pdf_bytes, spec)`** reads each sheet page's header, labels and rows under the spec's columns, each row's cells as their lines, the box all its ink lies in, and each character outside its column (`crossing`) or each line that runs into the next (`overlapping`). `crossing` leaves out spaces: MuPDF reads the gap between two cells as a space whose box crosses the column edge, and a space prints nothing.

_The tests the change breaks, and the new ones:_

- **The broken tests are fixed in this commit.** The "no extra page" case of `test_a_repeat_group_whose_rows_cannot_continue_is_reported`, and `test_a_group_with_no_extra_page_is_not_counted_as_a_second`, now expect "names neither an extra_page nor a sheet". `_part_2(extra_page)` becomes `_part_2(declaration)`.
- **Synthetic schemas over the real templates (R18, R19, G11).** `_with_group` takes the form type. It copies the real schemas into `tmp_path` only if no earlier fixture of the test has, and adds its group beside any added before, so one test can carry two groups. `schedule_a_b_with_sheet` is tasks.md's group:
  - group `ab_line_3`, capacity 4, `number` `"3.{n}"`;
  - line 3's Make and value boxes: 3.1 `3 1` (p2 T30) and `undefined_15` (p2 T39); 3.2 `If you own or have more than one describe here` (p2 T42) and `undefined_17` (p2 T51); 3.3 `1_3` (p3 T3) and `undefined_19` (p3 T12); 3.4 `1_4` (p3 T15) and `undefined_21` (p3 T24);
  - a sheet titled "Official Form 106A/B, Schedule A/B: Property", with columns "Make" (`sofa.creditor_payments[].creditor_name`, 300 pt) and "Current value of the portion you own" (`…total_paid`, 168 pt).
  - A check of A/B's field index confirmed each name, page and tag; each is one drawn text box. A/B has 10 pages, and its `undefined_26` (p3 T51) is the real schema's `total_vehicles` box.
- **The tests use vehicle makes, not firm names.** A/B's Make boxes are 54.5 pt wide, and conftest's "Fenwick Motor Credit" is 56.68 pt even at 6 pt. `creditor_payments` takes `names` for that.
- **Finding 20, parked (R64): the totals test can't fail for a totals defect.** tasks.md asks for a test-only rule, so D's `undefined_24` and A/B's `undefined_26` are rebound to a lambda that adds up every row itself. The test proves that totals still print when rows overflow onto copies and sheets, and that D's total isn't repeated on its copy (R24). It doesn't prove that a production total sums right.
- **`test_api_readback._comparable_document` leaves a part without `values` as it is (review finding 17).** It is latent: no test sends a sheet part through it until 3b, so it has no red proof.

_Review outcome:_

- **Three reviews.**
  - The first found six distinct Important findings, all confirmed (deduped from nine): the letters, a slot no column prints, the filed sheet under the live schema, the shared width, the shared room, and no test of a copy with a sheet. It also gave one unverified Important (the line column) and Minors 8 to 20.
  - R62, R63 and R64 fixed every Important, and every Minor but finding 20. Findings 8 and 12 went with 7, the line column.
  - Re-review 1 found four Minors: the draw side's right padding unpinned, duplicate labels, 11 letters whose codes moved left out of the agreement test, and the commit body crediting the wrong test. R66 fixed all four.
  - Re-review 2 approved, noting only two commit-body lines over 72 characters.
- **The implementer's red proofs:** 68 mutations, every one red on the final commit.
  - Steps 13 to 19 repeat eleven of them, in nine runs. Five of those runs cover the tests that Step 6 shows passing before the resolver builds a sheet: the name guard, the tallest-cell refusal, the encoding pin, the letter agreement test and the totals case on copies.
  - The rest pin R62 (the WinAnsi codes and check), R63 (the live schema at check and at draw) and the three seams plan and draw share.
  - Every other new test or case fails on its own assertion or exception in Step 2, 6 or 10 and passes by Step 12. The two exceptions have no red proof: the `adobe_glyphs` pin and `_comparable_document`'s new branch (above).

_Left as found:_

- **`test_download_action.py`'s docstring** still cites "spec §5.5", the forms-foundation spec, not 3a2's (Task 6 noted it).
- **`pymupdf.get_text_length`** mis-measures 0x80–0x9F, as above; nothing in DigniFi calls it.

- [ ] **Step 1: Write the tests**

```python file=backend/apps/forms/tests/test_attached_sheets.py
"""
Rows past a repeat group's last slot print on an attached sheet when the form has no page
to copy (3a2 spec §5.3): plain US Letter pages after the form, headed by the filer's name,
the form's title and the case number, each row under the form's columns and labelled with
the line it continues. 3a2 proves it on a synthetic Schedule A/B group (§5.4; conftest's
schedule_a_b_with_sheet): line 3's four vehicles, 3.1 and 3.2 on page 2, 3.3 and 3.4 on
page 3.
"""

import json
import re
from io import BytesIO, StringIO
from pathlib import Path

import pymupdf
import pypdf
import pytest
from django.conf import settings

from apps.forms.registry import build_parts, get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services import sheets
from apps.forms.services.derivations import DERIVATIONS
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong
from apps.forms.services.sheets import draw_sheet, plan_sheet, sheet_spec
from apps.forms.services.text_fit import font_for
from apps.forms.tests.pdf_readback import read_drawn, read_sheets

MAKES = ["Honda", "Toyota", "Subaru", "Mazda", "Volvo", "Kia", "Saab", "Fiat"]
SLOTS = {  # line 3's boxes: (make, value), 3.1 to 3.4
    "3.1": ("3 1", "undefined_15"),
    "3.2": ("If you own or have more than one describe here", "undefined_17"),
    "3.3": ("1_3", "undefined_19"),
    "3.4": ("1_4", "undefined_21"),
}
HEADER = (
    "Maria Torres",
    "Official Form 106A/B, Schedule A/B: Property (attached sheet)",
    "Case number (if known)",
)
LABELS = ("", "Make", "Current value of the portion you own")
TITLE = "Official Form 106A/B, Schedule A/B: Property"
COLUMNS = [
    {"label": "Make", "width": 300.0},
    {"label": "Current value of the portion you own", "width": 168.0},
]


@pytest.fixture
def session(generated_form_factory, schedule_a_b_with_sheet):
    """Maria Torres's completed intake in the Northern District of Illinois."""
    return generated_form_factory().session


def _spec():
    return load_schema("schedule_a_b").groups["ab_line_3"].sheet


def _sheet_part(rows):
    """A/B's sheet part with these rows, as resolve_parts() stores one."""
    return {
        "kind": "sheet",
        "group": "ab_line_3",
        "title": TITLE,
        "columns": COLUMNS,
        "name": "Maria Torres",
        "rows": rows,
    }


def _drawn(session):
    """Schedule A/B's parts for the session, and its drawn PDF."""
    document = build_parts("schedule_a_b", session)
    return document["parts"], PDFFormFiller().fill("schedule_a_b", document)


def test_extra_rows_print_on_an_attached_sheet(session, creditor_payments):
    creditor_payments(session, 5, MAKES)

    parts, pdf = _drawn(session)

    # One sheet part carries the rows past the slots, the name its header prints (R23), and
    # the title and columns it is drawn with (R63).
    assert parts[1:] == [
        {
            "kind": "sheet",
            "group": "ab_line_3",
            "title": TITLE,
            "columns": COLUMNS,
            "name": "Maria Torres",
            "rows": [{"line": "3.5", "cells": ["Volvo", "500.00"]}],
        }
    ]
    pages = pymupdf.open("pdf", pdf)
    assert len(pages) == 11  # A/B's ten pages, then the sheet
    assert len(pypdf.PdfReader(BytesIO(pdf)).pages) == 11  # pypdf opens it the same
    # Rows 1 to 4 fill line 3's slots on pages 2 and 3; the fifth prints on the sheet.
    printed = {w.full_name: w.value for w in read_drawn("schedule_a_b", pdf, parts)}
    assert {line: (printed[make], printed[value]) for line, (make, value) in SLOTS.items()} == {
        "3.1": ("Honda", "100.00"),
        "3.2": ("Toyota", "200.00"),
        "3.3": ("Subaru", "300.00"),
        "3.4": ("Mazda", "400.00"),
    }
    (sheet,) = read_sheets(pdf, _spec())
    assert (sheet.header, sheet.labels, sheet.rows) == (
        HEADER,
        LABELS,
        (("3.5", "Volvo", "500.00"),),
    )
    assert "Volvo" not in "".join(page.get_text() for page in pages[:10])
    # Each character stays in its column, and no line runs into the next.
    assert (sheet.crossing, sheet.overlapping) == ((), ())
    # Every line is Helvetica at 10 pt (spec §5.3).
    spans = [
        span
        for block in pages[10].get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
    ]
    assert {(span["font"], span["size"]) for span in spans} == {("Helvetica", 10.0)}
    # The case number's blank line runs on from its label.
    label = pages[10].search_for("Case number (if known)")[0]
    blanks = [
        item
        for drawing in pages[10].get_drawings()
        for item in drawing["items"]
        if item[0] == "l" and item[1].x >= label.x1 and label.y0 <= item[1].y <= label.y1 + 2
    ]
    assert len(blanks) == 1 and blanks[0][2].x - blanks[0][1].x >= 144  # 2 in at least


def test_a_cell_filled_to_its_padding_stays_in_its_column(session, creditor_payments):
    # The Make column runs from 90 to 390 pt, and a cell's text starts 2 pt in, at 92, and
    # wraps within 296 pt, ending by 388. Row 3.5: thirty W's and two i's, 293.2 pt at 10 pt,
    # end at 385.2; a third i would end at 390.2, so it starts the next line. Row 3.6:
    # thirty-one W's and an i, 297.64 pt, would end at 389.64, inside the column but past
    # its right padding, so the i starts the next line.
    make = "W" * 30 + " i" * 4
    creditor_payments(session, 6, [*MAKES[:4], make, "W" * 31 + " i"])

    _, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.lines == (
        (("3.5",), ("W" * 30 + " i i", "i i"), ("500.00",)),
        (("3.6",), ("W" * 31, "i"), ("600.00",)),
    )
    assert sheet.crossing == ()
    (first_line,) = pymupdf.open("pdf", pdf)[10].search_for("W" * 30 + " i i")
    assert (round(first_line.x0, 2), round(first_line.x1, 2)) == (92.0, 385.2)


def _long_make(n):
    """A make that wraps to three lines in its column."""
    return (
        f"Vehicle {n}: Honda Civic LX sedan, silver, bought used in 2019 with the dealer’s "
        "extended service contract, roof rack, winter tyres and a tow hitch"
    )


def test_a_long_sheet_runs_to_a_second_page(session, creditor_payments):
    # Twenty rows on the sheet: three of one line, then three-line rows. Page 1 takes
    # fourteen, and has room left for the first line of the fifteenth but not the whole row.
    makes = {n: _long_make(n) if n >= 8 else MAKES[n - 1] for n in range(1, 25)}
    creditor_payments(session, 24, list(makes.values()))

    _, pdf = _drawn(session)

    assert len(pymupdf.open("pdf", pdf)) == 12
    first, second = read_sheets(pdf, _spec())
    for page in (first, second):
        assert (page.header, page.labels) == (HEADER, LABELS)  # on every page of the sheet
        # Nothing is cut off: every character inside the margins and its column, and no
        # line running into the next.
        x0, y0, x1, y1 = page.ink
        assert 54 <= x0 and 54 <= y0 and x1 <= 612 - 54 and y1 <= 792 - 54
        assert (page.crossing, page.overlapping) == ((), ())
    # Every row prints once, whole and in order: none is split across the pages.
    assert [*first.rows, *second.rows] == [(f"3.{n}", makes[n], f"{n}00.00") for n in range(5, 25)]
    assert (len(first.rows), len(second.rows)) == (14, 6)
    assert 792 - 54 - first.ink[3] > 6 + 14  # a row gap and a line: the fifteenth's first line


@pytest.mark.parametrize(
    "fixture, form_type, total, printed",
    [
        ("schedule_d_with_copies", "schedule_d", "undefined_24", {(None, "2100.00"), (1, "")}),
        ("schedule_a_b_with_sheet", "schedule_a_b", "undefined_26", {(None, "2100.00")}),
    ],
    ids=["copies", "a sheet"],
)
def test_totals_count_rows_printed_on_copies_and_sheets(
    request,
    monkeypatch,
    generated_form_factory,
    creditor_payments,
    fixture,
    form_type,
    total,
    printed,
):
    # Six rows of 100.00 to 600.00: Schedule D's five slots and one copy, A/B's four slots and
    # its sheet. A total adds up every row, not the slots (spec §5.1); page 2's total of
    # Schedule D prints once, on the form, not on its copy (R24).
    schemas = request.getfixturevalue(fixture)
    path = schemas / f"{form_type}.json"
    data = json.loads(path.read_text())
    box = next(f for f in data["fields"] if f["pdf_field"] == total)
    box.update(source="derived", rule="every_row_total")
    path.write_text(json.dumps(data))
    load_schema.cache_clear()
    monkeypatch.setitem(
        DERIVATIONS,
        "every_row_total",
        lambda s: str(sum(row.total_paid for row in s.sofa_report.creditor_payments.all())),
    )
    session = generated_form_factory().session
    creditor_payments(session, 6, MAKES)

    document = build_parts(form_type, session)
    pdf = PDFFormFiller().fill(form_type, document)

    assert [part["kind"] for part in document["parts"]][1:] == (
        ["copy"] if form_type == "schedule_d" else ["sheet"]
    )
    drawn = read_drawn(form_type, pdf, document["parts"])
    assert {(w.copy, w.value) for w in drawn if w.full_name == total} == printed


def test_a_letter_the_sheet_cannot_print_is_refused(session, creditor_payments):
    # The fifth vehicle prints only on the sheet; its make comes from the SOFA.
    rows = creditor_payments(session, 5, MAKES)
    rows[4].creditor_name = "Wąsowicz Motors"
    rows[4].save()
    document = build_parts("schedule_a_b", session)
    assert document["parts"][1]["rows"][0]["cells"][0] == "Wąsowicz Motors"

    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("schedule_a_b", document)

    assert str(refused.value) == (
        "The court form can't print the letter “ą” in “Make”. "
        "Change it to a letter without the mark."
    )
    # Fixed where the column's slots' binding is changed (fix_for): a SOFA list's, the SOFA page.
    assert (refused.value.step, refused.value.page) == (None, "/sofa")


def test_the_sheet_prints_every_letter_the_form_prints(session, creditor_payments):
    # The sheet prints in the templates' own encoding (R62), so Ł, ł and ı, which WinAnsi
    # lacks, print as themselves in its header and in a cell, as on the form.
    debtor = session.debtor_info
    debtor.first_name, debtor.last_name = "Łucja", "Kıłıç"
    debtor.save()
    creditor_payments(session, 5, [*MAKES[:4], "Łada Niva ł ı"])
    pymupdf.TOOLS.mupdf_warnings()  # clears them

    _, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert (sheet.header[0], sheet.rows) == (
        "Łucja Kıłıç",
        (("3.5", "Łada Niva ł ı", "500.00"),),
    )
    assert pymupdf.TOOLS.mupdf_warnings() == ""
    text = pypdf.PdfReader(BytesIO(pdf)).pages[10].extract_text()
    assert "Łucja Kıłıç" in text and "Łada Niva ł ı" in text


def test_a_name_neither_the_form_nor_the_sheet_can_print_is_refused_on_the_form(
    session, creditor_payments
):
    # The form's Debtor 1 box refuses the letter first, with or without a sheet: the box
    # named is one that can't print it.
    debtor = session.debtor_info
    debtor.last_name = "Wąsowicz"
    debtor.save()

    def refusal():
        with pytest.raises(UnprintableLetter) as refused:
            PDFFormFiller().check("schedule_a_b", build_parts("schedule_a_b", session))
        return str(refused.value), refused.value.step, refused.value.page

    the_form_s = (
        "The court form can't print the letter “ą” in “Debtor 1”. "
        "Change it to a letter without the mark.",
        "debtor_info",
        None,
    )
    payments = creditor_payments(session, 5, MAKES)
    assert refusal() == the_form_s  # a fifth vehicle, on a sheet
    payments[4].delete()
    assert refusal() == the_form_s  # no sheet


def test_a_name_the_sheet_cannot_print_is_refused_where_the_name_is_entered(
    schedule_a_b_with_sheet,
):
    # check() refuses such a name on the form first; plan_sheet() still refuses it alone,
    # named as the form's name box, and fixed where the name is entered (R23).
    part = {**_sheet_part([{"line": "3.5", "cells": ["Volvo", "500.00"]}]), "name": "Maria Wąs"}

    with pytest.raises(UnprintableLetter) as refused:
        plan_sheet("schedule_a_b", _spec(), part)

    assert (refused.value.letter, refused.value.label) == ("ą", "Debtor 1")
    assert (refused.value.step, refused.value.page) == ("debtor_info", None)


def test_the_sheet_prints_in_the_templates_own_encoding(schedule_a_b_with_sheet):
    # Every template's /Helv is the base-14 Helvetica with one /Encoding (R62). The sheet
    # encodes each letter by it, as pypdf encodes a form's, and gives every page's font it.
    for form_type in get_all_form_types():
        template = load_schema(form_type).template_filename
        reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template)
        helv = reader.root_object["/AcroForm"]["/DR"]["/Font"]["/Helv"].get_object()
        encoding = helv["/Encoding"].get_object()
        assert (helv["/BaseFont"], helv["/Subtype"], "/BaseEncoding" in encoding) == (
            "/Helvetica",
            "/Type1",
            False,
        )
        assert [str(entry) for entry in encoding["/Differences"]] == sheets._DIFFERENCES.split()
        assert sheets._font().encoding == font_for(template, "/Helv").encoding
    # A sheet of two pages: each page's Helvetica has the encoding.
    rows = [{"line": f"3.{n}", "cells": ["\n".join(["Volvo"] * 40), ""]} for n in (5, 6)]
    part = _sheet_part(rows)
    document = pymupdf.open("pdf", draw_sheet(sheet_spec(part), part))
    fonts = [xref for page in document for xref, *_ in page.get_fonts()]
    assert (len(document), len(fonts)) == (2, 2)
    for xref in fonts:
        _, differences = document.xref_get_key(xref, "Encoding/Differences")
        assert re.findall(r"\d+|/[^\s/\[\]]+", differences) == sheets._DIFFERENCES.split()


def test_a_word_wider_than_its_cell_is_refused(session, creditor_payments):
    rows = creditor_payments(session, 5, MAKES)
    rows[4].creditor_name = "Volvo " + "YV1MS382X42" * 6  # one word, wider than the column
    rows[4].save()

    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_a_b", build_parts("schedule_a_b", session))

    assert str(refused.value) == (
        "“Make” is too long to fit on the court form, even in small print. Shorten it."
    )
    assert (refused.value.step, refused.value.page) == (None, "/sofa")


def test_a_word_as_wide_as_its_cell_prints_and_a_wider_one_is_refused(session, creditor_payments):
    # The Make column is 300 pt, 296 pt inside its padding. Thirty-one W's and an i are
    # 294.86 pt at 10 pt and print whole; with a second i, 297.08 pt, Generate refuses them
    # rather than Download failing.
    payments = creditor_payments(session, 5, [*MAKES[:4], "W" * 31 + "i"])

    _, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.rows == (("3.5", "W" * 31 + "i", "500.00"),)
    assert sheet.crossing == ()
    payments[4].creditor_name = "W" * 31 + "ii"
    payments[4].save()
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_a_b", build_parts("schedule_a_b", session))
    assert refused.value.label == "Make"


def test_a_row_as_tall_as_a_page_prints_and_a_taller_one_is_refused(schedule_a_b_with_sheet):
    # Below the header's three lines, a blank line, the labels' one and a 6 pt gap, a page
    # has 792 - 54 - 128.70 = 609.30 pt for its rows: 44 lines of 13.74 pt.
    def parts(lines):
        make = "\n".join(["Volvo"] * lines)
        row = {"line": "3.5", "cells": [make, "500.00"]}
        return {"version": 2, "parts": [{"kind": "form", "values": {}}, _sheet_part([row])]}

    pdf = PDFFormFiller().fill("schedule_a_b", parts(44))

    assert len(pymupdf.open("pdf", pdf)) == 11
    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.lines == ((("3.5",), ("Volvo",) * 44, ("500.00",)),)
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_a_b", parts(45))
    assert refused.value.label == "Make"


def test_a_row_taller_than_a_page_is_refused_naming_its_tallest_cell(schedule_a_b_with_sheet):
    part = _sheet_part([{"line": "3.5", "cells": ["Volvo", "worth " * 600]}])

    with pytest.raises(ValueTooLong) as refused:
        plan_sheet("schedule_a_b", _spec(), part)

    assert refused.value.label == "Current value of the portion you own"


def test_a_sheet_page_is_never_read_as_a_page_of_the_form(session, creditor_payments):
    creditor_payments(session, 5, MAKES)
    parts, pdf = _drawn(session)
    with pytest.raises(ValueError, match="11 pages, but its parts print 10$"):
        read_drawn("schedule_a_b", pdf)
    # A drawing with no sheet, read with parts that have one.
    session.sofa_report.creditor_payments.order_by("pk").last().delete()
    _, unsheeted = _drawn(session)
    with pytest.raises(ValueError, match="10 pages, but its parts print 10 and 1 attached sheet"):
        read_drawn("schedule_a_b", unsheeted, parts)


def test_a_guarded_column_prints_blank_on_the_sheet(
    schedule_a_b_with_sheet, session, creditor_payments, monkeypatch
):
    # UPL guard: the value slots print only an asked answer, so they print nothing here,
    # on the form's pages or on the sheet. The guard decides which cells print, never
    # which rows exist: the fifth row and its make still print.
    path = schedule_a_b_with_sheet / "schedule_a_b.json"
    data = json.loads(path.read_text())
    for f in data["fields"]:
        if f["repeat"] == "ab_line_3" and f["binding"].endswith("total_paid"):
            f.update(source="derived", rule="full_name", legal_review=True)
    path.write_text(json.dumps(data))
    load_schema.cache_clear()
    creditor_payments(session, 5, MAKES)
    # PyMuPDF's own log, where it writes an error it swallows; stdout by default.
    log = StringIO()
    monkeypatch.setattr(pymupdf, "_g_out_log", log)

    parts, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.rows == (("3.5", "Volvo", ""),)
    text = "".join(page.get_text() for page in pymupdf.open("pdf", pdf))
    assert [amount for amount in ("100.00", "400.00", "500.00") if amount in text] == []
    # The blank cell draws no line, so PyMuPDF logs no error for an empty one.
    assert log.getvalue() == ""


def test_a_form_with_a_copy_and_a_sheet_prints_the_sheet_last(
    session, schedule_d_with_a_copy_and_a_sheet, creditor_payments
):
    # Seven payments: Part 1 prints five rows and its sixth and seventh on a sheet; Part 2
    # prints six entries on page 3, the template's last, and its seventh on a copy of it.
    # The pages are the form's, then the copy, then the sheet (spec §6, printing order).
    creditor_payments(session, 7, MAKES)

    document = build_parts("schedule_d", session)
    pdf = PDFFormFiller().fill("schedule_d", document)

    assert [part["kind"] for part in document["parts"]] == ["form", "copy", "sheet"]
    pages = pymupdf.open("pdf", pdf)
    headed = ["(attached sheet)" in " ".join(page.get_text().split()) for page in pages]
    assert headed == [False] * 4 + [True]
    drawn = read_drawn("schedule_d", pdf, document["parts"])
    assert {(w.copy, w.value) for w in drawn if w.full_name == "Name"} == {
        (None, "Honda"),
        (1, "Saab"),
    }
    (sheet,) = read_sheets(pdf, sheet_spec(document["parts"][2]))
    assert sheet.rows == (("2.6", "Kia", "600.00"), ("2.7", "Saab", "700.00"))
```

`test_attached_sheets.py` draws the synthetic Schedule A/B through `build_parts`, `fill()`, `read_drawn(..., parts)` and `read_sheets`:

- five vehicles: the fifth prints on an eleventh page, labelled 3.5, under the header, the labels and the case number's blank line, in Helvetica at 10 pt, and the sheet part is exactly the stored shape;
- a long sheet (twenty rows on it) runs to a second page, 14 rows and 6, with the header on each, no row split, and nothing outside the margins or its column;
- a cell keeps its 2 pt padding, at the boundaries plan and draw share (a word, a row of 44 lines);
- totals count rows printed on copies and sheets;
- the letters: "ą" refused in a Make cell, naming `/sofa`; Ł, ł and ı printed and read back in MuPDF and pypdf; the templates' `/Encoding` pinned; the name refused on the form with or without a sheet, and by `plan_sheet` alone;
- a word wider than its cell and a row taller than a page are refused;
- `read_drawn` refuses a sheet page read as a form page;
- a guarded column prints blank, and PyMuPDF logs nothing;
- a form with a copy and a sheet prints the sheet last.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/conftest.py b/backend/apps/forms/tests/conftest.py
index 0fa282d..baf6674 100644
--- a/backend/apps/forms/tests/conftest.py
+++ b/backend/apps/forms/tests/conftest.py
@@ -43,6 +43,43 @@ _D_PART_1 = [
 _D_PART_2 = [
     (3, [(box, *_NAME)]) for box in ["Name", "Name_2", "Name_3", "Name_4", "Name_5", "Name_6"]
 ]
+# Schedule A/B line 3's four vehicles, 3.1 and 3.2 on page 2, 3.3 and 3.4 on page 3: each a
+# make and the current value of the portion the filer owns, kept as a SOFA creditor payment's
+# name and amount (R19: no new list source in 3a2).
+_MAKE = ("Make", "creditor_name")
+_VALUE = ("Current value of the portion you own", "total_paid")
+_AB_LINE_3 = [
+    (2, [("3 1", *_MAKE), ("undefined_15", *_VALUE)]),
+    (2, [("If you own or have more than one describe here", *_MAKE), ("undefined_17", *_VALUE)]),
+    (3, [("1_3", *_MAKE), ("undefined_19", *_VALUE)]),
+    (3, [("1_4", *_MAKE), ("undefined_21", *_VALUE)]),
+]
+_AB_SHEET = {
+    "title": "Official Form 106A/B, Schedule A/B: Property",
+    "columns": [
+        {"label": "Make", "binding": "sofa.creditor_payments[].creditor_name", "width": 300},
+        {
+            "label": "Current value of the portion you own",
+            "binding": "sofa.creditor_payments[].total_paid",
+            "width": 168,
+        },
+    ],
+}
+_D_SHEET = {
+    "title": "Official Form 106D, Schedule D: Creditors Who Have Claims Secured by Property",
+    "columns": [
+        {
+            "label": "Creditor's name",
+            "binding": "sofa.creditor_payments[].creditor_name",
+            "width": 300,
+        },
+        {
+            "label": "Amount of claim",
+            "binding": "sofa.creditor_payments[].total_paid",
+            "width": 168,
+        },
+    ],
+}
 _CREDITORS = [
     "Ashby Auto Credit",
     "Birchfield Lending",
@@ -80,16 +117,18 @@ def index_copy(tmp_path, settings):
     template_widgets.cache_clear()


-def _schedule_d_with_group(tmp_path, settings, group, rows, declaration):
+def _with_group(tmp_path, settings, form_type, group, rows, declaration):
     """
-    Copy the real schemas into tmp_path and point FORM_SCHEMAS_DIRECTORY there, with a
-    synthetic repeat group on Schedule D: row n's slot is rows[n - 1], (page, boxes), each
-    box bound to that SOFA creditor payment's attribute; the group's declaration is
-    `declaration`. Returns the schemas directory.
+    Copy the real schemas into tmp_path, unless an earlier fixture of the test has, and point
+    FORM_SCHEMAS_DIRECTORY there, with a synthetic repeat group on form_type: row n's slot is
+    rows[n - 1], (page, boxes), each box bound to that SOFA creditor payment's attribute; the
+    group's declaration is `declaration`, beside any group added before. Returns the
+    schemas directory.
     """
     schemas = tmp_path / "schemas"
-    shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, schemas)
-    path = schemas / "schedule_d.json"
+    if not schemas.exists():
+        shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, schemas)
+    path = schemas / f"{form_type}.json"
     schema = json.loads(path.read_text())
     for row, (page, boxes) in enumerate(rows, start=1):
         for pdf_field, label, attr in boxes:
@@ -112,7 +151,7 @@ def _schedule_d_with_group(tmp_path, settings, group, rows, declaration):
                     "legal_review": False,
                 }
             )
-    schema["groups"] = {group: declaration}
+    schema.setdefault("groups", {})[group] = declaration
     path.write_text(json.dumps(schema))
     settings.FORM_SCHEMAS_DIRECTORY = schemas
     return schemas
@@ -141,7 +180,7 @@ def schedule_d_with_copies(tmp_path, settings):
             {"page": 3, "this": "fill_28.1.1", "of": "fill_28.1.2"},
         ],
     }
-    schemas = _schedule_d_with_group(tmp_path, settings, "d_part_1", _D_PART_1, declaration)
+    schemas = _with_group(tmp_path, settings, "schedule_d", "d_part_1", _D_PART_1, declaration)
     load_schema.cache_clear()
     yield schemas
     load_schema.cache_clear()
@@ -154,7 +193,39 @@ def schedule_d_part_2_with_copies(tmp_path, settings):
     entries on page 3, continued on copies of that page, the template's last, as C, G
     and H continue theirs. Yields the schemas directory.
     """
-    schemas = _schedule_d_with_group(tmp_path, settings, "d_part_2", _D_PART_2, {"extra_page": 3})
+    schemas = _with_group(
+        tmp_path, settings, "schedule_d", "d_part_2", _D_PART_2, {"extra_page": 3}
+    )
+    load_schema.cache_clear()
+    yield schemas
+    load_schema.cache_clear()
+
+
+@pytest.fixture
+def schedule_a_b_with_sheet(tmp_path, settings):
+    """
+    A copy of the real schemas whose Schedule A/B has a synthetic repeat group (3a2 spec
+    §5.4, R18, R19): line 3's four vehicles, each a make and its value, continued on an
+    attached sheet under those two columns, its rows numbered "3.{n}". Yields the schemas
+    directory, cleared from the schema cache before and after, as schedule_d_with_copies.
+    """
+    declaration = {"number": "3.{n}", "sheet": _AB_SHEET}
+    schemas = _with_group(tmp_path, settings, "schedule_a_b", "ab_line_3", _AB_LINE_3, declaration)
+    load_schema.cache_clear()
+    yield schemas
+    load_schema.cache_clear()
+
+
+@pytest.fixture
+def schedule_d_with_a_copy_and_a_sheet(tmp_path, settings):
+    """
+    Schedule D with both continuations (R56): Part 2's six entries on copies of page 3, the
+    template's last, and Part 1's five rows on an attached sheet, numbered "2.{n}" under a
+    name column and an amount column. Yields the schemas directory.
+    """
+    _with_group(tmp_path, settings, "schedule_d", "d_part_2", _D_PART_2, {"extra_page": 3})
+    declaration = {"number": "2.{n}", "sheet": _D_SHEET}
+    schemas = _with_group(tmp_path, settings, "schedule_d", "d_part_1", _D_PART_1, declaration)
     load_schema.cache_clear()
     yield schemas
     load_schema.cache_clear()
@@ -162,14 +233,18 @@ def schedule_d_part_2_with_copies(tmp_path, settings):

 @pytest.fixture
 def creditor_payments():
-    """add(session, count): that many SOFA creditor payments, each a firm and an amount."""
+    """
+    add(session, count, names=None): that many SOFA creditor payments, the nth named
+    names[n - 1] (by default a firm), each at n00.00.
+    """

-    def add(session, count):
+    def add(session, count, names=None):
+        names = names or _CREDITORS
         report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
         return [
             SOFACreditorPayment.objects.create(
                 report=report,
-                creditor_name=_CREDITORS[n - 1] if n <= len(_CREDITORS) else f"Creditor {n}",
+                creditor_name=names[n - 1] if n <= len(names) else f"Creditor {n}",
                 total_paid=Decimal(f"{n}00.00"),
             )
             for n in range(1, count + 1)
diff --git a/backend/apps/forms/tests/pdf_readback.py b/backend/apps/forms/tests/pdf_readback.py
index 2aca871..e488616 100644
--- a/backend/apps/forms/tests/pdf_readback.py
+++ b/backend/apps/forms/tests/pdf_readback.py
@@ -6,7 +6,8 @@ mark, while the templates print their own words in Arial, Wingdings and Times. A
 character belongs to a widget when its centre lies inside the widget's rect from the
 field index: two pairs of boxes overlap by about 2 pt, and a glyph merely touching a
 rect would put a neighbour's tick in it. A copy of an extra page is read as the template
-page it copies, found through the form's parts.
+page it copies, found through the form's parts. An attached sheet has no widget: its
+pages are read line by line under its columns (read_sheets).
 """

 from dataclasses import dataclass, replace
@@ -19,7 +20,8 @@ import pypdf
 from django.conf import settings
 from pypdf.generic import ArrayObject, NameObject

-from apps.forms.schema import load_schema
+from apps.forms.schema import SheetSpec, load_schema
+from apps.forms.services.sheets import LINE_WIDTH, MARGIN
 from apps.forms.services.widgets import TemplateWidget, page_count, template_widgets, widget_for

 _BOXES = ("CheckBox", "RadioButton")
@@ -44,6 +46,7 @@ class _Character:
     centre: tuple[float, float]
     line: tuple[int, int]  # MuPDF's (block, line) on the page
     baseline: float
+    box: tuple[float, float, float, float]


 def _characters(page: pymupdf.Page) -> list[_Character]:
@@ -63,6 +66,7 @@ def _characters(page: pymupdf.Page) -> list[_Character]:
                             ((x0 + x1) / 2, (y0 + y1) / 2),
                             (b, n),
                             char["origin"][1],
+                            (x0, y0, x1, y1),
                         )
                     )
     return characters
@@ -152,7 +156,8 @@ def read_drawn(
     """
     What the drawn form prints in each widget of its template, one entry per index row
     in page and tag order. With `parts`, the parts it was drawn from (spec §6), each copy
-    of an extra page follows that page, its widgets read with their copy number. A text
+    of an extra page follows that page, its widgets read with their copy number, and the
+    pages of its attached sheets, which come last, are left to read_sheets(). A text
     box that prints exactly what the blank form prints there reads as "": nothing the
     template prints passes for a value, so a value equal to that box's blank text reads
     blank too.
@@ -161,9 +166,9 @@ def read_drawn(
         ValueError: a page still has a widget. MuPDF reads an unbaked widget's appearance
             as text, and a viewer may rebuild it from the field's one value, so only a
             baked page shows what prints. Not an assertion, so a listed defect's xfail
-            never takes a missing bake for that defect. Also when the PDF has a page
-            count other than the template's and its copies', so no copy is read as
-            another page.
+            never takes a missing bake for that defect. Also when the PDF's pages aren't
+            the template's and its copies', then at least one attached sheet page per
+            sheet part and nothing else, so no copy or sheet is read as another page.
     """
     template = load_schema(form_type).template_filename
     blank = _blank(template)
@@ -172,9 +177,127 @@ def read_drawn(
     if unbaked:
         raise ValueError(f"the PDF still has widgets on pages {unbaked}: it was never baked")
     pages = _pages(template, parts or [])
-    if len(document) != len(pages):
-        raise ValueError(f"the PDF has {len(document)} pages, but its parts print {len(pages)}")
+    # An attached sheet's pages come after the form's pages and copies, each headed by its
+    # title "… (attached sheet)" (spec §5.3); they hold no widget, so they aren't read here.
+    sheets = sum(part["kind"] == "sheet" for part in parts or [])
+    form, after = list(document)[: len(pages)], list(document)[len(pages) :]
+    if (
+        len(form) != len(pages)
+        or any(_is_sheet(page) for page in form)
+        or not all(_is_sheet(page) for page in after)
+        or len(after) < sheets
+        or (after and not sheets)
+    ):
+        raise ValueError(
+            f"the PDF has {len(document)} pages, but its parts print {len(pages)}"
+            + (f" and {sheets} attached sheet(s)" if sheets else "")
+        )
     return [
         replace(w, value="") if w.value and blank.get((w.page, w.tag)) == w.value else w
-        for w in _read(template, document, pages)
+        for w in _read(template, form, pages)
     ]
+
+
+_SHEET_TITLE = "(attached sheet)"
+
+
+def _is_sheet(page: pymupdf.Page) -> bool:
+    """Whether the page is an attached sheet's: its header's title says so."""
+    return _SHEET_TITLE in " ".join(page.get_text().split())
+
+
+@dataclass(frozen=True)
+class SheetPage:
+    """One page of an attached sheet, read the way a person reads it."""
+
+    header: tuple[str, ...]  # its lines down to "Case number (if known)", top to bottom
+    labels: tuple[str, ...]  # each column's label, the line column's ("") first
+    rows: tuple[tuple[str, ...], ...]  # each row: its line, then its cells, column by column
+    lines: tuple[tuple[tuple[str, ...], ...], ...]  # each row's cells, each as its lines
+    ink: tuple[float, float, float, float]  # the box every character of the page lies in
+    # Below the header, each character not inside its column. A space is left out: it
+    # prints nothing, and MuPDF reads the gap between two cells' text as one.
+    crossing: tuple[str, ...]
+    overlapping: tuple[str, ...]  # each line whose characters reach into the next line's
+
+
+def read_sheets(pdf_bytes: bytes, spec: SheetSpec) -> list[SheetPage]:
+    """
+    Each attached sheet page of a drawn form, read under the columns of `spec`: the line
+    column's 36 pt from the left margin (0.75 in), then the group's columns, each as wide
+    as declared. A character belongs to the column its centre lies in, and to the line of
+    its baseline. A row starts at each line that prints a line number, and takes every line
+    down to the next; a cell's lines, like a label's, are joined with spaces in `rows` and
+    kept apart in `lines`. A character's box is MuPDF's, from its font's ascender to its
+    descender.
+    """
+    edges = [MARGIN, MARGIN + LINE_WIDTH]
+    for column in spec.columns:
+        edges.append(edges[-1] + column.width)
+    pages = []
+    for page in pymupdf.open("pdf", pdf_bytes):
+        if not _is_sheet(page):
+            continue
+        characters = [c for c in _characters(page) if c.font == _TEXT_FONT]
+        baselines: dict[float, list[_Character]] = {}
+        for character in characters:
+            baselines.setdefault(round(character.baseline, 1), []).append(character)
+        texts, lines, columns = [], [], []  # each line's text, its cells, its characters' columns
+        for baseline in sorted(baselines):
+            ordered = sorted(baselines[baseline], key=lambda c: c.centre[0])
+            texts.append("".join(c.text for c in ordered).strip())
+            cells = [""] * (len(edges) - 1)
+            for character in ordered:
+                column = max(
+                    (i for i, edge in enumerate(edges[:-1]) if edge <= character.centre[0]),
+                    default=0,
+                )
+                cells[column] += character.text
+                columns.append((character, column))
+            lines.append([cell.strip() for cell in cells])
+        case_number = next(i for i, text in enumerate(texts) if text.startswith("Case number"))
+        header = texts[: case_number + 1]
+        below = sorted(baselines)[case_number + 1 :]
+        crossing = tuple(
+            c.text
+            for c, i in columns
+            if round(c.baseline, 1) in below
+            and not c.text.isspace()
+            and not (edges[i] - 0.01 <= c.box[0] and c.box[2] <= edges[i + 1] + 0.01)
+        )
+        extents = [
+            (texts[n], min(c.box[1] for c in baselines[b]), max(c.box[3] for c in baselines[b]))
+            for n, b in enumerate(sorted(baselines))
+        ]
+        overlapping = tuple(
+            text
+            for (text, _, bottom), (_, top, _) in zip(extents, extents[1:], strict=False)
+            if bottom > top + 0.01
+        )
+        body = lines[case_number + 1 :]
+        starts = [i for i, line in enumerate(body) if line[0]] + [len(body)]
+        labels = _joined(body[: starts[0]], len(edges) - 1)
+        spans = list(zip(starts, starts[1:], strict=False))
+        rows = [_joined(body[a:b], len(edges) - 1) for a, b in spans]
+        lines_of = [
+            tuple(tuple(line[i] for line in body[a:b] if line[i]) for i in range(len(edges) - 1))
+            for a, b in spans
+        ]
+        boxes = [c.box for c in characters]
+        ink = (
+            min(b[0] for b in boxes),
+            min(b[1] for b in boxes),
+            max(b[2] for b in boxes),
+            max(b[3] for b in boxes),
+        )
+        pages.append(
+            SheetPage(
+                tuple(header), labels, tuple(rows), tuple(lines_of), ink, crossing, overlapping
+            )
+        )
+    return pages
+
+
+def _joined(lines: list[list[str]], columns: int) -> tuple[str, ...]:
+    """Each column's text over several lines, its non-empty lines joined with spaces."""
+    return tuple(" ".join(line[i] for line in lines if line[i]) for i in range(columns))
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index c4360cf..d2642cd 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -157,11 +157,15 @@ def _comparable(form_type, values):


 def _comparable_document(form_type, document):
-    """A form's parts document, each part's values made comparable as _comparable does."""
+    """
+    A form's parts document, each part's values made comparable as _comparable does. An
+    attached sheet's part has no values: its rows are compared as they are.
+    """
     return {
         **document,
         "parts": [
-            {**part, "values": _comparable(form_type, part["values"])} for part in document["parts"]
+            {**part, "values": _comparable(form_type, part["values"])} if "values" in part else part
+            for part in document["parts"]
         ],
     }

diff --git a/backend/apps/forms/tests/test_check.py b/backend/apps/forms/tests/test_check.py
index ce58cc7..fe4022b 100644
--- a/backend/apps/forms/tests/test_check.py
+++ b/backend/apps/forms/tests/test_check.py
@@ -99,6 +99,9 @@ def _pypdf_stream(form_type, widget, value, size=-1):
         ("Wąsowicz", "ą"),
         ("Dvořák", "ř"),
         ("Nguyễn", "ễ"),
+        # pypdf reads the template's /.notdef, at code 173, as □: drawn, it prints that code,
+        # a soft hyphen.
+        ("Nowak□", "□"),
     ],
 )
 def test_a_letter_the_form_cannot_print_is_refused(last_name, letter):
diff --git a/backend/apps/forms/tests/test_checks.py b/backend/apps/forms/tests/test_checks.py
index e4bc623..370b508 100644
--- a/backend/apps/forms/tests/test_checks.py
+++ b/backend/apps/forms/tests/test_checks.py
@@ -338,7 +338,7 @@ def _row_3_numbered_on_the_page_of_its_unmapped_box(d):
         ),
         (
             _group(lambda g: g.pop("extra_page")),
-            ("forms.E007", "schedule_d: group 'd_part_1' names no extra_page"),
+            ("forms.E007", "schedule_d: group 'd_part_1' names neither an extra_page nor a sheet"),
         ),
         (
             # Page 3 is Part 2's: no row of Part 1 is there.
@@ -704,7 +704,7 @@ def test_an_untagged_box_slot_whose_boxes_each_have_their_own_state_passes(
     assert _errors("schedule_d") == []


-def _part_2(extra_page):
+def _part_2(declaration):
     """Add a second group to the synthetic Schedule D: Part 2's six names on page 3."""

     def add(d):
@@ -720,14 +720,14 @@ def _part_2(extra_page):
                     "row": row,
                 }
             )
-        d["groups"]["d_part_2"] = {} if extra_page is None else {"extra_page": extra_page}
+        d["groups"]["d_part_2"] = declaration

     return add


 def test_a_second_group_continued_on_copies_is_reported(schedule_d_with_copies):
     # 3a2 numbers a form's pages counting one group's copies only (R21, R56).
-    _edit(schedule_d_with_copies, "schedule_d", _part_2(extra_page=3))
+    _edit(schedule_d_with_copies, "schedule_d", _part_2({"extra_page": 3}))
     assert _errors("schedule_d") == [
         (
             "forms.E007",
@@ -738,13 +738,250 @@ def test_a_second_group_continued_on_copies_is_reported(schedule_d_with_copies):


 def test_a_group_with_no_extra_page_is_not_counted_as_a_second(schedule_d_with_copies):
-    # Such a group is refused for its own reason (T7's sheet groups will declare a sheet).
-    _edit(schedule_d_with_copies, "schedule_d", _part_2(extra_page=None))
+    # Such a group is refused for its own reason.
+    _edit(schedule_d_with_copies, "schedule_d", _part_2({}))
     assert _errors("schedule_d") == [
-        ("forms.E007", "schedule_d: group 'd_part_2' names no extra_page")
+        ("forms.E007", "schedule_d: group 'd_part_2' names neither an extra_page nor a sheet")
     ]


+def test_a_group_continued_on_an_attached_sheet_is_not_counted_as_a_second(
+    schedule_d_with_copies,
+):
+    # A sheet's pages aren't copies of the form's, so they number none of its pages (R56).
+    sheet = {
+        "title": "Official Form 106D, Schedule D: Creditors Who Have Claims Secured by Property",
+        "columns": [
+            {"label": "Name", "binding": "sofa.creditor_payments[].creditor_name", "width": 300}
+        ],
+    }
+    _edit(schedule_d_with_copies, "schedule_d", _part_2({"number": "3.{n}", "sheet": sheet}))
+    assert _errors("schedule_d") == []
+
+
+def test_a_group_continued_on_an_attached_sheet_passes(schedule_a_b_with_sheet):
+    assert _errors("schedule_a_b") == []
+
+
+def _sheet(change):
+    """Change the synthetic Schedule A/B group's declaration."""
+    return lambda d: change(d["groups"]["ab_line_3"])
+
+
+def _column(n, **change):
+    """Change the nth column of the synthetic Schedule A/B group's sheet."""
+    return _sheet(lambda g: g["sheet"]["columns"][n].update(change))
+
+
+def _makes_asked_on_ask_page(d):
+    # The slots and the column bind one answer: a binding, but no list of rows.
+    for f in d["fields"]:
+        if f["repeat"] == "ab_line_3" and f["binding"].endswith("creditor_name"):
+            f["binding"] = "answer:schedule_a_b.make"
+    d["groups"]["ab_line_3"]["sheet"]["columns"][0]["binding"] = "answer:schedule_a_b.make"
+
+
+def _community_property_boxes(d):
+    # Each vehicle's community-property box, ticked from a list: a sheet has no box to tick.
+    for row, (page, box) in enumerate([(2, ""), (2, "_2"), (3, "_3"), (3, "_4")], start=1):
+        d["fields"].append(
+            {
+                **_text(f"Check if this is community property see{box}", page, None),
+                "type": "checkbox",
+                "source": "asked",
+                "value": None,
+                "choices": {"true": "/On"},
+                "binding": "sofa.creditor_payments[].dates_of_payments",
+                "repeat": "ab_line_3",
+                "repeat_capacity": 4,
+                "row": row,
+            }
+        )
+
+
+def _a_column_of_boxes(d):
+    _community_property_boxes(d)
+    columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
+    columns[0]["width"] = 200
+    columns.append(
+        {
+            "label": "Community property",
+            "binding": "sofa.creditor_payments[].dates_of_payments",
+            "width": 100,
+        }
+    )
+
+
+def _another_lists_column(d):
+    columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
+    columns[0]["width"] = 200
+    columns.append(
+        {"label": "Paid on", "binding": "sofa.creditor_payments[].dates_of_payments", "width": 100}
+    )
+
+
+def _ab_slots(change):
+    """Change every field of the synthetic Schedule A/B group."""
+    return lambda d: [change(f) for f in d["fields"] if f["repeat"] == "ab_line_3"]
+
+
+def _swap_rows_2_and_3(f):
+    f["row"] = {2: 3, 3: 2}.get(f["row"], f["row"])
+
+
+_AB = "schedule_a_b: group 'ab_line_3'"
+
+
+@pytest.mark.parametrize(
+    "change, error",
+    [
+        (
+            _sheet(lambda g: g.update(extra_page=3)),
+            ("forms.E007", f"{_AB} names both an extra_page and a sheet"),
+        ),
+        (
+            # T6's slot rules hold for a sheet group's slots too.
+            _ab_slots(lambda f: f.update(repeat_capacity=5)),
+            (
+                "forms.E007",
+                "schedule_a_b: repeat group 'ab_line_3': its slot rows aren't exactly 1 to "
+                "its repeat_capacity, 5",
+            ),
+        ),
+        (
+            _ab_slots(_swap_rows_2_and_3),
+            (
+                "forms.E007",
+                "schedule_a_b: repeat group 'ab_line_3': row 3 is on a page before row 2's",
+            ),
+        ),
+        (
+            # A sheet labels each row with the line it continues.
+            _sheet(lambda g: g.pop("number")),
+            ("forms.E007", f"{_AB}: number must contain {{n}}"),
+        ),
+        (
+            _sheet(lambda g: g.update(page_numbers=[{"page": 2}])),
+            ("forms.E007", f"{_AB}: a sheet group has no copies, so it numbers no pages"),
+        ),
+        (
+            # A row of line numbers alone.
+            _sheet(lambda g: g["sheet"].update(columns=[])),
+            ("forms.E007", f"{_AB}: its sheet has no columns for its rows"),
+        ),
+        (
+            # 36 pt of line column, then 301 and 168: one point past the margins.
+            _column(0, width=301),
+            (
+                "forms.E007",
+                f"{_AB}: its sheet's columns and line column are 505 pt wide, "
+                "more than the 504 pt (7 in) between its margins",
+            ),
+        ),
+        (
+            _makes_asked_on_ask_page,
+            (
+                "forms.E007",
+                f"{_AB}: sheet column 'Make' binds 'answer:schedule_a_b.make', "
+                "not a sofa.<collection>[].<attr> list",
+            ),
+        ),
+        (
+            # Another list of the same report: its rows aren't the group's.
+            _another_lists_column,
+            (
+                "forms.E007",
+                f"{_AB}: sheet column 'Paid on' binds "
+                "'sofa.creditor_payments[].dates_of_payments', which no slot of the group binds",
+            ),
+        ),
+        (
+            _a_column_of_boxes,
+            (
+                "forms.E007",
+                f"{_AB}: sheet column 'Community property' binds a box's answer, "
+                "which a sheet can't tick",
+            ),
+        ),
+        (
+            # Rows 1 to 4 print their values on the form, the fifth's nowhere.
+            _sheet(lambda g: g["sheet"].update(columns=g["sheet"]["columns"][:1])),
+            (
+                "forms.E007",
+                f"{_AB}: no sheet column prints 'sofa.creditor_payments[].total_paid', "
+                "which a slot of the group binds",
+            ),
+        ),
+        (
+            # Rows 1 to 4 tick their boxes on the form; a fifth row has no box to tick.
+            _community_property_boxes,
+            (
+                "forms.E007",
+                f"{_AB}: a box slot binds 'sofa.creditor_payments[].dates_of_payments', "
+                "and a sheet can't tick a box",
+            ),
+        ),
+        (
+            # "Line 3.5" is 35.58 pt at 10 pt, wider than the 32 pt inside the line column's
+            # padding: it would print on two lines.
+            _sheet(lambda g: g.update(number="Line 3.{n}")),
+            (
+                "forms.E007",
+                f"{_AB}: its sheet can't print its first line, 'Line 3.5', whole in the "
+                "36 pt line column",
+            ),
+        ),
+        (
+            # The filer couldn't tell the two apart, nor could a refusal's fix.
+            _column(1, label="Make"),
+            ("forms.E007", f"{_AB}: its sheet has more than one column labelled 'Make'"),
+        ),
+        (
+            # "Make" is 24.45 pt wide at 10 pt: it doesn't fit 20 pt less its padding.
+            _column(0, width=20),
+            ("forms.E007", f"{_AB}: sheet column 'Make' can't print its label whole in 20 pt"),
+        ),
+        (
+            _column(0, width=0),
+            ("forms.E007", f"{_AB}: sheet column 'Make' can't print its label whole in 0 pt"),
+        ),
+        (
+            _column(0, label="Mąke"),
+            ("forms.E007", f"{_AB}: sheet column 'Mąke' can't print its label whole in 300 pt"),
+        ),
+        (
+            _sheet(lambda g: g["sheet"].update(title="Schedule A/B: Własność")),
+            ("forms.E007", f"{_AB}: its sheet can't print its title whole"),
+        ),
+    ],
+    ids=[
+        "an extra page too",
+        "capacity other than the slots",
+        "rows that go back a page",
+        "no number",
+        "page numbers",
+        "no columns",
+        "wider than the margins",
+        "a column of no list",
+        "a column of another list",
+        "a column of boxes",
+        "a slot with no column",
+        "a box slot",
+        "a first line wider than the line column",
+        "two columns with one label",
+        "a label wider than its column",
+        "a column with no width",
+        "a label with a letter the sheet can't print",
+        "a title with a letter the sheet can't print",
+    ],
+)
+def test_a_sheet_that_cannot_print_its_rows_whole_is_reported(
+    schedule_a_b_with_sheet, change, error
+):
+    _edit(schedule_a_b_with_sheet, "schedule_a_b", change)
+    assert _errors("schedule_a_b") == [error]
+
+
 def test_a_template_that_doesnt_match_its_index_is_reported_not_raised(schema_copy, index_copy):
     def move_a_row_off_its_widget(rows):
         next(row for row in rows if row["page"] == 2)["rect"] = [1, 1, 2, 2]
diff --git a/backend/apps/forms/tests/test_download_action.py b/backend/apps/forms/tests/test_download_action.py
index 419d03a..fb87213 100644
--- a/backend/apps/forms/tests/test_download_action.py
+++ b/backend/apps/forms/tests/test_download_action.py
@@ -11,9 +11,10 @@ import pymupdf
 import pytest
 from django.urls import reverse

+from apps.forms.checks import validate_form
 from apps.forms.schema import load_schema
 from apps.forms.services.pdf_filler import PDFFormFiller, TemplateHasNoForm
-from apps.forms.tests.pdf_readback import read_drawn
+from apps.forms.tests.pdf_readback import read_drawn, read_sheets


 def _download(client, form):
@@ -61,50 +62,138 @@ def test_unfiled_form_prints_the_filers_current_answers(api_client_authed, gener
     assert part["values"]["Debtor1.First name"] == "Marisol"


+_FILED_SHEET = [
+    # Schedule A/B's fifth and sixth vehicles, on its attached sheet, under the filer's name.
+    ("Maria Torres", (("3.5", "Volvo", "500.00"), ("3.6", "Kia", "600.00")))
+]
+
+
 @pytest.mark.parametrize(
-    "form_type, parts, box, printed",
+    "form_type, parts, box, printed, sheets",
     [
-        ("form_121", ["form"], "Debtor1.First name", {(None, "Maria")}),
+        ("form_121", ["form"], "Debtor1.First name", {(None, "Maria")}, []),
         # Schedule D's sixth row prints on a copy of page 2, under the filer's name.
-        ("schedule_d", ["form", "copy"], "Debtor 1", {(None, "Maria Torres"), (1, "Maria Torres")}),
+        (
+            "schedule_d",
+            ["form", "copy"],
+            "Debtor 1",
+            {(None, "Maria Torres"), (1, "Maria Torres")},
+            [],
+        ),
+        ("schedule_a_b", ["form", "sheet"], "Debtor 1", {(None, "Maria Torres")}, _FILED_SHEET),
     ],
-    ids=["form", "with a copy"],
+    ids=["form", "with a copy", "with a sheet"],
 )
 def test_a_filed_form_downloads_exactly_what_was_filed(
     api_client_authed,
     generated_form_factory,
     schedule_d_with_copies,
+    schedule_a_b_with_sheet,
     creditor_payments,
     form_type,
     parts,
     box,
     printed,
+    sheets,
 ):
     form = generated_form_factory(status="generated")
     form.form_type = form_type
     form.save()
-    rows = creditor_payments(form.session, 6)
+    rows = creditor_payments(
+        form.session, 6, ["Honda", "Toyota", "Subaru", "Mazda", "Volvo", "Kia"]
+    )
     regenerate = reverse("generated-forms-regenerate", kwargs={"pk": form.pk})
     mark_filed = reverse("generated-forms-mark-filed", kwargs={"pk": form.pk})
     assert api_client_authed.post(regenerate).status_code == 200
     assert api_client_authed.post(mark_filed).status_code == 200
     form.refresh_from_db()
     filed = form.field_values
-    # Spec §6's parts document: a version, the form's own part, then one part per copy.
+    # Spec §6's parts document: a version, the form's own part, then one part per copy, then
+    # one per attached sheet.
     document = json.loads(filed)
     assert (document["version"], [part["kind"] for part in document["parts"]]) == (2, parts)
     _rename_filer(form, "Marisol")  # the filer's later edits
-    rows[5].delete()  # Schedule D would now print five rows, and no copy
+    rows[5].delete()  # Schedule D would now print five rows, and no copy; A/B one sheet row

     response = _download(api_client_authed, form)

     assert response.status_code == 200
     drawn = read_drawn(form_type, response.content, document["parts"])
     assert {(w.copy, w.value) for w in drawn if w.full_name == box} == printed
+    spec = load_schema("schedule_a_b").groups["ab_line_3"].sheet
+    assert [(page.header[0], page.rows) for page in read_sheets(response.content, spec)] == sheets
     form.refresh_from_db()
     assert (form.status, form.field_values) == ("filed", filed)


+def _words(pdf):
+    """Each page's words with their boxes, as MuPDF reads them."""
+    return [page.get_text("words") for page in pymupdf.open("pdf", pdf)]
+
+
+def _ab_group(change):
+    """Change the synthetic Schedule A/B group's declaration."""
+    return lambda d: change(d["groups"]["ab_line_3"])
+
+
+def _rename_the_group(d):
+    d["groups"]["ab_vehicles"] = d["groups"].pop("ab_line_3")
+    for f in d["fields"]:
+        if f["repeat"] == "ab_line_3":
+            f["repeat"] = "ab_vehicles"
+
+
+def _add_a_column(d):
+    columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
+    columns[0]["width"] = 200
+    columns.insert(
+        1, {"label": "Model", "binding": "sofa.creditor_payments[].creditor_name", "width": 100}
+    )
+
+
+def _relabel(sheet):
+    sheet["title"] = "Schedule A/B (renamed)"
+    sheet["columns"][0]["label"] = "Model"
+
+
+@pytest.mark.parametrize(
+    "edit",
+    [
+        _rename_the_group,
+        _add_a_column,
+        _ab_group(lambda g: g["sheet"]["columns"][0].update(width=29)),
+        _ab_group(lambda g: _relabel(g["sheet"])),
+    ],
+    ids=["rename the group", "add a column", "narrow a column", "relabel"],
+)
+def test_a_filed_sheet_prints_what_was_filed_whatever_its_schema_says_later(
+    api_client_authed, generated_form_factory, schedule_a_b_with_sheet, creditor_payments, edit
+):
+    # A sheet part stores the title and columns it was drawn with (R63), so a schema edit
+    # that passes startup changes nothing a filed form prints (spec §6, DIG-155).
+    form = generated_form_factory(status="generated")
+    form.form_type = "schedule_a_b"
+    form.save()
+    creditor_payments(form.session, 6, ["Honda", "Toyota", "Subaru", "Mazda", "Volvo", "Kia"])
+    regenerate = reverse("generated-forms-regenerate", kwargs={"pk": form.pk})
+    mark_filed = reverse("generated-forms-mark-filed", kwargs={"pk": form.pk})
+    assert api_client_authed.post(regenerate).status_code == 200
+    assert api_client_authed.post(mark_filed).status_code == 200
+    filed = _download(api_client_authed, form)
+    path = schedule_a_b_with_sheet / "schedule_a_b.json"
+    schema = json.loads(path.read_text())
+    edit(schema)
+    path.write_text(json.dumps(schema))
+    load_schema.cache_clear()
+    assert validate_form("schedule_a_b") == []
+
+    response = _download(api_client_authed, form)
+
+    assert response.status_code == 200
+    # Every word of every page, where it prints. (The bytes differ: each PDF has its own /ID.)
+    assert _words(response.content) == _words(filed.content)
+
+
 def test_a_form_filed_before_3a2_still_downloads(api_client_authed, generated_form_factory):
     # Filed in the shape stored before 3a2: {full name: value}, with no parts.
     form = generated_form_factory(status="filed")
diff --git a/backend/apps/forms/tests/test_pdf_filler.py b/backend/apps/forms/tests/test_pdf_filler.py
index c419496..22900fd 100644
--- a/backend/apps/forms/tests/test_pdf_filler.py
+++ b/backend/apps/forms/tests/test_pdf_filler.py
@@ -14,6 +14,7 @@ from io import BytesIO
 import pymupdf
 import pypdf
 import pytest
+from pypdf._codecs import adobe_glyphs
 from pypdf._font import Font
 from pypdf.generic import NullObject
 from pypdf.generic._appearance_stream import TextStreamAppearance
@@ -107,6 +108,7 @@ def test_text_is_measured_with_pinned_pypdf_font_internals():
     assert reverse_cmap_for("form_b121.pdf", "/Helv") == reverse_cmap
     assert font.get_text_width(reverse_cmap["W"]) == 944  # Helvetica's W
     assert font.can_encode("é") and not font.can_encode("ą")
+    assert adobe_glyphs["/.notdef"] == "□"  # what printable() leaves out
     bbox = font.font_descriptor.bbox
     assert (bbox[1], bbox[3]) == (-225, 931)  # its line spacing

diff --git a/backend/apps/forms/tests/test_printed_page.py b/backend/apps/forms/tests/test_printed_page.py
index 0d93978..a7e216f 100644
--- a/backend/apps/forms/tests/test_printed_page.py
+++ b/backend/apps/forms/tests/test_printed_page.py
@@ -26,11 +26,12 @@ from pypdf.generic._appearance_stream import TextStreamAppearance

 from apps.districts.models import District
 from apps.forms.registry import build_field_values, get_all_form_types, packet
-from apps.forms.schema import load_schema
+from apps.forms.schema import SheetColumn, SheetSpec, load_schema
 from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong
-from apps.forms.services.text_fit import font_for
+from apps.forms.services.sheets import draw_sheet, plan_sheet
+from apps.forms.services.text_fit import font_for, printable
 from apps.forms.services.widgets import field_of, template_widgets, widget_for
-from apps.forms.tests.pdf_readback import read_drawn
+from apps.forms.tests.pdf_readback import read_drawn, read_sheets
 from apps.intake.management.commands.seed_demo_data import PERSONAS
 from apps.intake.models import IntakeSession

@@ -743,3 +744,78 @@ def test_check_agrees_with_the_drawing_on_every_letter():
                 f"U+{ord(c):04X}" for w, c in as_itself if _pixels(alone, w) != _pixels(empty, w)
             ]
     assert inked == []
+
+
+# ── An attached sheet's letter check agrees with what it prints ───────
+
+_SHEET = SheetSpec(
+    "Official Form 106A/B, Schedule A/B: Property",
+    (SheetColumn("Make", "sofa.creditor_payments[].creditor_name", 300.0),),
+)
+
+
+def _sheet_of(cells):
+    """A sheet part with a row for each cell, numbered from 3.5."""
+    return {
+        "kind": "sheet",
+        "group": "ab_line_3",
+        "title": _SHEET.title,
+        "columns": [{"label": "Make", "width": 300.0}],
+        "name": "Maria Torres",
+        "rows": [{"line": f"3.{n}", "cells": [cell]} for n, cell in enumerate(cells, start=5)],
+    }
+
+
+def _sheet_rows(cells):
+    """What each row's cell of a sheet drawn with those cells reads back as."""
+    pages = read_sheets(draw_sheet(_SHEET, _sheet_of(cells)), _SHEET)
+    return [row[1] for page in pages for row in page.rows]
+
+
+def _cell_ink(cell):
+    """The Make cell of a sheet's one row holding `cell`, rendered."""
+    page = pymupdf.open("pdf", draw_sheet(_SHEET, _sheet_of([cell])))[0]
+    line = page.search_for("3.5")[0]
+    return page.get_pixmap(dpi=288, clip=pymupdf.Rect(90, line.y0, 390, line.y1)).samples
+
+
+def _template_letters():
+    """Every BMP character a template's text font prints (text_fit.printable), in code order."""
+    font = font_for(_template("schedule_a_b"), "/Helv")
+    return [chr(c) for c in range(0x10000) if not 0xD800 <= c <= 0xDFFF and printable(font, chr(c))]
+
+
+def test_the_sheets_letter_check_agrees_with_what_it_prints():
+    # plan_sheet() refuses exactly the letters the sheet can't print as themselves (spec
+    # §5.3, §4.3): one it accepts reads back as it prints, and leaves ink alone in its
+    # cell; one it refuses, drawn without the check, reads back as something else or
+    # leaves no ink. The sheet prints in the templates' encoding (R62), so every letter a
+    # template's text font prints is drawn, those at codes other than WinAnsi's among
+    # them, and so is □, which a template's /.notdef reads as.
+    letters = _template_letters()
+    accepted, refused = [], []
+    for letter in dict.fromkeys([*_LETTERS, *letters, "□"]):
+        try:
+            plan_sheet("schedule_a_b", _SHEET, _sheet_of([f"x{letter}x"]))
+            accepted.append(letter)
+        except UnprintableLetter:
+            refused.append(letter)
+    # Of the font's letters, the sheet refuses only control characters, as check() does.
+    assert [f"U+{ord(c):04X}" for c in letters if c in refused and c.isprintable()] == []
+    assert "□" in refused
+    invisible = [c for c in refused if c == "\t" or unicodedata.category(c) in ("Zs", "Cf")]
+    assert [f"U+{ord(c):04X}" for c in invisible] == []
+
+    printed = _sheet_rows([f"x{c}x" for c in accepted])
+    assert {
+        f"U+{ord(c):04X}": p for c, p in zip(accepted, printed, strict=True) if p != _as_printed(c)
+    } == {}
+    glyphs = [c for c in accepted if _as_printed(c) == f"x{c}x" and not c.isspace()]
+    with _no_anti_aliasing():
+        empty = _cell_ink("")
+        assert [f"U+{ord(c):04X}" for c in glyphs if _cell_ink(c) == empty] == []
+
+    printed = _sheet_rows([f"x{c}x" for c in refused])
+    as_itself = [c for c, p in zip(refused, printed, strict=True) if p == f"x{c}x"]
+    with _no_anti_aliasing():
+        assert [f"U+{ord(c):04X}" for c in as_itself if _cell_ink(c) != empty] == []
PATCH
```

- `conftest.py`: `_with_group` replaces `_schedule_d_with_group`, the A/B and D sheet fixtures, and `creditor_payments(session, count, names=None)`.
- `pdf_readback.py` is the oracle, so it changes with the tests: `read_drawn` leaves sheet pages to the new `read_sheets` and refuses a PDF whose pages its parts don't explain. It imports `LINE_WIDTH` and `MARGIN` from `sheets.py`, which Step 5 adds.
- `test_api_readback.py`: `_comparable_document` leaves a part without values as it is.
- `test_check.py`: □ is refused like ą.
- `test_checks.py`: the sheet group passes, a sheet group isn't counted as a second extra-page group, and each sheet rule has a case it refuses, with the exact message (18 cases). Two Task 6 cases take the new "names neither" message.
- `test_download_action.py`: a filed form with a sheet downloads what was filed, and a filed sheet draws its own title and columns after four schema edits.
- `test_pdf_filler.py`: pins `adobe_glyphs["/.notdef"] == "□"`.
- `test_printed_page.py`: the sheet's letter check agrees with what it prints, over Task 4's `_LETTERS`, every letter the template's `/Helv` prints, and □.

- [ ] **Step 2: Run the tests and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE --continue-on-collection-errors apps/forms/tests/test_attached_sheets.py apps/forms/tests/test_download_action.py apps/forms/tests/test_printed_page.py apps/forms/tests/test_pdf_filler.py apps/forms/tests/test_check.py apps/forms/tests/test_checks.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `23 failed, 119 passed` and `4 errors in`, with `ERROR apps/forms/tests/test_attached_sheets.py`, `test_a_letter_the_form_cannot_print_is_refused[Nowak\u25a1-\u25a1] - Failed: DID NOT RAISE`, `test_a_group_continued_on_an_attached_sheet_passes - assert [('forms.E007... extra_page')] == []` and `test_a_sheet_that_cannot_print_its_rows_whole_is_reported[an extra page too] - assert [] == [('forms.E007...and a sheet')]`.

`--continue-on-collection-errors` runs `test_check.py` and `test_checks.py` while four modules can't be imported: `test_attached_sheets.py`, `test_download_action.py`, `test_printed_page.py` and `test_pdf_filler.py` import `pdf_readback.py`, which needs `sheets.py`. Steps 6 and 10 show their own failures. (A node id in a module that can't be imported stops the whole run, so this step names `test_printed_page.py` whole.)

- `test_check.py`: □ isn't refused, since the font says it encodes it.
- `test_checks.py`: all 22 of its new or changed items fail. The parent knows no `sheet`, so the synthetic A/B group "names no extra_page", and a group with both declarations passes as an extra-page group. Two Task 6 cases expect the new message.
- The 119 that pass are `test_check.py`'s other 38 and `test_checks.py`'s other 81.

- [ ] **Step 3: Refuse □ in the forms' letter check**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/text_fit.py b/backend/apps/forms/services/text_fit.py
index d101be8..d5d4c19 100644
--- a/backend/apps/forms/services/text_fit.py
+++ b/backend/apps/forms/services/text_fit.py
@@ -17,7 +17,8 @@ from pathlib import Path
 import pypdf
 from django.conf import settings

-# pypdf internal, pinned with pypdf==6.13.1; test_pdf_filler.py fails if it moves.
+# pypdf internals, pinned with pypdf==6.13.1; test_pdf_filler.py fails if they move.
+from pypdf._codecs import adobe_glyphs
 from pypdf._font import Font

 from apps.forms.services.widgets import TemplateWidget
@@ -45,8 +46,12 @@ def reverse_cmap_for(template_filename: str, font_name: str) -> dict[str, str]:


 def printable(font: Font, letter: str) -> bool:
-    """The font's encoding has the letter: pypdf draws it, not "?" or another glyph (R7)."""
-    return font.can_encode(letter)
+    """
+    The font's encoding has the letter: pypdf draws it, not "?" or another glyph (R7). pypdf
+    reads the glyph /.notdef as "□", which no font draws: a template's /Helv has it at 173,
+    which prints a soft hyphen's code, so □ isn't printable.
+    """
+    return font.can_encode(letter) and letter != adobe_glyphs["/.notdef"]


 def _escaped(text: str) -> str:
PATCH
```

pypdf reads a template's `/.notdef` as □, so `can_encode` said the font prints it, and a form drew code 173, a soft hyphen. `printable` now leaves it out. Every letter check goes through `printable`, the forms' now and the sheet's from Step 5.

- [ ] **Step 4: Run the letter tests**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_check.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `39 passed`.

That is all of `test_check.py`, the □ case among them.

- [ ] **Step 5: Declare a group's sheet, and the module that measures and draws it**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -80,10 +80,28 @@


 @dataclass(frozen=True)
+class SheetColumn:
+    """One column of an attached sheet: its label, the list binding its cells print, its width."""
+
+    label: str
+    binding: str  # "sofa.<collection>[].<attr>"
+    width: float  # points
+
+
+@dataclass(frozen=True)
+class SheetSpec:
+    """An attached sheet (3a2 spec §5.3): the form's title, and the columns of the group's row."""
+
+    title: str
+    columns: tuple[SheetColumn, ...]
+
+
+@dataclass(frozen=True)
 class GroupSpec:
     """
-    A repeat group's declaration (3a2 spec §5.2): the template page whose copies take the
-    rows past its last slot, and the boxes that number the rows and the pages.
+    A repeat group's declaration (3a2 spec §5.2, §5.3): the template page whose copies take
+    the rows past its last slot, or the attached sheet that takes them, and the boxes that
+    number the rows and the pages.
     """

     name: str
@@ -91,6 +109,7 @@
     number: str | None  # the entry number, such as "2.{n}", n the row's position in the group
     number_boxes: dict[int, str]  # slot row → the key of that slot's entry-number box
     page_numbers: tuple[PageNumberBoxes, ...]
+    sheet: SheetSpec | None = None


 @dataclass(frozen=True)
@@ -144,6 +163,7 @@
                 PageNumberBoxes(page=boxes["page"], this=boxes.get("this"), of=boxes.get("of"))
                 for boxes in group.get("page_numbers", [])
             ),
+            sheet=_sheet(group["sheet"]) if "sheet" in group else None,
         )
         for name, group in raw.get("groups", {}).items()
     }
@@ -154,6 +174,17 @@
         template_version=raw["template_version"],
         fields=fields,
         groups=groups,
+    )
+
+
+def _sheet(sheet: dict) -> SheetSpec:
+    """A group's "sheet": {"title": str, "columns": [{"label", "binding", "width"}]}."""
+    return SheetSpec(
+        title=sheet["title"],
+        columns=tuple(
+            SheetColumn(label=c["label"], binding=c["binding"], width=float(c["width"]))
+            for c in sheet["columns"]
+        ),
     )


PATCH
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -21,7 +21,9 @@

 import re
 import unicodedata
+from collections.abc import Callable
 from dataclasses import dataclass
+from functools import partial
 from io import BytesIO
 from pathlib import Path

@@ -29,9 +31,8 @@
 import pypdf
 from django.conf import settings

-# pypdf._font and pypdf.generic._appearance_stream are pypdf internals, pinned with
-# pypdf==6.13.1; test_pdf_filler.py fails if they move.
-from pypdf._font import Font
+# pypdf.generic._appearance_stream is a pypdf internal, pinned with pypdf==6.13.1;
+# test_pdf_filler.py fails if it moves.
 from pypdf.generic import (
     ArrayObject,
     DictionaryObject,
@@ -174,16 +175,17 @@
     )


-def _refused_letter(widget: TemplateWidget, font: Font, text: str) -> str | None:
-    """
-    The first character the box can't print: one its font can't encode, a control
-    character, or in a comb box ( ) or \\. Line breaks aren't letters (G15).
+def _refused_letter(text: str, prints: Callable[[str], bool], comb: bool = False) -> str | None:
+    """
+    The first character a box can't print: one its font can't encode (`prints` says which
+    it can), a control character, or in a comb box ( ) or \\. Line breaks aren't letters
+    (G15). An attached sheet's cells are checked the same way (apps.forms.services.sheets).
     """
     for letter in "".join(text.splitlines()):
         if (
-            not printable(font, letter)
+            not prints(letter)
             or unicodedata.category(letter) == "Cc"
-            or (widget.comb and letter in _COMB_BREAKERS)
+            or (comb and letter in _COMB_BREAKERS)
         ):
             return letter
     return None
@@ -385,7 +387,7 @@
                 raise InvalidFieldValue(form_type, widget.full_name)
             font = font_for(schema.template_filename, widget.font)
             text = _as_printed(value)
-            letter = _refused_letter(widget, font, text)
+            letter = _refused_letter(text, partial(printable, font), widget.comb)
             if letter is not None:
                 raise UnprintableLetter(form_type, letter, *_source(schema, key, widget))
             fitted = fit(widget, schema.template_filename, text)
PATCH
```

```python file=backend/apps/forms/services/sheets.py
"""
Attached sheets (3a2 spec §5.3): the rows past a repeat group's last slot, when the form has
no page to copy, on plain US Letter pages that PDFFormFiller.fill() appends after the
form's pages and copies.

Every page of a sheet starts with its header: the filer's name, the form's title followed
by " (attached sheet)", and "Case number (if known)" with a blank line. Then come the
column labels and the rows: each row's line, the form line it continues, then its cells
under the group's columns, in Helvetica at 10 pt. A cell's text wraps at its spaces, a row
never splits across pages, and the sheet runs to as many pages as its rows need.

The sheet prints in the templates' own text font (R62): the base-14 Helvetica, with the
/Encoding every template's /Helv has. PyMuPDF draws "helv" in WinAnsiEncoding, so
draw_sheet() writes each letter's code in the templates' encoding and gives every page's
font that /Encoding. The sheet so prints exactly the forms' letters, and plan_sheet()
refuses a letter with the forms' own check, text_fit.printable() on the form's /Helv.

plan_sheet() measures the text with PyMuPDF's Font, without drawing: Generate runs it
through check(). draw_sheet() draws, at Download.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import pymupdf

# pypdf internal, pinned with pypdf==6.13.1 as in text_fit; test_pdf_filler.py fails if it moves.
from pypdf._font import Font
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject

from apps.forms.schema import FormSchema, SheetColumn, SheetSpec, load_schema
from apps.forms.services.derivations import RULE_FIXES
from apps.forms.services.fill_resolver import fix_for
from apps.forms.services.pdf_filler import (
    UnprintableLetter,
    ValueTooLong,
    _as_printed,
    _refused_letter,
)
from apps.forms.services.text_fit import font_for, printable

PAGE = (612.0, 792.0)  # US Letter
MARGIN = 54.0  # 0.75 in on every side
WIDTH = PAGE[0] - 2 * MARGIN  # 504 pt, 7.0 in
LINE_WIDTH = 36.0  # the line column, "3.5"
PAD = 2.0  # a cell's text keeps this far from each side of its column
SIZE = 10.0
_HELVETICA = pymupdf.Font("helv")  # the font insert_text draws "helv" in: its metrics
# A line of text is PyMuPDF's own Helvetica line, ascender to descender (13.74 pt), so
# every character's box lies inside its line, and its baseline is the ascender below its top.
LEADING = (_HELVETICA.ascender - _HELVETICA.descender) * SIZE
_BASELINE = _HELVETICA.ascender * SIZE
_ROW_GAP = 6.0
_BLANK = 180.0  # the line to write the case number on, 2.5 in
_CASE_NUMBER = "Case number (if known)"
_TEXT_FONT = "/Helv"  # the templates' text font, in their /AcroForm /DR

# The /Differences of every template's /Helv /Encoding, which all 17 share
# (test_attached_sheets.py pins it): Helvetica's own encoding, with PDFDocEncoding's
# letters from 128 up, Ł, ł and ı among them, and nothing at 173 (/.notdef).
_DIFFERENCES = (
    "24 /breve /caron /circumflex /dotaccent /hungarumlaut /ogonek /ring /tilde 39 "
    "/quotesingle 96 /grave 128 /bullet /dagger /daggerdbl /ellipsis /emdash "
    "/endash /florin /fraction /guilsinglleft /guilsinglright /minus /perthousand "
    "/quotedblbase /quotedblleft /quotedblright /quoteleft /quoteright "
    "/quotesinglbase /trademark /fi /fl /Lslash /OE /Scaron /Ydieresis /Zcaron "
    "/dotlessi /lslash /oe /scaron /zcaron 160 /Euro 164 /currency 166 /brokenbar "
    "168 /dieresis /copyright /ordfeminine 172 /logicalnot /.notdef /registered "
    "/macron /degree /plusminus /twosuperior /threesuperior /acute /mu 183 "
    "/periodcentered /cedilla /onesuperior /ordmasculine 188 /onequarter /onehalf "
    "/threequarters 192 /Agrave /Aacute /Acircumflex /Atilde /Adieresis /Aring /AE "
    "/Ccedilla /Egrave /Eacute /Ecircumflex /Edieresis /Igrave /Iacute /Icircumflex "
    "/Idieresis /Eth /Ntilde /Ograve /Oacute /Ocircumflex /Otilde /Odieresis "
    "/multiply /Oslash /Ugrave /Uacute /Ucircumflex /Udieresis /Yacute /Thorn "
    "/germandbls /agrave /aacute /acircumflex /atilde /adieresis /aring /ae "
    "/ccedilla /egrave /eacute /ecircumflex /edieresis /igrave /iacute /icircumflex "
    "/idieresis /eth /ntilde /ograve /oacute /ocircumflex /otilde /odieresis "
    "/divide /oslash /ugrave /uacute /ucircumflex /udieresis /yacute /thorn "
    "/ydieresis"
)
_ENCODING = f"<</Type/Encoding/Differences[{_DIFFERENCES}]>>"


def _font() -> Font:
    """The sheet's font as pypdf builds a template's /Helv: Helvetica with _DIFFERENCES."""
    differences = ArrayObject(
        NumberObject(token) if token.isdigit() else NameObject(token)
        for token in _DIFFERENCES.split()
    )
    encoding = {
        NameObject("/Type"): NameObject("/Encoding"),
        NameObject("/Differences"): differences,
    }
    return Font.from_font_resource(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): DictionaryObject(encoding),
            }
        )
    )


# Each letter → its code in that encoding, as a character, the way pypdf encodes a form's.
_CODES, _ = _font()._get_typographic_maps()


def _prints(template: str) -> Callable[[str], bool]:
    """The forms' own letter check, for the form's template (R62)."""
    return partial(printable, font_for(template, _TEXT_FONT))


def _encoded(line: str) -> str:
    """
    The line as insert_text() writes it: one byte per letter, its code in the templates'
    encoding. A letter plan_sheet() refuses prints as "?", as pypdf prints one on a form.
    """
    return "".join(_CODES.get(letter, "?") for letter in line)


def inner_width(width: float) -> float:
    """The width a column's text takes: the column's, less its padding on each side."""
    return width - 2 * PAD


def _lines(text: str, width: float) -> list[str] | None:
    """
    The text as printed (pdf_filler._as_printed), broken at its line breaks, then at spaces
    into lines no wider than width at 10 pt, each taking as many words as fit. Spaces are
    kept as typed, except one at each break. None when a word is wider than width.
    """
    lines = []
    for paragraph in _as_printed(text).splitlines() or [""]:
        line = None
        for word in paragraph.split(" "):
            if _HELVETICA.text_length(word, SIZE) > width:
                return None
            joined = word if line is None else f"{line} {word}"
            if line is None or _HELVETICA.text_length(joined, SIZE) <= width:
                line = joined
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def prints_whole(text: str, width: float, template: str) -> bool:
    """
    Whether the sheet of a form with that template prints every letter of the text, and no
    word of it is wider than width.
    """
    letter = _refused_letter(_as_printed(text), _prints(template))
    return letter is None and _lines(text, width) is not None


def fits_line_column(line: str, template: str) -> bool:
    """Whether a row's line, the group's number for it, prints whole on one line of its column."""
    width = inner_width(LINE_WIDTH)
    return prints_whole(line, width, template) and len(_lines(line, width)) == 1


def sheet_spec(part: dict) -> SheetSpec:
    """
    The sheet a sheet part prints: the title and the columns' labels and widths it stores
    (R63), so a filed sheet draws as it was filed, whatever its schema says later. Its
    columns carry no binding: the part holds their cells.
    """
    return SheetSpec(
        part["title"],
        tuple(SheetColumn(column["label"], "", column["width"]) for column in part["columns"]),
    )


def _header(spec: SheetSpec, name: str) -> list[str]:
    """The lines that start every page of the sheet, the case number's last."""
    return [
        *_lines(name, WIDTH),
        *_lines(f"{spec.title} (attached sheet)", WIDTH),
        _CASE_NUMBER,
    ]


def _labels(spec: SheetSpec) -> list[list[str]]:
    """Each column's label, as the lines it prints in its column."""
    return [_lines(column.label, inner_width(column.width)) for column in spec.columns]


def _rows_top(spec: SheetSpec, header: list[str]) -> float:
    """Where a page's first row starts: below the header, a blank line and the labels."""
    labels = max((len(lines) for lines in _labels(spec)), default=0)
    return MARGIN + (len(header) + 1 + labels) * LEADING + _ROW_GAP


def _room(spec: SheetSpec, header: list[str]) -> float:
    """The height a page of the sheet has for its rows: from the first row to the margin."""
    return PAGE[1] - MARGIN - _rows_top(spec, header)


def _cells(spec: SheetSpec, row: dict) -> list[list[str]]:
    """A row's cells as the lines each prints: its line first, in the line column."""
    widths = [LINE_WIDTH, *(column.width for column in spec.columns)]
    return [
        _lines(text, inner_width(width))
        for text, width in zip([row["line"], *row["cells"]], widths, strict=True)
    ]


def _height(cells: list[list[str]]) -> float:
    return max(len(lines) for lines in cells) * LEADING


def _check(
    form_type: str, template: str, text: str, width: float, label: str, fix: dict[str, str]
) -> list[str]:
    """The text's lines in width, or check()'s refusal for a box with the label and fix."""
    letter = _refused_letter(_as_printed(text), _prints(template))
    if letter is not None:
        raise UnprintableLetter(form_type, letter, label, fix)
    lines = _lines(text, width)
    if lines is None:
        raise ValueTooLong(form_type, label, fix)
    return lines


def _fixes(schema: FormSchema, group: str, spec: SheetSpec) -> list[dict[str, str]]:
    """
    Where the filer changes each column's cells (3a2 spec §4.5): the fix of the group's slot
    that binds what the schema's column of that label prints (fill_resolver.fix_for). A
    column the schema no longer declares, as a filed sheet's may be (R63), has none: a
    filed form's refusal shows none anyway.
    """
    declared = schema.groups.get(group)
    sheet = declared.sheet if declared is not None else None
    bindings = {column.label: column.binding for column in sheet.columns} if sheet else {}
    fixes = []
    for column in spec.columns:
        binding = bindings.get(column.label)
        slot = next((f for f in schema.fields if f.repeat == group and f.binding == binding), None)
        fixes.append(fix_for(slot) if binding and slot else {})
    return fixes


def plan_sheet(form_type: str, spec: SheetSpec, part: dict) -> None:
    """
    Check that a sheet part prints whole, without drawing (as check() does for a form).

    Raises:
        UnprintableLetter: a letter the sheet can't print, which the form's own boxes can't
            either (R62): in a cell, named by its column's label, fixed where its slots'
            binding is changed; or in the filer's name, named as the form's own name box,
            fixed where the filer's name is entered (R23).
        ValueTooLong: a word wider than its cell, or a row taller than a page, named by the
            column with the most lines.
        ValueError: a row's line that doesn't print whole on one line of the line column
            (the group's number pattern; forms.E007 checks the first).
    """
    schema = load_schema(form_type)
    template = schema.template_filename
    name_label = next(
        (f.label for f in schema.fields if f.source == "derived" and f.rule == "full_name"),
        f"{spec.title} (attached sheet)",
    )
    _check(form_type, template, part["name"], WIDTH, name_label, dict(RULE_FIXES["full_name"]))
    header = _header(spec, part["name"])
    fixes = _fixes(schema, part["group"], spec)
    for row in part["rows"]:
        if not fits_line_column(row["line"], template):
            raise ValueError(f"{form_type}: line {row['line']!r} doesn't fit the line column")
        cells = [
            _check(form_type, template, cell, inner_width(column.width), column.label, fix)
            for column, cell, fix in zip(spec.columns, row["cells"], fixes, strict=True)
        ]
        if _height([[row["line"]], *cells]) > _room(spec, header):
            heights = [len(lines) for lines in cells]
            tallest = heights.index(max(heights))
            raise ValueTooLong(form_type, spec.columns[tallest].label, fixes[tallest])


def _text(page: pymupdf.Page, x: float, top: float, lines: list[str]) -> None:
    """Draw lines of text from (x, top) down, one line height each."""
    for n, line in enumerate(lines):
        if not line:
            continue  # nothing to print, and PyMuPDF logs a traceback for an empty line
        # A list, so insert_text never splits the line at a byte it reads as a line break
        # (– is the templates' 0x85, NEL).
        page.insert_text(
            (x, top + n * LEADING + _BASELINE), [_encoded(line)], fontname="helv", fontsize=SIZE
        )


def _new_page(document: pymupdf.Document, spec: SheetSpec, header: list[str]) -> pymupdf.Page:
    """A sheet page with its header and column labels drawn."""
    page = document.new_page(width=PAGE[0], height=PAGE[1])
    _text(page, MARGIN, MARGIN, header)
    case_number = MARGIN + (len(header) - 1) * LEADING + _BASELINE + 1.5
    start = MARGIN + _HELVETICA.text_length(_CASE_NUMBER, SIZE) + 4
    page.draw_line((start, case_number), (start + _BLANK, case_number), width=0.5)
    top = MARGIN + (len(header) + 1) * LEADING
    x = MARGIN + LINE_WIDTH
    for column, lines in zip(spec.columns, _labels(spec), strict=True):
        _text(page, x + PAD, top, lines)
        x += column.width
    rule = _rows_top(spec, header) - _ROW_GAP / 2
    page.draw_line((MARGIN, rule), (MARGIN + WIDTH, rule), width=0.5)
    return page


def draw_sheet(spec: SheetSpec, part: dict) -> bytes:
    """
    Draw a sheet part, as plan_sheet() passed it, on as many US Letter pages as its rows
    need, and return the PDF.
    """
    document = pymupdf.open()
    header = _header(spec, part["name"])
    page, used = None, 0.0  # the height the page's rows take so far
    for row in part["rows"]:
        cells = _cells(spec, row)
        if page is None or used + _height(cells) > _room(spec, header):
            page, used = _new_page(document, spec, header), 0.0
            if _height(cells) > _room(spec, header):
                raise ValueError("a row taller than a page reached the drawing unchecked")
        x = MARGIN
        for lines, width in zip(cells, [LINE_WIDTH, *(c.width for c in spec.columns)], strict=True):
            _text(page, x + PAD, _rows_top(spec, header) + used, lines)
            x += width
        used += _height(cells) + _ROW_GAP
    # The templates' encoding, for the codes _encoded() wrote, on every page's Helvetica.
    for page in document:
        for xref, *_ in page.get_fonts():
            document.xref_set_key(xref, "Encoding", _ENCODING)
    return document.tobytes()
```

- `schema.py` gains `SheetColumn` and `SheetSpec`, and `GroupSpec.sheet`, read from a group's `"sheet"`. Startup still knows only `extra_page`; Step 7 adds the sheet's rules.
- `pdf_filler.py`'s `_refused_letter` takes what the font prints as a function and comb as a flag, so the sheet can use `check()`'s own letter handling. `_plan` passes `partial(printable, font)` and `widget.comb`. The `Font` import goes with the old signature.
- `sheets.py` is new:

  - `plan_sheet` checks a sheet part without drawing: the name, each row's line against the line column, each cell's letters and words, and each row's height against a page's room;
  - `draw_sheet` draws it with PyMuPDF, in the templates' encoding;
  - `sheet_spec` builds the sheet from the part;
  - `prints_whole` and `fits_line_column` are what startup uses in Step 7.
    It imports `schema` and `pdf_filler` at the top, so `schema.py` and `pdf_filler.py` import it inside the functions that use it.

- [ ] **Step 6: Watch the startup and sheet tests fail**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_checks.py apps/forms/tests/test_attached_sheets.py apps/forms/tests/test_download_action.py apps/forms/tests/test_printed_page.py::test_the_sheets_letter_check_agrees_with_what_it_prints -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `40 failed, 102 passed`, with `test_extra_rows_print_on_an_attached_sheet - ValueError: schedule_a_b: group 'ab_line_3' names no extra page`, `test_a_row_as_tall_as_a_page_prints_and_a_taller_one_is_refused - ValueError: schedule_a_b: no part of kind 'sheet'`, `test_a_filed_sheet_prints_what_was_filed_whatever_its_schema_says_later[relabel] - assert 500 == 200` and `test_a_group_continued_on_an_attached_sheet_passes - assert [('forms.E007... extra_page')] == []`.

The modules import now.

- Startup still refuses the synthetic group as naming no extra page, so the 22 `test_checks.py` items fail as in Step 2.
- `resolve_parts` still raises for rows past the last slot of a group with no `extra_page`. So 12 of `test_attached_sheets.py`'s 17 items fail, and so do the five filed-sheet downloads, as 500s.
- The test of a row 44 lines tall builds its own sheet part, and `check()` refuses a part of kind `sheet`.

The 102 that pass are `test_checks.py`'s other 81, `test_download_action.py`'s other 16, the letter agreement test and four of `test_attached_sheets.py`:

- the name guard, the encoding pin and the tallest-cell refusal call `sheets.py` directly;
- the totals case on copies needs only Task 6.

Steps 13 to 16 and 19 show each of these five red.

- [ ] **Step 7: Refuse at startup a sheet that can't print its rows whole**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -9,6 +9,7 @@

 import hashlib
 import json
+import re
 from dataclasses import dataclass, field
 from functools import lru_cache
 from io import BytesIO
@@ -400,8 +401,54 @@
         pages = {f.page for f in paged}
         if group is None:
             errors.append(("E007", f"repeat group {name!r} isn't declared in groups"))
+        elif group.extra_page is not None and group.sheet is not None:
+            errors.append(("E007", f"group {name!r} names both an extra_page and a sheet"))
+        elif group.sheet is not None:
+            # The rows a sheet prints are the slots' rows: a column of another list would
+            # print rows that aren't the group's, or leave some of them out. A cell prints
+            # its slot's text, and a box's answer is a state, which a sheet can't tick.
+            for column in group.sheet.columns:
+                bound = [f for f in mapped if f.binding == column.binding]
+                if not bound:
+                    errors.append(
+                        (
+                            "E007",
+                            f"group {name!r}: sheet column {column.label!r} binds "
+                            f"{column.binding!r}, which no slot of the group binds",
+                        )
+                    )
+                elif any(f.type in ("checkbox", "radio") for f in bound):
+                    errors.append(
+                        (
+                            "E007",
+                            f"group {name!r}: sheet column {column.label!r} binds a box's "
+                            "answer, which a sheet can't tick",
+                        )
+                    )
+            # And every slot's value prints in a column, or the rows past the slots would
+            # drop it: a text or combo slot needs a column of its binding, and a box slot
+            # can't continue at all. (A sheet with no columns is reported as such below.)
+            columns = {column.binding for column in group.sheet.columns}
+            unprinted = {f.binding for f in mapped if f.binding} - columns if columns else set()
+            for binding in sorted(unprinted):
+                if any(f.type in ("checkbox", "radio") for f in mapped if f.binding == binding):
+                    errors.append(
+                        (
+                            "E007",
+                            f"group {name!r}: a box slot binds {binding!r}, and a sheet "
+                            "can't tick a box",
+                        )
+                    )
+                else:
+                    errors.append(
+                        (
+                            "E007",
+                            f"group {name!r}: no sheet column prints {binding!r}, "
+                            "which a slot of the group binds",
+                        )
+                    )
         elif group.extra_page is None:
-            errors.append(("E007", f"group {name!r} names no extra_page"))
+            errors.append(("E007", f"group {name!r} names neither an extra_page nor a sheet"))
         elif group.extra_page not in pages:
             errors.append(
                 ("E007", f"group {name!r}: extra_page {group.extra_page} holds none of its slots")
@@ -428,7 +475,11 @@
             )
         )
     for name, group in schema.groups.items():
-        if (group.number is not None or group.number_boxes) and "{n}" not in (group.number or ""):
+        if group.sheet is not None:
+            errors += _sheet_errors(name, group, schema.template_filename)
+        # A sheet labels each row with the line it continues, its number.
+        numbered_rows = group.number is not None or group.number_boxes or group.sheet is not None
+        if numbered_rows and "{n}" not in (group.number or ""):
             errors.append(("E007", f"group {name!r}: number must contain {{n}}"))
         elif group.number is not None:
             try:
@@ -444,6 +495,22 @@
                             "for every row",
                         )
                     )
+                elif group.sheet is not None:
+                    # The sheet's first row is the one past the slots: its line must print
+                    # whole in the line column, or every Generate with a sheet would fail.
+                    from apps.forms.services.sheets import LINE_WIDTH, fits_line_column
+
+                    capacities = {f.repeat_capacity for f in slots.get(name, [])}
+                    if len(capacities) == 1 and (capacity := capacities.pop()):
+                        line = group.number.format(n=capacity + 1)
+                        if not fits_line_column(line, schema.template_filename):
+                            errors.append(
+                                (
+                                    "E007",
+                                    f"group {name!r}: its sheet can't print its first line, "
+                                    f"{line!r}, whole in the {LINE_WIDTH:g} pt line column",
+                                )
+                            )
         if widget_map is None:
             continue
         # A row is on its mapped boxes' page: an unmapped box prints nothing, wherever it is.
@@ -476,6 +543,70 @@
                         f"{_pages_drawn(key, drawn)}, so it needs a tag",
                     )
                 )
+    return errors
+
+
+_LIST_BINDING = re.compile(r"sofa\.\w+\[\]\.\w+")
+
+
+def _sheet_errors(name: str, group: GroupSpec, template: str) -> list[tuple[str, str]]:
+    """
+    What keeps a group's attached sheet from printing every row whole (3a2 spec §5.3): its
+    columns must fit the 7 in between the sheet's margins beside the line column, each
+    print a list's rows, and each label, like the title, print whole in its width, in the
+    letters the form's template prints.
+    """
+    from apps.forms.services.sheets import (  # here: it imports this module
+        LINE_WIDTH,
+        WIDTH,
+        inner_width,
+        prints_whole,
+    )
+
+    sheet = group.sheet
+    errors = []
+    # Page numbers are filled when a group has copies (R21), and a sheet group has none.
+    if group.page_numbers:
+        errors.append(
+            ("E007", f"group {name!r}: a sheet group has no copies, so it numbers no pages")
+        )
+    if not sheet.columns:
+        errors.append(("E007", f"group {name!r}: its sheet has no columns for its rows"))
+    total = LINE_WIDTH + sum(c.width for c in sheet.columns)
+    if total > WIDTH:
+        errors.append(
+            (
+                "E007",
+                f"group {name!r}: its sheet's columns and line column are {total:g} pt wide, "
+                f"more than the {WIDTH:g} pt (7 in) between its margins",
+            )
+        )
+    if not prints_whole(f"{sheet.title} (attached sheet)", WIDTH, template):
+        errors.append(("E007", f"group {name!r}: its sheet can't print its title whole"))
+    # A label names one column, to the filer and to a refusal's fix (sheets._fixes).
+    labels = [column.label for column in sheet.columns]
+    for label in sorted({label for label in labels if labels.count(label) > 1}):
+        errors.append(
+            ("E007", f"group {name!r}: its sheet has more than one column labelled {label!r}")
+        )
+    for column in sheet.columns:
+        if not _LIST_BINDING.fullmatch(column.binding):
+            errors.append(
+                (
+                    "E007",
+                    f"group {name!r}: sheet column {column.label!r} binds {column.binding!r}, "
+                    "not a sofa.<collection>[].<attr> list",
+                )
+            )
+        width = inner_width(column.width)
+        if width <= 0 or not prints_whole(column.label, width, template):
+            errors.append(
+                (
+                    "E007",
+                    f"group {name!r}: sheet column {column.label!r} can't print its label "
+                    f"whole in {column.width:g} pt",
+                )
+            )
     return errors


PATCH
```

`validate_schema` now refuses a group with both an `extra_page` and a `sheet`, or neither, and checks a sheet group's columns against its slots (per group, beside Task 6's rules). Then, for each group, `_sheet_errors` checks the sheet itself: page numbers, columns, widths, list bindings, unique labels, and a title and labels that print whole. A sheet group needs a `number` with `{n}`, and its first sheet line must fit the line column. `sheets` is imported inside the functions, since it imports this module.

- [ ] **Step 8: Run the startup tests**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_checks.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `103 passed`.

That includes `test_every_registered_form_passes`: all 17 production schemas pass the sheet rules.

- [ ] **Step 9: Put the rows past a sheet group's slots in a sheet part**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/fill_resolver.py b/backend/apps/forms/services/fill_resolver.py
index 10bad0f..09c5ea2 100644
--- a/backend/apps/forms/services/fill_resolver.py
+++ b/backend/apps/forms/services/fill_resolver.py
@@ -5,7 +5,8 @@ binding with a tag, {"<pdf_field>@<page>:<tag>": str}.
 Source priority is encoded per-field in the schema (constant/derived/asked/
 ingested/signature). This module resolves ``binding`` references; resolve_parts()
 orchestrates dispatch, conditional sections, and repeat groups, whose rows past the
-last slot continue on copies of an extra page, and resolve() returns its form part.
+last slot continue on copies of an extra page or on an attached sheet, and resolve()
+returns its form part.
 """

 from __future__ import annotations
@@ -253,6 +254,45 @@ def _copies(
     return copies


+def _sheet(
+    group: GroupSpec,
+    fields: list[FieldSpec],
+    printed: list[FieldSpec],
+    columns: dict[str, str | list[str]],
+    capacity: int,
+    actual: int,
+    session: IntakeSession,
+    ingested_cache: dict,
+) -> dict:
+    """
+    The attached sheet that prints the group's rows past `capacity` (spec §5.3): each row
+    labelled with its line, the group's number for its position, and a cell per column,
+    the column's binding for that row as the group's slot of that binding prints it. A
+    column whose slots the UPL guard keeps blank is blank, as on the form and its copies.
+    The sheet carries the filer's name for its header (R23), and its title and its columns'
+    labels and widths (R63), so a filed sheet redraws as it was filed.
+    """
+    rows = []
+    for position in range(capacity + 1, actual + 1):
+        cells = []
+        for column in group.sheet.columns:
+            slots = [f for f in fields if f.binding == column.binding]  # one at least: E007
+            emitted = None
+            if all(f in printed for f in slots):
+                emitted = _cell(slots[0], position, columns, session, ingested_cache)
+            cells.append(emitted or "")
+        rows.append({"line": group.number.format(n=position), "cells": cells})
+    name = DERIVATIONS["full_name"](session)
+    return {
+        "kind": "sheet",
+        "group": group.name,
+        "title": group.sheet.title,
+        "columns": [{"label": c.label, "width": c.width} for c in group.sheet.columns],
+        "name": name,
+        "rows": rows,
+    }
+
+
 def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
     """The values the form's own pages print: resolve_parts()'s form part."""
     return resolve_parts(schema, session)["parts"][0]["values"]
@@ -261,11 +301,15 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
 def resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
     """
     The form's values as the parts it prints, in printing order (spec §6):
-    {"version": 2, "parts": [{"kind": "form", "values": {key: value}}, *copies]}.
+    {"version": 2, "parts": [{"kind": "form", "values": {key: value}}, *copies, *sheets]}.

     A repeat group fills its slots in row order. Rows past its last slot continue on
     copies of the extra page its declaration names (spec §5.2), each
-    {"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}}.
+    {"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}},
+    or on the attached sheet it declares (spec §5.3, R23, R63), one part for all of them:
+    {"kind": "sheet", "group": <group>, "title": <its title>,
+    "columns": [{"label": str, "width": <points>}], "name": <the filer's full name>,
+    "rows": [{"line": "3.5", "cells": [<one per column>]}]}.
     """
     out: dict[str, str] = {}

@@ -308,6 +352,7 @@ def resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
             groups.setdefault(f.repeat, []).append(f)

     copies: list[dict] = []
+    sheets: list[dict] = []
     overflowing = []
     for group_name, fields in groups.items():
         capacity = fields[0].repeat_capacity or 0
@@ -327,7 +372,20 @@ def resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
             for row, key in group.number_boxes.items():
                 if row <= min(actual, capacity):
                     out[key] = group.number.format(n=row)
-        if actual > capacity:
+        if actual > capacity and group is not None and group.sheet is not None:
+            sheets.append(
+                _sheet(
+                    group,
+                    fields,
+                    printed,
+                    resolved_cols,
+                    capacity,
+                    actual,
+                    session,
+                    _ingested_cache,
+                )
+            )
+        elif actual > capacity:
             if group is None or group.extra_page is None:
                 # The startup check refuses such a schema (forms.E007); never drop a row.
                 raise ValueError(f"{schema.form_type}: group {group_name!r} names no extra page")
@@ -347,4 +405,4 @@ def resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
             session,
             _ingested_cache,
         )
-    return {"version": 2, "parts": [{"kind": "form", "values": out}, *copies]}
+    return {"version": 2, "parts": [{"kind": "form", "values": out}, *copies, *sheets]}
PATCH
```

For a group with a `sheet`, `resolve_parts` no longer raises on rows past the last slot. `_sheet` builds one sheet part from them: each row's line and cells, the filer's name, and the sheet's title and columns. The part goes after the copies.

- [ ] **Step 10: Watch the sheet tests fail while check() knows no sheet part**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py apps/forms/tests/test_download_action.py apps/forms/tests/test_printed_page.py::test_the_sheets_letter_check_agrees_with_what_it_prints -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `17 failed, 22 passed`, with `test_extra_rows_print_on_an_attached_sheet - ValueError: schedule_a_b: no part of kind 'sheet'`, `test_a_form_with_a_copy_and_a_sheet_prints_the_sheet_last - ValueError: schedule_d: no part of kind 'sheet'` and `test_a_filed_form_downloads_exactly_what_was_filed[with a sheet] - assert 500 == 200`.

The resolver now builds the sheet part, and `check()` still refuses a part of any kind but `form` and `copy` (Task 6, R54). So every test that checks or draws a sheet fails there, and Download is a 500.

The name test now passes, because the form's own Debtor 1 box refuses "ą" before `check()` reaches the sheet part. In Step 6 it failed with five vehicles, since no sheet part could be built.

- [ ] **Step 11: Check and draw a sheet part**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -311,27 +311,34 @@
                 name, which fills every drawn widget of that name, or
                 "<full name>@<page>:<tag>", which fills that one widget and wins over
                 the full name there. A value is text, a combo's option, or a box's
-                export state such as "/Chapter 7".
+                export state such as "/Chapter 7". A sheet part's rows print on an
+                attached sheet under the title and columns the part stores, never the
+                schema's (R63; sheets.plan_sheet checks them).

         Returns:
             One planned part per part, each holding every widget a key fills in page
             and tag order: a text or combo box with its text as drawn and its size, a
-            box with its state or "/Off".
+            box with its state or "/Off". A sheet part fills no widget.

         Raises:
             UnknownField: a key names no drawn widget (on a copy's page, for a copy), or
                 is neither form of key.
             InvalidFieldValue: a box state or combo option the template lacks.
-            UnprintableLetter: a letter the box can't print.
-            ValueTooLong: a value too long for its box even at 6 pt.
-            ValueError: a part of a kind other than "form" and "copy".
-        """
+            UnprintableLetter: a letter the box, or the sheet, can't print.
+            ValueTooLong: a value too long for its box even at 6 pt, or for its sheet.
+            ValueError: a part of a kind other than "form", "copy" and "sheet".
+        """
+        from apps.forms.services.sheets import plan_sheet, sheet_spec  # here: they import this
+
         planned = []
         for part in parts_of(values):
             if part["kind"] == "form":
                 widgets = self._plan(form_type, part["values"])
             elif part["kind"] == "copy":
                 widgets = self._plan(form_type, part["values"], page=part["page"])
+            elif part["kind"] == "sheet":
+                plan_sheet(form_type, sheet_spec(part), part)
+                widgets = ()
             else:
                 raise ValueError(f"{form_type}: no part of kind {part['kind']!r}")
             planned.append(PlannedPart(part, widgets))
@@ -405,7 +412,8 @@
         second widget of each stacked pair are removed; and PyMuPDF bakes every other
         widget into its page. An unfilled widget prints as the blank form shows it. Each
         copy of an extra page is drawn alone, on a clone of the template of its own, and
-        goes in right after that page, or after the copy of it before (spec §5.2).
+        goes in right after that page, or after the copy of it before (spec §5.2). Each
+        attached sheet follows the form's pages and copies (spec §5.3).

         Args:
             form_type: a registered form type; its schema names the template.
@@ -416,7 +424,10 @@
             UnknownField, InvalidFieldValue, UnprintableLetter, ValueTooLong, ValueError:
                 as check().
         """
-        template = load_schema(form_type).template_filename
+        from apps.forms.services.sheets import draw_sheet, sheet_spec  # here: they import this
+
+        schema = load_schema(form_type)
+        template = schema.template_filename
         writer = _clone(form_type, template)
         planned = self.check(form_type, values)
         form = tuple(p for part in planned if part.part["kind"] == "form" for p in part.widgets)
@@ -430,5 +441,9 @@
             at = max(i for i, template_page in enumerate(shown) if template_page == page) + 1
             document.insert_pdf(copy, start_at=at)
             shown.insert(at, page)
+        for part in planned:
+            if part.part["kind"] == "sheet":
+                sheet = draw_sheet(sheet_spec(part.part), part.part)
+                document.insert_pdf(pymupdf.open("pdf", sheet))
         document.xref_set_key(document.pdf_catalog(), "AcroForm", "null")
         return document.tobytes()
PATCH
```

`check()` plans a `sheet` part through `plan_sheet`, from the part's own title and columns (`sheet_spec`), and gives it no widgets. `fill()` draws each sheet with `draw_sheet` and appends it after the form's pages and copies. Both import `sheets` inside the method, since `sheets` imports this module.

- [ ] **Step 12: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py apps/forms/tests/test_download_action.py apps/forms/tests/test_printed_page.py::test_the_sheets_letter_check_agrees_with_what_it_prints apps/forms/tests/test_check.py apps/forms/tests/test_checks.py apps/forms/tests/test_pdf_filler.py apps/forms/tests/test_continuation_copies.py apps/forms/tests/test_api_readback.py -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: `239 passed`.

The run covers:

- `test_attached_sheets.py` 17, `test_download_action.py` 21 and the letter agreement test;
- `test_check.py` 39 and `test_checks.py` 103;
- `test_pdf_filler.py` 41, with the `/.notdef` pin;
- `test_continuation_copies.py` 11, whose fixtures now go through `_with_group`;
- `test_api_readback.py` 6.

- [ ] **Step 13: Watch the sheet's name guard fail when the name isn't checked**

```bash
set -eo pipefail
cp backend/apps/forms/services/sheets.py backend/apps/forms/services/sheets.py.keep
trap 'mv backend/apps/forms/services/sheets.py.keep backend/apps/forms/services/sheets.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/sheets.py b/backend/apps/forms/services/sheets.py
--- a/backend/apps/forms/services/sheets.py
+++ b/backend/apps/forms/services/sheets.py
@@ -265,7 +265,6 @@
         (f.label for f in schema.fields if f.source == "derived" and f.rule == "full_name"),
         f"{spec.title} (attached sheet)",
     )
-    _check(form_type, template, part["name"], WIDTH, name_label, dict(RULE_FIXES["full_name"]))
     header = _header(spec, part["name"])
     fixes = _fixes(schema, part["group"], spec)
     for row in part["rows"]:
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py::test_a_name_the_sheet_cannot_print_is_refused_where_the_name_is_entered -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_a_name_the_sheet_cannot_print_is_refused_where_the_name_is_entered - Failed: DID NOT RAISE`.

Here `plan_sheet` never checks the filer's name, so "Maria Wąs" passes. The block restores `sheets.py` from the copy it kept, pass or fail; each mutation block below does the same with its file.

- [ ] **Step 14: Watch the tallest-cell refusal fail when it names the first column**

```bash
set -eo pipefail
cp backend/apps/forms/services/sheets.py backend/apps/forms/services/sheets.py.keep
trap 'mv backend/apps/forms/services/sheets.py.keep backend/apps/forms/services/sheets.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/sheets.py b/backend/apps/forms/services/sheets.py
--- a/backend/apps/forms/services/sheets.py
+++ b/backend/apps/forms/services/sheets.py
@@ -277,7 +277,7 @@
         ]
         if _height([[row["line"]], *cells]) > _room(spec, header):
             heights = [len(lines) for lines in cells]
-            tallest = heights.index(max(heights))
+            tallest = 0
             raise ValueTooLong(form_type, spec.columns[tallest].label, fixes[tallest])


PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py::test_a_row_taller_than_a_page_is_refused_naming_its_tallest_cell -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_a_row_taller_than_a_page_is_refused_naming_its_tallest_cell - AssertionError: assert 'Make' == 'Current valu...rtion you own'`.

Here a row taller than a page is refused naming the first column, not the 600-word value cell that makes it tall.

- [ ] **Step 15: Watch the encoding pin fail when the sheet's encoding loses Ł**

```bash
set -eo pipefail
cp backend/apps/forms/services/sheets.py backend/apps/forms/services/sheets.py.keep
trap 'mv backend/apps/forms/services/sheets.py.keep backend/apps/forms/services/sheets.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/sheets.py b/backend/apps/forms/services/sheets.py
--- a/backend/apps/forms/services/sheets.py
+++ b/backend/apps/forms/services/sheets.py
@@ -65,7 +65,7 @@
     "/quotesingle 96 /grave 128 /bullet /dagger /daggerdbl /ellipsis /emdash "
     "/endash /florin /fraction /guilsinglleft /guilsinglright /minus /perthousand "
     "/quotedblbase /quotedblleft /quotedblright /quoteleft /quoteright "
-    "/quotesinglbase /trademark /fi /fl /Lslash /OE /Scaron /Ydieresis /Zcaron "
+    "/quotesinglbase /trademark /fi /fl /L /OE /Scaron /Ydieresis /Zcaron "
     "/dotlessi /lslash /oe /scaron /zcaron 160 /Euro 164 /currency 166 /brokenbar "
     "168 /dieresis /copyright /ordfeminine 172 /logicalnot /.notdef /registered "
     "/macron /degree /plusminus /twosuperior /threesuperior /acute /mu 183 "
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py::test_the_sheet_prints_in_the_templates_own_encoding -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_the_sheet_prints_in_the_templates_own_encoding - AssertionError: assert ['24', '/brev...rumlaut', ...] == ['24', '/brev...rumlaut', ...]`.

Here `_DIFFERENCES` names `/L` where the templates name `/Lslash`, so it no longer equals any template's `/Helv` `/Differences`.

- [ ] **Step 16: Watch the letter tests fail when the sheet goes back to WinAnsi**

```bash
set -eo pipefail
cp backend/apps/forms/services/sheets.py backend/apps/forms/services/sheets.py.keep
trap 'mv backend/apps/forms/services/sheets.py.keep backend/apps/forms/services/sheets.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/sheets.py b/backend/apps/forms/services/sheets.py
--- a/backend/apps/forms/services/sheets.py
+++ b/backend/apps/forms/services/sheets.py
@@ -111,7 +111,7 @@

 def _prints(template: str) -> Callable[[str], bool]:
     """The forms' own letter check, for the form's template (R62)."""
-    return partial(printable, font_for(template, _TEXT_FONT))
+    return lambda c: c == "?" or c.encode("cp1252", errors="replace") != b"?"


 def _encoded(line: str) -> str:
@@ -119,7 +119,7 @@
     The line as insert_text() writes it: one byte per letter, its code in the templates'
     encoding. A letter plan_sheet() refuses prints as "?", as pypdf prints one on a form.
     """
-    return "".join(_CODES.get(letter, "?") for letter in line)
+    return line.encode("cp1252", errors="replace").decode("latin-1")


 def inner_width(width: float) -> float:
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py::test_the_sheet_prints_every_letter_the_form_prints apps/forms/tests/test_printed_page.py::test_the_sheets_letter_check_agrees_with_what_it_prints -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `2 failed`, with `test_the_sheet_prints_every_letter_the_form_prints - apps.forms.services.pdf_filler.UnprintableLetter: The court form can't print the letter “Ł” in “Debtor 1”. Change it to a letter without the mark.` and `test_the_sheets_letter_check_agrees_with_what_it_prints - AssertionError: assert ['U+0131', 'U...'U+02D9', ...] == []`.

Here the sheet is drawn as the first build drew it: WinAnsi's codes, and a check that a letter has a Windows-1252 code. The filer "Łucja Kıłıç" is then refused on the sheet's header, naming "Debtor 1", a box that prints Ł (review finding 1). The agreement test lists the letters the template's `/Helv` prints that the sheet now refuses, ı (U+0131) first.

- [ ] **Step 17: Watch a filed sheet fail when it is checked and drawn under the live schema**

```bash
set -eo pipefail
cp backend/apps/forms/services/pdf_filler.py backend/apps/forms/services/pdf_filler.py.keep
trap 'mv backend/apps/forms/services/pdf_filler.py.keep backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -337,7 +337,7 @@
             elif part["kind"] == "copy":
                 widgets = self._plan(form_type, part["values"], page=part["page"])
             elif part["kind"] == "sheet":
-                plan_sheet(form_type, sheet_spec(part), part)
+                plan_sheet(form_type, load_schema(form_type).groups[part["group"]].sheet, part)
                 widgets = ()
             else:
                 raise ValueError(f"{form_type}: no part of kind {part['kind']!r}")
@@ -443,7 +443,7 @@
             shown.insert(at, page)
         for part in planned:
             if part.part["kind"] == "sheet":
-                sheet = draw_sheet(sheet_spec(part.part), part.part)
+                sheet = draw_sheet(schema.groups[part.part["group"]].sheet, part.part)
                 document.insert_pdf(pymupdf.open("pdf", sheet))
         document.xref_set_key(document.pdf_catalog(), "AcroForm", "null")
         return document.tobytes()
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_download_action.py::test_a_filed_sheet_prints_what_was_filed_whatever_its_schema_says_later -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `4 failed`, with `[rename the group] - assert 500 == 200`, `[add a column] - assert 500 == 200`, `[narrow a column] - assert 422 == 200` and `[relabel] - AssertionError`.

Here `check()` and `fill()` take a sheet's title and columns from the live schema, as the first build did (review finding 3). After each edit that passes startup, the filed form breaks:

- a renamed group is no longer in the schema, a 500;
- an added column no longer matches the stored cells, a 500;
- a narrowed column refuses a stored word for good, a 422;
- a new title and label print words the filer never filed.

- [ ] **Step 18: Watch the boundary tests fail when plan and draw measure apart**

```bash
set -eo pipefail
cp backend/apps/forms/services/sheets.py backend/apps/forms/services/sheets.py.keep
trap 'mv backend/apps/forms/services/sheets.py.keep backend/apps/forms/services/sheets.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/sheets.py b/backend/apps/forms/services/sheets.py
--- a/backend/apps/forms/services/sheets.py
+++ b/backend/apps/forms/services/sheets.py
@@ -272,7 +272,7 @@
         if not fits_line_column(row["line"], template):
             raise ValueError(f"{form_type}: line {row['line']!r} doesn't fit the line column")
         cells = [
-            _check(form_type, template, cell, inner_width(column.width), column.label, fix)
+            _check(form_type, template, cell, column.width, column.label, fix)
             for column, cell, fix in zip(spec.columns, row["cells"], fixes, strict=True)
         ]
         if _height([[row["line"]], *cells]) > _room(spec, header):
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py::test_a_word_as_wide_as_its_cell_prints_and_a_wider_one_is_refused -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_a_word_as_wide_as_its_cell_prints_and_a_wider_one_is_refused - Failed: DID NOT RAISE`.

Here `plan_sheet` measures a cell at its column's full width, 300 pt, while `draw_sheet` wraps it at 296. The 297.08 pt word passes the check that should refuse it. In the first build, such a word passed Generate and was then a 500 at Download (review finding 4).

```bash
set -eo pipefail
cp backend/apps/forms/services/sheets.py backend/apps/forms/services/sheets.py.keep
trap 'mv backend/apps/forms/services/sheets.py.keep backend/apps/forms/services/sheets.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/sheets.py b/backend/apps/forms/services/sheets.py
--- a/backend/apps/forms/services/sheets.py
+++ b/backend/apps/forms/services/sheets.py
@@ -275,7 +275,7 @@
             _check(form_type, template, cell, inner_width(column.width), column.label, fix)
             for column, cell, fix in zip(spec.columns, row["cells"], fixes, strict=True)
         ]
-        if _height([[row["line"]], *cells]) > _room(spec, header):
+        if _height([[row["line"]], *cells]) > _room(spec, header) + LEADING:
             heights = [len(lines) for lines in cells]
             tallest = heights.index(max(heights))
             raise ValueTooLong(form_type, spec.columns[tallest].label, fixes[tallest])
PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py::test_a_row_as_tall_as_a_page_prints_and_a_taller_one_is_refused -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_a_row_as_tall_as_a_page_prints_and_a_taller_one_is_refused - Failed: DID NOT RAISE`.

Here `plan_sheet` gives a row one line more room than `draw_sheet` does, and a row of 45 lines passes the check. In the first build, a row one line too tall passed Generate and was then a 500 at Download (review finding 5).

```bash
set -eo pipefail
cp backend/apps/forms/services/sheets.py backend/apps/forms/services/sheets.py.keep
trap 'mv backend/apps/forms/services/sheets.py.keep backend/apps/forms/services/sheets.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/sheets.py b/backend/apps/forms/services/sheets.py
--- a/backend/apps/forms/services/sheets.py
+++ b/backend/apps/forms/services/sheets.py
@@ -205,7 +205,7 @@
     """A row's cells as the lines each prints: its line first, in the line column."""
     widths = [LINE_WIDTH, *(column.width for column in spec.columns)]
     return [
-        _lines(text, inner_width(width))
+        _lines(text, width - PAD)
         for text, width in zip([row["line"], *row["cells"]], widths, strict=True)
     ]

PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py::test_a_cell_filled_to_its_padding_stays_in_its_column -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed`, with `test_a_cell_filled_to_its_padding_stays_in_its_column - AssertionError: assert ((('3.5',), (...`.

Here `draw_sheet` wraps a cell at its column's width less one padding, 298 pt, so it keeps no right padding (re-review 1's B03). Row 3.6, "W"×31 + " i" at 297.64 pt, then prints as one line where the test expects two.

- [ ] **Step 19: Watch the totals test fail on copies when a copy repeats the page total**

```bash
set -eo pipefail
cp backend/apps/forms/services/fill_resolver.py backend/apps/forms/services/fill_resolver.py.keep
trap 'mv backend/apps/forms/services/fill_resolver.py.keep backend/apps/forms/services/fill_resolver.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/fill_resolver.py b/backend/apps/forms/services/fill_resolver.py
--- a/backend/apps/forms/services/fill_resolver.py
+++ b/backend/apps/forms/services/fill_resolver.py
@@ -198,7 +198,7 @@
         here = [
             w for w in widgets if w.page == page and (tag is None or (at, tag) == (w.page, w.tag))
         ]
-        if key not in own and here and any(w.page != page for w in widgets):
+        if key not in own and here:
             headers[key] = value
     return headers

PATCH
source .claude/forms-step3a2.env
(cd backend && COLUMNS=320 $PY -m pytest --tb=no -rfE apps/forms/tests/test_attached_sheets.py::test_totals_count_rows_printed_on_copies_and_sheets -q -p no:cacheprovider) 2>&1 | grep -E '^(FAILED|ERROR) |^[0-9]+ (passed|failed)|^=+ .*(passed|failed|error).* in [0-9.]+s'
```

Expected: FAIL — `1 failed, 1 passed`, with `test_totals_count_rows_printed_on_copies_and_sheets[copies] - AssertionError`.

Here Task 6's copies repeat a form value drawn on the extra page alone, so Schedule D's page 2 total prints again on its copy (R24). The case on copies sees it; the case on a sheet, which has no copy, passes.

- [ ] **Step 20: Say in the docs what a sheet is and what startup refuses**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index ea8c6b2..63e8b32 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -33,12 +33,12 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
-- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. Generate, Generate All and Regenerate check without drawing: each resolves the form's parts (`build_parts`), runs `PDFFormFiller.check()` and stores them, so a letter the form can't print or a value too long for its box is a 422, or a Generate All `errors` entry, carrying its `step` or `page`. Download draws: `fill()` bakes with PyMuPDF, which isn't thread-safe, so the server stays on sync gunicorn workers with no `--threads` unless the bake gets a lock. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download draws its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
-- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. For repeat groups, E007 refuses one not declared in the schema's `groups`, an `extra_page` that isn't the page of the group's last slots, a `number` without `{n}` (also when only `number_boxes` is set), one that `format(n=1)` can't fill or that prints the same for `n=1` and `n=2`, a second group with an `extra_page` on one form (3a2's limit), fields that differ in `repeat_capacity` or `conditional_on` or whose slot rows aren't exactly 1 to `repeat_capacity`, a slot row whose boxes sit on more than one page, rows that go back a page as the row number rises, and an untagged slot binding that would print its row more than once: a text or combo one whose name has more than one drawn widget, or a checkbox or radio one whose drawn widgets share an on-state (a column whose boxes each have their own state, such as Schedule D's `check 4`, passes); E003 refuses a number box for a row that isn't a slot row, a number or page-number box that is no drawn widget on its row's or page's page, an untagged number or page-number `this` box whose name has more than one drawn widget, and any untagged binding whose `page` holds no drawn widget of its name (a copy picks its rows' boxes by `page`); and E006 counts each group box (`number_boxes` values and `page_numbers` `this` and `of`, one `of` key once) as a writer beside the bindings. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
+- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. Generate, Generate All and Regenerate check without drawing: each resolves the form's parts (`build_parts`), runs `PDFFormFiller.check()` and stores them, so a letter the form can't print or a value too long for its box is a 422, or a Generate All `errors` entry, carrying its `step` or `page`. Download draws: `fill()` bakes with PyMuPDF, which isn't thread-safe, so the server stays on sync gunicorn workers with no `--threads` unless the bake gets a lock. Generate calls PyMuPDF too, without drawing: `check()` measures an attached sheet's text with PyMuPDF's `Font` (`sheets.plan_sheet`), and so does the startup check. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download draws its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
+- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. For repeat groups, E007 refuses one not declared in the schema's `groups`, one that names neither or both of an `extra_page` and a `sheet`, an `extra_page` that isn't the page of the group's last slots, a `number` without `{n}` (also when only `number_boxes` or a `sheet` is set), one that `format(n=1)` can't fill or that prints the same for `n=1` and `n=2`, a second group with an `extra_page` on one form (3a2's limit), fields that differ in `repeat_capacity` or `conditional_on` or whose slot rows aren't exactly 1 to `repeat_capacity`, a slot row whose boxes sit on more than one page, rows that go back a page as the row number rises, and an untagged slot binding that would print its row more than once: a text or combo one whose name has more than one drawn widget, or a checkbox or radio one whose drawn widgets share an on-state (a column whose boxes each have their own state, such as Schedule D's `check 4`, passes); for a `sheet`, E007 also refuses no columns, columns wider than 504 pt (7 in) with the 36 pt line column, a column whose binding isn't a `sofa.<collection>[].<attr>` list or isn't one of the group's slot bindings, or that any box slot binds, a slot binding no column prints (the rows past the slots would drop it), any other box slot (a sheet has no box to tick), a first sheet line (`number` for the row past the slots) that doesn't print whole on one line of the 36 pt line column, two columns with one label, a label or title the sheet can't print whole (a letter the form's template can't print, or a word wider than its column or the page), and `page_numbers` (a sheet group has no copies); E003 refuses a number box for a row that isn't a slot row, a number or page-number box that is no drawn widget on its row's or page's page, an untagged number or page-number `this` box whose name has more than one drawn widget, and any untagged binding whose `page` holds no drawn widget of its name (a copy picks its rows' boxes by `page`); and E006 counts each group box (`number_boxes` values and `page_numbers` `this` and `of`, one `of` key once) as a writer beside the bindings. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. Tiers 1 and 3 read the printed page, not `/V`: `read_drawn` (`apps/forms/tests/pdf_readback.py`) takes a widget's Helvetica text and the template's ZapfDingbats check mark inside its rect, and reads `""` where a box prints only the blank template's own default (the district combos' placeholder, A/B `19.1`–`19.3 % of ownership` "0%", C `page 2` and G `fill 2.6` "2"), so a blank assertion on such a box can't see that default. `read_drawn` refuses a PDF that still has a widget (a `ValueError`, never a listed defect), so it reads only `fill()`'s baked output. The list has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
-- **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, the one function behind all of them; any other error fails the form). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine stays for later steps, and only synthetic tests reach it: a repeat group (`repeat`) is declared in the schema's top-level `groups` with the `extra_page` that continues it (forms.E007 refuses a group without one), and rows past its last slot print on copies of that page, each a `copy` part drawn alone and put in right after the page or the copy before it, numbered by the group's `number` and `page_numbers` boxes. `RepeatOverflow` is gone.
-- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, a parts document in printing order: `{"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}` (`registry.build_parts`). The API never returns it. Each copy of an extra page follows the form part as a part of its own, `{"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}}`. `form_data` is blank; its column is dropped one release after this code is live. Generate, Generate All and Regenerate store the document they checked; an unfiled form is resolved, checked and drawn fresh on every download, and its document stored again. A filed form draws its stored document, so it prints exactly what was filed. A form filed before forms step 3a2 holds `{full name: value}` with no `version`, which `parts_of` (`pdf_filler.py`) reads as one form part. A filed form whose stored values `check()` refuses downloads as a 422 with the refusal's sentence and no `step` or `page`, since no step changes what was filed.
+- **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, the one function behind all of them; any other error fails the form). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine stays for later steps, and only synthetic tests reach it: a repeat group (`repeat`) is declared in the schema's top-level `groups` with the `extra_page` that continues it or the `sheet` that takes its rows (forms.E007 refuses a group with neither or both). Rows past its last slot print on copies of that page, each a `copy` part drawn alone and put in right after the page or the copy before it, numbered by the group's `number` and `page_numbers` boxes, or on an attached sheet (`apps/forms/services/sheets.py`): plain US Letter pages after the form's pages and copies, each headed by the filer's name, the form's title with "(attached sheet)" and a blank "Case number (if known)", with every row labelled by its `number` under the group's columns, in Helvetica at 10 pt. PyMuPDF draws its Helvetica in WinAnsiEncoding, so `draw_sheet()` writes each letter's code in the templates' own `/Helv` encoding (`sheets._DIFFERENCES`, which all 17 templates share and a test pins) and gives every sheet page's font that `/Encoding`: a sheet prints exactly the forms' letters, Ł, ł and ı included, and refuses the rest with the forms' own check (`text_fit.printable` on the form's `/Helv`, which also refuses □, the template's `/.notdef`). A sheet's pages are not counted in the form's page numbers. A total adds up every row, the copies' and the sheet's included. `RepeatOverflow` is gone.
+- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, a parts document in printing order: `{"version": 2, "parts": [{"kind": "form", "values": {key: value}}]}` (`registry.build_parts`). The API never returns it. Each copy of an extra page follows the form part as a part of its own, `{"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}}`, and each attached sheet follows the copies, `{"kind": "sheet", "group": <group>, "title": <its title>, "columns": [{"label": str, "width": <points>}], "name": <the filer's full name>, "rows": [{"line": "3.5", "cells": [<one per column>]}]}`; `check()` and `fill()` draw a sheet part from its own title and columns (`sheets.sheet_spec`), never the schema's, so a filed sheet prints exactly what was filed whatever its schema says later. `form_data` is blank; its column is dropped one release after this code is live. Generate, Generate All and Regenerate store the document they checked; an unfiled form is resolved, checked and drawn fresh on every download, and its document stored again. A filed form draws its stored document, so it prints exactly what was filed. A form filed before forms step 3a2 holds `{full name: value}` with no `version`, which `parts_of` (`pdf_filler.py`) reads as one form part. A filed form whose stored values `check()` refuses downloads as a 422 with the refusal's sentence and no `step` or `page`, since no step changes what was filed.
 - **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
 - **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
 - **CI ruff is pinned** — `ci.yml` installs `ruff==0.8.5`. Unpinned ruff broke CI when new rules shipped.
@@ -103,7 +103,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - `apps/eligibility/services/means_test_calculator.py` — `MeansTestCalculator`, which runs and saves `MeansTest.calculate()` (`apps/eligibility/models.py`, where CMI is annualized)
 - `apps/eligibility/cmi.py` — `current_monthly_income` (the one CMI), `IncomeNotSplit`, `is_above_median`
 - `apps/forms/registry.py` — `FORM_REGISTRY` (17 form_type → `PacketForm(applies, requires)`) in filing order, `packet()`, `build_parts()`, `build_field_values()`
-- `apps/forms/services/` — `pdf_filler.py` (`PDFFormFiller`: `check()` plans, `fill()` draws and bakes), `widgets.py` (each template widget by page and tag), `text_fit.py` (letters and fit, as pypdf lays text out), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
+- `apps/forms/services/` — `pdf_filler.py` (`PDFFormFiller`: `check()` plans, `fill()` draws and bakes), `widgets.py` (each template widget by page and tag), `text_fit.py` (letters and fit, as pypdf lays text out), `sheets.py` (attached sheets: `plan_sheet()` checks, `draw_sheet()` draws), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
 - `apps/forms/field_index.py` + `apps/forms/checks.py` — the field index loader and the schema system check
 - `apps/forms/views.py` — GeneratedFormViewSet (generate, generate_all, download, mark_filed)
 - `apps/documents/services/providers/` — `base.py` (`BaseOCRProvider`), `openai_provider.py`, `gemini.py`, `prompts/`
PATCH
```

In `CLAUDE.md`:

- "GenerateAll vs single" says Generate calls PyMuPDF too, measuring a sheet's text without drawing, and so does the startup check.
- "Schemas are checked at startup" lists the sheet rules.
- "Blank, not 0.00, on the forms" says a group continues on an extra page's copies or on an attached sheet, describes the sheet and its letters, says its pages aren't counted in page numbers, and says a total adds up every row.
- "`field_values`, not `form_data`" gives the sheet part's shape, and says a filed sheet draws from its own title and columns.
- The File Map's `apps/forms/services/` line gains `sheets.py`.

- [ ] **Step 21: Run every gate**

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

Expected: `2797 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  397 passed (397)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

That is 44 more backend cases than after Task 6: `test_attached_sheets.py`'s 17, 20 more in `test_checks.py`, 5 more in `test_download_action.py`, the □ case in `test_check.py` and the letter agreement test in `test_printed_page.py`. No frontend file changes.

Under a heavy load (1-minute load above 15), a SOFAStep or FormDashboard test can run past vitest's 5 s per-test timeout. Run vitest again on a quieter machine before suspecting the code.

The 25 skips are the Postgres-only tests under sqlite. The next command runs them against the Postgres database named by `DATABASE_URL` in `.claude/forms-step3a2.env`, as CI's "Run the Postgres-only tests" step does.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

This task touches no locking, so they pass unchanged.

- [ ] **Step 22: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/services/sheets.py \
  backend/apps/forms/tests/test_attached_sheets.py \
  CLAUDE.md \
  backend/apps/forms/schema.py \
  backend/apps/forms/services/fill_resolver.py \
  backend/apps/forms/services/pdf_filler.py \
  backend/apps/forms/services/text_fit.py \
  backend/apps/forms/tests/conftest.py \
  backend/apps/forms/tests/pdf_readback.py \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_check.py \
  backend/apps/forms/tests/test_checks.py \
  backend/apps/forms/tests/test_download_action.py \
  backend/apps/forms/tests/test_pdf_filler.py \
  backend/apps/forms/tests/test_printed_page.py
git commit -F - <<'MSG'
feat(forms): print rows past a group's last slot on an attached sheet

T6 continued a repeat group's rows on copies of its extra page. A/B,
Schedule I's employers, 122A-2 and 103B have no page to copy, so their
rows past the last slot print on an attached sheet instead (3a2 spec
§5.3): plain US Letter pages appended after the form's pages and
copies. No production schema has a repeat group yet; 3a2 proves sheets
on a synthetic Schedule A/B group (§5.4).

- A group declares its sheet in "groups":
  {"<group>": {"number": "3.{n}", "sheet": {"title": str, "columns":
  [{"label": str, "binding": "sofa.<collection>[].<attr>", "width":
  <points>}]}}}, read into GroupSpec.sheet as SheetSpec and
  SheetColumn.
- The startup check (forms.E007) refuses a group that names neither or
  both of an extra_page and a sheet, and for a sheet:
  - a number without {n}: each row is labelled with the line it
    continues;
  - a first sheet line, the number for the row past the slots, that
    doesn't print whole on one line of the line column;
  - no columns, or columns wider than the 504 pt (7 in) between the
    margins, with the 36 pt line column;
  - a column binding that isn't a sofa.<collection>[].<attr> list, that
    no slot of the group binds (its rows wouldn't be the group's), or
    that any box slot binds (a box's answer is a state, and a sheet has
    no box to tick);
  - a slot binding no column prints, which the rows past the slots
    would drop, and any other box slot;
  - two columns with one label: a label names one column, to the filer
    and to a refusal's fix;
  - a column label or title the sheet can't print whole: a letter the
    form's template can't print, or a word wider than its column or the
    page;
  - page_numbers: they count a group's copies (R21), and a sheet group
    has none, so they would never print.
  A sheet group doesn't count against the one group with an extra_page
  per form (R56). T6's slot rules (capacity, one page per row, rows in
  page order, tags, E006 writers) hold for a sheet group's slots too.
- resolve_parts() puts the rows past a sheet group's slots in one part
  after the form's and its copies: {"kind": "sheet", "group", "title",
  "columns": [{"label", "width"}], "name", "rows": [{"line": "3.5",
  "cells": [...]}]}. "line" is the group's number for the row's
  position, each cell is its column's binding for that row as the
  group's slot of that binding prints it, and "name" is
  DERIVATIONS["full_name"]. check() and fill() draw a sheet part from
  its own title and columns (sheets.sheet_spec), never the schema's, so
  a filed sheet prints exactly what was filed, under the name it was
  filed with (R23, R63), whatever its schema says later. The UPL guard
  blanks a column whose slots it keeps blank, as on the form and its
  copies; the row still prints.
- apps/forms/services/sheets.py:
  - draw_sheet(spec, part) draws the sheet in Helvetica at 10 pt on
    612 x 792 pt pages with 0.75 in margins. Every page starts with the
    header: the filer's name, the title followed by " (attached sheet)",
    and "Case number (if known)" with a blank line to write on. Then the
    column labels, a rule, and the rows: the line in the first column,
    each cell's text 2 pt in from each side of its column. A cell wraps
    at its spaces and starts a new line at a line break (G15); a row
    never splits across pages, and the sheet takes as many pages as its
    rows need. Lines are PyMuPDF's own Helvetica line (ascender to
    descender), so every character's box stays inside its line, its
    column and the margins. An empty line isn't drawn.
  - The sheet prints in the templates' own text font (R62): the base-14
    Helvetica with the /Encoding all 17 templates' /Helv share. PyMuPDF
    draws "helv" in WinAnsiEncoding, so each line goes to insert_text as
    its codes in the templates' encoding (as pypdf maps a form's), as a
    one-item list, since insert_text splits a string at NEL, the byte of
    "–" there; then every page's font gets that /Encoding. The sheet
    prints exactly the forms' letters, Ł, ł and ı among them, and reads
    back as itself in MuPDF and pypdf.
  - plan_sheet(form_type, spec, part) checks a sheet part as check()
    checks a box, with the forms' own letter check (text_fit.printable
    on the form's /Helv) through _as_printed and _refused_letter. It
    refuses a letter the sheet can't print (UnprintableLetter) and a
    word wider than its cell or a row taller than a page (ValueTooLong,
    naming the column with the most lines), each naming its column's
    label, fixed where the column's slots' binding is changed
    (fill_resolver.fix_for on the slot behind the schema's column of
    that label: the SOFA page for today's columns). It also checks the
    filer's name, naming the form's own name box and the step where the
    name is entered, though check() refuses such a name on the form
    first.
  - plan_sheet and draw_sheet share a column's inner width
    (inner_width) and a page's room for its rows (_room).
  - Widths come from PyMuPDF's Font("helv") on the Unicode text:
    pymupdf.get_text_length measures each WinAnsi letter at 0x80 to 0x9F
    (’ “ ” – — … € • Š Œ ž …) at 2.78 pt at 10 pt, whatever the letter.
  - Generate now calls PyMuPDF too, measuring a sheet's text without
    drawing; Download still draws and bakes.
- text_fit.printable() refuses □: pypdf reads a template's /.notdef, at
  code 173, as □, and a form drew it as that code, a soft hyphen.
- _refused_letter(text, prints, comb=False) takes what the font can
  encode as a function, and comb as a flag, so the sheet reuses it;
  check() passes printable for the box's font and widget.comb. The
  unused pypdf Font import goes.
- check() plans a sheet part with plan_sheet (it fills no widget), and
  fill() appends each sheet after the form's pages and copies. A sheet's
  pages are not counted in a form's page numbers: §5.2 numbers each page
  "with the copies counted", and §5.3 appends a sheet "right after its
  form", with no registry entry, schema or field index.
- read_drawn() leaves an attached sheet's pages to read_sheets(). It
  still refuses a PDF whose pages aren't the template's and its copies',
  then at least one page per sheet part, each headed "(attached sheet)",
  and nothing else; no page of the 67 templates says "attached sheet".
  read_sheets(pdf_bytes, spec) reads each sheet page's header, its
  column labels and its rows under the spec's columns, each row's cells
  as their lines, the box its characters lie in, each character outside
  its column (a space, which MuPDF reads between two cells, aside) and
  each line that runs into the next.

The tests the change breaks are fixed here: the "no extra page" case of
test_a_repeat_group_whose_rows_cannot_continue_is_reported and
test_a_group_with_no_extra_page_is_not_counted_as_a_second expect the
new message, "names neither an extra_page nor a sheet". conftest's
synthetic-group helper takes the form type, copies the schemas once and
adds a group beside those before, so a test can stack groups, and
creditor_payments takes names. test_api_readback reads a part with no
values, a sheet's.

New tests, over conftest's synthetic Schedule A/B (the real schema plus
group ab_line_3 over line 3's four vehicles, 3.1 and 3.2 on page 2, 3.3
and 3.4 on page 3, each a make and the current value of the portion the
filer owns, bound to SOFA creditor payments; R18, R19):
- five vehicles print the fifth on a sheet page after A/B's ten pages,
  labelled 3.5, under its columns, in Helvetica at 10 pt, with the
  header and the case number's blank line, while rows 1 to 4 fill the
  slots; the sheet part is exactly the shape above, and pypdf and
  PyMuPDF both open the PDF with its 11 pages;
- a long sheet runs to a second page: twenty rows, three of one line
  and then rows of three lines, fill fourteen rows on page 1 and six on
  page 2, though page 1 had room for the fifteenth's first line; the
  header and labels repeat, every row prints once, whole and in order,
  and no character lies outside the margins or its column, nor any line
  over the next;
- a cell's text keeps its 2 pt padding: thirty W's and two i's
  (293.2 pt) print from 92 to 385.2 pt in the Make column (90 to 390)
  and a third i starts the next line; thirty-one W's and an i
  (297.64 pt), which would end inside the column but past its padding,
  wrap before the i;
- at the boundaries plan and draw share: a word of 294.86 pt prints in
  the Make cell and one of 297.08 pt is refused naming "Make"; a row of
  44 lines prints on one page and one of 45 is refused;
- a form with both continuations, Schedule D with Part 2 copied on page
  3 and Part 1 on a sheet, prints the form's pages, the copy, then the
  sheet, and read_drawn reads them;
- totals count rows printed on copies and sheets: D's page 2 total and
  A/B's Part 2 total, each bound to a test-only rule that adds up every
  row, print 2100.00 for six rows of 100.00 to 600.00, and D's total
  prints once, not on its copy;
- the sheet prints Ł, ł and ı in its header and in a cell, read back in
  MuPDF, with no warning, and in pypdf; every template's /Helv has the
  sheet's /Encoding, and every page of a two-page sheet's font has it;
- check() refuses a letter the sheet can't print in a cell (“ą” in
  “Make”, /sofa), a name the form's own box can't print there, with or
  without a sheet (“ą” in “Debtor 1”, debtor_info), and a word wider
  than its cell; plan_sheet refuses such a name alone, and a row taller
  than a page naming its tallest column;
- the UPL guard blanks a guarded column on the sheet, and the row and
  its make still print; PyMuPDF logs nothing for the blank cell;
- read_drawn refuses a sheet page read as a page of the form, and a
  drawing that lacks the sheet its parts have;
- the sheet's letter check agrees with a read-back of the sheet over
  T4's character set, every letter a template's text font prints (all
  255 of them, ™ † ƒ and the others whose codes differ from WinAnsi's
  among them) and □: each accepted letter reads back as it prints and
  leaves ink, and each refused one, drawn without the check, reads back
  as something else or leaves none;
- a form value with □ is refused with the letter sentence;
- test_a_filed_form_downloads_exactly_what_was_filed gains a sheet
  case: after the filer's rename and a deleted row, the download still
  prints both sheet rows under "Maria Torres";
- test_a_filed_sheet_prints_what_was_filed_whatever_its_schema_says_later:
  after a schema edit that passes startup (the group renamed, a column
  added, one narrowed, the title and a label changed), a filed sheet
  downloads with every word where it printed before;
- the startup check passes the synthetic group, and a sheet group beside
  D's copied group, and refuses each broken sheet declaration above. T6's
  slot rules still hold for a sheet group's slots: a capacity other than
  the slots and rows that go back a page are refused as for a copied
  group. Only the extra page's own rules (the page of the last slots,
  one group with an extra_page per form) leave a sheet group alone.

CLAUDE.md: the File Map line for apps/forms/services/ gains sheets.py;
"Blank, not 0.00" describes sheets, their letters and their page
numbers; "Schemas are checked at startup" lists the sheet rules;
"field_values, not form_data" gives the sheet part's shape; "GenerateAll
vs single" says Generate measures a sheet's text with PyMuPDF.
MSG
git status --short
```

### Task 8: The dashboard links each refusal to its fix; no retry

_Built and verified as commit `71c173f` on `plan/forms-step3a2`._

**Files:**

- Create: `frontend/src/constants/wizardSteps.ts`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/tests/test_rule_fixes.py`
- Modify: `frontend/src/api/__tests__/client.test.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/forms/FormCard.tsx`
- Modify: `frontend/src/pages/FormDashboard.tsx`
- Modify: `frontend/src/pages/IntakeWizard.tsx`
- Modify: `frontend/src/pages/__tests__/FormDashboard.test.tsx`
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/types/api.ts`

**Interfaces:**

- Consumes:
  - In `frontend/src/api/client.ts`:
    - `apiFetchOnce<T>(endpoint: string, options: RequestInit = {}, skipAuth = false): Promise<T>` (module-private): one request; on a 401 it refreshes the token once and sends the request once more; any other refusal goes through `handleAPIError`. `apiFetch<T>` wraps it in `withRetry` (`frontend/src/utils/retry.ts`), which sends a request that got a 5xx three more times, 0.5 s, 1 s and 2 s apart.
    - `handleAPIError(response: Response): Promise<never>` (module-private): reads the JSON body once and throws `APIClientError(body.message || body.error || 'Request failed', status, body.details, body.error, {errors, step, page})`, keeping `step` and `page` only when they are strings. A body that isn't JSON throws "An unexpected error occurred. Please try again." with the status.
    - `class APIClientError extends Error` with `statusCode: number`, `serverError?: string`, `step?: string` (a `WIZARD_STEPS` key) and `page?: string` (a route).
    - `formsAPI.generateAll(sessionId: number): Promise<GenerateAllFormsResponse>`, which called `apiFetch`.
    - `formsAPI.downloadForm(formId: number, filename: string): Promise<void>`: it fetches `/forms/{id}/download/` with the access token, refreshes once on a 401 (`attemptTokenRefresh()`) and fetches again, then saves the PDF through an object URL and a clicked `<a download>`. Before this task any other refusal threw `APIClientError('Download failed (<status>)', status)` without reading the body.
    - `setAccessToken(token: string | null)` and `setRefreshToken(token: string | null)` (exported).
  - In `frontend/src/pages/FormDashboard.tsx` (3a1): `wholeCallRefusal(err, generic)` (a 422's own words, else the generic words), `loadFailure(err) -> {message, namesFix}` for the packet list, `PAGE_LINK_LABELS = {'/intake': 'Finish your intake'}`, `generateAllRefusal: {message, page?}`, and ruling R4-a's rule that "Finish your intake" shows at most once (`noticeLinksIntake`, `errorLinksIntake`, `refusalLinkLabel`). `handleGenerate` and `handleDownload` let a refusal reach `FormCard`. Generate All's per-form `errors` show as plain text under "You can try generating them individually below."
  - `FormCard({ formType, generatedForm, leftPacket, onGenerate, onDownload, onMarkFiled })` (`frontend/src/components/forms/FormCard.tsx`), whose `handleAction` catches every error and drops it ("Error handled by parent").
  - In `frontend/src/pages/IntakeWizard.tsx`: the module constant `WIZARD_STEPS` (eight `{ number, label, key }` entries), `sessionIdToRead` fixed at mount in a `useState` initializer, the read effect keyed on `readAttempt` (Try again), and `setCurrentStepNumber(fresh.current_step)` in the read's `.then`.
  - `FORM_TYPE_METADATA: Record<FormType, { label, ... }>` and `GenerateAllFormsResponse` (`frontend/src/types/api.ts`); `ERROR_GENERIC` ("Something went wrong. Your information is safe — please try again in a moment.") and `DASHBOARD_ERROR` (`frontend/src/constants/copy.ts`).
  - From the backend (3a1, Tasks 2 and 5): a refusal's 422 body `{form_type?, error, step?, page?}` from `_failure` in `backend/apps/forms/views.py`, and Generate All's `errors` entries in the same shape. `fix_for` and `RULE_FIXES` (Task 2) give a `WIZARD_STEPS` key or one of the pages `/fee-waiver`, `/sofa`, `/documents` and `/ask/<form type>`. `IncomeNotSplit` carries `step: "income_info"` and `IntakeNotFinished` `page: "/intake"`. A filed form's refused Download carries neither (R46, Task 5).
  - For the tests: `server` (`frontend/src/test/mocks/server`); in `FormDashboard.test.tsx`, `renderFormDashboard()`, `completedSession`, and inside the describe "when Generate All or the packet list is refused" `INCOME_NOT_SPLIT`, `NOT_SPLIT` and `openGenerateAll()`; the default handlers' Form 101 (generated, id 1) and Form 121 (not generated); in `IntakeWizard.test.tsx`, `renderWizard()`, `sessionAtStep1`, `sessionAtStep8` and the describe "IntakeWizard session re-read"; in `client.test.ts`, `refusalOf(call)` and the describe "what a refusal says fixes it".
- Produces:
  - `frontend/src/constants/wizardSteps.ts`: `export const WIZARD_STEPS`, moved from `IntakeWizard.tsx` with the same eight entries and no `as const`, imported by `IntakeWizard.tsx` and `FormDashboard.tsx`.
  - `GenerateAllFormsResponse.errors: Array<{ form_type: string; error: string; step?: string; page?: string }>`.
  - `formsAPI.generateAll` calls `apiFetchOnce`. `formsAPI.downloadForm` calls `await handleAPIError(response)` on a refusal, after its one 401 refresh.
  - In `FormCard.tsx`: `export interface FormRefusal { message: string; link?: { to: string; label: string } }`, and `FormCard`'s new prop `refusal?: FormRefusal`, shown in `div.form-card-refusal[aria-live="polite"]` after the card's actions. `.form-card-refusal:empty` in `frontend/src/styles/global.css`.
  - In `FormDashboard.tsx`, module-private: `type Fix = { step?: string; page?: string }`, `type Refusal = { message: string } & Fix`, `refusalOf(err: unknown, generic: string): Refusal`, `PAGE_LINK_LABELS` with four pages, `fixLink(fix: Fix): FormRefusal['link']` and `linksInPageOrder(intakeLinked: boolean): (fix: Fix) => FormRefusal['link']`. State: `error: Refusal | null`, `generateAllRefusal: Refusal | null` and `formRefusals: Partial<Record<FormType, Refusal>>`.
  - `IntakeWizard` opens at the step `?step=<key>` names, then drops `step` from the address with a replace.
  - New vitest tests, listed in Step 1.
  - `CLAUDE.md`: "GenerateAll vs single", "The wizard re-reads the session on every mount", "Document upload sits mid-wizard" and the File Map line for `IntakeWizard.tsx`.
  - Where the commit differs from tasks.md: the Interfaces table names only `WIZARD_STEPS` and the `errors` type, while the commit also exports `FormRefusal` and gives `FormCard` its `refusal` prop (the T8 bullets name the prop). T8's `CLAUDE.md` bullet names two gotchas; the commit changes four places, adding "Document upload sits mid-wizard" (review Minor 9) and the File Map line. T8's test list lacks fix round 2's test that a failed read keeps `?step=` in the address.

**Decisions already made in this task:**

_What the filer sees (spec §4.5, §7):_

- **R1: frontend tests have prose names,** `it('…')` as every other frontend test has, each carrying the meaning of a spec §9 name. `a_refused_form_links_to_the_step_that_fixes_it` is "links a form Generate All refused to the step that fixes it, with no advice to retry", "links a form whose Generate was refused to the step that fixes it" and "links a form whose download was refused to the step that fixes it". `a_refused_download_shows_its_reason` is "shows why a download was refused, in a polite region that was on the card before it". `the_wizard_opens_at_the_step_a_link_names` is "opens at the step a link names, without moving the filer’s saved place", and the unknown key is "opens at the saved step when a link names no step of the wizard". `generate_all_is_sent_once_on_a_server_error` is "sends Generate All once, and shows generic words, never the server’s, when it fails on the server".
- **R2: no Regenerate in the frontend.** Spec §4.5 lists Regenerate among the calls whose refusals link to their fix, but the frontend has no Regenerate button, handler or client method. The links cover Generate All, Generate and Download.
- **Generate All is sent once** (spec §7): `formsAPI.generateAll` calls `apiFetchOnce`, so a slow or failed run is never repeated behind the filer's back; through `withRetry` a 5xx could start four runs at once. The dashboard shows the error, and the filer can press again. A 401 still refreshes the token and sends once more: DRF refuses an expired token before the view runs, so that is not a second run.
- **Single Generate still goes through `apiFetch`** (the implementer's call, accepted by the review): spec §7 names only Generate All. A card's generic refusal after a 5xx Generate therefore arrives after the retries, about 3.5 s later.
- **`downloadForm` reads a refused download's body** with `handleAPIError`, after its one 401 refresh, so the refusal keeps its own words, `step` and `page` like every other call. A body that isn't JSON, such as a router's 503 page, still throws an `APIClientError` with its status, and the card shows the generic words.
- **R22 (amended): the link words go to the owner with the plan.** A step that is a `WIZARD_STEPS` key links to `/intake?step=<key>` as "Go to <step label>" (the wizard's own Review idiom), so "Go to Your Information", "Go to Income", "Go to Review & Results". `/intake` stays "Finish your intake". `/fee-waiver`, `/sofa` and `/documents` read "Go to Filing Fee Waiver Application", "Go to Statement of Financial Affairs" and "Go to Upload your documents", each "Go to" plus that page's own `h1`, lower-case "your" kept. `/ask/<form type>` reads "Answer the questions for <the form's `FORM_TYPE_METADATA` label>", such as "Answer the questions for Form 107 - Financial Affairs" (R22 amended), the label the dashboard names forms by everywhere.
  - `AskModulePage`'s own `FORM_LABELS` has no `form_101` or `form_107`, so its `h1` would read the raw key and not match the link. That is a ticket candidate; no `answer:` refusal can arise today, since no schema field carries the `ui` that page shows.
- **What "names a fix" means:** `fixLink` returns a link. A step wins over a page. A step that isn't a `WIZARD_STEPS` key, a page with no words, or an `/ask/` form type missing from `FORM_TYPE_METADATA` gets no link, and counts as naming no fix.
- **Own keys only (review Minor 11, R69):** `fixLink` looks in `FORM_TYPE_METADATA` and `PAGE_LINK_LABELS` through `Object.hasOwn`. A plain lookup let `/ask/constructor` render "Answer the questions for undefined", and a page named `constructor` would get a function for its words. `tsconfig.app.json` targets ES2022, whose library declares `Object.hasOwn`.
- **Generate All's list:** each entry shows its form's label, its message and, when it names a fix, its link. "You can try generating them individually below." shows only when at least one listed entry names no fix (spec §4.5: the retry advice goes for a refusal that names a fix). An `/intake` link withheld by the once-only rule still names a fix, so it doesn't bring the sentence back.
- **R4-a (3a1): "Finish your intake" shows at most once, now in page order** over every block that can offer it: the notice for an unfinished intake, the packet list's refusal, Generate All's refusal of the whole call, Generate All's list, then the cards (the packet in order, then filed forms outside it). That is the order the page renders them. `linksInPageOrder` is a module-level function returning a closure that the render calls in that order; the implementer kept the reassigned flag out of the component so that the React Compiler rules of `eslint-plugin-react-hooks` 7 have no reassignment during render to report. A step link (`/intake?step=…`) is never withheld.
- **R69: the packet list's refusal and Generate All's refusal of the whole call link their step or page through the same helpers.** Before, the whole-call refusal kept only its `page`, and the packet list offered "Finish your intake" for any refusal that named a fix (3a1's R4-b), which opened a completed filer's saved step, Review, under the sentence "Enter your income by source on the Income step." Both now read "Go to Income" (`/intake?step=income_info`) for `IncomeNotSplit`. Two existing packet-list tests expected "Finish your intake" and now expect "Go to Income": tests the change breaks, fixed in this commit. The packet list is refused only for a completed session, with `IncomeNotSplit` or `NoTableInForce`, never with `/intake`, so it no longer offers "Finish your intake" at all.
- **One helper, `refusalOf(err, generic)`, turns a thrown refusal into the filer's words and its fix**: a 422's own words with its `step` and `page`, anything else the generic words (a 500's text is for operations). It serves the packet list's refusal, Generate All's refusal of the whole call and each card's. Generate All's list entries arrive in its reply and link as they are.

_A card's refusal:_

- **One refusal per form type**, set when that card's Generate or Download is refused. It clears when the form's own Generate or Download next succeeds, when Generate All returns that form in `generated`, and when the form is marked filed (R69).
  - **Generate All clears every form in `generated`, a filed form included** (the implementer's call, accepted by the re-review and worded by R70). Generate All returns a filed form untouched (DIG-155), so a filed form's R46 Download refusal disappears though nothing changed, and the next Download shows it again. Production v31 holds no such row; a self-hoster's `main` can (R73).
  - **Mark as Filed clears it after `markFiled` resolves:** a filed form prints what was filed, which no step changes (R46).
  - **An entry in Generate All's `errors` neither clears nor replaces a card's refusal,** so a form refused on its card and again by Generate All shows both (the re-review's Minor 4, the rest of the review's Minor 7). Under R70 it is a ticket candidate, left as found.
- **A refused Download doesn't reload the forms,** as before: it returns before `loadForms()`, so the card and its live region stay mounted. The refusal is keyed by the form's type, found in `forms` by id.
- **The card shows the refusal in a polite live region that is on the card from the start** (`div.form-card-refusal`, `aria-live="polite"`, after the actions), as Review shows its reasons: a screen reader reads out only a change to a region already on the page. It is not `role="alert"`, since the partial-failure test's single `getByRole('alert')` would then find two, and not `role="status"`, since the card's badge already has one. It takes no error colour, like the dashboard's own error blocks. Empty, `.form-card-refusal:empty` gives back the card's flex gap (`var(--space-3)`), as `.review-reasons:empty` does, so a card without a refusal looks as it did.

_The wizard's `?step=`:_

- **Read once at mount,** in a `useState` initializer as `sessionIdToRead` is, so StrictMode's second call reads the same value. A key that is one of `WIZARD_STEPS` opens that step once the session read returns, in the same `.then` as the hydration, so autosave's first copy of the step is the loaded one and opening it saves nothing. It sends no `update_step`, so the saved step stays where Continue last put it. Anything else opens the saved step.
- **R69: once a linked step has opened, the wizard drops `step` from the address** with `setSearchParams(…, { replace: true })` inside the read's `.then`, keeping any other parameter and adding no history entry. A refresh, or Back to the wizard from a later page, then opens the saved step, not the linked one again (review Minors 4 and 8). The re-review saw exactly one replace under StrictMode.
- **R70: dropped after the read, not before.** A failed read keeps `?step=` in the address, so a refresh during the failure still opens the linked step; Try again opens it either way, since `linkedStep` is fixed at mount, and then drops it.
- **An unknown `?step=` stays in the address and is ignored** (the implementer's call, accepted by the re-review): only a key that opened a step is dropped.
- **A new session also opens at a valid linked step;** only a dashboard link, which always has a session, produces one, and Complete checks everything.
- **A fix link can cost the filer a walk:** Continue from the linked step saves and moves the saved step, any edit reopens a completed intake, and Continue from step 1 detours to `/documents`, so the filer walks forward to Review and presses Complete again (frontend survey §0.7). That works as designed.

_The review (R69) and fix round 2 (R70):_

- **The review's Critical finding is an owner question, not fixed here (R69).** A pay stub's employer name (Schedule I's `Employers Name Debtor 1`, label "Debtor 1 employer", an ingested value) that the form can't print, for a letter such as Ż or about 41 capital letters, is refused with `page: "/documents"`, as spec §4.5 maps an ingested value. The dashboard links it "Go to Upload your documents", where nothing can change the name. Schedule I is in every packet, so that filer can't get a whole packet. This task follows spec §4.5 and the owner's answer that a refusal sends the filer to the step or page that holds the value, so the link stays as the spec has it. The owner's options: a correction field for the employer name on `/documents` (recommended; the backend's `validate` endpoint already reruns the aggregate), no link and a sentence of its own, or a bound at ingest. It goes into spec errata §11 and the hand-over list; production is unaffected until steps 3–5.
- **The two Important findings, fixed in round 1:**
  - Every step-link test used `debtor_info`, the first `WIZARD_STEPS` entry, so a lookup that sent every step to step 1 passed. The Download test now refuses with `IncomeNotSplit` (`step: "income_info"`) and expects "Go to Income"; Step 14 shows it red under that lookup.
  - No card test showed a page link. Form 103B's Generate is now refused with `page: "/fee-waiver"` and "“Type of assistance” is too long…", the real label of Form 103B's `3 type` box (rule `fee_waiver_benefit_types`), and a card names `/intake` when no block above offers "Finish your intake". Step 15 shows both red when a card links only a step.
- **Round 1's Minors:** the test copies of the letter sentence use the backend's straight apostrophe in "can't" (Minor 1). The `/ask/` example is `/ask/form_107`, a page a binding can name, and `/sofa` is shown on `schedule_d`, whose synthetic group binds `sofa.creditor_payments`, since no production schema has a `sofa.` binding (Minor 2). The download-reason test's comment calls its card generated, not filed (Minors 3 and 16). The unknown-`?step=` test saves the filer at step 5, so neither the first step nor the last stands in for the saved one (Minor 15). A client test refreshes an expired token once before reading a refusal (Minor 17). The page-order test (Minors 10 and 14) and the card's own "Finish your intake" test (Minor 6) are new.
- **R70, fix round 2 (wording and tests only):** the comments, `CLAUDE.md` and the commit body say "Generate All returns it in `generated`" (a filed form included); the commit body says `refusalOf` serves the thrown refusals only; the Try-again test pins the drop after the read; and the two packet-list tests are titled for what they assert, the words "Finish your intake" shown once, since the packet list's "Go to Income" is now a second link into the intake. The controller read the delta and accepted it without another re-review.
- **Mutants that survive, each unreachable from the server:** Generate All's list skipping the once-only rule (no list entry can name `/intake`: `generate_all` refuses an unfinished intake for the whole call); `PAGE_LINK_LABELS` read with a plain lookup (the backend's pages are fixed strings); and the packet list's refusal moved in, or out of, the once-only order (it never names `/intake`).
- **Ticket candidates, not fixed (R69):** autosave drops an edit made less than 2 s before the wizard unmounts (`useAutoSave`, pre-existing), and the fix links make that likely: a filer who fixes a letter and presses Back at once returns to the same refusal. `AskModulePage`'s `h1` for `form_101` and `form_107`.

_What was checked:_

- The implementer showed the first build's new tests red on the parent, and every new test and changed assertion of each later round red on the commit before it or under a mutation: 22 of 22 mutations red on this commit, M1–M22 in `.claude/plan3a2-work/t08/mutate.py`. Steps 11 to 18 run nine mutations: three that prove the tests which pass on the parent, and six the reviews found surviving before their fixes (K6, K15, K21 adapted, K26, K27 and X7).
- E2E locators are unchanged: `.form-card` doesn't match `.form-card-refusal`, the Download button keeps its name, and no journey reads the retry sentence.
- The commit ends with `Refs DIG-137`, the ticket spec §7 names for Generate All.

_Left as found (pre-existing):_

- `FormCard.handleAction` still drops a refused Mark as Filed, and `handleMarkFiled` has no `catch`.
- `src/test/accessibility.test.tsx` renders `FormCard` with an `onMarkDownloaded` prop that doesn't exist and no `onDownload` (`tsconfig.app.json` doesn't type-check tests). Its dashboard test runs axe before the forms load, and once printed five `act(...)` warnings.
- Every dashboard test sends `POST /intake/sessions/1/dischargeability/` and `POST /audit/logs/` with no MSW handler, so MSW warns.
- Frontend survey §10: `e2e/pages/dashboard.page.ts` reads `.form-card-status`; `formsAPI.markDownloaded` has no caller; `client.ts` and `utils/retry.ts` import each other; `ProtectedRoute` drops `?step=` through a login; and a form refused on a Generate All rerun drops off the dashboard until a reload (`setForms(response.generated)`; the ledger's ticket candidate).

- [ ] **Step 1: Write the tests**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/api/__tests__/client.test.ts b/frontend/src/api/__tests__/client.test.ts
index a6b5a61..a854f64 100644
--- a/frontend/src/api/__tests__/client.test.ts
+++ b/frontend/src/api/__tests__/client.test.ts
@@ -1,6 +1,6 @@
 import { http, HttpResponse } from 'msw';
 import { server } from '../../test/mocks/server';
-import { api, APIClientError } from '../client';
+import { api, APIClientError, setAccessToken, setRefreshToken } from '../client';

 /** The error a call rejects with, so its fields can be read. */
 async function refusalOf(call: Promise<unknown>): Promise<APIClientError> {
@@ -73,6 +73,65 @@ describe('what a refusal says fixes it', () => {
     expect(notSplit.page).toBeUndefined();
   });

+  it('keeps a refused download’s own words and the step that fixes it', async () => {
+    const letter =
+      "The court form can't print the letter “ą” in “Last name”. Change it to a letter without the mark.";
+    server.use(
+      http.get('http://localhost:8000/api/forms/:id/download/', () =>
+        HttpResponse.json(
+          { form_type: 'form_101', error: letter, step: 'debtor_info' },
+          { status: 422 }
+        )
+      )
+    );
+
+    const err = await refusalOf(api.forms.downloadForm(1, 'form_101.pdf'));
+
+    expect(err.statusCode).toBe(422);
+    expect(err.message).toBe(letter);
+    expect(err.serverError).toBe(letter);
+    expect(err.step).toBe('debtor_info');
+    expect(err.page).toBeUndefined();
+  });
+
+  // An access token lasts 30 minutes: an expired one is refreshed once before the refusal is read
+  it('reads a refused download’s words only after refreshing an expired token', async () => {
+    const notSplit = 'Enter your income by source on the Income step.';
+    let downloads = 0;
+    let refreshes = 0;
+    server.use(
+      http.get('http://localhost:8000/api/forms/:id/download/', () => {
+        downloads += 1;
+        return downloads === 1
+          ? HttpResponse.json(
+              { detail: 'Given token not valid for any token type' },
+              { status: 401 }
+            )
+          : HttpResponse.json(
+              { form_type: 'form_101', error: notSplit, step: 'income_info' },
+              { status: 422 }
+            );
+      }),
+      http.post('http://localhost:8000/api/token/refresh/', () => {
+        refreshes += 1;
+        return HttpResponse.json({ access: 'refreshed-access-token' });
+      })
+    );
+    setRefreshToken('mock-refresh-token');
+
+    try {
+      const err = await refusalOf(api.forms.downloadForm(1, 'form_101.pdf'));
+
+      expect(refreshes).toBe(1);
+      expect(downloads).toBe(2);
+      expect(err.statusCode).toBe(422);
+      expect(err.message).toBe(notSplit);
+      expect(err.step).toBe('income_info');
+    } finally {
+      setAccessToken(null);
+    }
+  });
+
   it('keeps no step or page that is not a string, such as a field error', async () => {
     server.use(
       http.post('http://localhost:8000/api/forms/generate_all/', () =>
PATCH
```

`downloadForm` must reject a refused download with the refusal's own words and step, also when it first refreshes an expired token: one refresh, two downloads, and the 422's words.

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/FormDashboard.test.tsx b/frontend/src/pages/__tests__/FormDashboard.test.tsx
index 1c16e80..7a8a04f 100644
--- a/frontend/src/pages/__tests__/FormDashboard.test.tsx
+++ b/frontend/src/pages/__tests__/FormDashboard.test.tsx
@@ -313,6 +313,10 @@ describe('FormDashboard', () => {
     const failure = within(screen.getByRole('alert')).getByRole('listitem');
     expect(failure).toHaveTextContent('Form 101 - Voluntary Petition: Missing debtor name');
     expect(failure).not.toHaveTextContent('form_101');
+    // An error that names no fix leaves trying again as the filer's only move
+    expect(
+      screen.getByText(/You can try generating them individually below\./)
+    ).toBeInTheDocument();
   });

   // ---------------------------------------------------------------------------
@@ -330,6 +334,11 @@ describe('FormDashboard', () => {
     const SERVER_FAILURE = "This form couldn't be prepared. Please try again later.";
     const GENERIC =
       'Something went wrong. Your information is safe — please try again in a moment.';
+    // A single form's refusals, as the server words them (step 3a2 spec §4.5)
+    const LETTER =
+      "The court form can't print the letter “ą” in “Last name”. Change it to a letter without the mark.";
+    const TOO_LONG =
+      '“Name of Financial Institution” is too long to fit on the court form, even in small print. Shorten it.';

     /** Open Generate All and tick the UPL notice; returns the notice's Continue button. */
     async function openGenerateAll() {
@@ -364,7 +373,7 @@ describe('FormDashboard', () => {
       expect(screen.queryByText(/unable to load your forms/i)).not.toBeInTheDocument();
     });

-    it('offers the way back to the intake, not a retry, when the packet list is refused', async () => {
+    it('offers the step that fixes it, not a retry, when the packet list is refused', async () => {
       // A completed filer whose income isn't split gets the same refusal on every reload
       server.use(
         http.get('http://localhost:8000/api/forms/packet/', () =>
@@ -375,9 +384,9 @@ describe('FormDashboard', () => {
       renderFormDashboard();

       await screen.findByText(INCOME_NOT_SPLIT);
-      expect(screen.getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
+      expect(screen.getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
         'href',
-        '/intake'
+        '/intake?step=income_info'
       );
       expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
     });
@@ -427,31 +436,150 @@ describe('FormDashboard', () => {
       expect(screen.queryByText(GENERIC)).not.toBeInTheDocument();
     });

-    it('shows generic words, never the server’s, when Generate All fails on the server', async () => {
+    // A run repeated behind the filer's back can start four at once (step 3a2 spec §7)
+    it('sends Generate All once, and shows generic words, never the server’s, when it fails on the server', async () => {
+      let generateAllCalls = 0;
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () => {
+          generateAllCalls += 1;
+          return HttpResponse.json({ error: SERVER_FAILURE }, { status: 500 });
+        })
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+
+      expect(await screen.findByText(GENERIC)).toBeInTheDocument();
+      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
+      expect(generateAllCalls).toBe(1);
+    });
+
+    it('links a form Generate All refused to the step that fixes it, with no advice to retry', async () => {
       server.use(
         http.post('http://localhost:8000/api/forms/generate_all/', () =>
-          HttpResponse.json({ error: SERVER_FAILURE }, { status: 500 })
+          HttpResponse.json({
+            generated: [],
+            errors: [{ form_type: 'form_101', error: LETTER, step: 'debtor_info' }],
+            total_generated: 0,
+            total_errors: 1,
+          })
         )
       );

       renderFormDashboard();
-      const continueBtn = await openGenerateAll();
+      await userEvent.click(await openGenerateAll());

-      // A 500 is tried three more times (0.5 s, 1 s, 2 s apart) before the dashboard gives up
-      vi.useFakeTimers();
-      try {
-        fireEvent.click(continueBtn);
-        for (let second = 0; second < 5; second += 1) {
-          await act(async () => {
-            await vi.advanceTimersByTimeAsync(1000);
-          });
-        }
-      } finally {
-        vi.useRealTimers();
-      }
+      const failure = within(await screen.findByRole('alert')).getByRole('listitem');
+      expect(failure).toHaveTextContent(`Form 101 - Voluntary Petition: ${LETTER}`);
+      expect(within(failure).getByRole('link', { name: 'Go to Your Information' })).toHaveAttribute(
+        'href',
+        '/intake?step=debtor_info'
+      );
+      expect(screen.queryByText(/try generating them individually/i)).not.toBeInTheDocument();
+    });

-      expect(await screen.findByText(GENERIC)).toBeInTheDocument();
-      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
+    it('still suggests generating one at a time when any form Generate All refused names no fix', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({
+            generated: [],
+            errors: [
+              { form_type: 'form_101', error: LETTER, step: 'debtor_info' },
+              { form_type: 'form_121', error: SERVER_FAILURE },
+            ],
+            total_generated: 0,
+            total_errors: 2,
+          })
+        )
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+
+      const alert = await screen.findByRole('alert');
+      expect(alert).toHaveTextContent(
+        '2 forms could not be generated. You can try generating them individually below.'
+      );
+      const [letter, serverFailure] = within(alert).getAllByRole('listitem');
+      expect(
+        within(letter).getByRole('link', { name: 'Go to Your Information' })
+      ).toBeInTheDocument();
+      expect(within(serverFailure).queryByRole('link')).not.toBeInTheDocument();
+    });
+
+    // The words of each link go to the owner with the plan (ruling R22). Each page is one a
+    // binding of that form can name: the fee-waiver rules, a SOFA list (the synthetic Schedule D
+    // group's), the pay stub's employer name, and Form 107's asked answers.
+    it('names each page that fixes a form Generate All refused', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({
+            generated: [],
+            errors: [
+              { form_type: 'form_103b', error: TOO_LONG, page: '/fee-waiver' },
+              { form_type: 'schedule_d', error: TOO_LONG, page: '/sofa' },
+              { form_type: 'schedule_i', error: TOO_LONG, page: '/documents' },
+              { form_type: 'form_107', error: TOO_LONG, page: '/ask/form_107' },
+            ],
+            total_generated: 0,
+            total_errors: 4,
+          })
+        )
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+
+      const alert = await screen.findByRole('alert');
+      const links = within(alert)
+        .getAllByRole('link')
+        .map((link) => [link.textContent, link.getAttribute('href')]);
+      expect(links).toEqual([
+        ['Go to Filing Fee Waiver Application', '/fee-waiver'],
+        ['Go to Statement of Financial Affairs', '/sofa'],
+        ['Go to Upload your documents', '/documents'],
+        ['Answer the questions for Form 107 - Financial Affairs', '/ask/form_107'],
+      ]);
+      expect(screen.queryByText(/try generating them individually/i)).not.toBeInTheDocument();
+    });
+
+    // A page is linked only by words this page has for it, never by a built-in property's name
+    it('offers no link for a page it has no words for, such as /ask/constructor', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({
+            generated: [],
+            errors: [{ form_type: 'form_107', error: TOO_LONG, page: '/ask/constructor' }],
+            total_generated: 0,
+            total_errors: 1,
+          })
+        )
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+
+      const alert = await screen.findByRole('alert');
+      expect(within(alert).queryByRole('link')).not.toBeInTheDocument();
+      expect(alert).toHaveTextContent('You can try generating them individually below.');
+    });
+
+    it('links a refused Generate All to the step that fixes it', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json(NOT_SPLIT, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+
+      const alert = await screen.findByRole('alert');
+      expect(alert).toHaveTextContent(INCOME_NOT_SPLIT);
+      expect(within(alert).getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
+        'href',
+        '/intake?step=income_info'
+      );
     });

     // The intake was reopened since this page loaded it as complete (step 3a1 spec §4.4)
@@ -490,7 +618,7 @@ describe('FormDashboard', () => {
     });

     // This page loaded the intake as unfinished; it was completed since, elsewhere
-    it('adds no second link back to the intake when a refused packet list names its fix', async () => {
+    it('shows the words "Finish your intake" once when the packet list is refused while the unfinished-intake notice shows', async () => {
       server.use(
         http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
           HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
@@ -507,7 +635,7 @@ describe('FormDashboard', () => {
     });

     // This page loaded the intake as complete; it was reopened since, elsewhere
-    it('adds no second link back to the intake when both the packet list and Generate All are refused', async () => {
+    it('shows the words "Finish your intake" once when both the packet list and Generate All are refused', async () => {
       let packetCalls = 0;
       server.use(
         http.get('http://localhost:8000/api/forms/packet/', () => {
@@ -590,9 +718,9 @@ describe('FormDashboard', () => {
       await userEvent.click(await openGenerateAll());

       expect(await screen.findByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
-      expect(screen.getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
+      expect(screen.getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
         'href',
-        '/intake'
+        '/intake?step=income_info'
       );
       expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
     });
@@ -651,4 +779,298 @@ describe('FormDashboard', () => {
       expect(screen.getByText('Form 121 - SSN Statement')).toBeInTheDocument();
     });
   });
+
+  // ---------------------------------------------------------------------------
+  // A single form refused on its card (step 3a2 spec §4.5)
+  // ---------------------------------------------------------------------------
+
+  describe('when a form’s Generate or Download is refused', { timeout: 15_000 }, () => {
+    const LETTER =
+      "The court form can't print the letter “ą” in “Last name”. Change it to a letter without the mark.";
+    const TOO_LONG =
+      '“Name of Financial Institution” is too long to fit on the court form, even in small print. Shorten it.';
+    const FINISH_INTAKE = 'Finish your intake before preparing your forms.';
+    const INCOME_NOT_SPLIT = 'Enter your income by source on the Income step.';
+    const SERVER_FAILURE = "This form couldn't be prepared. Please try again later.";
+    const GENERIC =
+      'Something went wrong. Your information is safe — please try again in a moment.';
+    // Form 101 is generated (id 1) and Form 121 is not, in the default handlers
+    const GENERATED = 'Form 101 - Voluntary Petition';
+    const PENDING = 'Form 121 - SSN Statement';
+
+    /** The card of the form with this label, once the forms have loaded */
+    async function cardOf(label: string) {
+      return screen.findByRole('article', { name: label });
+    }
+
+    /** Answers each download of Form 101 in turn with these responses, the last one repeated */
+    function downloads(...responses: Array<() => Response>) {
+      let calls = 0;
+      server.use(
+        http.get('http://localhost:8000/api/forms/:id/download/', () => {
+          calls += 1;
+          return responses[Math.min(calls, responses.length) - 1]();
+        })
+      );
+    }
+
+    const refused =
+      (body: Record<string, string>, status = 422) =>
+      () =>
+        HttpResponse.json(body, { status });
+
+    /** Open Generate All and confirm it through the UPL notice */
+    async function generateAll() {
+      await userEvent.click(await screen.findByRole('button', { name: /generate all/i }));
+      await userEvent.click(screen.getByRole('checkbox'));
+      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
+    }
+
+    it('links a form whose Generate was refused to the step that fixes it', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate/', () =>
+          HttpResponse.json(
+            { form_type: 'form_121', error: LETTER, step: 'debtor_info' },
+            { status: 422 }
+          )
+        )
+      );
+
+      renderFormDashboard();
+      const card = await cardOf(PENDING);
+      await userEvent.click(within(card).getByRole('button', { name: 'Generate' }));
+
+      expect(await within(card).findByText(LETTER)).toBeInTheDocument();
+      expect(within(card).getByRole('link', { name: 'Go to Your Information' })).toHaveAttribute(
+        'href',
+        '/intake?step=debtor_info'
+      );
+    });
+
+    // An unfiled form's download works the means test out again, which needs income by source
+    it('links a form whose download was refused to the step that fixes it', async () => {
+      downloads(refused({ form_type: 'form_101', error: INCOME_NOT_SPLIT, step: 'income_info' }));
+
+      renderFormDashboard();
+      const card = await cardOf(GENERATED);
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+
+      expect(await within(card).findByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
+      expect(within(card).getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
+        'href',
+        '/intake?step=income_info'
+      );
+    });
+
+    it('links a form whose Generate was refused to the page that fixes it', async () => {
+      // The fee-waiver application feeds Form 103B, which is in the packet only with one
+      const TYPE_TOO_LONG =
+        '“Type of assistance” is too long to fit on the court form, even in small print. Shorten it.';
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () =>
+          HttpResponse.json({ session: 1, form_types: ['form_101', 'form_103b'] })
+        ),
+        http.post('http://localhost:8000/api/forms/generate/', () =>
+          HttpResponse.json(
+            { form_type: 'form_103b', error: TYPE_TOO_LONG, page: '/fee-waiver' },
+            { status: 422 }
+          )
+        )
+      );
+
+      renderFormDashboard();
+      const card = await cardOf('Form 103B - Fee Waiver Application');
+      await userEvent.click(within(card).getByRole('button', { name: 'Generate' }));
+
+      expect(await within(card).findByText(TYPE_TOO_LONG)).toBeInTheDocument();
+      expect(
+        within(card).getByRole('link', { name: 'Go to Filing Fee Waiver Application' })
+      ).toHaveAttribute('href', '/fee-waiver');
+    });
+
+    // The context says the intake is complete, so no notice links to it; the server reopened it
+    it('links a form’s refusal back to the intake when nothing above it does', async () => {
+      downloads(refused({ form_type: 'form_101', error: FINISH_INTAKE, page: '/intake' }));
+
+      renderFormDashboard();
+      const card = await cardOf(GENERATED);
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+
+      expect(await within(card).findByText(FINISH_INTAKE)).toBeInTheDocument();
+      expect(within(card).getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
+        'href',
+        '/intake'
+      );
+      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
+    });
+
+    // A live region announces only changes to a region already on the page
+    it('shows why a download was refused, in a polite region that was on the card before it', async () => {
+      // A refusal that names no fix, as a filed form's does (R46), here on a generated card
+      downloads(refused({ form_type: 'form_101', error: TOO_LONG }));
+
+      renderFormDashboard();
+      const card = await cardOf(GENERATED);
+      const politeRegionsBefore = Array.from(card.querySelectorAll('[aria-live="polite"]'));
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+
+      const reason = await within(card).findByText(TOO_LONG);
+      expect(politeRegionsBefore).toContain(reason.closest('[aria-live="polite"]'));
+      expect(within(card).queryByRole('link')).not.toBeInTheDocument();
+    });
+
+    it('shows generic words, never the server’s, when a download fails on the server', async () => {
+      downloads(refused({ error: SERVER_FAILURE }, 500));
+
+      renderFormDashboard();
+      const card = await cardOf(GENERATED);
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+
+      expect(await within(card).findByText(GENERIC)).toBeInTheDocument();
+      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
+    });
+
+    it('clears a form’s refusal once its Generate succeeds', async () => {
+      let generateCalls = 0;
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate/', () => {
+          generateCalls += 1;
+          return generateCalls === 1
+            ? HttpResponse.json(
+                { form_type: 'form_121', error: LETTER, step: 'debtor_info' },
+                { status: 422 }
+              )
+            : HttpResponse.json({
+                form: { id: 2, session: 1, form_type: 'form_121', status: 'generated' },
+                message: 'Form generated.',
+              });
+        })
+      );
+
+      renderFormDashboard();
+      const card = await cardOf(PENDING);
+      await userEvent.click(within(card).getByRole('button', { name: 'Generate' }));
+      await within(card).findByText(LETTER);
+
+      await userEvent.click(within(card).getByRole('button', { name: 'Generate' }));
+
+      expect(await within(card).findByRole('button', { name: 'Download' })).toBeInTheDocument();
+      expect(within(card).queryByText(LETTER)).not.toBeInTheDocument();
+      expect(within(card).queryByRole('link')).not.toBeInTheDocument();
+    });
+
+    it('clears a form’s refusal once its download succeeds', async () => {
+      // jsdom has no object URLs and doesn't follow a download link
+      const objectUrls = {
+        createObjectURL: URL.createObjectURL,
+        revokeObjectURL: URL.revokeObjectURL,
+      };
+      URL.createObjectURL = () => 'blob:pdf';
+      URL.revokeObjectURL = () => {};
+      const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
+      downloads(
+        refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }),
+        () =>
+          new HttpResponse(new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d]), {
+            headers: { 'Content-Type': 'application/pdf' },
+          })
+      );
+
+      try {
+        renderFormDashboard();
+        const card = await cardOf(GENERATED);
+        await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+        await within(card).findByText(LETTER);
+
+        await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+
+        await waitFor(() => expect(click).toHaveBeenCalled());
+        // The forms reload after a download, so the card is drawn again once they have
+        await waitFor(() => {
+          expect(screen.queryByText('Loading your forms...')).not.toBeInTheDocument();
+          expect(screen.getByRole('article', { name: GENERATED })).toBeInTheDocument();
+          expect(screen.queryByText(LETTER)).not.toBeInTheDocument();
+        });
+        expect(
+          screen.queryByRole('link', { name: 'Go to Your Information' })
+        ).not.toBeInTheDocument();
+      } finally {
+        click.mockRestore();
+        Object.assign(URL, objectUrls);
+      }
+    });
+
+    // Ruling R4-a: "Finish your intake" shows at most once, on the first block that offers it
+    it('adds no second link back to the intake when a form’s refusal names it', async () => {
+      server.use(
+        http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+          HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
+        )
+      );
+      downloads(refused({ form_type: 'form_101', error: FINISH_INTAKE, page: '/intake' }));
+
+      renderFormDashboard();
+      const card = await cardOf(GENERATED);
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+
+      expect(await within(card).findByText(FINISH_INTAKE)).toBeInTheDocument();
+      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
+    });
+
+    // Ruling R4-a, in page order: Generate All's refusal sits above every card
+    it('keeps "Finish your intake" on Generate All’s refusal, not on a card below it that names it too', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({ error: FINISH_INTAKE, page: '/intake' }, { status: 422 })
+        )
+      );
+      downloads(refused({ form_type: 'form_101', error: FINISH_INTAKE, page: '/intake' }));
+
+      renderFormDashboard();
+      await generateAll();
+      const wholeCall = await screen.findByRole('alert');
+      const card = await cardOf(GENERATED);
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+      await within(card).findByText(FINISH_INTAKE);
+
+      expect(within(wholeCall).getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
+        'href',
+        '/intake'
+      );
+      expect(within(card).queryByRole('link')).not.toBeInTheDocument();
+    });
+
+    it('clears a form’s refusal once Generate All generates it', async () => {
+      // The default Generate All prepares Form 101
+      downloads(refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }));
+
+      renderFormDashboard();
+      const card = await cardOf(GENERATED);
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+      await within(card).findByText(LETTER);
+
+      await generateAll();
+
+      await waitFor(() => expect(within(card).queryByText(LETTER)).not.toBeInTheDocument());
+      expect(within(card).queryByRole('link')).not.toBeInTheDocument();
+    });
+
+    it('clears a form’s refusal once it is marked filed', async () => {
+      downloads(refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }));
+
+      renderFormDashboard();
+      const card = await cardOf(GENERATED);
+      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
+      await within(card).findByText(LETTER);
+
+      await userEvent.click(within(card).getByRole('button', { name: 'Mark as Filed' }));
+
+      // Marking a form filed reloads the forms, so the card is drawn again once they have
+      await waitFor(() => {
+        expect(screen.queryByText('Loading your forms...')).not.toBeInTheDocument();
+        expect(screen.getByRole('article', { name: GENERATED })).toBeInTheDocument();
+        expect(screen.queryByText(LETTER)).not.toBeInTheDocument();
+      });
+    });
+  });
 });
PATCH
```

The dashboard tests, in two describes:

- **Generate All and the packet list.** Generate All is sent once on a server error: a request counter replaces the fake-timer scaffolding that waited out three retries, and must read 1. A form Generate All refused shows its message and its link, and the retry sentence goes, unless some listed form names no fix. Four list entries pin the page link words and their `href`s, one per page a binding of that form can name. `/ask/constructor` gets no link. Generate All's refusal of the whole call, and the packet list's refusal, link `IncomeNotSplit` as "Go to Income". The existing partial-failure test also asserts the retry sentence for an error that names no fix, and two packet-list tests are retitled.
- **A card's Generate or Download** (a new describe with a 15 s timeout, like the one above it, so a test that never finds its text fails on that search's own error rather than on vitest's 5 s test timeout). A refused Generate links to the step that fixes it, a refused Download to Income, and Form 103B's refused Generate to the fee-waiver page. A card names `/intake` when nothing above it does, adds no second link when the notice does, and leaves the link on Generate All's refusal when that names it too. A refusal with no fix shows its words, with no link, in a polite region that was on the card before it; a download that fails on the server shows the generic words. The refusal clears when the form's Generate or Download succeeds, when Generate All returns it, and when it is marked filed.

The sentences are the backend's: "The court form can't print the letter “ą” in “Last name”. Change it to a letter without the mark." (straight apostrophe, curly quotes) and "“Name of Financial Institution” is too long to fit on the court form, even in small print. Shorten it."

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/IntakeWizard.test.tsx b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
index 164a547..f9e3bbd 100644
--- a/frontend/src/pages/__tests__/IntakeWizard.test.tsx
+++ b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
@@ -1,7 +1,7 @@
 import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
 import { vi } from 'vitest';
 import userEvent from '@testing-library/user-event';
-import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
+import { MemoryRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
 import { http, HttpResponse } from 'msw';
 import { server } from '../../test/mocks/server';
 import { IntakeProvider, useIntake } from '../../context/IntakeContext';
@@ -51,10 +51,10 @@ const sessionAtStep1 = {
   debts: [],
 };

-function renderWizard() {
+function renderWizard(entry = '/intake') {
   localStorage.setItem('current_session_id', '1');
   return render(
-    <MemoryRouter initialEntries={['/intake']}>
+    <MemoryRouter initialEntries={[entry]}>
       <IntakeProvider>
         <Routes>
           <Route path="/intake" element={<IntakeWizard />} />
@@ -855,6 +855,121 @@ describe('IntakeWizard session re-read', { timeout: 15_000 }, () => {
     ).toBeInTheDocument();
     expect(sessionsCreated).toBe(1);
   });
+
+  /** The server holds this session; returns how many update_step calls went out. */
+  function savedAs(saved: Record<string, unknown>) {
+    const stepUpdates = { count: 0 };
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(saved)),
+      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () => {
+        stepUpdates.count += 1;
+        return HttpResponse.json({ session: saved, message: 'Step updated.' });
+      })
+    );
+    return stepUpdates;
+  }
+
+  /** What the address bar holds, and the browser's Back button */
+  function AddressBar() {
+    const location = useLocation();
+    const navigate = useNavigate();
+    return (
+      <>
+        <p data-testid="address">{location.pathname + location.search}</p>
+        <button type="button" onClick={() => navigate(-1)}>
+          Browser back
+        </button>
+      </>
+    );
+  }
+
+  // The dashboard links a refusal to the step that fixes it (step 3a2 spec §4.5)
+  it('opens at the step a link names, without moving the filer’s saved place', async () => {
+    // The intake is complete, so it would open at Review
+    const stepUpdates = savedAs({ ...sessionAtStep8, status: 'completed' });
+
+    renderWizard('/intake?step=expense_info');
+
+    expect(await screen.findByRole('heading', { name: 'Expenses', level: 2 })).toBeInTheDocument();
+    expect(stepUpdates.count).toBe(0);
+  });
+
+  // A refresh then opens the saved step, and Back leaves the wizard rather than reopening the link
+  it('drops the step from the address once it has opened it, without a new history entry', async () => {
+    const stepUpdates = savedAs({ ...sessionAtStep8, status: 'completed' });
+    localStorage.setItem('current_session_id', '1');
+    render(
+      <MemoryRouter initialEntries={['/forms', '/intake?step=expense_info']} initialIndex={1}>
+        <IntakeProvider>
+          <Routes>
+            <Route path="/intake" element={<IntakeWizard />} />
+            <Route path="/forms" element={<div>FormDashboard</div>} />
+          </Routes>
+          <AddressBar />
+        </IntakeProvider>
+      </MemoryRouter>
+    );
+
+    await screen.findByRole('heading', { name: 'Expenses', level: 2 });
+    await waitFor(() => expect(screen.getByTestId('address')).toHaveTextContent(/^\/intake$/));
+    expect(stepUpdates.count).toBe(0);
+
+    await userEvent.click(screen.getByRole('button', { name: 'Browser back' }));
+
+    expect(await screen.findByText('FormDashboard')).toBeInTheDocument();
+  });
+
+  // The step is dropped only once it has opened, so a refresh during a failed read still opens it
+  it('keeps the linked step in the address while the read fails, and drops it once Try again opens it', async () => {
+    let serverBusy = true;
+    const stepUpdates = { count: 0 };
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        serverBusy
+          ? HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
+          : HttpResponse.json({ ...sessionAtStep8, status: 'completed' })
+      ),
+      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () => {
+        stepUpdates.count += 1;
+        return HttpResponse.json({ session: sessionAtStep8, message: 'Step updated.' });
+      })
+    );
+    localStorage.setItem('current_session_id', '1');
+    render(
+      <MemoryRouter initialEntries={['/intake?step=expense_info']}>
+        <IntakeProvider>
+          <Routes>
+            <Route path="/intake" element={<IntakeWizard />} />
+          </Routes>
+          <AddressBar />
+        </IntakeProvider>
+      </MemoryRouter>
+    );
+
+    expect(await screen.findByRole('alert')).toHaveTextContent(
+      "We couldn't get your latest information just now. Please try again in a moment."
+    );
+    expect(screen.getByTestId('address')).toHaveTextContent('/intake?step=expense_info');
+
+    serverBusy = false;
+    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
+
+    expect(await screen.findByRole('heading', { name: 'Expenses', level: 2 })).toBeInTheDocument();
+    await waitFor(() => expect(screen.getByTestId('address')).toHaveTextContent(/^\/intake$/));
+    expect(stepUpdates.count).toBe(0);
+  });
+
+  it('opens at the saved step when a link names no step of the wizard', async () => {
+    // Saved mid-wizard, so neither the first step nor the last stands in for it
+    const stepUpdates = savedAs({ ...sessionAtStep1, current_step: 5 });
+
+    renderWizard('/intake?step=sofa');
+
+    expect(
+      await screen.findByRole('heading', { name: 'Amounts Owed', level: 2 })
+    ).toBeInTheDocument();
+    expect(stepUpdates.count).toBe(0);
+  });
 });

 // ===========================================================================
PATCH
```

`renderWizard` takes the address to open. The wizard must open at the step a link names without an `update_step`, drop `?step=` from the address with no new history entry (Back from there reaches `/forms`), keep it while the read fails and drop it once Try again opens the step, and open the saved step, saved mid-wizard at step 5, for a key that names no step.

- [ ] **Step 2: Run the tests and watch them fail**

```bash
set -eo pipefail
(cd frontend && NO_COLOR=1 npx vitest run src/api/__tests__/client.test.ts src/pages/__tests__/FormDashboard.test.tsx src/pages/__tests__/IntakeWizard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Test Files  3 failed (3)` and `Tests  24 failed | 86 passed (110)`, with `AssertionError: expected 4 to be 1`, `AssertionError: expected 'Download failed (422)' to be 'The court form can\'t print the lette…'`, `Unable to find an accessible element with the role "link" and name "Go to Income"` and `TestingLibraryElementError: Unable to find role="heading" and name "Expenses"`.

- **`client.test.ts`, 2 of 5:** a refused download throws "Download failed (422)" and drops the body, with or without a refresh first.
- **`FormDashboard.test.tsx`, 19 of 47:**
  - Generate All is sent four times (`expected 4 to be 1`).
  - No refusal links to a step or a page: Generate All's list (three tests), its refusal of the whole call, and the packet list (two tests, which now expect "Go to Income").
  - All twelve card tests fail where they look for the refusal's words on the card, which never shows a refusal.
- **`IntakeWizard.test.tsx`, 3 of 58:** the three linked-step tests can't find the Expenses heading; the wizard opens the saved step, Review.

Five new or changed tests pass here. Two are the packet-list tests retitled under R70, whose bodies are unchanged: `shows the words "Finish your intake" once when the packet list is refused while the unfinished-intake notice shows` and `shows the words "Finish your intake" once when both the packet list and Generate All are refused`. Three carry new assertions. The unknown-`?step=` test passes because this wizard ignores `?step=` altogether; the `/ask/constructor` test because this dashboard links no list entry; and the partial-failure test's new assertion because this dashboard always shows the retry sentence. Steps 11 to 13 show each of those three fail against a wrong version of this task's code.

- [ ] **Step 3: Send Generate All once, and read a refused download's body**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/api/client.ts b/frontend/src/api/client.ts
index e163c96..ae17814 100644
--- a/frontend/src/api/client.ts
+++ b/frontend/src/api/client.ts
@@ -578,9 +578,11 @@ export const formsAPI = {
   /**
    * Generate every form in the session's packet
    * POST /api/forms/generate_all/
+   * Sent once, never retried: a slow or failed run is not repeated behind the filer's back
+   * (step 3a2 spec §7). The dashboard shows the error, and the filer can press again.
    */
   generateAll: async (sessionId: number): Promise<GenerateAllFormsResponse> => {
-    return apiFetch<GenerateAllFormsResponse>('/forms/generate_all/', {
+    return apiFetchOnce<GenerateAllFormsResponse>('/forms/generate_all/', {
       method: 'POST',
       body: JSON.stringify({ session_id: sessionId }),
     });
@@ -622,7 +624,8 @@ export const formsAPI = {
   /**
    * Download a generated form as a filled PDF.
    * GET /api/forms/{id}/download/
-   * Triggers a browser file save dialog.
+   * Triggers a browser file save dialog. A refused download throws the refusal's own words and
+   * the step or page that fixes it, as every other call does.
    */
   downloadForm: async (formId: number, filename: string): Promise<void> => {
     const doFetch = () => {
@@ -637,7 +640,7 @@ export const formsAPI = {
       if (refreshed) response = await doFetch();
     }
     if (!response.ok) {
-      throw new APIClientError(`Download failed (${response.status})`, response.status);
+      await handleAPIError(response);
     }
     const blob = await response.blob();
     const url = URL.createObjectURL(blob);
PATCH
```

`generateAll` calls `apiFetchOnce`, so a 5xx is never sent again behind the filer's back (spec §7). `downloadForm` hands a refused response to `handleAPIError` after its one 401 refresh, so the error carries the refusal's own words, `step` and `page`.

- [ ] **Step 4: Run the client tests**

```bash
set -eo pipefail
(cd frontend && NO_COLOR=1 npx vitest run src/api/__tests__/client.test.ts) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: `Tests  5 passed (5)`.

- [ ] **Step 5: Move the wizard's steps to their own module**

```ts file=frontend/src/constants/wizardSteps.ts
/**
 * The intake wizard's steps, in order. A refusal names the step that fixes it by its key, and
 * `/intake?step=<key>` opens that step.
 */
export const WIZARD_STEPS = [
  { number: 1, label: 'Your Information', key: 'debtor_info' },
  { number: 2, label: 'Income', key: 'income_info' },
  { number: 3, label: 'Expenses', key: 'expense_info' },
  { number: 4, label: 'Assets', key: 'assets' },
  { number: 5, label: 'Amounts Owed', key: 'debts' },
  { number: 6, label: 'Contracts & Leases', key: 'contracts' },
  { number: 7, label: 'Codebtors', key: 'codebtors' },
  { number: 8, label: 'Review & Results', key: 'review' },
];
```

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -38,21 +38,11 @@
   WizardRow,
 } from '../types/api';
 import { EXPENSE_FIELDS, INCOME_FIELDS } from '../types/api';
+import { WIZARD_STEPS } from '../constants/wizardSteps';

 // ============================================================================
 // Wizard Configuration
 // ============================================================================
-
-const WIZARD_STEPS = [
-  { number: 1, label: 'Your Information', key: 'debtor_info' },
-  { number: 2, label: 'Income', key: 'income_info' },
-  { number: 3, label: 'Expenses', key: 'expense_info' },
-  { number: 4, label: 'Assets', key: 'assets' },
-  { number: 5, label: 'Amounts Owed', key: 'debts' },
-  { number: 6, label: 'Contracts & Leases', key: 'contracts' },
-  { number: 7, label: 'Codebtors', key: 'codebtors' },
-  { number: 8, label: 'Review & Results', key: 'review' },
-];

 // DRF sends these decimals as strings ("2500.00"). The steps add and compare them,
 // so they become numbers as session data enters wizard state.
PATCH
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_rule_fixes.py b/backend/apps/forms/tests/test_rule_fixes.py
index 50f4403..cbf73b8 100644
--- a/backend/apps/forms/tests/test_rule_fixes.py
+++ b/backend/apps/forms/tests/test_rule_fixes.py
@@ -14,7 +14,7 @@ from apps.forms.schema import FieldSpec, load_schema
 from apps.forms.services.derivations import DERIVATIONS, RULE_FIXES
 from apps.forms.services.fill_resolver import fix_for

-# The keys of WIZARD_STEPS in frontend/src/pages/IntakeWizard.tsx: what /intake?step= opens.
+# The keys of WIZARD_STEPS in frontend/src/constants/wizardSteps.ts: what /intake?step= opens.
 WIZARD_STEPS = {
     "debtor_info",
     "income_info",
PATCH
```

`WIZARD_STEPS` moves, entries unchanged and without `as const` (so its element type stays as it was), to `frontend/src/constants/wizardSteps.ts`, where the dashboard can import it too. The backend test's comment that names where the keys live names the new file.

- [ ] **Step 6: Open the wizard at the step a link names**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -7,7 +7,7 @@

 import { useState, useEffect, useMemo, useRef, useLayoutEffect } from 'react';
 import { useAutoSave } from '../hooks/useAutoSave';
-import { useNavigate } from 'react-router-dom';
+import { useNavigate, useSearchParams } from 'react-router-dom';
 import { useIntake } from '../context/IntakeContext';
 import { api, APIClientError } from '../api/client';
 import { trackEvent } from '../utils/analytics';
@@ -85,6 +85,7 @@

 export function IntakeWizard() {
   const navigate = useNavigate();
+  const [searchParams, setSearchParams] = useSearchParams();
   const {
     session,
     createSession,
@@ -131,6 +132,12 @@
     const savedSessionId = localStorage.getItem('current_session_id');
     return session?.id ?? (savedSessionId ? parseInt(savedSessionId, 10) : null);
   });
+  // Fixed at mount too: the step a link names (`?step=<key>`, from a refusal on the forms
+  // dashboard), opened instead of the saved step once the read returns, and then dropped from the
+  // address. Opening it sends no update_step, so the saved step stays where Continue last put it.
+  const [linkedStep] = useState(
+    () => WIZARD_STEPS.find((step) => step.key === searchParams.get('step'))?.number
+  );
   const [sessionRead, setSessionRead] = useState<'pending' | 'failed' | 'done'>('pending');
   const [readAttempt, setReadAttempt] = useState(0);

@@ -173,7 +180,20 @@
     openSession()
       .then(({ fresh, contracts, codebtors }) => {
         if (cancelled) return;
-        setCurrentStepNumber(fresh.current_step);
+        setCurrentStepNumber(linkedStep ?? fresh.current_step);
+        // The link has done its work. Dropped from the address in place, with no new history
+        // entry, so a refresh, or Back to the wizard from a later page, opens the saved step,
+        // not the linked one again.
+        if (linkedStep !== undefined) {
+          setSearchParams(
+            (params) => {
+              const next = new URLSearchParams(params);
+              next.delete('step');
+              return next;
+            },
+            { replace: true }
+          );
+        }
         if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
         if (fresh.income_info) setIncomeData(hydrateAmounts(fresh.income_info, INCOME_FIELDS));
         if (fresh.expense_info) setExpenseData(hydrateAmounts(fresh.expense_info, EXPENSE_FIELDS));
PATCH
```

`linkedStep` reads `?step=` once at mount and keeps the number of the step whose key it names, or nothing. Once the session read returns, the wizard opens that step instead of the saved one, sends no `update_step`, and drops `step` from the address with a replace, keeping any other parameter. A failed read leaves the address alone, and Try again uses the same `linkedStep`.

- [ ] **Step 7: Run the wizard tests**

```bash
set -eo pipefail
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/IntakeWizard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: `Tests  58 passed (58)`.

- [ ] **Step 8: Give each form card a place for its refusal**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/forms/FormCard.tsx b/frontend/src/components/forms/FormCard.tsx
index 0a46029..301634f 100644
--- a/frontend/src/components/forms/FormCard.tsx
+++ b/frontend/src/components/forms/FormCard.tsx
@@ -6,17 +6,24 @@
  */

 import { useState } from 'react';
-import { useNavigate } from 'react-router-dom';
+import { Link, useNavigate } from 'react-router-dom';
 import { Button } from '../common';
 import { FormStatusBadge } from './FormStatusBadge';
 import type { GeneratedForm, FormType } from '../../types/api';
 import { FORM_TYPE_METADATA } from '../../types/api';

+/** Why this form's last Generate or Download was refused, and the link to its fix, if any */
+export interface FormRefusal {
+  message: string;
+  link?: { to: string; label: string };
+}
+
 interface FormCardProps {
   formType: FormType;
   generatedForm?: GeneratedForm;
   /** A filed form whose type is no longer in the filer's packet */
   leftPacket?: boolean;
+  refusal?: FormRefusal;
   onGenerate: (formType: FormType) => Promise<void>;
   onDownload: (formId: number) => Promise<void>;
   onMarkFiled: (formId: number) => Promise<void>;
@@ -26,6 +33,7 @@ export function FormCard({
   formType,
   generatedForm,
   leftPacket = false,
+  refusal,
   onGenerate,
   onDownload,
   onMarkFiled,
@@ -119,6 +127,21 @@ export function FormCard({
           </span>
         )}
       </div>
+
+      {/* A polite live region from the start, so a screen reader reads out a refusal that
+          Generate or Download adds to it (step 3a2 spec §4.5) */}
+      <div className="form-card-refusal" aria-live="polite">
+        {refusal && (
+          <>
+            <p>{refusal.message}</p>
+            {refusal.link && (
+              <Link to={refusal.link.to} className="button button--primary">
+                {refusal.link.label}
+              </Link>
+            )}
+          </>
+        )}
+      </div>
     </article>
   );
 }
diff --git a/frontend/src/styles/global.css b/frontend/src/styles/global.css
index 38a2ed4..37264fd 100644
--- a/frontend/src/styles/global.css
+++ b/frontend/src/styles/global.css
@@ -1538,6 +1538,12 @@ a {
   flex-wrap: wrap;
 }

+/* The live region for a refused Generate or Download is on the card from the start. Empty, it
+   gives back the gap before it, so the card looks as it did. */
+.form-card-refusal:empty {
+  margin-top: calc(-1 * var(--space-3));
+}
+
 .form-card-filed-check {
   color: var(--color-sage);
   font-weight: 600;
PATCH
```

`FormCard` takes a `refusal` (`FormRefusal`: the words, and the link to the fix if there is one) and shows it after its actions, inside a polite live region that is on the card from the first render. Empty, the region gives back the gap before it, so a card with no refusal looks as before.

- [ ] **Step 9: Link each refusal on the dashboard to its fix**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
index 772371b..438306f 100644
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -12,9 +12,11 @@ import { useIntake } from '../context/IntakeContext';
 import { api, APIClientError } from '../api/client';
 import { FormCard, GenerateAllButton, DebtExplanationsPanel } from '../components/forms';
 import type { DebtClassification } from '../components/forms/DebtExplanationsPanel';
+import type { FormRefusal } from '../components/forms/FormCard';
 import { UPLDisclaimer } from '../components/compliance';
 import { UPL_FORM_DISCLAIMER } from '../constants/upl';
 import { DASHBOARD_ERROR, ERROR_GENERIC } from '../constants/copy';
+import { WIZARD_STEPS } from '../constants/wizardSteps';
 import { Button } from '../components/common';
 import { PostTaskSurvey } from '../components/survey/PostTaskSurvey';
 import type {
@@ -28,27 +30,73 @@ import { trackEvent } from '../utils/analytics';

 type GenerateAllError = GenerateAllFormsResponse['errors'][number];

+/** What a refusal names as its fix: a wizard step (a `WIZARD_STEPS` key) or a page */
+type Fix = { step?: string; page?: string };
+
+/** A refusal in the filer's words, with what fixes it */
+type Refusal = { message: string } & Fix;
+
 /**
- * What the filer reads when Generate All or the packet list is refused as a whole
- * (forms step 2 §5.6): a 422 says in plain words what to fix; anything else gets the
- * generic words, since a 500's text is for operations.
+ * What the filer reads when a call is refused (forms step 2 §5.6), and what fixes it (step 3a2
+ * spec §4.5): a 422 says in plain words what to fix, with the step or page that fixes it;
+ * anything else gets the generic words, since a 500's text is for operations.
  */
-function wholeCallRefusal(err: unknown, generic: string): string {
-  return err instanceof APIClientError && err.statusCode === 422 ? err.message : generic;
+function refusalOf(err: unknown, generic: string): Refusal {
+  return err instanceof APIClientError && err.statusCode === 422
+    ? { message: err.message, step: err.step, page: err.page }
+    : { message: generic };
 }

-/** The words of the link to each page a refusal can name as its fix (step 3a1 spec §4.3) */
-const PAGE_LINK_LABELS: Record<string, string> = { '/intake': 'Finish your intake' };
+/**
+ * The words of the link to each page a refusal can name as its fix (step 3a1 spec §4.3): the
+ * intake's own words, and "Go to" with each other page's heading (step 3a2 spec §4.5, ruling R22)
+ */
+const PAGE_LINK_LABELS: Record<string, string> = {
+  '/intake': 'Finish your intake',
+  '/fee-waiver': 'Go to Filing Fee Waiver Application',
+  '/sofa': 'Go to Statement of Financial Affairs',
+  '/documents': 'Go to Upload your documents',
+};
+
+/**
+ * The link to what fixes a refusal (step 3a2 spec §4.5): a wizard step opens the intake at that
+ * step, `/ask/<form type>` takes its form's label, and any other page its words above. None when
+ * the refusal names no fix, or one this page has no words for. Only the maps' own keys count, so a
+ * name such as "constructor" is no form and no page.
+ */
+function fixLink({ step, page }: Fix): FormRefusal['link'] {
+  const wizardStep = WIZARD_STEPS.find((s) => s.key === step);
+  if (wizardStep) {
+    return { to: `/intake?step=${wizardStep.key}`, label: `Go to ${wizardStep.label}` };
+  }
+  if (!page) return undefined;
+  if (page.startsWith('/ask/')) {
+    const formType = page.slice('/ask/'.length);
+    return Object.hasOwn(FORM_TYPE_METADATA, formType)
+      ? {
+          to: page,
+          label: `Answer the questions for ${FORM_TYPE_METADATA[formType as FormType].label}`,
+        }
+      : undefined;
+  }
+  return Object.hasOwn(PAGE_LINK_LABELS, page)
+    ? { to: page, label: PAGE_LINK_LABELS[page] }
+    : undefined;
+}

 /**
- * A failed packet list in the filer's words, and whether its refusal names a fix: a wizard step
- * or a page (step 3a1 spec §4.3). No step fixes one that names neither, such as no median table
- * in force on the fill date.
+ * Hands out the link to each refusal's fix, called in the order the page shows them. "Finish your
+ * intake" goes only to the first block that offers it (ruling R4-a), so `intakeLinked` says
+ * whether a block above the refusals already does.
  */
-function loadFailure(err: unknown): { message: string; namesFix: boolean } {
-  return {
-    message: wholeCallRefusal(err, DASHBOARD_ERROR),
-    namesFix: err instanceof APIClientError && err.statusCode === 422 && !!(err.step || err.page),
+function linksInPageOrder(intakeLinked: boolean) {
+  let linked = intakeLinked;
+  return (fix: Fix): FormRefusal['link'] => {
+    const link = fixLink(fix);
+    if (link?.to !== '/intake') return link;
+    if (linked) return undefined;
+    linked = true;
+    return link;
   };
 }

@@ -90,13 +138,13 @@ export function FormDashboard() {
   const [packet, setPacket] = useState<FormType[]>([]);
   const [tables, setTables] = useState<DatedTableUsed[]>([]);
   const [isLoading, setIsLoading] = useState(true);
-  const [error, setError] = useState<{ message: string; namesFix: boolean } | null>(null);
+  const [error, setError] = useState<Refusal | null>(null);
   const [showSurvey, setShowSurvey] = useState(false);
   const [generationErrors, setGenerationErrors] = useState<GenerateAllError[]>([]);
-  const [generateAllRefusal, setGenerateAllRefusal] = useState<{
-    message: string;
-    page?: string;
-  } | null>(null);
+  const [generateAllRefusal, setGenerateAllRefusal] = useState<Refusal | null>(null);
+  // Each form's last refused Generate or Download, until its own Generate or Download next
+  // succeeds, Generate All returns it in `generated` (a filed form included), or it is marked filed
+  const [formRefusals, setFormRefusals] = useState<Partial<Record<FormType, Refusal>>>({});
   const [dischargeData, setDischargeData] = useState<DebtClassification[]>([]);

   // Load existing forms on mount
@@ -114,7 +162,7 @@ export function FormDashboard() {
       setTables(loadedPacket.tables);
       setError(null);
     } catch (err) {
-      setError(loadFailure(err));
+      setError(refusalOf(err, DASHBOARD_ERROR));
     } finally {
       setIsLoading(false);
     }
@@ -139,11 +187,19 @@ export function FormDashboard() {
     (f) => f.status === 'filed' && !packet.includes(f.form_type)
   );

+  const setFormRefusal = (formType: FormType, refusal?: Refusal) =>
+    setFormRefusals((prev) => ({ ...prev, [formType]: refusal }));
+
   const handleGenerate = async (formType: FormType) => {
     if (!session) return;
-    const response = await api.forms.generate(session.id, formType);
-    setForms((prev) => [...prev.filter((f) => f.form_type !== formType), response.form]);
-    trackEvent('form_generated', { form_type: formType, session_id: session.id });
+    try {
+      const response = await api.forms.generate(session.id, formType);
+      setForms((prev) => [...prev.filter((f) => f.form_type !== formType), response.form]);
+      setFormRefusal(formType, undefined);
+      trackEvent('form_generated', { form_type: formType, session_id: session.id });
+    } catch (err) {
+      setFormRefusal(formType, refusalOf(err, ERROR_GENERIC));
+    }
   };

   const handleGenerateAll = async () => {
@@ -153,14 +209,14 @@ export function FormDashboard() {
     try {
       const response = await api.forms.generateAll(session.id);
       setForms(response.generated);
+      // Every form Generate All returns in `generated` loses its card's refusal, a filed form
+      // included, which Generate All returns untouched
+      response.generated.forEach((form) => setFormRefusal(form.form_type, undefined));
       setGenerationErrors(response.errors);
       trackEvent('form_generated', { form_type: 'all', session_id: session.id });
       setShowSurvey(true);
     } catch (err) {
-      setGenerateAllRefusal({
-        message: wholeCallRefusal(err, ERROR_GENERIC),
-        page: err instanceof APIClientError ? err.page : undefined,
-      });
+      setGenerateAllRefusal(refusalOf(err, ERROR_GENERIC));
     }
     // Generate All works the means test out again, so the packet may have changed
     try {
@@ -169,19 +225,28 @@ export function FormDashboard() {
       setTables(reloaded.tables);
       setError(null);
     } catch (err) {
-      setError(loadFailure(err));
+      setError(refusalOf(err, DASHBOARD_ERROR));
     }
   };

   const handleDownload = async (formId: number) => {
     const form = forms.find((f) => f.id === formId);
     const filename = form ? `${form.form_type}.pdf` : `form_${formId}.pdf`;
-    await api.forms.downloadForm(formId, filename);
+    try {
+      await api.forms.downloadForm(formId, filename);
+    } catch (err) {
+      if (form) setFormRefusal(form.form_type, refusalOf(err, ERROR_GENERIC));
+      return;
+    }
+    if (form) setFormRefusal(form.form_type, undefined);
     await loadForms();
   };

   const handleMarkFiled = async (formId: number) => {
+    const form = forms.find((f) => f.id === formId);
     await api.forms.markFiled(formId);
+    // A filed form prints what was filed, which no step changes (ruling R46)
+    if (form) setFormRefusal(form.form_type, undefined);
     await loadForms();
   };

@@ -207,16 +272,21 @@ export function FormDashboard() {
   const filedCount = forms.filter((f) => f.status === 'filed').length;
   const generatedCount = forms.filter((f) => packet.includes(f.form_type)).length;
   const totalCount = packet.length;
-  // "Finish your intake" shows at most once, on the first block that offers it: the notice for
-  // an unfinished intake, then a packet-list refusal that names its fix, then the page Generate
-  // All's refusal names (ruling R4-a). The context's status and the server's can disagree.
+  // Each refusal links to what fixes it, a step or a page (step 3a2 spec §4.5). "Finish your
+  // intake" shows at most once, on the first block that offers it: the notice for an unfinished
+  // intake, then the packet list's refusal, then Generate All's, then each form Generate All
+  // refused, then each card's refusal (ruling R4-a). The context's status and the server's can
+  // disagree.
   const noticeLinksIntake = session.status !== 'completed';
-  const errorLinksIntake = !noticeLinksIntake && !!error?.namesFix;
-  const refusalPage = generateAllRefusal?.page;
-  const refusalLinkLabel =
-    refusalPage && !(refusalPage === '/intake' && (noticeLinksIntake || errorLinksIntake))
-      ? PAGE_LINK_LABELS[refusalPage]
-      : undefined;
+  const linkTo = linksInPageOrder(noticeLinksIntake);
+  const errorLink = error ? linkTo(error) : undefined;
+  const refusalLink = generateAllRefusal ? linkTo(generateAllRefusal) : undefined;
+  const generationErrorLinks = generationErrors.map((e) => linkTo(e));
+  const cardRefusals = new Map<FormType, FormRefusal>();
+  for (const formType of [...packet, ...filedOutsidePacket.map((form) => form.form_type)]) {
+    const refusal = formRefusals[formType];
+    if (refusal) cardRefusals.set(formType, { message: refusal.message, link: linkTo(refusal) });
+  }

   return (
     <div className="form-dashboard">
@@ -248,15 +318,15 @@ export function FormDashboard() {
           <p>{error.message}</p>
           {/* Our own words mean the load failed and may work again; a 422's words name
               something to fix, which a retry can't. Only a refusal that names a step or page
-              has a fix at the intake (ruling R4-b). */}
+              links to its fix (ruling R4-b). */}
           {error.message === DASHBOARD_ERROR ? (
             <Button variant="outline" size="sm" onClick={loadForms}>
               Try Again
             </Button>
           ) : (
-            errorLinksIntake && (
-              <Link to="/intake" className="button button--primary">
-                Finish your intake
+            errorLink && (
+              <Link to={errorLink.to} className="button button--primary">
+                {errorLink.label}
               </Link>
             )
           )}
@@ -266,9 +336,9 @@ export function FormDashboard() {
       {generateAllRefusal && (
         <div className="form-dashboard-error" role="alert">
           <p>{generateAllRefusal.message}</p>
-          {refusalPage && refusalLinkLabel && (
-            <Link to={refusalPage} className="button button--primary">
-              {refusalLinkLabel}
+          {refusalLink && (
+            <Link to={refusalLink.to} className="button button--primary">
+              {refusalLink.label}
             </Link>
           )}
         </div>
@@ -278,14 +348,28 @@ export function FormDashboard() {
         <div className="form-dashboard-error" role="alert">
           <p>
             {generationErrors.length} form{generationErrors.length > 1 ? 's' : ''} could not be
-            generated. You can try generating them individually below.
+            generated.
+            {/* Trying again is all the filer can do about a form whose refusal names no fix */}
+            {generationErrors.some((e) => !fixLink(e)) &&
+              ' You can try generating them individually below.'}
           </p>
           <ul>
-            {generationErrors.map((e) => (
-              <li key={e.form_type}>
-                {FORM_TYPE_METADATA[e.form_type as FormType]?.label ?? e.form_type}: {e.error}
-              </li>
-            ))}
+            {generationErrors.map((e, index) => {
+              const link = generationErrorLinks[index];
+              return (
+                <li key={e.form_type}>
+                  {FORM_TYPE_METADATA[e.form_type as FormType]?.label ?? e.form_type}: {e.error}
+                  {link && (
+                    <>
+                      {' '}
+                      <Link to={link.to} className="button button--primary">
+                        {link.label}
+                      </Link>
+                    </>
+                  )}
+                </li>
+              );
+            })}
           </ul>
         </div>
       )}
@@ -342,6 +426,7 @@ export function FormDashboard() {
               key={formType}
               formType={formType}
               generatedForm={formsByType.get(formType)}
+              refusal={cardRefusals.get(formType)}
               onGenerate={handleGenerate}
               onDownload={handleDownload}
               onMarkFiled={handleMarkFiled}
@@ -353,6 +438,7 @@ export function FormDashboard() {
               formType={form.form_type}
               generatedForm={form}
               leftPacket
+              refusal={cardRefusals.get(form.form_type)}
               onGenerate={handleGenerate}
               onDownload={handleDownload}
               onMarkFiled={handleMarkFiled}
diff --git a/frontend/src/types/api.ts b/frontend/src/types/api.ts
index 42c2921..f94a7a7 100644
--- a/frontend/src/types/api.ts
+++ b/frontend/src/types/api.ts
@@ -462,7 +462,8 @@ export type GenerateForm101Response = GenerateFormResponse;

 export interface GenerateAllFormsResponse {
   generated: GeneratedForm[];
-  errors: Array<{ form_type: string; error: string }>;
+  /** Each form refused, with the wizard step (a `WIZARD_STEPS` key) or page that fixes it, if any */
+  errors: Array<{ form_type: string; error: string; step?: string; page?: string }>;
   total_generated: number;
   total_errors: number;
 }
PATCH
```

Generate All's `errors` entries carry `step` and `page`. On the dashboard:

- `refusalOf` turns a thrown refusal into the filer's words and its fix.
- `fixLink` gives a step its wizard link and a page its words, looking only at the maps' own keys.
- `linksInPageOrder` hands out the links in the order the page shows them, withholding "Finish your intake" after the first.
- The packet list's refusal, Generate All's refusal of the whole call, each entry of Generate All's list and each card get their link. The retry sentence shows only when some listed entry names no fix.
- `formRefusals` keeps one refusal per form type: a refused Generate or Download sets it, and its own success, Generate All returning the form, or Mark as Filed clears it.

- [ ] **Step 10: Run the tests again**

```bash
set -eo pipefail
(cd frontend && NO_COLOR=1 npx vitest run src/api/__tests__/client.test.ts src/pages/__tests__/FormDashboard.test.tsx src/pages/__tests__/IntakeWizard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: `Test Files  3 passed (3)` and `Tests  110 passed (110)`.

- [ ] **Step 11: Watch the unknown-key test fail when an unknown key opens the first step, or the last**

```bash
set -eo pipefail
cp frontend/src/pages/IntakeWizard.tsx frontend/src/pages/IntakeWizard.tsx.keep
trap 'mv frontend/src/pages/IntakeWizard.tsx.keep frontend/src/pages/IntakeWizard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -136,7 +136,7 @@
   // dashboard), opened instead of the saved step once the read returns, and then dropped from the
   // address. Opening it sends no update_step, so the saved step stays where Continue last put it.
   const [linkedStep] = useState(
-    () => WIZARD_STEPS.find((step) => step.key === searchParams.get('step'))?.number
+    () => WIZARD_STEPS.find((step) => step.key === searchParams.get('step'))?.number ?? (searchParams.get('step') ? 1 : undefined)
   );
   const [sessionRead, setSessionRead] = useState<'pending' | 'failed' | 'done'>('pending');
   const [readAttempt, setReadAttempt] = useState(0);
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/IntakeWizard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  1 failed | 57 passed (58)`, with `opens at the saved step when a link names no step of the wizard` and `Unable to find role="heading" and name "Amounts Owed"`.

```bash
set -eo pipefail
cp frontend/src/pages/IntakeWizard.tsx frontend/src/pages/IntakeWizard.tsx.keep
trap 'mv frontend/src/pages/IntakeWizard.tsx.keep frontend/src/pages/IntakeWizard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -136,7 +136,7 @@
   // dashboard), opened instead of the saved step once the read returns, and then dropped from the
   // address. Opening it sends no update_step, so the saved step stays where Continue last put it.
   const [linkedStep] = useState(
-    () => WIZARD_STEPS.find((step) => step.key === searchParams.get('step'))?.number
+    () => WIZARD_STEPS.find((step) => step.key === searchParams.get('step'))?.number ?? (searchParams.get('step') ? WIZARD_STEPS.length : undefined)
   );
   const [sessionRead, setSessionRead] = useState<'pending' | 'failed' | 'done'>('pending');
   const [readAttempt, setReadAttempt] = useState(0);
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/IntakeWizard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  1 failed | 57 passed (58)`, with `opens at the saved step when a link names no step of the wizard` and `Unable to find role="heading" and name "Amounts Owed"`.

Here a key that names no step opens step 1, then step 8, instead of the saved step. The test saves the filer at step 5 (review Minor 15): saved at Review, as it first was, the second mutation passed. Each block restores `IntakeWizard.tsx` from the copy it kept, pass or fail; each mutation block below does the same with its file.

- [ ] **Step 12: Watch the retry-sentence tests fail when the sentence never shows**

```bash
set -eo pipefail
cp frontend/src/pages/FormDashboard.tsx frontend/src/pages/FormDashboard.tsx.keep
trap 'mv frontend/src/pages/FormDashboard.tsx.keep frontend/src/pages/FormDashboard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -350,7 +350,7 @@
             {generationErrors.length} form{generationErrors.length > 1 ? 's' : ''} could not be
             generated.
             {/* Trying again is all the filer can do about a form whose refusal names no fix */}
-            {generationErrors.some((e) => !fixLink(e)) &&
+            {generationErrors.some(() => false) &&
               ' You can try generating them individually below.'}
           </p>
           <ul>
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  3 failed | 44 passed (47)`, with `shows error banner when generate_all returns partial failures`, `still suggests generating one at a time when any form Generate All refused names no fix` and `offers no link for a page it has no words for, such as /ask/constructor`.

Here the retry sentence is gone for every list, though an entry that names no fix leaves trying again as the filer's only move. Each of the three tests lists such an entry: a plain server message, a 500's sentence beside a linked one, and a page this dashboard has no words for.

- [ ] **Step 13: Watch the `/ask/constructor` test fail when an inherited key counts as a form**

```bash
set -eo pipefail
cp frontend/src/pages/FormDashboard.tsx frontend/src/pages/FormDashboard.tsx.keep
trap 'mv frontend/src/pages/FormDashboard.tsx.keep frontend/src/pages/FormDashboard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -72,7 +72,7 @@
   if (!page) return undefined;
   if (page.startsWith('/ask/')) {
     const formType = page.slice('/ask/'.length);
-    return Object.hasOwn(FORM_TYPE_METADATA, formType)
+    return formType in FORM_TYPE_METADATA
       ? {
           to: page,
           label: `Answer the questions for ${FORM_TYPE_METADATA[formType as FormType].label}`,
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  1 failed | 46 passed (47)`, with `offers no link for a page it has no words for, such as /ask/constructor`.

Here `constructor`, which every object inherits, passes for a form type, and the list shows a link reading "Answer the questions for undefined" (review Minor 11).

- [ ] **Step 14: Watch the Income link fail when every step links to the first**

```bash
set -eo pipefail
cp frontend/src/pages/FormDashboard.tsx frontend/src/pages/FormDashboard.tsx.keep
trap 'mv frontend/src/pages/FormDashboard.tsx.keep frontend/src/pages/FormDashboard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -65,7 +65,7 @@
  * name such as "constructor" is no form and no page.
  */
 function fixLink({ step, page }: Fix): FormRefusal['link'] {
-  const wizardStep = WIZARD_STEPS.find((s) => s.key === step);
+  const wizardStep = WIZARD_STEPS.find(() => step !== undefined);
   if (wizardStep) {
     return { to: `/intake?step=${wizardStep.key}`, label: `Go to ${wizardStep.label}` };
   }
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  4 failed | 43 passed (47)`, with `links a form whose download was refused to the step that fixes it`, `links a refused Generate All to the step that fixes it`, `offers the step that fixes it, not a retry, when the packet list is refused` and `shows the packet list’s refusal when it reloads after Generate All`.

Here every named step opens step 1 as "Go to Your Information". Before the review, every step-link test named `debtor_info`, step 1, and this passed (review finding 2).

- [ ] **Step 15: Watch the card's page links fail when a card links only a step**

```bash
set -eo pipefail
cp frontend/src/pages/FormDashboard.tsx frontend/src/pages/FormDashboard.tsx.keep
trap 'mv frontend/src/pages/FormDashboard.tsx.keep frontend/src/pages/FormDashboard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -285,7 +285,7 @@
   const cardRefusals = new Map<FormType, FormRefusal>();
   for (const formType of [...packet, ...filedOutsidePacket.map((form) => form.form_type)]) {
     const refusal = formRefusals[formType];
-    if (refusal) cardRefusals.set(formType, { message: refusal.message, link: linkTo(refusal) });
+    if (refusal) cardRefusals.set(formType, { message: refusal.message, link: linkTo({ step: refusal.step }) });
   }

   return (
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  2 failed | 45 passed (47)`, with `links a form whose Generate was refused to the page that fixes it` and `links a form’s refusal back to the intake when nothing above it does`.

Here a card drops its refusal's page. Before the review no card test named a page, and this passed (review finding 3).

- [ ] **Step 16: Watch the page-order test fail when the cards take their own once-only rule**

```bash
set -eo pipefail
cp frontend/src/pages/FormDashboard.tsx frontend/src/pages/FormDashboard.tsx.keep
trap 'mv frontend/src/pages/FormDashboard.tsx.keep frontend/src/pages/FormDashboard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -282,10 +282,11 @@
   const errorLink = error ? linkTo(error) : undefined;
   const refusalLink = generateAllRefusal ? linkTo(generateAllRefusal) : undefined;
   const generationErrorLinks = generationErrors.map((e) => linkTo(e));
+  const cardLinkTo = linksInPageOrder(noticeLinksIntake);
   const cardRefusals = new Map<FormType, FormRefusal>();
   for (const formType of [...packet, ...filedOutsidePacket.map((form) => form.form_type)]) {
     const refusal = formRefusals[formType];
-    if (refusal) cardRefusals.set(formType, { message: refusal.message, link: linkTo(refusal) });
+    if (refusal) cardRefusals.set(formType, { message: refusal.message, link: cardLinkTo(refusal) });
   }

   return (
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  1 failed | 46 passed (47)`, with `keeps "Finish your intake" on Generate All’s refusal, not on a card below it that names it too`.

Here the cards ignore Generate All's refusal above them, so "Finish your intake" shows twice (review Minors 10 and 14).

- [ ] **Step 17: Watch the Try-again test fail when the wizard drops `?step=` before the read**

```bash
set -eo pipefail
cp frontend/src/pages/IntakeWizard.tsx frontend/src/pages/IntakeWizard.tsx.keep
trap 'mv frontend/src/pages/IntakeWizard.tsx.keep frontend/src/pages/IntakeWizard.tsx' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -177,6 +177,16 @@
       return { fresh, contracts, codebtors };
     };

+    if (linkedStep !== undefined) {
+      setSearchParams(
+        (params) => {
+          const next = new URLSearchParams(params);
+          next.delete('step');
+          return next;
+        },
+        { replace: true }
+      );
+    }
     openSession()
       .then(({ fresh, contracts, codebtors }) => {
         if (cancelled) return;
@@ -184,16 +194,6 @@
         // The link has done its work. Dropped from the address in place, with no new history
         // entry, so a refresh, or Back to the wizard from a later page, opens the saved step,
         // not the linked one again.
-        if (linkedStep !== undefined) {
-          setSearchParams(
-            (params) => {
-              const next = new URLSearchParams(params);
-              next.delete('step');
-              return next;
-            },
-            { replace: true }
-          );
-        }
         if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
         if (fresh.income_info) setIncomeData(hydrateAmounts(fresh.income_info, INCOME_FIELDS));
         if (fresh.expense_info) setExpenseData(hydrateAmounts(fresh.expense_info, EXPENSE_FIELDS));
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/IntakeWizard.test.tsx) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  1 failed | 57 passed (58)`, with `keeps the linked step in the address while the read fails, and drops it once Try again opens it`.

Here `?step=` is gone from the address before the session read, so a refresh while the read fails opens the saved step (the re-review's X7, R70).

- [ ] **Step 18: Watch the refreshed-download test fail when the body is read before the refresh**

```bash
set -eo pipefail
cp frontend/src/api/client.ts frontend/src/api/client.ts.keep
trap 'mv frontend/src/api/client.ts.keep frontend/src/api/client.ts' EXIT
git apply <<'PATCH'
diff --git a/frontend/src/api/client.ts b/frontend/src/api/client.ts
--- a/frontend/src/api/client.ts
+++ b/frontend/src/api/client.ts
@@ -635,6 +635,7 @@
       });
     };
     let response = await doFetch();
+    if (!response.ok) await handleAPIError(response);
     if (response.status === 401 && getRefreshToken()) {
       const refreshed = await attemptTokenRefresh();
       if (refreshed) response = await doFetch();
PATCH
(cd frontend && NO_COLOR=1 npx vitest run src/api/__tests__/client.test.ts) 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Tests  1 failed | 4 passed (5)`, with `reads a refused download’s words only after refreshing an expired token`.

Here an expired token's 401 is thrown as the refusal, and every download after 30 minutes would fail (review Minor 17).

- [ ] **Step 19: Say in the docs how the browser sends Generate All and where each refusal links**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 63e8b32..1abf2bb 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -33,7 +33,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
-- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. Generate, Generate All and Regenerate check without drawing: each resolves the form's parts (`build_parts`), runs `PDFFormFiller.check()` and stores them, so a letter the form can't print or a value too long for its box is a 422, or a Generate All `errors` entry, carrying its `step` or `page`. Download draws: `fill()` bakes with PyMuPDF, which isn't thread-safe, so the server stays on sync gunicorn workers with no `--threads` unless the bake gets a lock. Generate calls PyMuPDF too, without drawing: `check()` measures an attached sheet's text with PyMuPDF's `Font` (`sheets.plan_sheet`), and so does the startup check. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download draws its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
+- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. Generate, Generate All and Regenerate check without drawing: each resolves the form's parts (`build_parts`), runs `PDFFormFiller.check()` and stores them, so a letter the form can't print or a value too long for its box is a 422, or a Generate All `errors` entry, carrying its `step` or `page`. The browser sends Generate All once (`apiFetchOnce`, never `withRetry`), and the dashboard links each refusal it shows (the packet list's, Generate All's whole-call refusal, a Generate All `errors` entry, or a card's refused Generate or Download, whose body `downloadForm` reads after its one token refresh) to its fix: a `step` to `/intake?step=<key>`, a `page` to that page, "Finish your intake" at most once. A card's refusal stays until its own Generate or Download next succeeds, Generate All returns that form in `generated` (a filed form included, which it returns untouched), or the form is marked filed. Download draws: `fill()` bakes with PyMuPDF, which isn't thread-safe, so the server stays on sync gunicorn workers with no `--threads` unless the bake gets a lock. Generate calls PyMuPDF too, without drawing: `check()` measures an attached sheet's text with PyMuPDF's `Font` (`sheets.plan_sheet`), and so does the startup check. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download draws its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
 - **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. For repeat groups, E007 refuses one not declared in the schema's `groups`, one that names neither or both of an `extra_page` and a `sheet`, an `extra_page` that isn't the page of the group's last slots, a `number` without `{n}` (also when only `number_boxes` or a `sheet` is set), one that `format(n=1)` can't fill or that prints the same for `n=1` and `n=2`, a second group with an `extra_page` on one form (3a2's limit), fields that differ in `repeat_capacity` or `conditional_on` or whose slot rows aren't exactly 1 to `repeat_capacity`, a slot row whose boxes sit on more than one page, rows that go back a page as the row number rises, and an untagged slot binding that would print its row more than once: a text or combo one whose name has more than one drawn widget, or a checkbox or radio one whose drawn widgets share an on-state (a column whose boxes each have their own state, such as Schedule D's `check 4`, passes); for a `sheet`, E007 also refuses no columns, columns wider than 504 pt (7 in) with the 36 pt line column, a column whose binding isn't a `sofa.<collection>[].<attr>` list or isn't one of the group's slot bindings, or that any box slot binds, a slot binding no column prints (the rows past the slots would drop it), any other box slot (a sheet has no box to tick), a first sheet line (`number` for the row past the slots) that doesn't print whole on one line of the 36 pt line column, two columns with one label, a label or title the sheet can't print whole (a letter the form's template can't print, or a word wider than its column or the page), and `page_numbers` (a sheet group has no copies); E003 refuses a number box for a row that isn't a slot row, a number or page-number box that is no drawn widget on its row's or page's page, an untagged number or page-number `this` box whose name has more than one drawn widget, and any untagged binding whose `page` holds no drawn widget of its name (a copy picks its rows' boxes by `page`); and E006 counts each group box (`number_boxes` values and `page_numbers` `this` and `of`, one `of` key once) as a writer beside the bindings. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. Tiers 1 and 3 read the printed page, not `/V`: `read_drawn` (`apps/forms/tests/pdf_readback.py`) takes a widget's Helvetica text and the template's ZapfDingbats check mark inside its rect, and reads `""` where a box prints only the blank template's own default (the district combos' placeholder, A/B `19.1`–`19.3 % of ownership` "0%", C `page 2` and G `fill 2.6` "2"), so a blank assertion on such a box can't see that default. `read_drawn` refuses a PDF that still has a widget (a `ValueError`, never a listed defect), so it reads only `fill()`'s baked output. The list has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
@@ -58,13 +58,13 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **OCR provider is config-driven** — `_get_processor()` branches on `settings.OCR_PROVIDER` (`openai` | `gemini`) and lazy-imports the provider, so a missing SDK/key surfaces at OCR time, not app boot. `OCR_MODEL` empty ⇒ the provider's own default. Don't hardcode a provider.
 - **`openai_provider.py`, never `openai.py`** — a module named `openai.py` inside `providers/` would shadow the installed `openai` package.
 - **Prod throttling lives in `production.py`, not `base.py`** — base defines only the `auth` scope (`30/minute`); production adds `DEFAULT_THROTTLE_CLASSES` with `anon: 60/minute`, `user: 120/minute`, `auth: 5/minute`. Reading base alone wrongly concludes endpoints are unthrottled — polling ~14 documents exhausts `user` fast.
-- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8. A scanned bill or credit report pre-fills Amounts Owed; a pay stub supplies only Schedule I's employer name (`IngestedAggregate` `paystub.employer_name`), never an amount and never the Income step: every income box prints what was typed on the Income step. A scanned debt is a draft (`is_draft`) and stays off every form and out of the means test until the filer saves the Amounts Owed step, whose session PATCH carrying `debts` clears every draft of the session; Complete refuses while one remains (DIG-163). Every reader that feeds a form or the means test reads through `DebtInfo.objects.confirmed()` or `session.debts.confirmed()`, and a new one must too; dischargeability, the completion percentage and the API's reads still see drafts, so the wizard can show them. The aggregator still stores `paystub.gross`, which no form reads (pre-fill is DIG-176). `IntakeWizard.handleNext` detours when `nextStep === 2`. Nothing currently links back to `/documents` after a skip. The persona journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1; `scanned-bill-journey` uploads with `uploadBill()` and clicks Continue.
+- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8. A scanned bill or credit report pre-fills Amounts Owed; a pay stub supplies only Schedule I's employer name (`IngestedAggregate` `paystub.employer_name`), never an amount and never the Income step: every income box prints what was typed on the Income step. A scanned debt is a draft (`is_draft`) and stays off every form and out of the means test until the filer saves the Amounts Owed step, whose session PATCH carrying `debts` clears every draft of the session; Complete refuses while one remains (DIG-163). Every reader that feeds a form or the means test reads through `DebtInfo.objects.confirmed()` or `session.debts.confirmed()`, and a new one must too; dischargeability, the completion percentage and the API's reads still see drafts, so the wizard can show them. The aggregator still stores `paystub.gross`, which no form reads (pre-fill is DIG-176). `IntakeWizard.handleNext` detours when `nextStep === 2`. After a skip, only the forms dashboard links back to `/documents`: a refusal of the one value read from an upload, Schedule I's employer name, reads "Go to Upload your documents". The persona journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1; `scanned-bill-journey` uploads with `uploadBill()` and clicks Continue.
 - **`updateCurrentStep` is POST `/intake/sessions/{id}/update_step/`** — _not_ the PATCH that saves step data. Mocking the PATCH to assert step advancement silently captures the wrong call and passes vacuously.
 - **Upload is synchronous despite the 202** — `views.py` uses `with ThreadPoolExecutor(...)`, whose `__exit__` calls `shutdown(wait=True)`, so `{"status": "processing"}` is returned _after_ OCR completes and holds a gunicorn worker. No `Future` is retained — that's the tell.
 - **PDFs: text layer first, then up to 3 scanned pages** — `processor.py` runs `opendataloader_pdf.convert(..., format="markdown", image_output="off", include_header_footer=True)` with no hybrid arguments. Text of at least `_MIN_TEXT_LENGTH` (30) characters goes to the text prompt; otherwise `_pdf_to_page_images()` sends up to `_MAX_SCANNED_PAGES` (3) JPEG pages to vision, and a PDF with no pages fails. Without `image_output="off"` a scan's image placeholders reach the text prompt; without `include_header_footer=True` the letterhead naming the creditor is dropped.
 - **`extract()` takes a list of page images** — `BaseOCRProvider.extract(images: list[bytes], prompt)`: `[]` means text mode, a photo upload is a one-item list, and pages go in page order (one OpenAI `image_url` part or one Gemini inline part each). `classify()` still takes bytes. Never hand a provider `[]` for a scan.
 - **An empty OpenAI reply raises `EmptyModelReply`** — `OpenAIProvider._complete` retries a blank or whitespace-only reply once, but never a refusal or `finish_reason == "content_filter"`. The error names `finish_reason` and whether a refusal was present, never its text. `_parse_result` records only the reply's length ("model reply was not valid JSON (N characters)"), so `error_message` never holds model output. Gemini still returns `""` (DIG-35).
-- **The wizard re-reads the session on every mount** — `IntakeWizard` fixes the session id at mount (context session, else `current_session_id`), calls `loadSession(id)`, and renders no step until it returns, so steps and autosave start from server data, not the context copy (which predates any upload on `/documents`). A failed read shows a "Try again" alert for the same id; a 404 starts a new session. `loadSession`/`createSession` resolve with the session, and `loadSession` clears `current_session_id` only on a 404, but the provider's own startup load still clears it on any error (DIG-11).
+- **The wizard re-reads the session on every mount** — `IntakeWizard` fixes the session id at mount (context session, else `current_session_id`), calls `loadSession(id)`, and renders no step until it returns, so steps and autosave start from server data, not the context copy (which predates any upload on `/documents`). A failed read shows a "Try again" alert for the same id; a 404 starts a new session. `?step=<key>`, also read once at mount, opens that step after the read instead of the saved one when the key is one of `WIZARD_STEPS`, and sends no `update_step`; the wizard then drops it from the address with a replace (no new history entry), so a refresh, or Back to the wizard from a later page, opens the saved step, not the linked one again. Any other value opens the saved step. `loadSession`/`createSession` resolve with the session, and `loadSession` clears `current_session_id` only on a 404, but the provider's own startup load still clears it on any error (DIG-11).
 - **Autosave sends only real edits** — `useAutoSave` compares the step's PATCH body (`currentStepBody` in `IntakeWizard`) as JSON with that step's last saved or loaded copy (the first body seen under a step's name) and skips an equal one, so showing a step again (Go Back) sends nothing and doesn't reopen a completed intake. A body must therefore be built the same way from loaded data as from edited data: leave out read-only totals and echoed fields, or every visit saves. A save of assets or debts returns the copy the server now holds, the sent rows with the ids the reply gave them, built by the same merge as the wizard's rows, unless a later save of the list has gone out since (it then returns nothing); `onSave` may return such a copy, and the hook keeps it as the saved copy, so the ids reaching the rows send nothing more. Continue (`saveNow`) always saves. Steps 6 and 7 have no body there; their lists save only on Continue.
 - **An empty scan is FAILED, not done** — `documents/views._record_findings` judges each type: a bill needs a creditor name, a pay stub must pass `PayStubExtraction`, the check the income aggregate applies (gross pay + both pay-period dates required; an invalid optional field such as a negative `net_pay` also fails it), a credit report needs one readable tradeline. Otherwise `OCRResult.status="failed"`, `failure_reason="nothing_found"`; any exception is `processing_error`. A bill with a creditor but no readable balance is `completed` with a $0 draft; a report of only $0 accounts is `completed` with no debts. Other document types are not judged.
 - **The documents API never returns `error_message` or `extracted_data`** — `_serialize_ocr` returns `status`, `failure_reason`, `confidence_scores`, `overall_confidence`, `user_validated`. `error_message` is operations-only (exception class, `finish_reason`); read it in a Django shell. The pipeline's catch-all handlers (`_run_processing`, `AggregateIngestionService.recalculate`) log only the exception's type with `logger.error`, never `logger.exception`: logs reach Sentry, and a DB error's DETAIL quotes row values (DIG-105).
@@ -120,7 +120,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - `src/context/AuthContext.tsx` — JWT auth, silent refresh
 - `src/context/IntakeContext.tsx` — Session state
 - `src/api/client.ts` — typed API client, `getAccessToken()`, `downloadForm()`
-- `src/pages/IntakeWizard.tsx` — 8-step wizard orchestrator (`WIZARD_STEPS`: debtor_info, income_info, expense_info, assets, debts, contracts, codebtors, review); detours to `/documents` after step 1
+- `src/pages/IntakeWizard.tsx` — 8-step wizard orchestrator (`WIZARD_STEPS`, in `src/constants/wizardSteps.ts`: debtor_info, income_info, expense_info, assets, debts, contracts, codebtors, review); detours to `/documents` after step 1
 - `src/pages/DocumentUploadPage.tsx` — upload + OCR queue; auto-creates a session if none exists
 - `src/pages/FormDashboard.tsx` — Generate All, download, mark filed
 - `src/pages/SOFAStep.tsx` (`/sofa`), `FeeWaiverPage.tsx` (`/fee-waiver`) — post-intake pages; `handleComplete` routes to one or the other on `qualifies_for_fee_waiver`, and the fee-waiver page continues to `/sofa`
PATCH
```

In `CLAUDE.md`:

- "GenerateAll vs single" says the browser sends Generate All once (`apiFetchOnce`), that the dashboard links each refusal it shows to its fix ("Finish your intake" at most once), that `downloadForm` reads a refusal's body after its one token refresh, and when a card's refusal clears.
- "The wizard re-reads the session on every mount" describes `?step=<key>` and its removal from the address.
- "Document upload sits mid-wizard" said nothing links back to `/documents` after a skip; now the dashboard does, for a refusal of Schedule I's employer name, the one value read from an upload (review Minor 9; the only `ingested` binding in `data/forms/schemas/` is in `schedule_i.json`).
- The File Map line for `IntakeWizard.tsx` says `WIZARD_STEPS` lives in `src/constants/wizardSteps.ts`.

- [ ] **Step 20: Run every gate**

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

The backend counts are Task 7's: this task changes one backend comment. Vitest gains 23 tests, all in the three files of Step 1. Under a heavy load (1-minute load above 15) a SOFAStep or FormDashboard test can run past vitest's 5 s per-test timeout; run vitest again on a quieter machine before suspecting the code. The 25 skips are the Postgres-only tests under sqlite; the next command runs them against the Postgres database named by `DATABASE_URL` in `.claude/forms-step3a2.env`.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

- [ ] **Step 21: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 8 passed` and `RUN 2 exit=0: 8 passed`.

Five persona journeys (Andrés, DeShawn, James, Maria and Sarah) and the SOFA journey press Generate All, which is now sent once, and the SOFA journey downloads Form 107 through `downloadForm`.

These results are the implementer's; this plan's own check doesn't run the journeys. They ran on the task's first commit, b793977 (`RUN 1 exit=0: 8 passed (1.6m)`, `RUN 2 exit=0: 8 passed (1.5m)`), and on the first fix round's, 190a51f (`RUN 1 exit=0: 8 passed (1.7m)`, `RUN 2 exit=0: 8 passed (56.2s)`). The tree committed below differs from 190a51f only in comments, `CLAUDE.md`, two test titles and one new wizard test (R70); the controller checked that no production line changed, and the journeys were not run again.

- [ ] **Step 22: Commit**

```bash
set -eo pipefail
git add \
  frontend/src/constants/wizardSteps.ts \
  CLAUDE.md \
  backend/apps/forms/tests/test_rule_fixes.py \
  frontend/src/api/__tests__/client.test.ts \
  frontend/src/api/client.ts \
  frontend/src/components/forms/FormCard.tsx \
  frontend/src/pages/FormDashboard.tsx \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/FormDashboard.test.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  frontend/src/styles/global.css \
  frontend/src/types/api.ts
git commit -F - <<'MSG'
feat(forms): link each refusal on the dashboard to its fix; no retry

Since forms step 3a2 checks every form on Generate, a letter the court
form can't print or a value too long for its box is refused with the
step or page that fixes it (3a2 spec §4.5). The dashboard dropped most
of that: Generate All's per-form errors were plain text under "You can
try generating them individually below", a refused Generate or Download
showed nothing (FormCard caught the error and the parent never handled
it), downloadForm threw "Download failed (422)" without reading the
body, a refusal of the whole call that named a step got no link or only
"Finish your intake", and the wizard could only open at the saved step.
And Generate All went through withRetry, so a 5xx could start four runs
at once (§7).

- formsAPI.generateAll calls apiFetchOnce: sent once, never retried.
  The dashboard shows the error, and the filer can press again.
- downloadForm reads a refused download's body with handleAPIError,
  after its one 401 refresh, so the refusal keeps its own words, step
  and page like every other call.
- WIZARD_STEPS moves, with the same entries, to
  frontend/src/constants/wizardSteps.ts, imported by IntakeWizard and
  the dashboard.
- GenerateAllFormsResponse's errors items gain step? and page?.
- The dashboard links each refusal it shows to its fix: the packet
  list's, Generate All's refusal of the whole call (which now keeps its
  step as well as its page), each form Generate All refused, and each
  card's. A step that is a WIZARD_STEPS key links to /intake?step=<key>
  as "Go to <step label>", so income not entered by source reads "Go to
  Income"; /intake stays "Finish your intake"; /fee-waiver, /sofa and
  /documents read "Go to Filing Fee Waiver Application", "Go to
  Statement of Financial Affairs" and "Go to Upload your documents"
  (each page's own h1); /ask/<form type> reads "Answer the questions
  for <the form's label>". Only the maps' own keys count, so a name
  such as /ask/constructor gets no link. A refusal that names no fix,
  or one the dashboard has no words for, gets no link. "Finish your
  intake" still shows at most once (ruling R4-a), now over the packet
  list's refusal, Generate All's, its list and the cards, in page
  order. One helper, refusalOf, turns a thrown refusal (the packet
  list's, Generate All's refusal of the whole call and a card's) into
  the filer's words and its fix; Generate All's list entries arrive in
  its reply and link as they are.
- Generate All's list shows each form's message and its link; the
  retry sentence shows only when a listed form names no fix.
- The dashboard keeps one refusal per form type, set when that card's
  Generate or Download is refused (a 422's own words and link;
  anything else the generic words) and cleared when its own Generate or
  Download next succeeds, when Generate All returns that form in
  `generated` (a filed form included, which Generate All returns
  untouched), or when it is marked filed (a filed form prints what was
  filed, R46). FormCard
  takes it as a refusal prop and shows it in a polite live region that
  is on the card from the start, as Review's reasons are; empty, the
  region gives back the card's gap.
- The wizard reads ?step= once at mount: after the session read, a
  WIZARD_STEPS key opens that step instead of the saved one, sending
  no update_step, and the wizard then drops ?step= from the address
  with a replace, so a refresh, or Back to the wizard from a later
  page, opens the saved step. Any other value opens the saved step.

Tests (vitest):
- a form Generate All refused links to its step, with no retry advice;
  the retry advice stays when any listed form names no fix (and in the
  existing partial-failure test); each page's link words, each on a
  page a binding of that form can name; /ask/constructor gets no link;
- the packet list's refusal and Generate All's refusal of the whole
  call link to the step they name ("Go to Income"); the packet-list
  tests that expected "Finish your intake" for that refusal now expect
  "Go to Income";
- a refused Generate links to the step that fixes the form, a refused
  Download to Income (a step past the first), and a refused Generate
  of Form 103B to the fee-waiver page; a card's refusal naming /intake
  links back to the intake when nothing above it does, adds no second
  link when the notice does, and leaves it on Generate All's refusal
  when that names it too; a refused download shows its reason in a
  polite region that was on the card before it; a download that fails
  on the server shows the generic words; the refusal clears when the
  form's Generate or Download succeeds, when Generate All returns it in
  `generated`, and when it is marked filed; two packet-list tests are
  titled for what they assert, the words "Finish your intake" shown
  once;
- the wizard opens at the step a link names without an update_step,
  drops ?step= from the address without a new history entry, keeps it
  there while the read fails and drops it once Try again opens the
  step, and opens the saved step (mid-wizard) for an unknown ?step=;
- downloadForm keeps a refusal's words and step, also when it first
  refreshes an expired token.
The Generate All test for a server error drops its fake-timer
scaffolding and now counts one request.

test_rule_fixes.py's comment names the new home of WIZARD_STEPS.

CLAUDE.md: "GenerateAll vs single" says the browser sends Generate All
once, the dashboard links each refusal it shows to its fix, and when a
card's refusal clears; "The wizard re-reads the session on every mount"
describes ?step= and its removal from the address; "Document upload
sits mid-wizard" says the dashboard now links back to /documents for a
refusal of Schedule I's employer name; the File Map line for
IntakeWizard.tsx says where WIZARD_STEPS now lives.

Refs DIG-137
MSG
git status --short
```
