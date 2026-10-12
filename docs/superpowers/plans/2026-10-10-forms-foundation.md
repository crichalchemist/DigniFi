# Forms Foundation (Step 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the court-form engine trustworthy and its defects visible. This means one fill path from schema to PDF, bindings that address verified full names and are checked at startup, the packet rules, encrypted field values, and a three-tier read-back oracle whose failures each carry a ticket.

**Architecture:** Each schema binds its fields to widget full names from the verified field index (`data/forms/field_index/`). `build_field_values()` checks a form's preconditions and resolves its schema, and `PDFFormFiller` fills exactly those names. A Django system check validates every schema against the index at startup, and three oracle tiers read filled PDFs back. Step 1 moves no binding to a different line; that is step 2. What step 1 does is turn every misplacement into a strict xfail that carries a ticket.

**Tech Stack:** Django 5.0 + DRF (Python 3.11), pypdf 6.13.1, encrypted-model-fields, pytest + pytest-django; React 19 + TypeScript, vitest + MSW; Playwright.

**Spec:** `docs/superpowers/specs/2026-10-10-forms-foundation-design.md` (approved 2026-10-10). Read it before Task 1; it is the authority this plan argues from.

**How this plan was checked:**

- Each task's code was built and committed in order on the local branch `plan/forms-step1`, and every task ended with a green suite.
- The plan was then dry-run from its own text in a fresh worktree.
- The finished code passed the E2E suite in 4 of 4 full runs.

## Global Constraints

- **Single filer only.** Joint filing is out, and Debtor 2 boxes stay blank (spec §3).
- **pypdf stays pinned at 6.13.1** (`backend/requirements/base.txt`); `test_pdf_filler.py` fails if the version changes (§5.3).
- **Appearance streams:** `/NeedAppearances` is false, and the filler stores the appearance streams. There is no flattening, and each form is one PDF (§5.3).
- **Exact names:** bindings name index `full_name`s. The filler matches full names exactly and never calls `update_page_form_field_values` (§5.3).
- **Error contract** (§5.7):
  - An expected failure returns 422 with `{"form_type", "error"}`, and the error is in plain words.
  - Anything else returns 500 and logs only the exception's type, with `logger.error`, never its message or a traceback (the DIG-105 rule).
- **Privacy:** the API never returns `form_data` or `field_values`. `field_values` is JSON stored in an `EncryptedTextField` (§5.5).
- **Test data** is synthetic only, with SSNs from the IRS-reserved 900 range (§7).
- **UPL:** user-facing text is legal information, never advice (`docs/UPL_COMPLIANCE.md`).
- **Coverage:** backend coverage stays at or above 90%. CI runs `pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs` (§8).
- **Lint:**
  - CI runs `ruff check backend/` with ruff 0.8.5.
  - Pre-commit runs black 24.10.0 (line length 100) on `backend/`.
  - Pre-commit runs prettier 3.4.2 on JSON, Markdown and TypeScript outside `backend/`, and eslint on the frontend.
- **Commit messages** end with the last line about the change. **Add no `Co-Authored-By`, `Claude-Session` or other agent trailer, even if your harness asks for one.**
- **Staging:** stage files by explicit path only, never with `git add -A`, `git add .` or `git commit -a`. Commit only the files the task lists.
- **No outward actions:** no push, PR, merge, deploy or production command. Those are the owner's decisions.
- **Keys:** never print, log or commit an API key. This plan does not use the repo-root `.env`.

## Before you start (once per worktree)

- Work in `/Volumes/Containers/DigniFi/.claude/worktrees/forms-rebinding` (branch `feat/forms-rebinding`). Every command block runs from that worktree's root.
- Backend tools come from the main checkout's virtualenv, and frontend tools from its `node_modules`. Pre-commit's eslint hook expects that symlink.
- Task 10's E2E run needs Colima running, with the `dignifi-db-1` Postgres container answering on host port 5433.

```bash
set -o pipefail
mkdir -p backend/logs .claude   # the audit log handler needs backend/logs; CI creates it too
[ -e frontend/node_modules ] || ln -s /Volumes/Containers/DigniFi/frontend/node_modules frontend/node_modules
# CI's synthetic Fernet key (it encrypts nothing real), read from ci.yml rather than copied here
FERNET=$(sed -n 's/^ *FIELD_ENCRYPTION_KEY: //p' .github/workflows/ci.yml | head -1)
[ -n "$FERNET" ]
cat > .claude/forms-step1.env <<ENV
# Test settings for forms step 1 (git-ignored).
export PY=/Volumes/Containers/DigniFi/backend/.venv/bin/python
export PRECOMMIT=/Volumes/Containers/DigniFi/backend/.venv/bin/pre-commit
export DJANGO_SETTINGS_MODULE=config.settings.test
export DJANGO_SECRET_KEY=test-only-not-a-secret
export FIELD_ENCRYPTION_KEY=$FERNET
ENV
source .claude/forms-step1.env && $PY -c "import pypdf; assert pypdf.__version__ == '6.13.1', pypdf.__version__"
git check-ignore -q .claude/forms-step1.env && echo "env file is ignored"
```

Expected: `env file is ignored`.

## How to read the code blocks

- **`<language> file=<path>` blocks:** the block is the file's complete content. Create or overwrite the file with exactly that text.
- **`bash` blocks:** run from the worktree root in a fresh shell (bash or zsh). Each block starts with `set -o pipefail`, so a failure anywhere in a pipeline fails the block, and a block sources `.claude/forms-step1.env` itself when it needs it.
- **`git apply <<'PATCH'` blocks:** these patch the state the previous task left. If one doesn't apply, stop: the tree has drifted from the plan.
- **"Expected:" lines** say what the command must do. An "Expected: FAIL" step is the red half of test-first. Every other step must succeed.

## Rulings already made (do not undo)

Each of these was decided while the code was prototyped. A reviewer who questions one should check the spec and the reason given here before changing it.

1. **The conversion counts 709 exact renames, not the spec's 708.** Schedule J's district box was a TBD row; it is converted to `derived`/`district_name`, and that conversion counts as an exact rename. `convert_schemas.py` refuses to write when any total differs.
2. **A Debtor 2 widget is recognised by its label matching `Debtor 2|non-filing spouse`.** A bare `spouse` would also drop 122A-1's `Debto1.Quest3`.
3. **`audit/verification.json` overrides the audit files** when they disagree about a binding's correct target.
4. **Form 121's `Check Box1` stays unmapped** (`HELD_UNMAPPED`; DIG-68):
   - Its rule `has_ssn_check` is inverted.
   - Today's `/Yes` state never ticks the box. The true state is `/On`, so mapping it would print "no SSN" for every filer who has one.
   - The old `test_ssn_checkbox` pinned the defect and is deleted.
5. **Tier 2's empty audit target** means the binding's own box is correct. The exception is when the audit verdicts include `wrong_box`: then the case fails with no target.
6. **The orphan check** in `test_known_defects.py` compares entries with the generated case keys, not with the tests that ran, so running a single tier is safe.
7. **Ticket assignment** follows `record_known_defects.py`:
   - Use the audit row's `known` DIG ticket, unless it is DIG-63 or DIG-64, which this step closes.
   - Otherwise use the form's ticket.
   - Every `unmapped_choice` goes to DIG-68.
8. **Tier 3 values come from the seed,** which matches the E2E fixtures. Priya's income is $12,000 a month; her brief said $10,000 (DIG-129, fixed in Task 11).
9. **Tier 3 money compares as a number** (`"3,200.00"` equals `"3200.00"`). Zero boxes are not asserted, because step 2 decides where a blank replaces `0.00`.
10. **122A-2 applies when `calculated_cmi × 12 ≥ median_income_threshold`.** `above_median_calculated` is sticky (DIG-128) and is never read.
11. **The search gate (§5.5) allows exactly five hits:**
    - the blanked `form_data` model field;
    - four lines of the DIG-124 privacy test, which assert that `form_data` is never returned and stays blank.
12. **The per-form schema tests call `resolve()` directly.**
    - They are resolver tests; preconditions are tested in `test_registry.py`.
    - Asserts that pinned known defects are removed: 103B `4 type`/`5 Type`, 106Sum `3c`/`4`, and 122A-1 `13A`.
    - So are `.get(x, default) == default` asserts, which pass whatever the code does.
13. **DIG-130 and DIG-131 are fixed here, in Task 10.** They are E2E flakes that predate this work. They surface because `generate_all` now test-fills every PDF (about 4 s per packet locally), which slows the journeys running beside it. `nextStep()` keeps its 500 ms settle delay, because other assertions rely on it.

## Spec coverage

| Spec                                                | Task                          |
| --------------------------------------------------- | ----------------------------- |
| §5.1 schema format (`choices`, full names)          | 3                             |
| §5.2 one-off conversion                             | 3                             |
| §5.3 filler                                         | 3                             |
| §5.4 validation at startup; shipping the index      | 4; 1                          |
| §5.5 one generation path, `field_values`, endpoints | 6, 8                          |
| §5.5 frontend (dashboard, dead callers, types)      | 9                             |
| §5.5 E2E packet sizes                               | 10                            |
| §5.6 packet list, 122B removal                      | 2, 6                          |
| §5.7 preconditions and the error contract           | 6                             |
| §6 oracle tiers 1, 2 / 3, known defects             | 5 / 7                         |
| §7 DIG-124, exemptions code removed, logging        | 6, 8                          |
| §8 success criteria 1–8                             | 4, 5, 7, 6, 6, 6, 8–9, 8 + 10 |

## Readings Task 7 encodes (owner confirms before Task 7)

Tier 3's expected values rest on six legal readings. If the owner rejects one, only Task 7 changes: its `EXPECTED` table and the known-defects list it re-records.

1. Monthly income is treated as gross, with no payroll deductions. Maria's brief calls hers "take-home".
2. The married personas (Priya, DeShawn) file alone, and their household sizes include the spouse. Column B and the marital-status box are not asserted.
3. Sarah's student loan is a nonpriority unsecured debt.
4. Every seeded expense counts in Schedule J line 22a.
5. Priya's income is $12,000 a month, as in the seed and the E2E fixture.
6. Boxes expected to hold zero are not asserted.

---

### Task 1: Load the verified field index and ship it in the image

_Built and verified as commit `27006d6` on `plan/forms-step1`._

**Files:**

- Create: `backend/apps/forms/field_index.py`
- Create: `backend/apps/forms/tests/test_field_index.py`
- Modify: `Dockerfile.heroku`
- Modify: `backend/config/settings/base.py`

**Interfaces:**

- Consumes: the field index files `data/forms/field_index/<template stem>.index.json` (committed in `941c873`).
- Produces: `apps.forms.field_index.export_state(on_state: str) -> str`; `IndexWidget(full_name, page, type, on_state, basis, label, column)` (frozen dataclass); `index_path(template_filename: str) -> Path`; `load_index(template_filename: str) -> dict[str, tuple[IndexWidget, ...]]` (cached; raises `FileNotFoundError`); setting `FORM_INDEX_DIRECTORY`.

- [ ] **Step 1: Write the failing test**

```python file=backend/apps/forms/tests/test_field_index.py
"""
The field index names every widget of each AO template (spec §5.1).

Schemas, the filler and the oracle all address widgets through it, so each
widget must be found by its full name, with the export state a filler writes.
"""

import pytest
from django.conf import settings

from apps.forms.field_index import export_state, index_path, load_index

PETITION = "form_b_101_0624_fillable_clean.pdf"


def test_export_states_are_decoded_the_way_pypdf_reads_them():
    assert export_state("Chapter#207") == "/Chapter 7"
    assert export_state("On") == "/On"


def test_a_checkbox_group_is_one_full_name_with_a_widget_per_option():
    # Form 101 prints the chapter boxes twice: the page 1 header and Part 1 on page 3.
    chapter = load_index(PETITION)["Check Box1"]
    assert {w.type for w in chapter} == {"CheckBox"}
    assert {w.page for w in chapter} == {1, 3}
    assert [export_state(w.on_state) for w in chapter].count("/Chapter 7") == 2


def test_a_text_box_is_found_by_its_full_name():
    (first_name,) = load_index(PETITION)["Debtor1.First name"]
    assert first_name.type == "Text"
    assert first_name.on_state is None


def test_the_index_is_read_from_the_directory_the_image_copies_it_to():
    # Dockerfile.heroku copies data/forms/field_index/*.index.json to this directory.
    path = index_path(PETITION)
    assert path == settings.FORM_INDEX_DIRECTORY / "form_b_101_0624_fillable_clean.index.json"
    assert path.is_file()


def test_a_template_without_an_index_cannot_be_loaded():
    with pytest.raises(FileNotFoundError):
        load_index("no_such_template.pdf")
```

- [ ] **Step 2: Run it and watch it fail**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_field_index.py -q -p no:cacheprovider
```

Expected: FAIL — `ModuleNotFoundError: No module named 'apps.forms.field_index'`.

- [ ] **Step 3: Add the loader, its setting, and the image copy**

```python file=backend/apps/forms/field_index.py
"""
The verified field index: one row per widget of each AO template.

Built from the templates themselves (see data/forms/field_index/README.md).
Schemas name widgets by an index ``full_name``; apps.forms.checks validates
every schema against it, and the filler and the oracle compare checkbox states
through export_state().
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings

_HEX_ESCAPE = re.compile(r"#([0-9A-Fa-f]{2})")


def export_state(on_state: str) -> str:
    """
    Turn an index ``on_state`` into the PDF export state a filler writes.

    The index stores the raw, #-encoded name with no leading slash
    ("Chapter#207"); pypdf reads the same name as "/Chapter 7".
    """
    return "/" + _HEX_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), on_state)


@dataclass(frozen=True)
class IndexWidget:
    """One widget of a template, as the index records it."""

    full_name: str
    page: int
    type: str  # Text | CheckBox | RadioButton | ComboBox | Button
    on_state: str | None
    basis: str
    label: str
    column: str


def index_path(template_filename: str) -> Path:
    """The index file for a template: <FORM_INDEX_DIRECTORY>/<template stem>.index.json."""
    return Path(settings.FORM_INDEX_DIRECTORY) / f"{Path(template_filename).stem}.index.json"


@lru_cache(maxsize=32)
def load_index(template_filename: str) -> dict[str, tuple[IndexWidget, ...]]:
    """
    Return {full_name: widgets} for a template filename such as "form_b121.pdf".

    A checkbox group has one full name and several widgets, one per option.

    Raises:
        FileNotFoundError: the template has no index file.
    """
    with open(index_path(template_filename)) as f:
        rows = json.load(f)

    widgets: dict[str, list[IndexWidget]] = {}
    for row in rows:
        widgets.setdefault(row["full_name"], []).append(
            IndexWidget(
                full_name=row["full_name"],
                page=row["page"],
                type=row["type"],
                on_state=row["on_state"],
                basis=row["basis"],
                label=row["label"] or "",
                column=row["column"] or "",
            )
        )
    return {name: tuple(ws) for name, ws in widgets.items()}
```

```bash
git apply <<'PATCH'
diff --git a/Dockerfile.heroku b/Dockerfile.heroku
index 20f2efa..50bf877 100644
--- a/Dockerfile.heroku
+++ b/Dockerfile.heroku
@@ -43,6 +43,9 @@ COPY backend/ .
 # Bake official AO court PDF templates into the image for PDF filling at runtime.
 COPY data/forms/pdfs/ /data/forms/pdfs/
 COPY data/forms/schemas/ /data/forms/schemas/
+# The verified field index: apps.forms.checks validates every schema against it at
+# migrate (the release phase), and the filler fills only the full names it lists.
+COPY data/forms/field_index/*.index.json /data/forms/field_index/

 # Wire up the frontend build artefacts:
 #   index.html → templates/frontend/index.html  (served by TemplateView catch-all)
diff --git a/backend/config/settings/base.py b/backend/config/settings/base.py
index 671dc02..1956354 100644
--- a/backend/config/settings/base.py
+++ b/backend/config/settings/base.py
@@ -234,6 +234,7 @@ TRAUMA_SENSITIVE_TERMS = {
 PDF_GENERATION_BACKEND = "PyPDF2"  # Alternative: 'pdfrw'
 PDF_FORMS_DIRECTORY = BASE_DIR.parent / "data" / "forms" / "pdfs"
 FORM_SCHEMAS_DIRECTORY = BASE_DIR.parent / "data" / "forms" / "schemas"
+FORM_INDEX_DIRECTORY = BASE_DIR.parent / "data" / "forms" / "field_index"
 PDF_OUTPUT_DIRECTORY = MEDIA_ROOT / "generated_forms"

 # ============================================
PATCH
```

In the image, `BASE_DIR` is `/app`, so `BASE_DIR.parent / "data" / "forms" / "field_index"` is `/data/forms/field_index`, the directory the new `COPY` line writes to. That line sits beside the existing `pdfs` and `schemas` copies. The `audit/` and `tools/` folders are test-only and stay out of the image.

- [ ] **Step 4: Run the test and the whole backend suite**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_field_index.py -q -p no:cacheprovider
$PY -m pytest -q -p no:cacheprovider 2>&1 | tail -2
```

Expected: `5 passed`, then the suite: `774 passed, 1 xfailed`.

- [ ] **Step 5: Commit**

```bash
set -o pipefail
git add \
  backend/apps/forms/field_index.py \
  backend/apps/forms/tests/test_field_index.py \
  Dockerfile.heroku \
  backend/config/settings/base.py
git commit -F - <<'MSG'
feat(forms): load the verified field index and ship it in the image
MSG
git status --short
```

### Task 2: Drop Form 122B, the Chapter 11 statement, from the Chapter 7 packet

_Built and verified as commit `355579d` on `plan/forms-step1`._

**Files:**

- Create: `backend/apps/forms/migrations/0005_remove_form_122b.py`
- Modify: `backend/apps/forms/models.py`
- Modify: `backend/apps/forms/registry.py`
- Modify: `backend/apps/forms/services/__init__.py`
- Modify: `backend/apps/forms/services/pdf_filler.py`
- Modify: `backend/apps/forms/tests/test_generate_all_schema_driven.py`
- Modify: `backend/apps/forms/tests/test_registry.py`
- Delete: `backend/apps/forms/services/form_122b_generator.py`
- Delete: `data/forms/schemas/form_122b.json`

**Interfaces:**

- Consumes: nothing new.
- Produces: `GeneratedForm.FORM_TYPE_CHOICES` without `form_122b`; migration `forms.0005_remove_form_122b` (deletes `form_122b` rows, then narrows the choices); a registry of 17 form types. Task 6's migration `0006` depends on `0005`.

- [ ] **Step 1: Update the registry tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_generate_all_schema_driven.py b/backend/apps/forms/tests/test_generate_all_schema_driven.py
index 22dd6f6..f6d5063 100644
--- a/backend/apps/forms/tests/test_generate_all_schema_driven.py
+++ b/backend/apps/forms/tests/test_generate_all_schema_driven.py
@@ -127,7 +127,7 @@ def full_session(db):
 class TestGenerateAll13Forms:
     def test_all_form_types_registered(self):
         """All form types are in the registry."""
-        assert len(get_all_form_types()) == 18
+        assert len(get_all_form_types()) == 17

     def test_all_forms_generate_without_error(self, full_session):
         """Every form type generates without raising an exception."""
diff --git a/backend/apps/forms/tests/test_registry.py b/backend/apps/forms/tests/test_registry.py
index 67a414f..2b67181 100644
--- a/backend/apps/forms/tests/test_registry.py
+++ b/backend/apps/forms/tests/test_registry.py
@@ -22,6 +22,7 @@ import pytest
 from django.contrib.auth import get_user_model

 from apps.districts.models import District
+from apps.forms.models import GeneratedForm
 from apps.forms.registry import (
     FORM_REGISTRY,
     get_all_form_types,
@@ -106,17 +107,22 @@ def session_with_debtor(session):
 class TestRegistryStructure:
     """Test the registry data structure and basic operations."""

-    def test_get_all_form_types_returns_18_entries(self):
+    def test_get_all_form_types_returns_17_entries(self):
         """
-        Verify get_all_form_types() returns exactly 18 entries.
+        Verify get_all_form_types() returns exactly 17 entries.

-        DigniFi supports 18 forms for Chapter 7 filing.
+        DigniFi supports 17 forms for Chapter 7 filing.
         """
         form_types = get_all_form_types()
-        assert len(form_types) == 18
+        assert len(form_types) == 17
+
+    def test_chapter_11_means_test_is_not_offered(self):
+        # Form 122B is the Chapter 11 statement, and its download raised a 500 (DIG-125).
+        assert "form_122b" not in FORM_REGISTRY
+        assert "form_122b" not in dict(GeneratedForm.FORM_TYPE_CHOICES)

     def test_all_expected_form_types_present(self):
-        """Verify all 18 expected form type keys exist in registry."""
+        """Verify all 17 expected form type keys exist in registry."""
         expected_form_types = [
             "form_101",
             "form_103b",
@@ -127,7 +133,6 @@ class TestRegistryStructure:
             "form_122a1",
             "form_122a1_supp",
             "form_122a2",
-            "form_122b",
             "schedule_a_b",
             "schedule_c",
             "schedule_d",
PATCH
```

- [ ] **Step 2: Run them and watch them fail**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_registry.py -q -p no:cacheprovider
```

Expected: FAIL — three tests: `AssertionError: assert 18 == 17`, `assert 'form_122b' not in` the registry, and `Unexpected form type: form_122b`.

- [ ] **Step 3: Remove 122B from the registry, the model, the filler table and the services**

```bash
set -o pipefail
git rm -q backend/apps/forms/services/form_122b_generator.py data/forms/schemas/form_122b.json
```

```python file=backend/apps/forms/migrations/0005_remove_form_122b.py
"""Form 122B is the Chapter 11 means-test statement; it leaves the Chapter 7 packet (DIG-125)."""

from django.db import migrations, models


def delete_form_122b_rows(apps, schema_editor):
    GeneratedForm = apps.get_model("forms", "GeneratedForm")
    GeneratedForm.objects.filter(form_type="form_122b").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0004_add_five_form_types"),
    ]

    operations = [
        migrations.RunPython(delete_form_122b_rows, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="generatedform",
            name="form_type",
            field=models.CharField(
                choices=[
                    ("form_101", "Form 101 - Voluntary Petition"),
                    ("form_103b", "Form 103B - Fee Waiver Application"),
                    ("form_106dec", "Form 106Dec - Declaration"),
                    ("form_106sum", "Form 106Sum - Summary of Assets/Liabilities"),
                    ("form_107", "Form 107 - Statement of Financial Affairs"),
                    ("form_121", "Form 121 - SSN Statement"),
                    ("form_122a1", "Form 122A-1 - Means Test"),
                    ("form_122a1_supp", "Form 122A-1 Supplement"),
                    ("form_122a2", "Form 122A-2 - Means Test Calculation"),
                    ("schedule_a_b", "Schedule A/B - Property"),
                    ("schedule_c", "Schedule C - Exemptions"),
                    ("schedule_d", "Schedule D - Secured Creditors"),
                    ("schedule_e_f", "Schedule E/F - Unsecured Creditors"),
                    ("schedule_g", "Schedule G - Executory Contracts/Leases"),
                    ("schedule_h", "Schedule H - Codebtors"),
                    ("schedule_i", "Schedule I - Income"),
                    ("schedule_j", "Schedule J - Expenses"),
                ],
                help_text="Type of bankruptcy form",
                max_length=20,
            ),
        ),
    ]
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/models.py b/backend/apps/forms/models.py
index 606be37..d582c7b 100644
--- a/backend/apps/forms/models.py
+++ b/backend/apps/forms/models.py
@@ -22,7 +22,6 @@ class GeneratedForm(models.Model):
         ("form_122a1", "Form 122A-1 - Means Test"),
         ("form_122a1_supp", "Form 122A-1 Supplement"),
         ("form_122a2", "Form 122A-2 - Means Test Calculation"),
-        ("form_122b", "Form 122B - Alternative Means Test"),
         ("schedule_a_b", "Schedule A/B - Property"),
         ("schedule_c", "Schedule C - Exemptions"),
         ("schedule_d", "Schedule D - Secured Creditors"),
diff --git a/backend/apps/forms/registry.py b/backend/apps/forms/registry.py
index 6a74e00..de79aa8 100644
--- a/backend/apps/forms/registry.py
+++ b/backend/apps/forms/registry.py
@@ -19,7 +19,6 @@ from .services import (
     Form122A1Generator,
     Form122A1SuppGenerator,
     Form122A2Generator,
-    Form122BGenerator,
     ScheduleABGenerator,
     ScheduleCGenerator,
     ScheduleDGenerator,
@@ -42,7 +41,6 @@ FORM_REGISTRY: dict[str, type] = {
     "form_122a1": Form122A1Generator,
     "form_122a1_supp": Form122A1SuppGenerator,
     "form_122a2": Form122A2Generator,
-    "form_122b": Form122BGenerator,
     "schedule_a_b": ScheduleABGenerator,
     "schedule_c": ScheduleCGenerator,
     "schedule_d": ScheduleDGenerator,
diff --git a/backend/apps/forms/services/__init__.py b/backend/apps/forms/services/__init__.py
index 81d8600..ff3ddc5 100644
--- a/backend/apps/forms/services/__init__.py
+++ b/backend/apps/forms/services/__init__.py
@@ -14,7 +14,6 @@ from .form_121_generator import Form121GenerationError, Form121Generator
 from .form_122a1_generator import Form122A1Generator
 from .form_122a1_supp_generator import Form122A1SuppGenerator
 from .form_122a2_generator import Form122A2Generator
-from .form_122b_generator import Form122BGenerator
 from .schedule_ab_generator import ScheduleABGenerator
 from .schedule_c_generator import ScheduleCGenerator
 from .schedule_d_generator import ScheduleDGenerator
@@ -36,7 +35,6 @@ __all__ = [
     "Form122A1Generator",
     "Form122A1SuppGenerator",
     "Form122A2Generator",
-    "Form122BGenerator",
     "ScheduleABGenerator",
     "ScheduleCGenerator",
     "ScheduleDGenerator",
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
index 962fc2b..c21e9fa 100644
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -26,7 +26,6 @@ FORM_TEMPLATES: dict[str, str] = {
     "form_122a1": "b_122a-1.pdf",
     "form_122a2": "b_122a-2_0425-form.pdf",
     "form_122a1_supp": "form_b122a-1supp.pdf",
-    "form_122b": "form_b122b.pdf",
     "schedule_a_b": "form_b106ab.pdf",
     "schedule_c": "b_106c_0425-form.pdf",
     "schedule_d": "form_b106d.pdf",
PATCH
```

- [ ] **Step 4: Run the tests, the migration check and the suite**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_registry.py -q -p no:cacheprovider
$PY manage.py makemigrations --check --dry-run
$PY -m pytest -q -p no:cacheprovider 2>&1 | tail -2
```

Expected: the registry tests pass, `No changes detected`, then `775 passed, 1 xfailed`.

- [ ] **Step 5: Commit**

```bash
set -o pipefail
git add \
  backend/apps/forms/migrations/0005_remove_form_122b.py \
  backend/apps/forms/models.py \
  backend/apps/forms/registry.py \
  backend/apps/forms/services/__init__.py \
  backend/apps/forms/services/pdf_filler.py \
  backend/apps/forms/tests/test_generate_all_schema_driven.py \
  backend/apps/forms/tests/test_registry.py
git commit -F - <<'MSG'
fix(forms): drop Form 122B, the Chapter 11 statement, from the Chapter 7 packet (DIG-125)
MSG
git status --short
```

### Task 3: Bind every schema field to an index full name, and fill only exact names

_Built and verified as commit `cdc523e` on `plan/forms-step1`._

**Files:**

- Create: `backend/apps/forms/tests/pdf_readback.py`
- Create: `data/forms/field_index/audit/conversion_report.json`
- Create: `data/forms/field_index/tools/convert_schemas.py`
- Modify: `backend/apps/forms/schema.py`
- Modify: `backend/apps/forms/services/fill_resolver.py`
- Modify: `backend/apps/forms/services/pdf_filler.py`
- Modify: `backend/apps/forms/tests/test_coverage.py`
- Modify: `backend/apps/forms/tests/test_engine_form_agnostic.py`
- Modify: `backend/apps/forms/tests/test_fill_resolver.py`
- Modify: `backend/apps/forms/tests/test_form_103b_schema.py`
- Modify: `backend/apps/forms/tests/test_form_106dec_schema.py`
- Modify: `backend/apps/forms/tests/test_form_106sum_schema.py`
- Modify: `backend/apps/forms/tests/test_form_121_schema.py`
- Modify: `backend/apps/forms/tests/test_form_122a1_schema.py`
- Modify: `backend/apps/forms/tests/test_pdf_field_maps.py`
- Modify: `backend/apps/forms/tests/test_pdf_filler.py`
- Modify: `backend/apps/forms/tests/test_schedule_i_schema.py`
- Modify: `backend/apps/forms/tests/test_schema.py`
- Modify: `backend/apps/forms/tests/test_schema_views.py`
- Delete: `backend/apps/forms/management/commands/ingest_form_schema.py`
- Delete: `backend/apps/forms/tests/test_ingest_command.py`
- Modify (generated by the conversion): all 17 `data/forms/schemas/*.json`

**Interfaces:**

- Consumes: `export_state`, `load_index` (Task 1); the 17 schemas without 122B (Task 2); the audit files under `data/forms/field_index/audit/`.
- Produces:

  - `FieldSpec.choices: dict[str, str] | None`, which replaces `on_states`. `{"true": state}` is a single box; `{}` means unmapped.
  - `apps.forms.services.fill_resolver.UnmappedChoice(Exception)`.
  - `PDFFormFiller().fill(form_type: str, field_values: dict[str, str]) -> bytes`. Keys are full names; values are text, an `/Opt` entry, or an export state such as `"/Chapter 7"`.
  - The exceptions `UnknownField(form_type, names)`, `TemplateHasNoForm(form_type)` and `InvalidFieldValue(form_type, name)`, all in `apps.forms.services.pdf_filler`.
  - `apps/forms/tests/pdf_readback.py`, with `read_widgets(pdf_bytes) -> list[FilledWidget(full_name, page, value, state)]`.
  - `FORM_TEMPLATES` is gone: the template name lives only in each schema's `template_filename`.

- [ ] **Step 1: Write the filler and resolver tests, and point the schema tests at full names**

```python file=backend/apps/forms/tests/pdf_readback.py
"""Read a filled PDF back widget by widget, the way a viewer sees it."""

from dataclasses import dataclass
from io import BytesIO

import pypdf

from apps.forms.services.pdf_filler import field_of, qualified_name


@dataclass(frozen=True)
class FilledWidget:
    full_name: str
    page: int
    value: str | None  # the field's /V
    state: str | None  # the widget's /AS; what a checkbox shows


def read_widgets(pdf_bytes: bytes) -> list[FilledWidget]:
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    widgets = []
    for page_number, page in enumerate(reader.pages, start=1):
        for annot in page.get("/Annots") or []:
            widget = annot.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            field = field_of(widget)
            value = field.get_inherited("/V")
            state = widget.get("/AS")
            widgets.append(
                FilledWidget(
                    full_name=qualified_name(field),
                    page=page_number,
                    value=None if value is None else str(value),
                    state=None if state is None else str(state),
                )
            )
    return widgets
```

```python file=backend/apps/forms/tests/test_pdf_filler.py
"""
PDFFormFiller fills exactly the widget a key names, the way a viewer will draw it.

The old filler matched a key against a parent's partial /T, so "Name" filled
both Debtor 1 and Debtor 2 (DIG-63), and it never ticked a checkbox (DIG-68).
"""

import json
from io import BytesIO

import pypdf
import pytest

from apps.forms.services.pdf_filler import (
    InvalidFieldValue,
    PDFFormFiller,
    TemplateHasNoForm,
    UnknownField,
)
from apps.forms.tests.pdf_readback import read_widgets


def _values(pdf_bytes, full_name):
    return [w.value for w in read_widgets(pdf_bytes) if w.full_name == full_name]


def test_filled_form_is_a_pdf():
    result = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
    assert result[:4] == b"%PDF"


def test_debtor_1_name_never_lands_in_debtor_2_box():
    pdf = PDFFormFiller().fill("form_122a1", {"Debtor1.Name": "Maria Torres"})
    assert set(_values(pdf, "Debtor1.Name")) == {"Maria Torres"}
    assert _values(pdf, "Debtor2.Name") == [None]


def test_text_prints_from_a_stored_appearance():
    """pypdf 6.13.1 internals build and install the appearance; this pins them."""
    assert pypdf.__version__ == "6.13.1"
    pdf = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
    reader = pypdf.PdfReader(BytesIO(pdf))
    # A BooleanObject is always truthy; its .value is the flag.
    assert reader.trailer["/Root"]["/AcroForm"]["/NeedAppearances"].value is False
    widget = next(
        a.get_object()
        for a in reader.pages[0]["/Annots"]
        if a.get_object().get("/T") == "First name"
        and a.get_object()["/Parent"].get("/T") == "Debtor1"
    )
    assert b"Maria" in widget["/AP"]["/N"].get_data()


def test_checkbox_ticks_only_the_widgets_for_its_state():
    pdf = PDFFormFiller().fill("form_101", {"Check Box1": "/Chapter 7"})
    states = [w.state for w in read_widgets(pdf) if w.full_name == "Check Box1"]
    # Chapter 7 is printed on pages 1 and 3; the other six options stay off.
    assert states.count("/Chapter 7") == 2
    assert states.count("/Off") == len(states) - 2


def test_state_the_template_lacks_raises_instead_of_printing_nothing():
    with pytest.raises(InvalidFieldValue):
        PDFFormFiller().fill("form_101", {"Check Box1": "/Chapter 9"})


def test_district_must_be_one_of_the_templates_options():
    district = "Bankruptcy District Information"
    pdf = PDFFormFiller().fill("form_121", {district: "Northern District of Illinois"})
    assert _values(pdf, district) == ["Northern District of Illinois"]
    with pytest.raises(InvalidFieldValue):
        PDFFormFiller().fill("form_121", {district: "District of Nowhere"})


def test_short_name_no_longer_fills_anything():
    with pytest.raises(UnknownField):
        PDFFormFiller().fill("form_122a1", {"Name": "Maria Torres"})


def test_unknown_form_type_raises():
    with pytest.raises(FileNotFoundError):
        PDFFormFiller().fill("form_does_not_exist", {})


def test_template_without_a_form_raises(tmp_path, settings):
    # Form 122B's template has no AcroForm (DIG-125).
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    schema = {
        "form_type": "form_no_acroform",
        "template_filename": "form_b122b.pdf",
        "template_version": "x",
        "fields": [],
    }
    (tmp_path / "form_no_acroform.json").write_text(json.dumps(schema))
    with pytest.raises(TemplateHasNoForm):
        PDFFormFiller().fill("form_no_acroform", {})
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_coverage.py b/backend/apps/forms/tests/test_coverage.py
index 10b067f..f972310 100644
--- a/backend/apps/forms/tests/test_coverage.py
+++ b/backend/apps/forms/tests/test_coverage.py
@@ -75,19 +75,3 @@ def test_form_101_all_applicable_fields_resolve(ilnd_fixture):
     ]
     unresolved = [f.pdf_field for f in applicable_required if f.pdf_field not in out]
     assert unresolved == [], f"unresolved Form 101 fields: {unresolved}"
-
-
-@pytest.mark.django_db
-def test_form_101_resolved_fields_from_multiple_sources(ilnd_fixture):
-    """Form 101 resolved fields come from derivations + FormAnswer + constants."""
-    call_command("seed_demo_data", "--reset", persona="maria")
-    session = IntakeSession.objects.filter(user__username="demo_maria").first()
-
-    schema = load_schema("form_101")
-    out = resolve(schema, session)
-
-    values = list(out.values())
-    # At least one constant (Check Box2)
-    assert any(v == "/Yes" for v in values)
-    # At least one derived value (full name or district)
-    assert any(v and "Maria" in str(v) for v in values)
diff --git a/backend/apps/forms/tests/test_engine_form_agnostic.py b/backend/apps/forms/tests/test_engine_form_agnostic.py
index 1802d71..9463a99 100644
--- a/backend/apps/forms/tests/test_engine_form_agnostic.py
+++ b/backend/apps/forms/tests/test_engine_form_agnostic.py
@@ -9,28 +9,11 @@ schema", not "rebuild the engine".
 import pytest

 from apps.districts.models import District
-from apps.forms.management.commands.ingest_form_schema import build_draft_schema
-from apps.forms.schema import FieldSpec, FormSchema, validate_schema
-from apps.forms.services.derivations import DERIVATIONS, PREDICATES
+from apps.forms.schema import FormSchema
 from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import IntakeSession


-def test_ingest_runs_on_a_second_form():
-    """build_draft_schema works on any AO template, not just form_107."""
-    draft = build_draft_schema("schedule_j")
-    assert len(draft["fields"]) > 0
-    assert all(f["source"] == "TBD" for f in draft["fields"])
-
-
-def test_validate_flags_uncurated_draft():
-    """An uncurated draft has TBD sources, which validate_schema flags."""
-    draft = build_draft_schema("schedule_j")
-    schema = FormSchema(**{**draft, "fields": [FieldSpec(**f) for f in draft["fields"]]})
-    errors = validate_schema(schema, set(DERIVATIONS), set(PREDICATES))
-    assert any("TBD" in e for e in errors), "uncurated draft should be flagged"
-
-
 @pytest.mark.django_db
 def test_resolver_noops_on_empty_schema():
     """resolve() returns an empty dict for a no-field schema (edge case)."""
@@ -59,7 +42,6 @@ def test_scalar_value_raises_on_asked_without_binding():
         type="text",
         source="asked",
         binding=None,
-        on_states=[],
         page=1,
         label="Test",
         required=False,
diff --git a/backend/apps/forms/tests/test_fill_resolver.py b/backend/apps/forms/tests/test_fill_resolver.py
index 9a14aa6..d969daf 100644
--- a/backend/apps/forms/tests/test_fill_resolver.py
+++ b/backend/apps/forms/tests/test_fill_resolver.py
@@ -8,7 +8,12 @@ from django.contrib.auth import get_user_model
 from apps.districts.models import District
 from apps.documents.models import IngestedAggregate
 from apps.forms.schema import FieldSpec, FormSchema
-from apps.forms.services.fill_resolver import RepeatOverflow, resolve, resolve_binding
+from apps.forms.services.fill_resolver import (
+    RepeatOverflow,
+    UnmappedChoice,
+    resolve,
+    resolve_binding,
+)
 from apps.intake.models import (
     DebtorInfo,
     FormAnswer,
@@ -75,7 +80,6 @@ def _field(**kw):
         "pdf_field": "F",
         "type": "text",
         "source": "constant",
-        "on_states": [],
         "page": 1,
         "label": "",
         "required": False,
@@ -147,25 +151,51 @@ def test_none_value_dropped(session):
     assert "Inert" not in resolve(schema, session)


-def test_checkbox_emits_on_state(session):
-    FormAnswer.objects.create(
-        session=session,
-        form_type="form_107",
-        field_key="q1",
-        value="yes",
-    )
+def _answer(session, value):
+    FormAnswer.objects.create(session=session, form_type="form_107", field_key="q1", value=value)
+
+
+def _box(**kw):
+    return _field(type="checkbox", source="asked", binding="answer:form_107.q1", **kw)
+
+
+def test_single_box_ticks_for_a_yes_answer(session):
+    _answer(session, "Yes")
+    schema = _schema([_box(pdf_field="Box", choices={"true": "/Yes"})])
+    assert resolve(schema, session)["Box"] == "/Yes"
+
+
+def test_single_box_stays_off_for_a_no_answer(session):
+    # The old _emit ticked any non-empty value, "false" included (DIG-68).
+    _answer(session, "false")
+    schema = _schema([_box(pdf_field="Box", choices={"true": "/Yes"})])
+    assert "Box" not in resolve(schema, session)
+
+
+def test_option_group_ticks_the_chosen_option(session):
+    _answer(session, "Chapter_7")
+    choices = {"chapter_7": "/Chapter 7", "chapter_13": "/Chapter 13"}
+    schema = _schema([_box(pdf_field="Chapter", choices=choices)])
+    assert resolve(schema, session)["Chapter"] == "/Chapter 7"
+
+
+def test_answer_with_no_box_raises_instead_of_printing_nothing(session):
+    _answer(session, "maybe")
+    schema = _schema([_box(pdf_field="Box", choices={"true": "/Yes"})])
+    with pytest.raises(UnmappedChoice):
+        resolve(schema, session)
+
+
+def test_unmapped_box_emits_nothing_and_reads_no_value(session):
+    # An unknown rule would raise if the resolver looked the value up.
     schema = _schema(
         [
             _field(
-                pdf_field="Box",
-                type="checkbox",
-                source="asked",
-                on_states=["/Yes"],
-                binding="answer:form_107.q1",
-            ),
+                pdf_field="Box", type="checkbox", source="derived", rule="no_such_rule", choices={}
+            )
         ]
     )
-    assert resolve(schema, session)["Box"] == "/Yes"
+    assert resolve(schema, session) == {}


 def test_repeat_group_expands_rows(session):
diff --git a/backend/apps/forms/tests/test_form_103b_schema.py b/backend/apps/forms/tests/test_form_103b_schema.py
index 491daa6..ca25471 100644
--- a/backend/apps/forms/tests/test_form_103b_schema.py
+++ b/backend/apps/forms/tests/test_form_103b_schema.py
@@ -65,7 +65,6 @@ class TestForm103BSchema:
     def test_schema_loads(self):
         schema = load_schema("form_103b")
         assert schema.form_type == "form_103b"
-        assert len(schema.fields) == 42

     def test_all_fields_have_valid_source(self):
         schema = load_schema("form_103b")
@@ -76,8 +75,8 @@ class TestForm103BSchema:
         generator = Form103BGenerator(session_with_fw)
         field_map = generator.pdf_field_map()
         assert "Bankruptcy District Information" in field_map
-        assert "Debtor" in field_map
-        assert "Jane Doe" in field_map["Debtor"]
+        assert "Debtor 1" in field_map
+        assert "Jane Doe" in field_map["Debtor 1"]

     def test_fee_waiver_fields(self, session_with_fw):
         generator = Form103BGenerator(session_with_fw)
diff --git a/backend/apps/forms/tests/test_form_106dec_schema.py b/backend/apps/forms/tests/test_form_106dec_schema.py
index fb40eb3..db24a33 100644
--- a/backend/apps/forms/tests/test_form_106dec_schema.py
+++ b/backend/apps/forms/tests/test_form_106dec_schema.py
@@ -51,7 +51,6 @@ class TestForm106DecSchema:
     def test_schema_loads(self):
         schema = load_schema("form_106dec")
         assert schema.form_type == "form_106dec"
-        assert len(schema.fields) == 8

     def test_all_fields_have_source(self):
         schema = load_schema("form_106dec")
diff --git a/backend/apps/forms/tests/test_form_106sum_schema.py b/backend/apps/forms/tests/test_form_106sum_schema.py
index a501a11..eb57942 100644
--- a/backend/apps/forms/tests/test_form_106sum_schema.py
+++ b/backend/apps/forms/tests/test_form_106sum_schema.py
@@ -96,7 +96,6 @@ class TestForm106SumSchema:
     def test_schema_loads(self):
         schema = load_schema("form_106sum")
         assert schema.form_type == "form_106sum"
-        assert len(schema.fields) == 21

     def test_all_fields_have_valid_source(self):
         schema = load_schema("form_106sum")
diff --git a/backend/apps/forms/tests/test_form_121_schema.py b/backend/apps/forms/tests/test_form_121_schema.py
index 8e35545..bfb283d 100644
--- a/backend/apps/forms/tests/test_form_121_schema.py
+++ b/backend/apps/forms/tests/test_form_121_schema.py
@@ -51,7 +51,6 @@ class TestForm121Schema:
     def test_schema_loads(self):
         schema = load_schema("form_121")
         assert schema.form_type == "form_121"
-        assert len(schema.fields) == 20

     def test_all_fields_have_valid_source(self):
         schema = load_schema("form_121")
@@ -67,11 +66,6 @@ class TestForm121Schema:
         assert "Debtor1a.SSNum" in field_map
         assert field_map["Debtor1a.SSNum"] == "123-45-6789"

-    def test_ssn_checkbox(self, session_with_ssn):
-        generator = Form121Generator(session_with_ssn)
-        field_map = generator.pdf_field_map()
-        assert field_map.get("Check Box1") == "/Yes"
-
     def test_district_name(self, session_with_ssn):
         generator = Form121Generator(session_with_ssn)
         field_map = generator.pdf_field_map()
diff --git a/backend/apps/forms/tests/test_form_122a1_schema.py b/backend/apps/forms/tests/test_form_122a1_schema.py
index 704c488..0e90831 100644
--- a/backend/apps/forms/tests/test_form_122a1_schema.py
+++ b/backend/apps/forms/tests/test_form_122a1_schema.py
@@ -60,7 +60,6 @@ class TestForm122A1Schema:
     def test_schema_loads(self):
         schema = load_schema("form_122a1")
         assert schema.form_type == "form_122a1"
-        assert len(schema.fields) == 24

     def test_all_fields_have_valid_source(self):
         schema = load_schema("form_122a1")
diff --git a/backend/apps/forms/tests/test_pdf_field_maps.py b/backend/apps/forms/tests/test_pdf_field_maps.py
index fccc781..697cf1d 100644
--- a/backend/apps/forms/tests/test_pdf_field_maps.py
+++ b/backend/apps/forms/tests/test_pdf_field_maps.py
@@ -152,25 +152,6 @@ def test_form_106dec_pdf_field_map(full_session):
 # ---------------------------------------------------------------------------


-def test_form_101_pdf_field_map(full_session):
-    gen = get_generator("form_101", full_session)
-    field_map = gen.pdf_field_map()
-    _assert_map_shape(field_map)
-    assert field_map.get("Debtor1.First name") == "Maria"
-    assert field_map.get("Debtor1.Last name") == "Torres"
-    # SSN last-4
-    assert field_map.get("Debtor1.SSNum") == "0001"
-    assert field_map.get("Debtor1.City") == "Chicago"
-    # Checkboxes
-    assert field_map.get("Check Box1") == "/Yes"  # Individual
-    assert field_map.get("Check Box5") == "/Yes"  # Chapter 7
-    assert field_map.get("Check Box16") == "/Yes"  # Consumer debts
-    # Attorney-gated fields are absent (pro se = no attorney)
-    assert field_map.get("Attorney.Firm name") is None  # gated behind has_attorney
-    # Business-gated fields absent if no business
-    assert field_map.get("Debtor1.Business name") is None
-
-
 # ---------------------------------------------------------------------------
 # Form 106Sum
 # ---------------------------------------------------------------------------
@@ -218,28 +199,11 @@ def test_schedule_j_pdf_field_map(full_session):
 # ---------------------------------------------------------------------------


-def test_form_122a1_pdf_field_map(full_session):
-    gen = get_generator("form_122a1", full_session)
-    field_map = gen.pdf_field_map()
-    _assert_map_shape(field_map)
-    assert "Maria" in field_map.get("Name", "")
-    # CMI = $2200/mo, annualized = $26,400
-    assert field_map.get("12B") == "26400.00"
-
-
 # ---------------------------------------------------------------------------
 # Form 103B
 # ---------------------------------------------------------------------------


-def test_form_103b_pdf_field_map(full_session):
-    gen = get_generator("form_103b", full_session)
-    field_map = gen.pdf_field_map()
-    _assert_map_shape(field_map)
-    assert "Torres" in field_map.get("Debtor", "")
-    assert field_map.get("Bankruptcy District Information") == "Northern District of Illinois"
-
-
 # ---------------------------------------------------------------------------
 # Schedule A/B
 # ---------------------------------------------------------------------------
@@ -295,12 +259,3 @@ def test_schedule_ef_pdf_field_map(full_session):
 # ---------------------------------------------------------------------------
 # Form 107
 # ---------------------------------------------------------------------------
-
-
-def test_form_107_pdf_field_map(full_session):
-    gen = get_generator("form_107", full_session)
-    field_map = gen.pdf_field_map()
-    assert isinstance(field_map, dict)
-    assert all(isinstance(k, str) and isinstance(v, str) for k, v in field_map.items())
-    assert field_map.get("Bankruptcy District Information") == "Northern District of Illinois"
-    assert "Torres" in field_map.get("Debtor 2", "")
diff --git a/backend/apps/forms/tests/test_schedule_i_schema.py b/backend/apps/forms/tests/test_schedule_i_schema.py
index d04cf5a..3c37e90 100644
--- a/backend/apps/forms/tests/test_schedule_i_schema.py
+++ b/backend/apps/forms/tests/test_schedule_i_schema.py
@@ -57,7 +57,6 @@ class TestScheduleISchema:
     def test_schema_loads(self):
         schema = load_schema("schedule_i")
         assert schema.form_type == "schedule_i"
-        assert len(schema.fields) == 24

     def test_all_fields_have_valid_source(self):
         schema = load_schema("schedule_i")
diff --git a/backend/apps/forms/tests/test_schema.py b/backend/apps/forms/tests/test_schema.py
index 99574ba..a5b408a 100644
--- a/backend/apps/forms/tests/test_schema.py
+++ b/backend/apps/forms/tests/test_schema.py
@@ -16,7 +16,6 @@ SAMPLE = {
             "pdf_field": "Debtor 1",
             "type": "text",
             "source": "derived",
-            "on_states": [],
             "page": 1,
             "label": "Debtor name",
             "required": True,
@@ -122,7 +121,6 @@ def test_load_schema_with_ui_metadata(tmp_path, settings):
                 "pdf_field": "street",
                 "type": "text",
                 "source": "asked",
-                "on_states": [],
                 "page": 1,
                 "label": "Street",
                 "required": True,
diff --git a/backend/apps/forms/tests/test_schema_views.py b/backend/apps/forms/tests/test_schema_views.py
index 445b7fb..8609985 100644
--- a/backend/apps/forms/tests/test_schema_views.py
+++ b/backend/apps/forms/tests/test_schema_views.py
@@ -18,7 +18,6 @@ class TestUISpecView(APITestCase):
                     type="text",
                     source="asked",
                     binding="answer:test.q1",
-                    on_states=(),
                     page=1,
                     label="l",
                     required=False,
@@ -68,7 +67,6 @@ class TestUISpecView(APITestCase):
                     type="text",
                     source="asked",
                     binding="expense.source",
-                    on_states=(),
                     page=1,
                     label="l",
                     required=False,
@@ -87,7 +85,6 @@ class TestUISpecView(APITestCase):
                     type="text",
                     source="asked",
                     binding="expense.amount",
-                    on_states=(),
                     page=1,
                     label="l",
                     required=False,
@@ -106,7 +103,6 @@ class TestUISpecView(APITestCase):
                     type="text",
                     source="asked",
                     binding="expense.source",
-                    on_states=(),
                     page=1,
                     label="l",
                     required=False,
@@ -125,7 +121,6 @@ class TestUISpecView(APITestCase):
                     type="text",
                     source="asked",
                     binding="expense.amount",
-                    on_states=(),
                     page=1,
                     label="l",
                     required=False,
@@ -144,7 +139,6 @@ class TestUISpecView(APITestCase):
                     type="text",
                     source="asked",
                     binding="expense.other.amount",
-                    on_states=(),
                     page=1,
                     label="l",
                     required=False,
PATCH
```

These patches do four things:

- They drop `on_states` from the test fixtures.
- They replace the old checkbox test with tests of `choices`.
- They remove the field-count asserts that the conversion changes.
- They delete the tests that pinned defects the conversion fixes or exposes:

  - Form 121's `test_ssn_checkbox` (ruling 4).
  - The Form 101 tests that expected `/Yes`, a state that never ticks a box (DIG-68).
  - The 122A-1 and 103B field-map tests that used the short names `Name` and `Debtor` (DIG-63, DIG-64).

- [ ] **Step 2: Run the new tests and watch them fail**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_pdf_filler.py apps/forms/tests/test_fill_resolver.py -q -p no:cacheprovider
```

Expected: FAIL — both files fail to import: `cannot import name 'InvalidFieldValue' from 'apps.forms.services.pdf_filler'` and `cannot import name 'UnmappedChoice' from 'apps.forms.services.fill_resolver'`.

- [ ] **Step 3: Add the conversion script and run it once**

```python file=data/forms/field_index/tools/convert_schemas.py
"""One-off conversion of the form schemas to full-name bindings (forms step 1, spec §5.2).

Rewrites ../../schemas/*.json in place against the field index and writes
../audit/conversion_report.json, whose "renamed" maps join converted bindings
back to their audit rows. Moves no binding to a different line. Exits non-zero
when a count differs from the spec, so a changed index or schema is caught.

usage (repo root, backend venv): python data/forms/field_index/tools/convert_schemas.py
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from apps.forms.field_index import export_state  # noqa: E402

SCHEMAS = ROOT / "data" / "forms" / "schemas"
INDEX = ROOT / "data" / "forms" / "field_index"
PDFS = ROOT / "data" / "forms" / "pdfs"

# Rule 3: bindings with no candidate widget, decided in the spec.
PRE_DECIDED = {
    ("form_103b", "Debtor"): "Debtor 1",
    ("form_121", "Debtor2a.First name"): None,
    ("form_121", "Debtor2a.Middle name"): None,
    ("form_121", "Debtor2a.Last name"): None,
    ("schedule_a_b", "17"): None,
}
# Rule 4: a Debtor 2 widget, by name or by its index label or column.
DEBTOR2_NAME = re.compile(r"Debtor 2|Debtor2|^Debto2\.")
DEBTOR2_TEXT = re.compile(r"Debtor 2|non-filing spouse", re.IGNORECASE)
DEBTOR1_PREFIXES = ("Debtor1.", "Debto1.")
# §5.1: Schedule J's district box gets the binding the other 16 forms use.
DISTRICT_BOX = "Bankruptcy District Information"
# Single boxes held unmapped ({}): mapping them would print a wrong answer that
# the old /Yes state hid. Form 121's "no SSN" box is driven by the inverted
# has_ssn_check (DIG-68), so it would tick for every filer who has an SSN.
HELD_UNMAPPED = {("form_121", "Check Box1")}

EXPECTED = {
    "exact": 709,  # the spec's 708 audited bindings + Schedule J's converted district box
    "single": 2,
    "multi": 21,
    "pre_decided": 5,
    "kept_wrong_box": 11,
    "placeholders_removed": 1194,
    "tbd_removed": 50,
    "tbd_converted": 1,
    "template_version_corrected": 3,
    "held_unmapped": 1,
}


def audit_targets(form_type):
    """pdf_field → the audit's correct target; verification.json wins (index README)."""
    targets = {
        row["pdf_field"]: row["correct_target"]
        for row in json.loads((INDEX / "audit" / f"{form_type}.audit.json").read_text())
    }
    for row in json.loads((INDEX / "audit" / "verification.json").read_text()):
        if row["schema"] == form_type:
            targets[row["pdf_field"]] = row["correct_target"]
    return targets


def resolve_target(form_type, pdf_field, widgets, audit_target):
    """Rules 1-3: (the full name a binding fills today or None to drop it, the rule used)."""
    if pdf_field in widgets:
        return pdf_field, "exact"
    if (form_type, pdf_field) in PRE_DECIDED:
        return PRE_DECIDED[(form_type, pdf_field)], "pre_decided"
    candidates = sorted(name for name in widgets if name.split(".")[-1] == pdf_field)
    if len(candidates) == 1:
        return candidates[0], "single"
    if not candidates:
        sys.exit(f"{form_type}: {pdf_field!r} matches no index widget and is not pre-decided")
    debtor1 = [name for name in candidates if name.startswith(DEBTOR1_PREFIXES)]
    if len(debtor1) == 1:
        return debtor1[0], "multi"
    if audit_target in debtor1:  # the audit only breaks a tie
        return audit_target, "multi"
    sys.exit(f"{form_type}: {pdf_field!r} has no single Debtor 1 candidate in {candidates}")


def drop_reason(field, target, widgets):
    """Rules 3-5: why a resolved binding is dropped, or None to keep it."""
    if target is None:
        return "no_widget"
    if field["conditional_on"] == "has_joint_filer":
        return "joint_filer_gate"
    rows = widgets[target]
    if DEBTOR2_NAME.search(target) or any(
        DEBTOR2_TEXT.search(w["label"] or "") or DEBTOR2_TEXT.search(w["column"] or "")
        for w in rows
    ):
        return "debtor_2"
    if any(w["basis"] == "form_control" for w in rows):
        return "form_control"
    return None


def choices_for(target, widgets):
    """Rule 6: one widget state → {"true": state}; an option group → {} until step 2 maps it."""
    states = sorted({w["on_state"] for w in widgets[target] if w["on_state"]})
    if not states:
        sys.exit(f"{target!r} is bound as a box but no widget has an on-state")
    return {"true": export_state(states[0])} if len(states) == 1 else {}


def converted(field, target, choices):
    out = {}
    for key, value in field.items():
        if key == "pdf_field":
            out[key] = target
        elif key == "on_states":
            if field["type"] in ("checkbox", "radio"):
                out["choices"] = choices
        else:
            out[key] = value
    return out


def convert(path, totals):
    schema = json.loads(path.read_text())
    form_type = schema["form_type"]
    rows = json.loads((INDEX / f"{Path(schema['template_filename']).stem}.index.json").read_text())
    widgets = {}
    for row in rows:
        widgets.setdefault(row["full_name"], []).append(row)
    targets = audit_targets(form_type)
    report = {
        "renamed": {},
        "dropped": [],
        "kept_wrong_box": [],
        "unmapped_groups": [],
        "held_unmapped": [],
        "tbd_removed": [],
        "tbd_converted": [],
        "placeholders_removed": 0,
        "template_version_corrected": False,
    }

    fields = []
    for field in schema["fields"]:
        if field["source"] == "TBD":
            if form_type == "schedule_j" and field["pdf_field"] == DISTRICT_BOX:
                field = {**field, "source": "derived", "rule": "district_name"}
                report["tbd_converted"].append(field["pdf_field"])
            else:
                report["tbd_removed"].append(field["pdf_field"])
                continue
        if (
            field["source"] == "constant"
            and field["value"] in (None, "")
            and "choices" not in field
        ):
            report["placeholders_removed"] += 1
            continue

        old = field["pdf_field"]
        audit_target = targets.get(old)
        target, rule = resolve_target(form_type, old, widgets, audit_target)
        totals[rule] += 1
        reason = drop_reason(field, target, widgets)
        if reason:
            report["dropped"].append({"pdf_field": old, "target": target, "reason": reason})
            continue
        if target != old:
            report["renamed"][old] = target
        if rule == "multi" and audit_target not in (None, "", target):
            report["kept_wrong_box"].append({"pdf_field": target, "audit_target": audit_target})
        choices = choices_for(target, widgets) if field["type"] in ("checkbox", "radio") else None
        if (form_type, target) in HELD_UNMAPPED:
            choices = {}
            report["held_unmapped"].append(target)
        elif choices == {}:
            report["unmapped_groups"].append(target)
        fields.append(converted(field, target, choices))

    digest = hashlib.sha256((PDFS / schema["template_filename"]).read_bytes()).hexdigest()
    if digest != schema["template_version"]:
        report["template_version_corrected"] = True
        schema["template_version"] = digest
    schema["fields"] = fields

    totals["kept_wrong_box"] += len(report["kept_wrong_box"])
    totals["placeholders_removed"] += report["placeholders_removed"]
    totals["tbd_removed"] += len(report["tbd_removed"])
    totals["tbd_converted"] += len(report["tbd_converted"])
    totals["held_unmapped"] += len(report["held_unmapped"])
    totals["template_version_corrected"] += report["template_version_corrected"]
    return form_type, report, schema


def main():
    paths = sorted(SCHEMAS.glob("*.json"))
    if len(paths) != 17 or any(p.stem == "form_122b" for p in paths):
        sys.exit("expected the 17 schemas left after form_122b.json is deleted")
    totals = dict.fromkeys(EXPECTED, 0)
    results = [convert(path, totals) for path in paths]

    wrong = {k: (totals[k], v) for k, v in EXPECTED.items() if totals[k] != v}
    if wrong:
        sys.exit(f"counts differ from the spec (got, expected): {wrong}; nothing written")

    dropped = {}
    for _, report, _ in results:
        for row in report["dropped"]:
            dropped[row["reason"]] = dropped.get(row["reason"], 0) + 1
    out = {
        "totals": {**totals, "dropped": dropped},
        "forms": {form_type: report for form_type, report, _ in results},
    }
    for path, (_, _, schema) in zip(paths, results):
        path.write_text(json.dumps(schema, indent=2) + "\n")
    (INDEX / "audit" / "conversion_report.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["totals"], indent=2))


if __name__ == "__main__":
    main()
```

```bash
set -o pipefail
source .claude/forms-step1.env
$PY data/forms/field_index/tools/convert_schemas.py | tail -12
# prettier (the pre-commit hook) owns JSON outside backend/; the first run rewrites, the second confirms
$PRECOMMIT run prettier --files data/forms/field_index/audit/conversion_report.json || true
$PRECOMMIT run prettier --files data/forms/field_index/audit/conversion_report.json
```

Expected:

- The script prints its totals and exits 0, writing the 17 schemas and `audit/conversion_report.json`. It exits non-zero without writing anything if a count differs from the spec (ruling 1).
- The totals are: exact 709, single 2, multi 21, pre_decided 5, kept_wrong_box 11, placeholders_removed 1194, tbd_removed 50, tbd_converted 1, template_version_corrected 3, held_unmapped 1; dropped: joint_filer_gate 19, debtor_2 63, form_control 2, no_widget 4.
- The second prettier run passes.

The output is deterministic. Check it byte for byte:

```bash
set -o pipefail
shasum -a 256 -c <<'SUMS'
928f4ccf92c7ffc5180baff4108eb2dd0ff66fe88b4e226e8243e23f8135a21c  data/forms/schemas/form_101.json
060db2aa116d0ff8c9b518698d7e255e0051b30edd91923f44bd3e8a4425825d  data/forms/schemas/form_103b.json
85639bfd62a9dc5f5d0a0078b0f6fdbdfc5a310deb13f6f43f719c3ddc9a472b  data/forms/schemas/form_106dec.json
29390c0738acddaaddf2882f1280f0e19f8513fd9087c47554ec1e73ba2901b7  data/forms/schemas/form_106sum.json
c639650cf50ce54b2fecdc2a8c6211c95f98b6e501c6f9fef4437726a53b7ed2  data/forms/schemas/form_107.json
cd9b256214674ea381a27870597fbf70708afe321d44bb4bb7aa50f17dac8c51  data/forms/schemas/form_121.json
2ab4542c4724832df7a32379805a391f1331c801a7cea967c7d2e41a9067befe  data/forms/schemas/form_122a1.json
c021e1c79e2d2526ec4b1174c33139fef378177d6f0f522b70169f5a9848b2f9  data/forms/schemas/form_122a1_supp.json
c714ff03ead912c79233287a66b41da4c075f382e41d4ec86521a46e2859c59e  data/forms/schemas/form_122a2.json
f9d846a6a89c3d84bff53a28d24da7a830e9ca0404bd60131a6d1400a2401347  data/forms/schemas/schedule_a_b.json
d9655cd891a68032d03f1e09b9dc4be82c4ab720f5393407b0ee14833b4878ca  data/forms/schemas/schedule_c.json
f14935de11784220ef088747d613e2ab5b17824109a2d8c0803831fb788bf96a  data/forms/schemas/schedule_d.json
2eabd22f860cae29a30a1264ad400404694021d52f586543c15333ad7e13af13  data/forms/schemas/schedule_e_f.json
ba7bf073d5a65bf1631b30606d949e36255c7598e1fa1e852e3f94246dec1284  data/forms/schemas/schedule_g.json
a1899388aac6eff2fafb6ac1642449f28d1d121c0756c807f15a6b4476f9b764  data/forms/schemas/schedule_h.json
ae76dcf7c325a0bd94206d0588399fb9c898824b19d5717904926759e9616d50  data/forms/schemas/schedule_i.json
b02ad2e8bb3b48c2255783424a05f7e455052c7082df4fbd30483759f87c9682  data/forms/schemas/schedule_j.json
f15634d31739f93a0067ab208e232795ac63092537c2307f474a247e36c89994  data/forms/field_index/audit/conversion_report.json
SUMS
```

Expected: every line ends `OK`.

- [ ] **Step 4: Switch the schema model to `choices`, emit export states, and fill exact names**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
index 24a9204..3880183 100644
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -37,10 +37,9 @@ class UIFieldSpec:
 class FieldSpec:
     """Specification for a single form field."""

-    pdf_field: str
+    pdf_field: str  # an index full_name (apps.forms.field_index)
     type: str  # text | checkbox | radio | choice
-    source: str  # constant | derived | asked | ingested | signature | TBD
-    on_states: tuple[str, ...]
+    source: str  # constant | derived | asked | ingested | signature
     page: int
     label: str
     required: bool
@@ -53,6 +52,9 @@ class FieldSpec:
     repeat_capacity: int | None
     row: int | None
     legal_review: bool
+    # checkbox/radio only: normalised answer → export state. {"true": state} is
+    # a single box; {} means not mapped yet, and the binding emits nothing.
+    choices: dict[str, str] | None = None
     ui: UIFieldSpec | None = None


diff --git a/backend/apps/forms/services/fill_resolver.py b/backend/apps/forms/services/fill_resolver.py
index ec7814f..4f93b53 100644
--- a/backend/apps/forms/services/fill_resolver.py
+++ b/backend/apps/forms/services/fill_resolver.py
@@ -27,6 +27,19 @@ class RepeatOverflow(Exception):
         )


+class UnmappedChoice(Exception):
+    """A checkbox or radio answer has no export state in its binding's choices."""
+
+    def __init__(self, pdf_field: str):
+        self.pdf_field = pdf_field
+        super().__init__(f"No box on the form matches the answer for {pdf_field!r}")
+
+
+# Single-box answers, compared case-insensitively (spec §5.1).
+_TICK = {"yes", "y", "true", "1", "on"}
+_NO_TICK = {"no", "n", "false", "0", "off", ""}
+
+
 def resolve_binding(binding: str, session: IntakeSession) -> str | list[str]:
     """
     Resolve a schema ``binding``:
@@ -98,12 +111,27 @@ def _scalar_value(
     return None


+def _unmapped(field: FieldSpec) -> bool:
+    """A checkbox or radio binding whose choices are not mapped yet emits nothing."""
+    return field.type in ("checkbox", "radio") and not field.choices
+
+
 def _emit(field: FieldSpec, value: str | None) -> str | None:
-    """Apply checkbox on-state semantics and string coercion. None = skip."""
+    """Turn a resolved value into what the filler writes. None = leave the box alone."""
+    if field.type in ("checkbox", "radio"):
+        key = "" if value is None else str(value).strip().lower()
+        if set(field.choices) == {"true"}:  # a single box
+            if key in _TICK:
+                return field.choices["true"]
+            if key in _NO_TICK:
+                return None
+        elif key == "":
+            return None
+        elif key in field.choices:
+            return field.choices[key]
+        raise UnmappedChoice(field.pdf_field)
     if value is None or value == "":
         return None
-    if field.type in ("checkbox", "radio"):
-        return field.on_states[0] if field.on_states else "/Yes"
     return str(value)


@@ -128,7 +156,7 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:

     # Non-repeat fields
     for f in schema.fields:
-        if f.repeat is not None:
+        if f.repeat is not None or _unmapped(f):
             continue
         if not _section_applies(f, session, answer_cache=_form_answers):
             continue
@@ -157,7 +185,7 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
         if actual > capacity:
             raise RepeatOverflow(schema.form_type, group_name, capacity, actual)
         for f in fields:
-            if f.legal_review and f.source != "asked":
+            if _unmapped(f) or (f.legal_review and f.source != "asked"):
                 continue
             if f.binding:
                 vals = resolved_cols.get(f.pdf_field)
PATCH
```

```python file=backend/apps/forms/services/pdf_filler.py
"""
PDFFormFiller — fills an AO court PDF template with resolved field values.

Keys are index full names (apps.forms.field_index). A key fills only the
widgets whose qualified name equals it exactly. pypdf's
update_page_form_field_values also matches a parent's partial /T, which put
the filer's name and dates in Debtor 2 boxes (DIG-63), so the filler walks the
widgets itself.

Usage:
    pdf_bytes = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
"""

from io import BytesIO
from pathlib import Path

import pypdf
from django.conf import settings
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

# pypdf internal, pinned with pypdf==6.13.1; test_pdf_filler.py fails if it moves.
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.forms.schema import load_schema


class UnknownField(Exception):
    """A key names no widget in the template."""

    def __init__(self, form_type: str, names: list[str]):
        self.form_type = form_type
        self.names = names
        super().__init__(f"{form_type}: no widget named {names}")


class TemplateHasNoForm(Exception):
    """The template PDF has no /AcroForm, so nothing can be filled."""

    def __init__(self, form_type: str):
        self.form_type = form_type
        super().__init__(f"{form_type}: the template has no fillable form")


class InvalidFieldValue(Exception):
    """A button value is no widget's appearance state, or a combo value is not in /Opt."""

    def __init__(self, form_type: str, name: str):
        self.form_type = form_type
        self.name = name
        super().__init__(f"{form_type}: {name!r} can't take this value")


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


class PDFFormFiller:
    """Fill AO court PDF templates with field values and return bytes."""

    def fill(self, form_type: str, field_values: dict[str, str]) -> bytes:
        """
        Fill the form's template with field_values and return the PDF bytes.

        Args:
            form_type: a registered form type; its schema names the template.
            field_values: {full_name: value}. A value is text, an /Opt entry for
                a combo box, or an export state such as "/Chapter 7" for a button.

        Raises:
            UnknownField: a key names no widget.
            TemplateHasNoForm: the template has no /AcroForm.
            InvalidFieldValue: a button state or combo option the template lacks.
        """
        schema = load_schema(form_type)
        template_path = Path(settings.PDF_FORMS_DIRECTORY) / schema.template_filename
        writer = pypdf.PdfWriter(clone_from=str(template_path))
        if "/AcroForm" not in writer.root_object:
            raise TemplateHasNoForm(form_type)
        acro_form = writer.root_object["/AcroForm"].get_object()
        # Viewers draw the appearance streams written here, not their own.
        writer.set_need_appearances_writer(False)

        filled: set[str] = set()
        buttons: set[str] = set()
        ticked: set[str] = set()
        for page in writer.pages:
            for annot in page.get("/Annots") or []:
                widget = annot.get_object()
                if widget.get("/Subtype") != "/Widget":
                    continue
                field = field_of(widget)
                name = qualified_name(field)
                if name not in field_values:
                    continue
                filled.add(name)
                value = field_values[name]

                if field.get_inherited("/FT") == "/Btn":
                    buttons.add(name)
                    field[NameObject("/V")] = NameObject(value)
                    if value in widget["/AP"]["/N"]:
                        widget[NameObject("/AS")] = NameObject(value)
                        ticked.add(name)
                    else:
                        widget[NameObject("/AS")] = NameObject("/Off")
                    continue

                if field.get_inherited("/FT") == "/Ch":
                    options = [str(o) for o in field.get_inherited("/Opt", [])]
                    if value not in options:
                        raise InvalidFieldValue(form_type, name)
                    if "/I" in field:  # a stale selected index would override /V
                        del field["/I"]
                field[NameObject("/V")] = TextStringObject(value)
                # pypdf internal, pinned: builds the text appearance from /DA and /V.
                appearance = TextStreamAppearance.from_text_annotation(
                    writer, page, False, acro_form, field, widget
                )
                widget[NameObject("/AP")] = DictionaryObject(
                    {NameObject("/N"): writer._add_object(appearance)}
                )

        unknown = sorted(set(field_values) - filled)
        if unknown:
            raise UnknownField(form_type, unknown)
        for name in sorted(buttons - ticked):
            raise InvalidFieldValue(form_type, name)

        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue()
```

```bash
set -o pipefail
git rm -q backend/apps/forms/management/commands/ingest_form_schema.py backend/apps/forms/tests/test_ingest_command.py
```

The ingest command rebuilt schemas from templates. It wrote `on_states`, and re-running it wiped bindings (DIG-127). The conversion above replaces it.

- [ ] **Step 5: Run the task's tests and the whole suite**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_pdf_filler.py apps/forms/tests/test_fill_resolver.py apps/forms/tests/test_schema.py -q -p no:cacheprovider
$PY -m ruff check apps/
$PY -m pytest -q -p no:cacheprovider 2>&1 | tail -2
```

Expected: all pass, `All checks passed!`, then `758 passed, 1 xfailed`.

- [ ] **Step 6: Commit**

```bash
set -o pipefail
git add \
  data/forms/field_index/tools/convert_schemas.py \
  data/forms/field_index/audit/conversion_report.json \
  data/forms/schemas/*.json \
  backend/apps/forms/tests/pdf_readback.py \
  backend/apps/forms/schema.py \
  backend/apps/forms/services/fill_resolver.py \
  backend/apps/forms/services/pdf_filler.py \
  backend/apps/forms/tests/test_coverage.py \
  backend/apps/forms/tests/test_engine_form_agnostic.py \
  backend/apps/forms/tests/test_fill_resolver.py \
  backend/apps/forms/tests/test_form_103b_schema.py \
  backend/apps/forms/tests/test_form_106dec_schema.py \
  backend/apps/forms/tests/test_form_106sum_schema.py \
  backend/apps/forms/tests/test_form_121_schema.py \
  backend/apps/forms/tests/test_form_122a1_schema.py \
  backend/apps/forms/tests/test_pdf_field_maps.py \
  backend/apps/forms/tests/test_pdf_filler.py \
  backend/apps/forms/tests/test_schedule_i_schema.py \
  backend/apps/forms/tests/test_schema.py \
  backend/apps/forms/tests/test_schema_views.py
git commit -F - <<'MSG'
feat(forms): bind every schema field to an index full name, and fill only exact names

Schemas name widgets by the field index's full_name; checkbox and radio
bindings carry a choices map from answer to export state. A one-off
conversion (data/forms/field_index/tools/convert_schemas.py) rewrote the 17
schemas and recorded every rename and drop in conversion_report.json. The
filler fills exactly the names it is given, stores a text appearance, and ticks
a box by its export state. Retires the schema ingest command (DIG-127).
MSG
git status --short
```

### Task 4: Check every schema against the field index at startup

_Built and verified as commit `264d63d` on `plan/forms-step1`._

**Files:**

- Create: `backend/apps/forms/checks.py`
- Create: `backend/apps/forms/tests/test_checks.py`
- Modify: `backend/apps/forms/apps.py`
- Modify: `backend/apps/forms/schema.py`
- Modify: `backend/apps/forms/tests/test_coverage.py`
- Modify: `backend/apps/forms/tests/test_schema.py`

**Interfaces:**

- Consumes: `load_index`, `export_state` (Task 1); `FieldSpec.choices` and the converted schemas (Task 3).
- Produces:

  - `apps.forms.schema.validate_schema(schema, derivations, predicates) -> list[tuple[str, str]]`, a list of (code, message) pairs with codes E002–E007.
  - `apps.forms.checks.validate_form(form_type: str) -> list[checks.Error]`. E001 means the schema or index is missing.
  - The registered system check `form_schemas_match_field_index`, imported in `FormsConfig.ready()`.
  - `template_field_names` is removed.

- [ ] **Step 1: Write the failing check tests**

```python file=backend/apps/forms/tests/test_checks.py
"""
A schema that disagrees with its template or field index stops the app from starting.

pytest-django runs no system checks, so these tests call the same
validate_form() the check uses (spec §5.4), on every registered form and on
deliberately broken copies of real schemas.
"""

import json
import shutil

import pytest
from django.conf import settings as django_settings
from django.core.management import call_command
from django.core.management.base import SystemCheckError

from apps.forms.checks import validate_form
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema


@pytest.fixture
def schema_copy(tmp_path, settings):
    """A writable copy of the real schemas; edit one, then validate it."""
    shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, tmp_path / "schemas")
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path / "schemas"
    load_schema.cache_clear()
    yield tmp_path / "schemas"
    load_schema.cache_clear()


def _edit(schemas, form_type, change):
    path = schemas / f"{form_type}.json"
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))


def _field(data, pdf_field):
    return next(f for f in data["fields"] if f["pdf_field"] == pdf_field)


def _ids(form_type):
    return [e.id for e in validate_form(form_type)]


@pytest.mark.parametrize("form_type", get_all_form_types())
def test_every_registered_form_passes(form_type):
    assert validate_form(form_type) == []


def test_missing_schema_is_reported(schema_copy):
    (schema_copy / "form_121.json").unlink()
    assert _ids("form_121") == ["forms.E001"]


def test_changed_template_is_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: d.update(template_version="0" * 64))
    assert _ids("form_121") == ["forms.E002"]


def test_short_name_is_reported(schema_copy):
    # A short name is what put the filer's name in Debtor 2 boxes (DIG-63).
    _edit(schema_copy, "form_122a1", lambda d: _field(d, "Debtor1.Name").update(pdf_field="Name"))
    assert _ids("form_122a1") == ["forms.E003"]


def test_checkbox_bound_as_text_is_reported(schema_copy):
    def change(d):
        box = _field(d, "Check Box1")
        box.update(type="text")
        del box["choices"]

    _edit(schema_copy, "form_121", change)
    assert _ids("form_121") == ["forms.E004"]


def test_push_button_binding_is_reported(schema_copy):
    print_button = {
        "pdf_field": "Button.Print1",
        "type": "text",
        "source": "constant",
        "page": 9,
        "label": "",
        "required": False,
        "conditional_on": None,
        "value": "x",
        "rule": None,
        "ingest_key": None,
        "binding": None,
        "repeat": None,
        "repeat_capacity": None,
        "row": None,
        "legal_review": False,
    }
    _edit(schema_copy, "form_101", lambda d: d["fields"].append(print_button))
    assert _ids("form_101") == ["forms.E004"]


def test_checkbox_without_choices_is_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: _field(d, "Check Box1").pop("choices"))
    assert _ids("form_121") == ["forms.E004"]


def test_state_the_template_lacks_is_reported(schema_copy):
    # The old schema wrote /Yes; the template's state is /On, so nothing ticked.
    _edit(
        schema_copy, "form_121", lambda d: _field(d, "Check Box1").update(choices={"true": "/Yes"})
    )
    assert _ids("form_121") == ["forms.E005"]


def test_district_constant_outside_the_options_is_reported(schema_copy):
    district = "Bankruptcy District Information"
    _edit(
        schema_copy,
        "form_121",
        lambda d: _field(d, district).update(source="constant", rule=None, value="Nowhere"),
    )
    assert _ids("form_121") == ["forms.E005"]


def test_box_bound_twice_is_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: d["fields"].append(_field(d, "Debtor1.First name")))
    assert _ids("form_121") == ["forms.E006"]


@pytest.mark.parametrize(
    "change",
    [
        {"source": "TBD"},
        {"source": "derived", "rule": "no_such_rule"},
        {"conditional_on": "no_such_predicate"},
        {"source": "asked", "rule": None, "binding": "intake.first_name"},
    ],
)
def test_unresolvable_source_is_reported(schema_copy, change):
    _edit(schema_copy, "form_121", lambda d: _field(d, "Debtor1.First name").update(change))
    assert _ids("form_121") == ["forms.E007"]


def test_manage_py_check_fails_on_a_bad_schema(schema_copy):
    """migrate runs the same checks, so this is what fails a Heroku release."""
    _edit(schema_copy, "form_121", lambda d: d.update(template_version="0" * 64))
    with pytest.raises(SystemCheckError, match="forms.E002"):
        call_command("check")
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_coverage.py b/backend/apps/forms/tests/test_coverage.py
index f972310..46f4cec 100644
--- a/backend/apps/forms/tests/test_coverage.py
+++ b/backend/apps/forms/tests/test_coverage.py
@@ -5,7 +5,7 @@ from django.core.management import call_command

 from apps.districts.models import District
 from apps.forms.schema import load_schema
-from apps.forms.services.fill_resolver import _section_applies, resolve  # noqa: PLC2701
+from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import IntakeSession


@@ -16,26 +16,6 @@ def ilnd_fixture(db):
         call_command("loaddata", "ilnd_2025_data")


-@pytest.mark.django_db
-def test_resolver_fills_every_applicable_required_field(ilnd_fixture):
-    call_command("seed_demo_data", "--reset", persona="maria")
-    session = IntakeSession.objects.filter(user__username="demo_maria").first()
-
-    schema = load_schema("form_107")
-    out = resolve(schema, session)
-
-    applicable_required = [
-        f
-        for f in schema.fields
-        if f.required
-        and _section_applies(f, session)
-        and f.source not in ("signature", "ingested")
-        and not f.legal_review
-    ]
-    unresolved = [f.pdf_field for f in applicable_required if f.pdf_field not in out]
-    assert unresolved == [], f"unresolved applicable fields: {unresolved}"
-
-
 @pytest.mark.django_db
 def test_resolved_fields_come_from_multiple_sources(ilnd_fixture):
     """Resolver pulls from derivations, SOFA, constants — not just one source."""
@@ -54,24 +34,3 @@ def test_resolved_fields_come_from_multiple_sources(ilnd_fixture):
     assert any(
         v for v in out.values() if v
     ), "all fields are empty — resolver may not be pulling source data"
-
-
-@pytest.mark.django_db
-def test_form_101_all_applicable_fields_resolve(ilnd_fixture):
-    """Every applicable Form 101 field resolves to a value for a seeded persona."""
-    call_command("seed_demo_data", "--reset", persona="maria")
-    session = IntakeSession.objects.filter(user__username="demo_maria").first()
-
-    schema = load_schema("form_101")
-    out = resolve(schema, session)
-
-    applicable_required = [
-        f
-        for f in schema.fields
-        if f.required
-        and _section_applies(f, session)
-        and f.source not in ("signature", "ingested")
-        and not f.legal_review
-    ]
-    unresolved = [f.pdf_field for f in applicable_required if f.pdf_field not in out]
-    assert unresolved == [], f"unresolved Form 101 fields: {unresolved}"
diff --git a/backend/apps/forms/tests/test_schema.py b/backend/apps/forms/tests/test_schema.py
index a5b408a..a957833 100644
--- a/backend/apps/forms/tests/test_schema.py
+++ b/backend/apps/forms/tests/test_schema.py
@@ -4,8 +4,7 @@ import json

 import pytest

-from apps.forms.schema import FieldSpec, FormSchema, load_schema, validate_schema
-from apps.forms.services.derivations import DERIVATIONS, PREDICATES
+from apps.forms.schema import FieldSpec, FormSchema, load_schema

 SAMPLE = {
     "form_type": "form_test",
@@ -52,64 +51,6 @@ def test_load_schema_missing_file_raises(tmp_path, settings):
         load_schema("does_not_exist")


-def _schema(**field_overrides):
-    base = dict(SAMPLE["fields"][0])
-    base.update(field_overrides)
-    return FormSchema("form_test", "b_107_0425-form.pdf", "v1", [FieldSpec(**base)])
-
-
-def test_validate_flags_unknown_pdf_field():
-    schema = _schema(pdf_field="NOT_A_REAL_FIELD_xyz", source="constant", value="x", rule=None)
-    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
-    assert any("NOT_A_REAL_FIELD_xyz" in e for e in errors)
-
-
-def test_validate_flags_tbd_source():
-    schema = _schema(pdf_field="Debtor 1", source="TBD", rule=None)
-    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
-    assert any("TBD" in e for e in errors)
-
-
-def test_validate_flags_unknown_rule():
-    schema = _schema(pdf_field="Debtor 1", source="derived", rule="no_such_rule")
-    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
-    assert any("no_such_rule" in e for e in errors)
-
-
-def test_validate_clean_schema_returns_empty():
-    schema = _schema(pdf_field="Debtor 1", source="derived", rule="full_name")
-    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
-    assert errors == []
-
-
-@pytest.mark.django_db
-def test_form_107_schema_is_valid(db):
-    schema = load_schema("form_107")
-    errors = validate_schema(schema, derivations=set(DERIVATIONS), predicates=set(PREDICATES))
-    assert errors == [], "form_107 schema invalid:\n" + "\n".join(errors)
-
-
-@pytest.mark.django_db
-def test_form_107_schema_has_no_tbd(db):
-    schema = load_schema("form_107")
-    assert all(f.source != "TBD" for f in schema.fields), "form_107 has fields with source=TBD"
-
-
-def test_form_101_schema_is_valid(db):
-    schema = load_schema("form_101")
-    errors = validate_schema(schema, derivations=set(DERIVATIONS), predicates=set(PREDICATES))
-    assert not errors
-
-
-def test_form_101_schema_has_no_tbd(db):
-    schema = load_schema("form_101")
-    for f in schema.fields:
-        if f.source != "skip":
-            assert "TBD" not in f.pdf_field
-            assert "TBD" not in str(f.rule)
-            assert "TBD" not in str(f.binding)
-
-
 def test_load_schema_with_ui_metadata(tmp_path, settings):
     settings.FORM_SCHEMAS_DIRECTORY = tmp_path
     schema_data = {
PATCH
```

The patch to `test_schema.py` deletes the old `validate_schema` tests, which `test_checks.py` supersedes. The patch to `test_coverage.py` deletes two required-field tests that loop over zero fields and so assert nothing.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_checks.py -q -p no:cacheprovider
```

Expected: FAIL — `ModuleNotFoundError: No module named 'apps.forms.checks'`.

- [ ] **Step 3: Rewrite `validate_schema`, add the check, and register it**

```python file=backend/apps/forms/schema.py
"""
Schema dataclasses and loader for form field specifications.

Provides FieldSpec (individual field definition) and FormSchema (complete form specification),
plus load_schema() function to load form schemas from JSON files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pypdf
from django.conf import settings

from apps.forms.field_index import export_state, load_index


@dataclass(frozen=True)
class UIFieldSpec:
    step: str
    prompt: str
    widget: str
    help_text: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> UIFieldSpec:
        return cls(
            step=data.get("step", "Unknown Step"),
            prompt=data.get("prompt", ""),
            widget=data.get("widget", "text"),
            help_text=data.get("help_text"),
        )


@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single form field."""

    pdf_field: str  # an index full_name (apps.forms.field_index)
    type: str  # text | checkbox | radio | choice
    source: str  # constant | derived | asked | ingested | signature
    page: int
    label: str
    required: bool
    conditional_on: str | None  # PREDICATES key, or None = always applicable
    value: str | None
    rule: str | None
    ingest_key: str | None
    binding: str | None
    repeat: str | None
    repeat_capacity: int | None
    row: int | None
    legal_review: bool
    # checkbox/radio only: normalised answer → export state. {"true": state} is
    # a single box; {} means not mapped yet, and the binding emits nothing.
    choices: dict[str, str] | None = None
    ui: UIFieldSpec | None = None


@dataclass(frozen=True)
class FormSchema:
    """Complete specification for a form, including all fields."""

    form_type: str
    template_filename: str
    template_version: str
    fields: list[FieldSpec]


@lru_cache(maxsize=32)
def load_schema(form_type: str) -> FormSchema:
    """
    Load and parse form schema from JSON.

    Args:
        form_type: The form type identifier (e.g., 'form_101')

    Returns:
        FormSchema dataclass instance

    Raises:
        FileNotFoundError: If schema file does not exist
        json.JSONDecodeError: If schema file is invalid JSON
    """
    schema_path = Path(settings.FORM_SCHEMAS_DIRECTORY) / f"{form_type}.json"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path) as f:
        raw = json.load(f)

    # Convert field dicts to FieldSpec dataclass instances
    fields = []
    for field_data in raw["fields"]:
        ui_data = field_data.pop("ui", None)
        ui_spec = UIFieldSpec.from_dict(ui_data) if ui_data else None
        fields.append(FieldSpec(**field_data, ui=ui_spec))

    return FormSchema(
        form_type=raw["form_type"],
        template_filename=raw["template_filename"],
        template_version=raw["template_version"],
        fields=fields,
    )


# Index widget types each binding type may target (spec §5.4 check 4).
_WIDGET_TYPES = {
    "text": {"Text"},
    "choice": {"ComboBox"},
    "checkbox": {"CheckBox", "RadioButton"},
    "radio": {"CheckBox", "RadioButton"},
}
_BINDING_NAMESPACES = ("answer:", "sofa.")


def validate_schema(
    schema: FormSchema, derivations: set[str], predicates: set[str]
) -> list[tuple[str, str]]:
    """
    Check a schema against its template and field index (spec §5.4, checks 2-7).

    Returns (code, message) pairs; an empty list means the schema is valid.
    apps.forms.checks reports each pair as a forms.<code> system-check error.
    """
    errors: list[tuple[str, str]] = []
    template = (Path(settings.PDF_FORMS_DIRECTORY) / schema.template_filename).read_bytes()
    if hashlib.sha256(template).hexdigest() != schema.template_version:
        errors.append(("E002", "template_version is not the template's SHA-256"))

    index = load_index(schema.template_filename)
    template_fields = pypdf.PdfReader(BytesIO(template)).get_fields() or {}
    seen: dict[str, list[FieldSpec]] = {}

    for f in schema.fields:
        widgets = index.get(f.pdf_field)
        if widgets is None:
            errors.append(("E003", f"{f.pdf_field!r} is not a full name in the field index"))
            continue
        seen.setdefault(f.pdf_field, []).append(f)

        types = {w.type for w in widgets}
        if any(w.basis == "form_control" for w in widgets):
            errors.append(("E004", f"{f.pdf_field!r} is a push button"))
        elif not types <= _WIDGET_TYPES.get(f.type, set()):
            errors.append(("E004", f"{f.pdf_field!r} is bound as {f.type} but is {sorted(types)}"))
        if (f.type in ("checkbox", "radio")) != (f.choices is not None):
            errors.append(("E004", f"{f.pdf_field!r}: choices go on checkbox and radio only"))

        if f.choices:
            states = {export_state(w.on_state) for w in widgets if w.on_state}
            for state in sorted(set(f.choices.values()) - states):
                errors.append(("E005", f"{f.pdf_field!r} has no state {state!r}"))
        if f.type == "choice" and f.source == "constant":
            options = [str(o) for o in template_fields[f.pdf_field].get("/Opt", [])]
            if f.value not in options:
                errors.append(("E005", f"{f.pdf_field!r} has no option {f.value!r}"))

        if f.source == "TBD":
            errors.append(("E007", f"{f.pdf_field!r}: source is still TBD"))
        if f.source == "derived" and f.rule not in derivations:
            errors.append(("E007", f"{f.pdf_field!r}: unknown derivation rule {f.rule!r}"))
        if f.conditional_on is not None and f.conditional_on not in predicates:
            errors.append(("E007", f"{f.pdf_field!r}: unknown predicate {f.conditional_on!r}"))
        if f.binding is not None and not f.binding.startswith(_BINDING_NAMESPACES):
            errors.append(("E007", f"{f.pdf_field!r}: unknown binding namespace {f.binding!r}"))
        if f.repeat is not None and not f.repeat_capacity:
            errors.append(("E007", f"repeat group {f.repeat!r} has no repeat_capacity"))

    for name, bindings in seen.items():
        rows = {(b.repeat, b.row) for b in bindings}
        same_group = len({b.repeat for b in bindings}) == 1 and bindings[0].repeat is not None
        if len(bindings) > 1 and not (same_group and len(rows) == len(bindings)):
            errors.append(("E006", f"{name!r} is bound {len(bindings)} times"))
    return errors
```

```python file=backend/apps/forms/checks.py
"""
System check: every registered form's schema agrees with its template and field index.

Django runs system checks on manage.py check, runserver and migrate. Heroku's
release phase runs migrate, so a bad schema fails the release before filers
see it. pytest-django runs no system checks, so test_checks.py calls
validate_form() for every form instead (spec §5.4).
"""

from django.core import checks

from apps.forms.field_index import index_path
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema, validate_schema
from apps.forms.services.derivations import DERIVATIONS, PREDICATES


def validate_form(form_type: str) -> list[checks.Error]:
    """Every problem with one form's schema, as forms.E0xx errors naming the form."""
    try:
        schema = load_schema(form_type)
    except FileNotFoundError:
        return [checks.Error(f"{form_type}: no schema file", id="forms.E001")]
    if not index_path(schema.template_filename).exists():
        return [
            checks.Error(
                f"{form_type}: no field index for {schema.template_filename}", id="forms.E001"
            )
        ]
    return [
        checks.Error(f"{form_type}: {message}", id=f"forms.{code}")
        for code, message in validate_schema(schema, set(DERIVATIONS), set(PREDICATES))
    ]


@checks.register()
def form_schemas_match_field_index(app_configs, **kwargs):
    return [error for form_type in get_all_form_types() for error in validate_form(form_type)]
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/apps.py b/backend/apps/forms/apps.py
index 11a4995..e5acde3 100644
--- a/backend/apps/forms/apps.py
+++ b/backend/apps/forms/apps.py
@@ -4,3 +4,6 @@ from django.apps import AppConfig
 class FormsConfig(AppConfig):
     default_auto_field = "django.db.models.BigAutoField"
     name = "apps.forms"
+
+    def ready(self):
+        from apps.forms import checks  # noqa: F401  registers the schema system check
PATCH
```

- [ ] **Step 4: Run the check tests, the system check and the suite**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_checks.py -q -p no:cacheprovider
$PY manage.py check
$PY -m pytest -q -p no:cacheprovider 2>&1 | tail -2
```

Expected: the check tests pass, `System check identified no issues (0 silenced).`, then `779 passed, 1 xfailed`.

- [ ] **Step 5: Commit**

```bash
set -o pipefail
git add \
  backend/apps/forms/checks.py \
  backend/apps/forms/tests/test_checks.py \
  backend/apps/forms/apps.py \
  backend/apps/forms/schema.py \
  backend/apps/forms/tests/test_coverage.py \
  backend/apps/forms/tests/test_schema.py
git commit -F - <<'MSG'
feat(forms): check every schema against the field index at startup

A Django system check (forms.E001-E007) validates all 17 schemas: template
hash, full names in the index, widget types, export states and /Opt values,
duplicate bindings, and TBD sources, rules, predicates and binding namespaces.
manage.py check, runserver and migrate (the Heroku release) fail on a bad
schema.
MSG
git status --short
```

### Task 5: Read every filled form back against the field index (oracle tiers 1 and 2)

_Built and verified as commit `2c7358b` on `plan/forms-step1`._

**Files:**

- Create: `backend/apps/forms/tests/known_defects.json`
- Create: `backend/apps/forms/tests/oracle.py`
- Create: `backend/apps/forms/tests/test_known_defects.py`
- Create: `backend/apps/forms/tests/test_oracle_tier1.py`
- Create: `backend/apps/forms/tests/test_oracle_tier2.py`
- Create: `data/forms/field_index/tools/record_known_defects.py`

**Interfaces:**

- Consumes: `PDFFormFiller`, `read_widgets` (Task 3); `load_index`, `export_state` (Task 1); `audit/*.json` and `audit/verification.json`; `conversion_report.json` (Task 3), whose `renamed` maps join converted bindings back to their audit rows.
- Produces:

  - `apps/forms/tests/oracle.py`, with `KNOWN_DEFECTS_PATH`, `DEFECT_CLASSES`, `load_known_defects()` keyed by `(form_type, pdf_field, tier, case)`, and `case_param(form_type, pdf_field, tier, case, *values)`, which builds a `pytest.param` with a strict xfail when the case is listed.
  - `known_defects.json`, a sorted list of `{form_type, pdf_field, tier, case, class, ticket}`.
  - The recorder `data/forms/field_index/tools/record_known_defects.py`. It is a one-off tool, kept so the list can be regenerated when a defect is fixed.
  - The assertion messages start with their class: `no_widget:`, `spill:`, `unmapped_choice:` (tier 1), `wrong_box:` (tier 2) and `wrong_value:` (tier 3). The recorder reads that prefix.

- [ ] **Step 1: Write the oracle, its two tiers, the list check, and an empty list**

```python file=backend/apps/forms/tests/oracle.py
"""
Shared pieces of the court-form oracle (spec §6): case keys and the known-defects list.

Every oracle case has a key (form_type, pdf_field, tier, case). A key listed in
known_defects.json runs as a strict expected failure, so a new break fails CI
and so does a fix until its entry is deleted. test_known_defects.py fails on an
entry that matches no generated case.
"""

import json
from pathlib import Path

import pytest

KNOWN_DEFECTS_PATH = Path(__file__).with_name("known_defects.json")
DEFECT_CLASSES = {
    "1": {"no_widget", "collision", "spill", "unmapped_choice"},
    "2": {"wrong_box"},
    "3": {"wrong_value", "no_source"},
}


def load_known_defects() -> dict[tuple[str, str, str, str], dict]:
    entries = json.loads(KNOWN_DEFECTS_PATH.read_text())
    return {(e["form_type"], e["pdf_field"], e["tier"], e["case"]): e for e in entries}


KNOWN_DEFECTS = load_known_defects()


def case_param(form_type: str, pdf_field: str, tier: str, case: str, *values):
    """A pytest.param for one oracle case, a strict xfail when the list names it."""
    entry = KNOWN_DEFECTS.get((form_type, pdf_field, tier, case))
    marks = (
        [pytest.mark.xfail(strict=True, reason=f"{entry['class']} {entry['ticket']}")]
        if entry
        else []
    )
    case_id = f"{form_type}:{pdf_field}" + (f":{case}" if case else "")
    return pytest.param(form_type, pdf_field, case, *values, marks=marks, id=case_id)
```

```python file=backend/apps/forms/tests/test_oracle_tier1.py
"""
Oracle tier 1: every binding lands in exactly the widget it names (spec §6).

Each text and combo binding gets a unique marker, the real filler fills the
real template, and every widget is read back. A checkbox state is set and read
from /AS, which is what a viewer draws; /V alone proves nothing (DIG-68).
No database is needed.
"""

from functools import cache
from pathlib import Path

import pypdf
import pytest
from django.conf import settings

from apps.forms.field_index import export_state, load_index
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.oracle import case_param
from apps.forms.tests.pdf_readback import read_widgets

TIER = "1"


def _fields(form_type, types):
    return [f for f in load_schema(form_type).fields if f.type in types]


def _first_option(form_type, pdf_field):
    template = Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
    return str(pypdf.PdfReader(template).get_fields()[pdf_field]["/Opt"][0])


@cache
def _text_landing(form_type):
    """pdf_field → the full names its marker was read back from."""
    markers = {
        f.pdf_field: (_first_option(form_type, f.pdf_field) if f.type == "choice" else f"Q{i:03d}")
        for i, f in enumerate(_fields(form_type, ("text", "choice")))
    }
    filler = PDFFormFiller()
    widgets = read_widgets(filler.fill(form_type, markers))
    landing = {
        name: {w.full_name for w in widgets if w.value == marker}
        for name, marker in markers.items()
    }
    # Another key's value can hide a marker in a batch (Schedule C 2.3); re-check alone.
    for name, found in landing.items():
        if not found:
            alone = read_widgets(filler.fill(form_type, {name: markers[name]}))
            landing[name] = {w.full_name for w in alone if w.value == markers[name]}
    return landing


@cache
def _box_fill(form_type, position):
    """Fill the position-th choice of every mapped box at once; boxes share no widgets."""
    values = {}
    for f in _fields(form_type, ("checkbox", "radio")):
        keys = sorted(f.choices or {})
        if position < len(keys):
            values[f.pdf_field] = f.choices[keys[position]]
    return read_widgets(PDFFormFiller().fill(form_type, values))


def _text_cases():
    for form_type in get_all_form_types():
        for f in _fields(form_type, ("text", "choice")):
            yield case_param(form_type, f.pdf_field, TIER, "")


def _box_cases(mapped):
    for form_type in get_all_form_types():
        for f in _fields(form_type, ("checkbox", "radio")):
            if mapped:
                for key in sorted(f.choices or {}):
                    yield case_param(form_type, f.pdf_field, TIER, key)
            elif not f.choices:
                yield case_param(form_type, f.pdf_field, TIER, "")


TEXT_CASES = list(_text_cases())
BOX_CASES = list(_box_cases(mapped=True))
UNMAPPED_CASES = list(_box_cases(mapped=False))


@pytest.mark.parametrize("form_type,pdf_field,case", TEXT_CASES)
def test_value_lands_only_in_the_box_it_names(form_type, pdf_field, case):
    landed = _text_landing(form_type)[pdf_field]
    assert landed, "no_widget: the value landed nowhere"
    assert landed == {pdf_field}, f"spill: the value also landed in {sorted(landed - {pdf_field})}"


@pytest.mark.parametrize("form_type,pdf_field,case", BOX_CASES)
def test_checkbox_ticks_only_the_widgets_for_its_answer(form_type, pdf_field, case):
    field = next(f for f in load_schema(form_type).fields if f.pdf_field == pdf_field)
    state = field.choices[case]
    template = load_schema(form_type).template_filename
    expected = sum(
        1
        for w in load_index(template)[pdf_field]
        if w.on_state and export_state(w.on_state) == state
    )
    own = [
        w
        for w in _box_fill(form_type, sorted(field.choices).index(case))
        if w.full_name == pdf_field
    ]
    ticked = [w for w in own if w.state == state]
    assert len(ticked) == expected, f"no_widget: {len(ticked)} of {expected} widgets show {state}"
    assert all(w.state == "/Off" for w in own if w.state != state), "spill: another option is on"


@pytest.mark.parametrize("form_type,pdf_field,case", UNMAPPED_CASES)
def test_checkbox_answer_is_mapped_to_a_box(form_type, pdf_field, case):
    field = next(f for f in load_schema(form_type).fields if f.pdf_field == pdf_field)
    assert field.choices, "unmapped_choice: no answer value maps to a box yet"
```

```python file=backend/apps/forms/tests/test_oracle_tier2.py
"""
Oracle tier 2: each binding targets the box the verified audit says it should (spec §6).

Bindings join their audit rows through the conversion report's old→new name
map. A binding is asserted only where the audit was checked against the page
image: a verification.json row, or a target widget whose index basis is
adjudicated or sampled_ok. Everything else is unverified and not asserted.
"""

import json
import re
from functools import cache

import pytest
from django.conf import settings

from apps.forms.field_index import load_index
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.tests.oracle import case_param

TIER = "2"
CHECKED_BASES = {"adjudicated", "sampled_ok"}
LEAVE_BLANK = "leave blank"


def _audit_dir():
    return settings.FORM_INDEX_DIRECTORY / "audit"


@cache
def _verification():
    rows = json.loads((_audit_dir() / "verification.json").read_text())
    return {(r["schema"], r["pdf_field"]): r for r in rows}


@cache
def _audit(form_type):
    rows = json.loads((_audit_dir() / f"{form_type}.audit.json").read_text())
    return {r["pdf_field"]: r for r in rows}


@cache
def _renamed(form_type):
    report = json.loads((_audit_dir() / "conversion_report.json").read_text())
    return report["forms"][form_type]["renamed"]


def _expected_target(form_type, pdf_field):
    """The full name the audit wants, LEAVE_BLANK, None for "not this box", or "" if unasserted."""
    old = {new: old for old, new in _renamed(form_type).items()}.get(pdf_field, pdf_field)
    verified = _verification().get((form_type, old))
    row = verified or _audit(form_type).get(old)
    widgets = load_index(load_schema(form_type).template_filename)[pdf_field]
    if row is None or not (verified or {w.basis for w in widgets} & CHECKED_BASES):
        return ""
    target = (verified["correct_target"] if verified else row["correct_target"]) or ""
    verdicts = verified["final_verdicts"] if verified else row["verdicts"]
    if not target:
        # Right box when the audit found no box fault; a wrong box with no recorded target.
        return None if "wrong_box" in verdicts else pdf_field
    # "Executed on (needs filler change: ...)" → "Executed on"
    return re.sub(r"\s*\(.*\)$", "", target)


def _cases():
    for form_type in get_all_form_types():
        for f in load_schema(form_type).fields:
            target = _expected_target(form_type, f.pdf_field)
            if target != "":
                yield case_param(form_type, f.pdf_field, TIER, "", target)


CASES = list(_cases())


@pytest.mark.parametrize("form_type,pdf_field,case,target", CASES)
def test_binding_targets_the_box_the_audit_verified(form_type, pdf_field, case, target):
    assert target != LEAVE_BLANK, "wrong_box: the audit says this box stays blank"
    assert target is not None, "wrong_box: the audit says this is the wrong box"
    assert pdf_field == target, f"wrong_box: the audit says it belongs in {target!r}"
```

```python file=backend/apps/forms/tests/test_known_defects.py
"""
The known-defects list names only defects the oracle still finds (spec §6).

A strict xfail already fails when a listed defect is fixed. These tests catch
the other way an entry goes stale: its case no longer exists (a binding was
renamed or removed), or it lacks a defect class and ticket.
"""

import re

from apps.forms.tests import test_oracle_tier1 as tier1
from apps.forms.tests import test_oracle_tier2 as tier2
from apps.forms.tests.oracle import DEFECT_CLASSES, KNOWN_DEFECTS

ORACLE_CASES = {
    "1": tier1.TEXT_CASES + tier1.BOX_CASES + tier1.UNMAPPED_CASES,
    "2": tier2.CASES,
}


def _case_keys():
    return {
        (param.values[0], param.values[1], tier, param.values[2])
        for tier, cases in ORACLE_CASES.items()
        for param in cases
    }


def test_every_listed_defect_is_a_case_the_oracle_runs():
    orphans = sorted(set(KNOWN_DEFECTS) - _case_keys())
    assert orphans == [], f"delete these entries; no oracle case matches them: {orphans}"


def test_every_listed_defect_has_a_class_and_a_ticket():
    for key, entry in KNOWN_DEFECTS.items():
        assert entry["class"] in DEFECT_CLASSES[entry["tier"]], key
        assert re.fullmatch(r"DIG-\d+", entry["ticket"]), key
```

```bash
set -o pipefail
echo '[]' > backend/apps/forms/tests/known_defects.json
```

- [ ] **Step 2: Run the tiers and watch them find the defects**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `85 failed, 989 passed`. These are 4 `unmapped_choice` (tier 1) and 81 `wrong_box` (tier 2), each a defect the audit already found.

- [ ] **Step 3: Add the recorder and record the list**

```python file=data/forms/field_index/tools/record_known_defects.py
"""Record every failing oracle case in backend/apps/forms/tests/known_defects.json (spec §6).

Runs the given oracle test files with --runxfail and writes one entry per failing
case. Each entry's class is the assertion message's prefix; its ticket comes from
the rules below. Review the diff of known_defects.json by hand before committing.

usage (from backend/, test settings):
    python ../data/forms/field_index/tools/record_known_defects.py \
        apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py \
        apps/forms/tests/test_oracle_tier3.py
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))
OUTPUT = ROOT / "backend" / "apps" / "forms" / "tests" / "known_defects.json"

# Step 1 closes DIG-63 and DIG-64, so an audit row citing only those falls back.
CLOSED = {"DIG-63", "DIG-64"}
FORM_TICKET = {
    "form_101": "DIG-76",
    "form_103b": "DIG-78",
    "form_106sum": "DIG-79",
    "form_107": "DIG-77",
    "form_121": "DIG-68",
    "form_122a1": "DIG-59",
    "form_122a2": "DIG-60",
    "schedule_a_b": "DIG-80",
    "schedule_c": "DIG-81",
    "schedule_d": "DIG-69",
    "schedule_i": "DIG-82",
    "schedule_j": "DIG-82",
}
# Tier 3 boxes whose wrong value has its own ticket.
TIER3_TICKET = {
    ("form_101", "Check Box1"): "DIG-68",  # the chapter box never ticks
    ("form_122a1", "14a"): "DIG-65",  # the result box is never marked
    "schedule_j": "DIG-61",  # 22c, 23b and 23c print blank
}
TIER_OF = {"test_oracle_tier1.py": "1", "test_oracle_tier2.py": "2", "test_oracle_tier3.py": "3"}


def ticket_for(tier, defect_class, form_type, pdf_field):
    if defect_class == "unmapped_choice":
        return "DIG-68"
    if tier == "2":
        from apps.forms.tests.test_oracle_tier2 import _audit, _renamed

        old = {new: old for old, new in _renamed(form_type).items()}.get(pdf_field, pdf_field)
        cited = re.findall(r"DIG-\d+", _audit(form_type).get(old, {}).get("known") or "")
        open_tickets = [t for t in cited if t not in CLOSED]
        if open_tickets:
            return open_tickets[0]
    if tier == "3":
        return (
            TIER3_TICKET.get((form_type, pdf_field))
            or TIER3_TICKET.get(form_type)
            or FORM_TICKET[form_type]
        )
    return FORM_TICKET[form_type]


class Recorder:
    def __init__(self):
        self.entries = []

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        if report.when != "call" or not report.failed:
            return
        params = item.callspec.params
        tier = TIER_OF[item.path.name]
        defect_class = str(call.excinfo.value).split(":", 1)[0].strip()
        form_type, pdf_field, case = params["form_type"], params["pdf_field"], params["case"]
        self.entries.append(
            {
                "form_type": form_type,
                "pdf_field": pdf_field,
                "tier": tier,
                "case": case,
                "class": defect_class,
                "ticket": ticket_for(tier, defect_class, form_type, pdf_field),
            }
        )


if __name__ == "__main__":
    recorder = Recorder()
    status = pytest.main(
        ["-q", "-p", "no:cacheprovider", "--runxfail", *sys.argv[1:]], plugins=[recorder]
    )
    if status not in (pytest.ExitCode.OK, pytest.ExitCode.TESTS_FAILED):
        sys.exit(f"pytest did not run cleanly ({status!r}); known_defects.json left unchanged")
    entries = sorted(
        recorder.entries, key=lambda e: (e["tier"], e["form_type"], e["pdf_field"], e["case"])
    )
    OUTPUT.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"{len(entries)} entries written to {OUTPUT.relative_to(ROOT)}")
```

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY ../data/forms/field_index/tools/record_known_defects.py \
  apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py | tail -1
```

Expected: `85 entries written to backend/apps/forms/tests/known_defects.json`. Check that the list matches the verified one:

```bash
set -o pipefail
shasum -a 256 -c <<'SUMS'
c73434c5c245b9027f8f356e52b1b09a03be26b77a0276d6854dbca82f8c001c  backend/apps/forms/tests/known_defects.json
SUMS
```

Expected: `OK`. If the hash differs, read the diff of `known_defects.json` before going on: something in Tasks 1–4 differs from the plan.

- [ ] **Step 4: Run the oracle again, then the suite**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
$PY -m pytest -q -p no:cacheprovider 2>&1 | tail -2
```

Expected: `85 xfailed` with no failures, then `1770 passed, 86 xfailed`.

- [ ] **Step 5: Commit**

```bash
set -o pipefail
git add \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/oracle.py \
  backend/apps/forms/tests/test_known_defects.py \
  backend/apps/forms/tests/test_oracle_tier1.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  data/forms/field_index/tools/record_known_defects.py
git commit -F - <<'MSG'
test(forms): read every filled form back against the field index (oracle tiers 1 and 2)

Tier 1 fills each form with a marker per box and reads the PDF back: every
marker lands in its own box, and every box ticks by its own export state.
Tier 2 checks each binding against the audit's verified target. Each of the 85
defects found is a strict xfail in known_defects.json with its DIG ticket, so a
fix flips it to a failure until its entry is removed.
MSG
git status --short
```

### Task 6: One generation path, the packet rules, and encrypted field values

_Built and verified as commit `f6a2450` on `plan/forms-step1`._

**Files:**

- Create: `backend/apps/forms/constants.py`
- Create: `backend/apps/forms/migrations/0006_field_values.py`
- Modify: `backend/apps/audit/tests/test_upl_compliance.py`
- Modify: `backend/apps/content/management/commands/check_reading_level.py`
- Modify: `backend/apps/eligibility/tests/test_means_test_calculator.py`
- Modify: `backend/apps/forms/models.py`
- Modify: `backend/apps/forms/registry.py`
- Modify: `backend/apps/forms/serializers.py`
- Modify: `backend/apps/forms/tests/conftest.py`
- Modify: `backend/apps/forms/tests/test_download_action.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/tests/test_registry.py`
- Modify: `backend/apps/forms/views.py`
- Modify: `backend/apps/intake/management/commands/seed_demo_data.py`
- Modify: `backend/apps/intake/tests/test_e2e_intake.py`
- Modify: `backend/apps/intake/views.py`
- Delete: `backend/apps/forms/tests/test_generate_all_schema_driven.py`
- Delete: `backend/apps/forms/tests/test_pdf_field_maps.py`
- Delete: `backend/test_schedule_ab_logic.py`

**Interfaces:**

- Consumes: `load_schema`, `resolve`, `RepeatOverflow`, `UnmappedChoice` (existing and Task 3); `PDFFormFiller`, `TemplateHasNoForm` (Task 3); migration `0005` (Task 2).
- Produces:

  - In `apps.forms.registry`:
    - `PreconditionMissing(Exception)`;
    - `PacketForm(applies, requires)`;
    - `FORM_REGISTRY: dict[str, PacketForm]`, in filing order;
    - `get_all_form_types() -> list[str]`;
    - `packet(session) -> list[str]`;
    - `build_field_values(form_type, session) -> dict[str, str]`, which raises `KeyError` or `PreconditionMissing`.
  - `apps.forms.constants._UPL_DISCLAIMER`.
  - `GeneratedForm.field_values`, an `EncryptedTextField` holding JSON. `form_data` gets `default=dict` and is blanked by migration `0006`.
  - `GET /api/forms/packet/?session=<id>` returns `{"session": id, "form_types": [...]}`. 422 bodies are `{"form_type", "error"}`.
  - The preview endpoints are removed: `forms/{id}/preview/` and `intake/sessions/{id}/preview_form_101/`.

- [ ] **Step 1: Rewrite the endpoint and registry tests, and switch the callers' tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/conftest.py b/backend/apps/forms/tests/conftest.py
index 23a419c..9f166ef 100644
--- a/backend/apps/forms/tests/conftest.py
+++ b/backend/apps/forms/tests/conftest.py
@@ -1,12 +1,14 @@
 """Shared test fixtures for the forms app."""

+from datetime import date
+
 import pytest
 from django.contrib.auth import get_user_model
 from rest_framework.test import APIClient

 from apps.districts.models import District
 from apps.forms.models import GeneratedForm
-from apps.intake.models import IntakeSession
+from apps.intake.models import DebtorInfo, IntakeSession

 User = get_user_model()

@@ -35,11 +37,21 @@ def generated_form_factory(db, api_client_authed):
         session = IntakeSession.objects.create(
             user=user, district=district, status="completed", current_step=6
         )
+        DebtorInfo.objects.create(
+            session=session,
+            first_name="Maria",
+            last_name="Torres",
+            ssn="900-11-0001",  # IRS-reserved range: synthetic
+            date_of_birth=date(1988, 6, 15),
+            street_address="2145 W Division St",
+            city="Chicago",
+            state="IL",
+            zip_code="60622",
+        )
         return GeneratedForm.objects.create(
             session=session,
             form_type="form_121",
             status=status,
-            form_data={"debtor_name": "Maria Torres"},
             generated_by=user,
         )

PATCH
```

```python file=backend/apps/forms/tests/test_registry.py
"""
The packet holds exactly the forms a single Chapter 7 filer needs (spec §5.6, §5.7).

applies() decides which forms are in the packet; requires() stops a form from
filling silently when data it needs is missing.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.models import MeansTest
from apps.forms.field_index import load_index
from apps.forms.models import GeneratedForm
from apps.forms.registry import (
    FORM_REGISTRY,
    PreconditionMissing,
    build_field_values,
    get_all_form_types,
    packet,
)
from apps.forms.schema import load_schema
from apps.intake.models import DebtorInfo, FeeWaiverApplication, IntakeSession

User = get_user_model()

ALWAYS = [
    "form_101",
    "form_106dec",
    "form_106sum",
    "form_107",
    "form_121",
    "form_122a1",
    "schedule_a_b",
    "schedule_c",
    "schedule_d",
    "schedule_e_f",
    "schedule_g",
    "schedule_h",
    "schedule_i",
    "schedule_j",
]


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        court_name="U.S. Bankruptcy Court, N.D. Ill.",
        state="IL",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def _debtor(session, ssn="900-55-0005"):
    return DebtorInfo.objects.create(
        session=session,
        first_name="Sarah",
        last_name="Chen",
        ssn=ssn,
        date_of_birth=date(1995, 1, 20),
        street_address="1520 N Damen Ave Apt 2F",
        city="Chicago",
        state="IL",
        zip_code="60622",
    )


def _means_test(session, monthly_cmi, annual_median, above_median_flag=False):
    return MeansTest.objects.create(
        session=session,
        district=session.district,
        calculated_cmi=Decimal(monthly_cmi),
        median_income_threshold=Decimal(annual_median),
        passes_means_test=Decimal(monthly_cmi) * 12 < Decimal(annual_median),
        above_median_calculated=above_median_flag,
    )


def test_registry_is_the_chapter_7_forms_in_filing_order():
    assert get_all_form_types() == [
        "form_101",
        "form_103b",
        "form_106dec",
        "form_106sum",
        "form_107",
        "form_121",
        "form_122a1",
        "form_122a1_supp",
        "form_122a2",
        "schedule_a_b",
        "schedule_c",
        "schedule_d",
        "schedule_e_f",
        "schedule_g",
        "schedule_h",
        "schedule_i",
        "schedule_j",
    ]


def test_chapter_11_means_test_is_not_offered():
    # Form 122B is the Chapter 11 statement, and its download raised a 500 (DIG-125).
    assert "form_122b" not in FORM_REGISTRY
    assert "form_122b" not in dict(GeneratedForm.FORM_TYPE_CHOICES)


def test_every_registered_form_can_be_stored():
    assert set(get_all_form_types()) <= set(dict(GeneratedForm.FORM_TYPE_CHOICES))


def test_below_median_filer_without_fee_waiver_gets_fourteen_forms(session):
    _means_test(session, "2000.00", "71304.00")
    assert packet(session) == ALWAYS


def test_fee_waiver_application_adds_form_103b(session):
    FeeWaiverApplication.objects.create(
        session=session,
        household_size=1,
        monthly_income=Decimal("1500.00"),
        monthly_expenses=Decimal("1400.00"),
        cannot_pay_full=True,
        cannot_pay_installments=True,
    )
    assert "form_103b" in packet(session)


@pytest.mark.parametrize(
    "monthly_cmi,applies",
    [("11197.17", True), ("11197.16", False)],  # 134366.04 and 134365.92 a year
)
def test_122a2_applies_at_or_above_the_median(session, monthly_cmi, applies):
    _means_test(session, monthly_cmi, "134366.00")
    assert ("form_122a2" in packet(session)) is applies


def test_122a2_ignores_the_sticky_above_median_flag(session):
    # calculate() sets above_median_calculated and never clears it (DIG-128).
    _means_test(session, "2000.00", "71304.00", above_median_flag=True)
    assert "form_122a2" not in packet(session)


def test_no_means_test_means_no_122a2(session):
    assert "form_122a2" not in packet(session)


def test_122a1_supplement_waits_for_its_questions(session):
    # Nothing collects a claimed exemption from the presumption until step 4.
    _means_test(session, "12000.00", "134366.00")
    assert "form_122a1_supp" not in packet(session)


def test_petition_needs_the_filers_name_and_address(session):
    with pytest.raises(PreconditionMissing, match="name and address"):
        build_field_values("form_101", session)


@pytest.mark.parametrize("ssn", ["", "1234", "900-55-000"])
def test_ssn_statement_needs_a_nine_digit_ssn(session, ssn):
    _debtor(session, ssn=ssn)
    with pytest.raises(PreconditionMissing, match="Social Security number"):
        build_field_values("form_121", session)


@pytest.mark.parametrize("ssn", ["900-55-0005", "900550005"])
def test_ssn_statement_accepts_either_ssn_format(session, ssn):
    _debtor(session, ssn=ssn)
    assert build_field_values("form_121", session)


def test_ssn_statement_without_a_debtor_fails_instead_of_ticking_no_ssn(session):
    # Before step 1, Form 121's "no SSN" box resolved from missing data.
    with pytest.raises(PreconditionMissing):
        build_field_values("form_121", session)


def test_means_test_form_needs_the_eligibility_check(session):
    _debtor(session)
    with pytest.raises(PreconditionMissing, match="eligibility check"):
        build_field_values("form_122a1", session)


def test_field_values_name_index_widgets(session):
    _debtor(session)
    values = build_field_values("form_101", session)
    widgets = load_index(load_schema("form_101").template_filename)
    assert values["Debtor1.First name"] == "Sarah"
    assert set(values) <= set(widgets)
```

```python file=backend/apps/forms/tests/test_form_views.py
"""
Tests for the form generation API endpoints.

Covers:
  - GET  /api/forms/packet/?session=<id>
  - POST /api/forms/generate/       (single form)
  - POST /api/forms/generate_all/   (every form in the packet)
  - POST /api/forms/{id}/regenerate/
  - POST /api/forms/{id}/mark_downloaded/
  - POST /api/forms/{id}/mark_filed/
  - Permission enforcement (users see only their own sessions)
  - The error contract: 422 with a reason, 500 logged by type only
  - The encrypted snapshot never leaves the server
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.models import GeneratedForm
from apps.intake.models import (
    DebtorInfo,
    IncomeInfo,
    IntakeSession,
)

User = get_user_model()

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def template_version_form(generated_form_factory):
    return generated_form_factory(status="generated")


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testfiler",
        email="filer@example.com",
        password="testpass123",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="otherfiler",
        email="other@example.com",
        password="testpass456",
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauth_client():
    return APIClient()


@pytest.fixture
def district(db):
    return District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
        pro_se_efiling_allowed=False,
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def session(user, district):
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_debtor(session):
    """Session with debtor info — minimum data most generators need."""
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        middle_name="",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


@pytest.fixture
def session_with_income(session_with_debtor):
    """Session with debtor + income info for means test generators."""
    IncomeInfo.objects.create(
        session=session_with_debtor,
        marital_status="single",
        number_of_dependents=0,
        monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
    )
    return session_with_debtor


@pytest.fixture
def other_session(other_user, district):
    return IntakeSession.objects.create(user=other_user, district=district)


# ── Generate Endpoint ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestGenerateEndpoint:
    """POST /api/forms/generate/"""

    URL = "/api/forms/generate/"

    def test_generate_form_101(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_101"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "form" in resp.data
        assert resp.data["form"]["form_type"] == "form_101"
        assert resp.data["form"]["status"] == "generated"

        # Verify DB record created
        assert GeneratedForm.objects.filter(
            session=session_with_debtor, form_type="form_101"
        ).exists()

    def test_generate_form_106dec(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_106dec"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form"]["form_type"] == "form_106dec"

    def test_generate_schedule_a_b(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "schedule_a_b"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form"]["form_type"] == "schedule_a_b"

    def test_generate_schedule_i(self, api_client, session_with_income):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_income.id, "form_type": "schedule_i"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form"]["form_type"] == "schedule_i"

    def test_idempotent_regeneration(self, api_client, session_with_debtor):
        """Calling generate twice for same form_type updates existing record."""
        for _ in range(2):
            resp = api_client.post(
                self.URL,
                {"session_id": session_with_debtor.id, "form_type": "form_106dec"},
                format="json",
            )
            assert resp.status_code == status.HTTP_200_OK

        assert (
            GeneratedForm.objects.filter(
                session=session_with_debtor, form_type="form_106dec"
            ).count()
            == 1
        )

    def test_missing_session_id(self, api_client):
        resp = api_client.post(self.URL, {"form_type": "form_101"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "session_id" in resp.data["error"]

    def test_missing_form_type(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "form_type" in resp.data["error"]

    def test_invalid_form_type(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_999"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "valid_types" in resp.data

    def test_other_users_session_forbidden(self, api_client, other_session):
        resp = api_client.post(
            self.URL,
            {"session_id": other_session.id, "form_type": "form_101"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated(self, unauth_client, session_with_debtor):
        resp = unauth_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_101"},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_form_outside_the_packet_is_refused(self, api_client, session_with_debtor):
        # Without a fee waiver application, Form 103B would print a $0 application.
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_103b"},
            format="json",
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data == {
            "form_type": "form_103b",
            "error": "This form isn't part of your packet.",
        }

    def test_missing_data_is_named_instead_of_filled_blank(self, api_client, session):
        resp = api_client.post(
            self.URL,
            {"session_id": session.id, "form_type": "form_121"},
            format="json",
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "name and address" in resp.data["error"]
        assert not GeneratedForm.objects.filter(session=session).exists()

    def test_unexpected_failure_logs_only_its_type(self, api_client, session_with_debtor, caplog):
        with patch(
            "apps.forms.views.build_field_values", side_effect=ValueError("900-12-3456 leaked")
        ):
            resp = api_client.post(
                self.URL,
                {"session_id": session_with_debtor.id, "form_type": "form_101"},
                format="json",
            )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "900-12-3456" not in json.dumps(resp.data)
        assert "900-12-3456" not in caplog.text
        assert "ValueError" in caplog.text


# ── Generate All Endpoint ─────────────────────────────────────────────


@pytest.mark.django_db
class TestGenerateAllEndpoint:
    """POST /api/forms/generate_all/"""

    URL = "/api/forms/generate_all/"

    def test_generates_every_form_in_the_packet(self, api_client, session_with_income):
        """One form's missing data is reported and doesn't undo the others."""
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_income.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        # No fee waiver: no 103B. No means test yet: 122A-1 can't fill, and no 122A-2.
        assert resp.data["errors"] == [
            {"form_type": "form_122a1", "error": "The eligibility check hasn't been run yet."}
        ]
        assert resp.data["total_generated"] == 13
        assert GeneratedForm.objects.filter(session=session_with_income).count() == 13

    def test_drops_forms_that_no_longer_apply(self, api_client, session_with_income, user):
        GeneratedForm.objects.create(
            session=session_with_income, form_type="form_103b", generated_by=user
        )
        api_client.post(self.URL, {"session_id": session_with_income.id}, format="json")
        assert not GeneratedForm.objects.filter(
            session=session_with_income, form_type="form_103b"
        ).exists()

    def test_missing_session_id(self, api_client):
        resp = api_client.post(self.URL, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_other_users_session(self, api_client, other_session):
        resp = api_client.post(self.URL, {"session_id": other_session.id}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestRegenerateEndpoint:
    """POST /api/forms/{id}/regenerate/"""

    def test_regenerate_existing_form(self, api_client, session_with_debtor, user):
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_106dec",
            status="generated",
            generated_by=user,
        )

        resp = api_client.post(f"/api/forms/{form.id}/regenerate/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["message"] == "Form regenerated successfully"

        form.refresh_from_db()
        assert json.loads(form.field_values)["Debtor 1"] == "Jane Doe"

    def test_regenerate_other_users_form(self, api_client, other_session, other_user):
        form = GeneratedForm.objects.create(
            session=other_session,
            form_type="form_101",
            status="generated",
            generated_by=other_user,
        )
        resp = api_client.post(f"/api/forms/{form.id}/regenerate/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── Status Transition Endpoints ───────────────────────────────────────


@pytest.mark.django_db
class TestStatusTransitions:

    def test_mark_downloaded(self, api_client, session_with_debtor, user):
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_101",
            status="generated",
            generated_by=user,
        )
        resp = api_client.post(f"/api/forms/{form.id}/mark_downloaded/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "downloaded"

    def test_mark_downloaded_idempotent_on_non_generated(
        self, api_client, session_with_debtor, user
    ):
        """Only transitions from 'generated' — already-downloaded stays put."""
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_101",
            status="downloaded",
            generated_by=user,
        )
        resp = api_client.post(f"/api/forms/{form.id}/mark_downloaded/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "downloaded"

    def test_mark_filed(self, api_client, session_with_debtor, user):
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_101",
            status="downloaded",
            generated_by=user,
        )
        resp = api_client.post(f"/api/forms/{form.id}/mark_filed/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "filed"


# ── List / Retrieve ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestListRetrieve:

    def test_list_only_own_forms(
        self, api_client, session_with_debtor, user, other_session, other_user
    ):
        GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_101",
            generated_by=user,
        )
        GeneratedForm.objects.create(
            session=other_session,
            form_type="form_101",
            generated_by=other_user,
        )

        resp = api_client.get("/api/forms/")
        assert resp.status_code == status.HTTP_200_OK
        # Response is paginated
        results = resp.data.get("results", resp.data)
        if isinstance(results, list):
            assert len(results) == 1
            assert results[0]["session"] == session_with_debtor.id
        else:
            assert resp.data["count"] == 1

    def test_retrieve_own_form(self, api_client, session_with_debtor, user):
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_101",
            generated_by=user,
        )
        resp = api_client.get(f"/api/forms/{form.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form_type"] == "form_101"

    def test_retrieve_other_users_form_404(self, api_client, other_session, other_user):
        form = GeneratedForm.objects.create(
            session=other_session,
            form_type="form_101",
            generated_by=other_user,
        )
        resp = api_client.get(f"/api/forms/{form.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_generated_form_template_version_round_trip(db, template_version_form):
    template_version_form.template_version = "abc123"
    template_version_form.save()
    template_version_form.refresh_from_db()
    assert template_version_form.template_version == "abc123"


# ── Packet ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPacketEndpoint:
    """GET /api/forms/packet/?session=<id>"""

    URL = "/api/forms/packet/"

    def test_lists_the_filers_forms_in_filing_order(self, api_client, session_with_debtor):
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form_types"][:3] == ["form_101", "form_106dec", "form_106sum"]
        assert "form_103b" not in resp.data["form_types"]
        assert len(resp.data["form_types"]) == 14

    def test_missing_session(self, api_client):
        assert api_client.get(self.URL).status_code == status.HTTP_400_BAD_REQUEST

    def test_other_users_session(self, api_client, other_session):
        resp = api_client.get(self.URL, {"session": other_session.id})
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── The snapshot stays on the server (DIG-124) ────────────────────────


@pytest.mark.django_db
class TestFieldValuesStayPrivate:

    def _generate_121(self, api_client, session):
        return api_client.post(
            "/api/forms/generate/",
            {"session_id": session.id, "form_type": "form_121"},
            format="json",
        )

    def test_api_never_returns_form_values(self, api_client, session_with_debtor):
        resp = self._generate_121(api_client, session_with_debtor)
        assert resp.status_code == status.HTTP_200_OK
        listed = api_client.get("/api/forms/").data["results"][0]
        for body in (resp.data["form"], listed):
            assert "form_data" not in body
            assert "field_values" not in body
            assert "900-12-3456" not in json.dumps(body)

    def test_full_ssn_is_encrypted_at_rest(self, api_client, session_with_debtor):
        self._generate_121(api_client, session_with_debtor)
        form = GeneratedForm.objects.get(session=session_with_debtor, form_type="form_121")
        assert "900-12-3456" in form.field_values  # Form 121 prints the full SSN
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT field_values, form_data FROM generated_forms WHERE id = %s", [form.id]
            )
            raw_values, raw_form_data = cursor.fetchone()
        assert "900-12-3456" not in raw_values
        assert "900123456" not in raw_values
        assert json.loads(raw_form_data) == {}
```

```python file=backend/apps/forms/tests/test_download_action.py
"""
Download fills the official template: the filer's current answers until a form
is filed, and exactly what was filed afterwards (spec §5.5).
"""

import json
from unittest.mock import patch

from django.urls import reverse

from apps.forms.services.fill_resolver import RepeatOverflow
from apps.forms.tests.pdf_readback import read_widgets


def _download(client, form):
    return client.get(reverse("generated-forms-download", kwargs={"pk": form.pk}))


def _printed(response, full_name):
    return {w.value for w in read_widgets(response.content) if w.full_name == full_name}


def _rename_filer(form, first_name):
    debtor = form.session.debtor_info
    debtor.first_name = first_name
    debtor.save()


def test_download_streams_the_filled_form(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    response = _download(api_client_authed, form)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == 'attachment; filename="form_121.pdf"'
    assert _printed(response, "Debtor1.First name") == {"Maria"}


def test_download_marks_a_generated_form_downloaded(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    _download(api_client_authed, form)
    form.refresh_from_db()
    assert form.status == "downloaded"


def test_unfiled_form_prints_the_filers_current_answers(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="downloaded")
    form.field_values = json.dumps({"Debtor1.First name": "Maria"})
    form.save()
    _rename_filer(form, "Marisol")

    response = _download(api_client_authed, form)

    assert _printed(response, "Debtor1.First name") == {"Marisol"}
    form.refresh_from_db()
    assert json.loads(form.field_values)["Debtor1.First name"] == "Marisol"


def test_filed_form_prints_what_was_filed(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="filed")
    form.field_values = json.dumps({"Debtor1.First name": "Maria"})
    form.save()
    _rename_filer(form, "Marisol")

    response = _download(api_client_authed, form)

    assert _printed(response, "Debtor1.First name") == {"Maria"}
    form.refresh_from_db()
    assert form.status == "filed"


def test_filed_form_without_a_snapshot_is_resolved_once_and_kept(
    api_client_authed, generated_form_factory
):
    form = generated_form_factory(status="filed")  # filed before snapshots existed

    response = _download(api_client_authed, form)

    assert _printed(response, "Debtor1.First name") == {"Maria"}
    form.refresh_from_db()
    assert json.loads(form.field_values)["Debtor1.First name"] == "Maria"


def test_form_no_longer_in_the_packet_is_refused(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    form.form_type = "form_103b"  # no fee waiver application for this session
    form.save()

    response = _download(api_client_authed, form)

    assert response.status_code == 422
    assert response.data["error"] == "This form isn't part of your packet."


def test_missing_data_is_a_422_with_its_reason(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    form.session.debtor_info.delete()

    response = _download(api_client_authed, form)

    assert response.status_code == 422
    assert "name and address" in response.data["error"]


def test_too_many_rows_is_a_422(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    overflow = RepeatOverflow("form_121", "rows", capacity=3, actual=4)
    with patch("apps.forms.views.build_field_values", side_effect=overflow):
        response = _download(api_client_authed, form)
    assert response.status_code == 422


def test_unexpected_failure_logs_only_its_type(api_client_authed, generated_form_factory, caplog):
    form = generated_form_factory(status="generated")
    with patch("apps.forms.views.build_field_values", side_effect=ValueError("900-11-0001")):
        response = _download(api_client_authed, form)
    assert response.status_code == 500
    assert "900-11-0001" not in caplog.text
    assert "ValueError" in caplog.text
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/audit/tests/test_upl_compliance.py b/backend/apps/audit/tests/test_upl_compliance.py
index f6d9e2b..fd4ca55 100644
--- a/backend/apps/audit/tests/test_upl_compliance.py
+++ b/backend/apps/audit/tests/test_upl_compliance.py
@@ -22,7 +22,7 @@ from django.contrib.auth import get_user_model
 from apps.audit.middleware import AuditLoggingMiddleware
 from apps.districts.models import District, MedianIncome
 from apps.eligibility.services.means_test_calculator import MeansTestCalculator
-from apps.forms.views import _UPL_DISCLAIMER
+from apps.forms.constants import _UPL_DISCLAIMER
 from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()
@@ -159,7 +159,7 @@ class TestFormsViewUPLCompliance:
     """Verify forms view UPL disclaimers and messaging."""

     def test_upl_disclaimer_constant_exists(self):
-        """_UPL_DISCLAIMER constant must be defined in forms views."""
+        """_UPL_DISCLAIMER constant must be defined in the forms app."""
         assert _UPL_DISCLAIMER is not None
         assert len(_UPL_DISCLAIMER) > 0

diff --git a/backend/apps/eligibility/tests/test_means_test_calculator.py b/backend/apps/eligibility/tests/test_means_test_calculator.py
index ca95a6e..4706859 100644
--- a/backend/apps/eligibility/tests/test_means_test_calculator.py
+++ b/backend/apps/eligibility/tests/test_means_test_calculator.py
@@ -25,7 +25,7 @@ from django.contrib.auth import get_user_model
 from apps.districts.models import District, MedianIncome
 from apps.eligibility.models import MeansTest
 from apps.eligibility.services.means_test_calculator import MeansTestCalculator
-from apps.forms.registry import get_generator
+from apps.forms.registry import build_field_values
 from apps.intake.models import DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession

 User = get_user_model()
@@ -1045,6 +1045,5 @@ class TestAboveMedianEndToEnd:
         assert session.means_test.above_median_calculated is True
         assert session.means_test.disposable_income is not None

-        gen = get_generator("form_122a2", session)
-        field_map = gen.pdf_field_map()
-        assert "Bankruptcy District Information" in field_map
+        values = build_field_values("form_122a2", session)
+        assert "Bankruptcy District Information" in values
diff --git a/backend/apps/intake/tests/test_e2e_intake.py b/backend/apps/intake/tests/test_e2e_intake.py
index 24e0da7..6014970 100644
--- a/backend/apps/intake/tests/test_e2e_intake.py
+++ b/backend/apps/intake/tests/test_e2e_intake.py
@@ -2,7 +2,7 @@
 Comprehensive end-to-end tests for intake flow.

 Tests the complete intake workflow from session creation through means test
-calculation and form preview, including permission isolation and error handling.
+calculation, including permission isolation and error handling.
 """

 from decimal import Decimal
@@ -723,85 +723,6 @@ class TestMeansTestCalculation:
         assert result["qualifies_for_fee_waiver"] is True


-@pytest.mark.django_db
-class TestForm101Preview:
-    """Test suite for Form 101 preview functionality."""
-
-    @pytest.fixture
-    def complete_session(self, api_client, district, median_income):
-        """Create session with all required data."""
-        url = reverse("intake-session-list")
-        response = api_client.post(url, {"district": district.id, "current_step": 1}, format="json")
-        session = IntakeSession.objects.get(id=response.data["session"]["id"])
-
-        DebtorInfo.objects.create(
-            session=session,
-            first_name="John",
-            last_name="Doe",
-            middle_name="Q",
-            ssn="123456789",
-            date_of_birth="1980-01-01",
-            phone="555-555-5555",
-            email="john@example.com",
-            street_address="123 Main St",
-            city="Chicago",
-            state="IL",
-            zip_code="60601",
-        )
-
-        IncomeInfo.objects.create(
-            session=session,
-            marital_status="single",
-            number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
-        )
-
-        ExpenseInfo.objects.create(
-            session=session,
-            rent_or_mortgage=Decimal("1500.00"),
-            utilities=Decimal("200.00"),
-            home_maintenance=Decimal("50.00"),
-            vehicle_payment=Decimal("300.00"),
-            vehicle_insurance=Decimal("100.00"),
-            vehicle_maintenance=Decimal("150.00"),
-            food_and_groceries=Decimal("400.00"),
-            childcare=Decimal("0.00"),
-            medical_expenses=Decimal("50.00"),
-            insurance_not_deducted=Decimal("0.00"),
-            other_expenses=Decimal("100.00"),
-        )
-
-        return session
-
-    def test_preview_form_101_success(self, api_client, complete_session):
-        """Test successful Form 101 preview generation."""
-        url = reverse("intake-session-preview-form-101", args=[complete_session.id])
-        response = api_client.get(url)
-
-        assert response.status_code == status.HTTP_200_OK
-        assert "form_preview" in response.data
-        assert "session_id" in response.data
-
-        preview = response.data["form_preview"]
-        assert "debtor_name" in preview
-        assert "debtor_address" in preview
-        assert "case_type" in preview
-
-    def test_preview_form_101_without_debtor_info(self, api_client, district):
-        """Test Form 101 preview without debtor info returns 400."""
-        # Create session without debtor info
-        url = reverse("intake-session-list")
-        response = api_client.post(url, {"district": district.id, "current_step": 1}, format="json")
-        session_id = response.data["session"]["id"]
-
-        # Try to preview form
-        preview_url = reverse("intake-session-preview-form-101", args=[session_id])
-        response = api_client.get(preview_url)
-
-        assert response.status_code == status.HTTP_400_BAD_REQUEST
-        assert "error" in response.data
-
-
 @pytest.mark.django_db
 class TestSessionSummary:
     """Test suite for session summary endpoint."""
PATCH
```

```bash
set -o pipefail
git rm -q backend/apps/forms/tests/test_generate_all_schema_driven.py backend/apps/forms/tests/test_pdf_field_maps.py backend/test_schedule_ab_logic.py
```

Three files are deleted:

- `test_generate_all_schema_driven.py` and `test_pdf_field_maps.py` tested the generator path this task retires.
- `backend/test_schedule_ab_logic.py` is a stray script that imports a generator.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_registry.py apps/forms/tests/test_form_views.py apps/forms/tests/test_download_action.py -q -p no:cacheprovider
```

Expected: FAIL — `ImportError: cannot import name 'PreconditionMissing' from 'apps.forms.registry'`.

- [ ] **Step 3: Add the constants module and the migration, and rewrite the registry and views**

```python file=backend/apps/forms/constants.py
"""Plain-language text the forms app shares with the content and audit checks."""

# UPL-compliant disclaimer (docs/UPL_COMPLIANCE.md); checked by check_reading_level.
_UPL_DISCLAIMER = (
    "This is a preview based on the information you provided. "
    "This software provides legal information, not legal advice. "
    "You are responsible for reviewing all information for accuracy before filing."
)
```

```python file=backend/apps/forms/migrations/0006_field_values.py
"""Forms step 1: encrypted field_values replaces form_data, which is blanked (DIG-124)."""

import encrypted_model_fields.fields
from django.db import migrations, models


def blank_form_data(apps, schema_editor):
    GeneratedForm = apps.get_model("forms", "GeneratedForm")
    GeneratedForm.objects.update(form_data={})


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0005_remove_form_122b"),
    ]

    operations = [
        migrations.AddField(
            model_name="generatedform",
            name="field_values",
            field=encrypted_model_fields.fields.EncryptedTextField(
                blank=True, default="", help_text="Encrypted JSON"
            ),
        ),
        migrations.AlterField(
            model_name="generatedform",
            name="form_data",
            field=models.JSONField(default=dict, help_text="Unused; see field_values"),
        ),
        migrations.RunPython(blank_form_data, migrations.RunPython.noop),
    ]
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/models.py b/backend/apps/forms/models.py
index d582c7b..328ad9b 100644
--- a/backend/apps/forms/models.py
+++ b/backend/apps/forms/models.py
@@ -2,6 +2,7 @@

 from django.conf import settings
 from django.db import models
+from encrypted_model_fields.fields import EncryptedTextField


 class GeneratedForm(models.Model):
@@ -57,8 +58,13 @@ class GeneratedForm(models.Model):
         help_text="Current status of the form",
     )

-    # Form data (JSON storage for form field values)
-    form_data = models.JSONField(help_text="Populated form field data ready for PDF generation")
+    # Blank since forms step 1 (DIG-124): it held Form 121's full SSN in plain
+    # JSON. Nothing reads or writes it; its column is dropped one release later.
+    form_data = models.JSONField(default=dict, help_text="Unused; see field_values")
+
+    # The values the form printed, as encrypted JSON {full name: value}. The API
+    # never returns it; download fills a filed form from it.
+    field_values = EncryptedTextField(blank=True, default="", help_text="Encrypted JSON")

     # Schema / template version (reproducibility)
     template_version = models.CharField(
diff --git a/backend/apps/forms/serializers.py b/backend/apps/forms/serializers.py
index bad7408..8c98b77 100644
--- a/backend/apps/forms/serializers.py
+++ b/backend/apps/forms/serializers.py
@@ -13,7 +13,8 @@ class GeneratedFormSerializer(serializers.ModelSerializer):
     """
     Serializer for generated bankruptcy forms.

-    Provides access to form metadata and data for preview/download.
+    Returns form metadata only. The printed values (field_values) are encrypted
+    and never leave the server; download fills the PDF from them.
     """

     form_type_display = serializers.CharField(source="get_form_type_display", read_only=True)
@@ -28,7 +29,6 @@ class GeneratedFormSerializer(serializers.ModelSerializer):
             "form_type_display",
             "status",
             "status_display",
-            "form_data",
             "pdf_file_path",
             "generated_by",
             "generated_at",
PATCH
```

```python file=backend/apps/forms/registry.py
"""
The Chapter 7 packet: which forms a filer needs, and what each needs first (spec §5.6, §5.7).

Each form_type maps to applies(session), which says whether the form is part
of this filer's packet and never raises, and requires(session), which raises
PreconditionMissing when data the form can't be filled without is absent.
build_field_values() is the one path from a session to a form's printed values.
FORM_REGISTRY is in filing order.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import IntakeSession

_SSN = re.compile(r"\d{3}-\d{2}-\d{4}|\d{9}")


class PreconditionMissing(Exception):
    """A form can't be filled yet; the message tells the filer what is missing."""


@dataclass(frozen=True)
class PacketForm:
    applies: Callable[[IntakeSession], bool]
    requires: Callable[[IntakeSession], None]


def _always(session: IntakeSession) -> bool:
    return True


def _never(session: IntakeSession) -> bool:
    # 122A-1Supp: nothing collects a claimed exemption from the presumption yet (step 4).
    return False


def _has_fee_waiver(session: IntakeSession) -> bool:
    return hasattr(session, "fee_waiver")


def _above_median(session: IntakeSession) -> bool:
    """
    Annualized income at or above the median, from the stored MeansTest.

    Not above_median_calculated: calculate() sets it and never clears it (DIG-128).
    """
    means_test = getattr(session, "means_test", None)
    if means_test is None:
        return False
    return means_test.calculated_cmi * 12 >= means_test.median_income_threshold


def _nothing(session: IntakeSession) -> None:
    return None


def _needs_debtor_info(session: IntakeSession) -> None:
    if not hasattr(session, "debtor_info"):
        raise PreconditionMissing("Your name and address haven't been entered yet.")


def _needs_ssn(session: IntakeSession) -> None:
    _needs_debtor_info(session)
    if not _SSN.fullmatch((session.debtor_info.ssn or "").strip()):
        raise PreconditionMissing("Your Social Security number is missing or isn't 9 digits.")


def _needs_means_test(session: IntakeSession) -> None:
    if not hasattr(session, "means_test"):
        raise PreconditionMissing("The eligibility check hasn't been run yet.")


# form_type → PacketForm. Every key must match a GeneratedForm.FORM_TYPE_CHOICES value.
FORM_REGISTRY: dict[str, PacketForm] = {
    "form_101": PacketForm(_always, _needs_debtor_info),
    "form_103b": PacketForm(_has_fee_waiver, _nothing),
    "form_106dec": PacketForm(_always, _nothing),
    "form_106sum": PacketForm(_always, _nothing),
    "form_107": PacketForm(_always, _nothing),
    "form_121": PacketForm(_always, _needs_ssn),
    "form_122a1": PacketForm(_always, _needs_means_test),
    "form_122a1_supp": PacketForm(_never, _nothing),
    "form_122a2": PacketForm(_above_median, _nothing),
    "schedule_a_b": PacketForm(_always, _nothing),
    "schedule_c": PacketForm(_always, _nothing),
    "schedule_d": PacketForm(_always, _nothing),
    "schedule_e_f": PacketForm(_always, _nothing),
    "schedule_g": PacketForm(_always, _nothing),
    "schedule_h": PacketForm(_always, _nothing),
    "schedule_i": PacketForm(_always, _nothing),
    "schedule_j": PacketForm(_always, _nothing),
}


def get_all_form_types() -> list[str]:
    """Return all registered form type keys in filing order."""
    return list(FORM_REGISTRY.keys())


def packet(session: IntakeSession) -> list[str]:
    """The form types this filer's packet holds, in filing order."""
    return [form_type for form_type, form in FORM_REGISTRY.items() if form.applies(session)]


def build_field_values(form_type: str, session: IntakeSession) -> dict[str, str]:
    """
    The values a form prints for this session, as {full name: value}.

    Raises:
        KeyError: form_type is not registered.
        PreconditionMissing: the form needs data the session lacks.
    """
    FORM_REGISTRY[form_type].requires(session)
    return resolve(load_schema(form_type), session)
```

```python file=backend/apps/forms/views.py
"""
API views for bankruptcy form generation.

One path fills every form: registry.build_field_values() resolves a session's
values, PDFFormFiller fills the template, and the values are kept as an
encrypted snapshot (GeneratedForm.field_values) that the API never returns.
"""

import json
import logging

from django.db import transaction
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.intake.models import IntakeSession

from .models import GeneratedForm
from .registry import (
    FORM_REGISTRY,
    PreconditionMissing,
    build_field_values,
    get_all_form_types,
    packet,
)
from .schema import load_schema
from .serializers import GeneratedFormSerializer
from .services.fill_resolver import RepeatOverflow, UnmappedChoice
from .services.pdf_filler import PDFFormFiller, TemplateHasNoForm

logger = logging.getLogger(__name__)


class NotInPacket(Exception):
    """The form isn't part of this filer's packet (registry applies() is false)."""

    def __init__(self):
        super().__init__("This form isn't part of your packet.")


# Failures a filer can act on: 422 with the reason (spec §5.7). Anything else is a 500.
_EXPECTED_FAILURES = (
    PreconditionMissing,
    NotInPacket,
    RepeatOverflow,
    UnmappedChoice,
    TemplateHasNoForm,
)


def _failure(form_type: str, exc: Exception) -> tuple[dict, int]:
    """The error body and status for a form that could not be filled."""
    if isinstance(exc, _EXPECTED_FAILURES):
        return {"form_type": form_type, "error": str(exc)}, status.HTTP_422_UNPROCESSABLE_ENTITY
    # Type only: a message or traceback can quote filer data, and logs reach Sentry (DIG-105).
    logger.error("Filling %s failed: %s", form_type, type(exc).__name__)
    return (
        {
            "form_type": form_type,
            "error": "This form couldn't be prepared. Please try again later.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _session_or_error(request, session_id) -> tuple[IntakeSession | None, Response | None]:
    """The requesting user's session, or (None, a 400/404 Response)."""
    if not session_id:
        return None, Response(
            {"error": "session_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        return IntakeSession.objects.get(id=session_id, user=request.user), None
    except (IntakeSession.DoesNotExist, ValueError):
        return None, Response(
            {"error": "Session not found or you don't have permission"},
            status=status.HTTP_404_NOT_FOUND,
        )


def _validate_form_type(form_type: str | None) -> Response | None:
    """Return an error Response if form_type is missing or unknown, else None."""
    if not form_type:
        return Response(
            {"error": "form_type is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if form_type not in FORM_REGISTRY:
        return Response(
            {
                "error": f"Unknown form_type: {form_type}",
                "valid_types": get_all_form_types(),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def _fill(form_type: str, session: IntakeSession) -> tuple[dict[str, str], bytes]:
    """Resolve a form that applies to this filer and fill its template."""
    if not FORM_REGISTRY[form_type].applies(session):
        raise NotInPacket()
    values = build_field_values(form_type, session)
    return values, PDFFormFiller().fill(form_type, values)


def _store(generated_form: GeneratedForm, values: dict[str, str]) -> None:
    generated_form.field_values = json.dumps(values)
    generated_form.template_version = load_schema(generated_form.form_type).template_version


def _generate_and_persist(session: IntakeSession, form_type: str, user) -> GeneratedForm:
    """Fill the form (which proves it fills) and keep its values as the snapshot."""
    values, _ = _fill(form_type, session)
    generated_form, _ = GeneratedForm.objects.get_or_create(
        session=session, form_type=form_type, defaults={"generated_by": user}
    )
    _store(generated_form, values)
    generated_form.status = "generated"
    generated_form.generated_by = user
    generated_form.save()
    return generated_form


class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for bankruptcy form generation and management.

    Endpoints:
      GET  /api/forms/packet/?session=<id>  The form types this filer's packet holds
      POST /api/forms/generate/              Generate a single form
      POST /api/forms/generate_all/          Generate every form in the packet
      POST /api/forms/{id}/regenerate/       Regenerate an existing form
      GET  /api/forms/{id}/download/         Fill and stream the PDF
      POST /api/forms/{id}/mark_downloaded/
      POST /api/forms/{id}/mark_filed/
    """

    serializer_class = GeneratedFormSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only forms for the authenticated user's sessions."""
        return GeneratedForm.objects.filter(session__user=self.request.user).select_related(
            "session", "generated_by"
        )

    # ------------------------------------------------------------------
    # The packet
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"])
    def packet(self, request):
        """
        The ordered form types that apply to this filer.

        GET /api/forms/packet/?session=1
        """
        session, err = _session_or_error(request, request.query_params.get("session"))
        if err:
            return err
        return Response({"session": session.id, "form_types": packet(session)})

    # ------------------------------------------------------------------
    # Generate single form
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """
        Generate a single bankruptcy form.

        POST /api/forms/generate/
        { "session_id": 1, "form_type": "form_101" }
        """
        session, err = _session_or_error(request, request.data.get("session_id"))
        if err:
            return err

        form_type = request.data.get("form_type")
        err = _validate_form_type(form_type)
        if err:
            return err

        try:
            generated_form = _generate_and_persist(session, form_type, request.user)
        except Exception as exc:
            body, code = _failure(form_type, exc)
            return Response(body, status=code)
        return Response(
            {
                "form": self.get_serializer(generated_form).data,
                "message": f"{generated_form.get_form_type_display()} generated successfully",
            }
        )

    # ------------------------------------------------------------------
    # Generate all forms for a session
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="generate_all")
    def generate_all(self, request):
        """
        Generate every form in the filer's packet.

        POST /api/forms/generate_all/
        { "session_id": 1 }

        Each form gets its own savepoint, so one form's failure can't undo the
        others. Rows for forms that no longer apply are deleted.
        """
        session, err = _session_or_error(request, request.data.get("session_id"))
        if err:
            return err

        form_types = packet(session)
        GeneratedForm.objects.filter(session=session).exclude(form_type__in=form_types).delete()

        results = []
        errors = []
        for form_type in form_types:
            try:
                with transaction.atomic():
                    generated_form = _generate_and_persist(session, form_type, request.user)
                results.append(self.get_serializer(generated_form).data)
            except Exception as exc:
                errors.append(_failure(form_type, exc)[0])

        return Response(
            {
                "generated": results,
                "errors": errors,
                "total_generated": len(results),
                "total_errors": len(errors),
            }
        )

    # ------------------------------------------------------------------
    # Regenerate existing form
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """
        Regenerate an existing form with updated session data.

        POST /api/forms/{id}/regenerate/
        """
        generated_form = self.get_object()
        try:
            generated_form = _generate_and_persist(
                generated_form.session, generated_form.form_type, request.user
            )
        except Exception as exc:
            body, code = _failure(generated_form.form_type, exc)
            return Response(body, status=code)
        return Response(
            {
                "form": self.get_serializer(generated_form).data,
                "message": "Form regenerated successfully",
            }
        )

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"])
    def mark_downloaded(self, request, pk=None):
        """Mark form as downloaded by the user."""
        generated_form = self.get_object()

        if generated_form.status == "generated":
            generated_form.status = "downloaded"
            generated_form.save()

        return Response(
            {
                "form_id": generated_form.id,
                "status": generated_form.status,
                "message": "Form marked as downloaded",
            }
        )

    @action(detail=True, methods=["post"])
    def mark_filed(self, request, pk=None):
        """Mark form as filed with the court."""
        generated_form = self.get_object()

        generated_form.status = "filed"
        generated_form.save()

        return Response(
            {
                "form_id": generated_form.id,
                "status": generated_form.status,
                "message": "Form marked as filed with court",
            }
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """
        Fill the official AO template and stream it.

        A form not yet filed is resolved fresh, so the filer always downloads
        their current answers, and its snapshot is refreshed. A filed form
        fills from its snapshot, so it matches what was filed.
        """
        generated_form = self.get_object()
        form_type = generated_form.form_type
        session = generated_form.session

        try:
            if generated_form.status == "filed" and generated_form.field_values:
                if not FORM_REGISTRY[form_type].applies(session):
                    raise NotInPacket()
                pdf_bytes = PDFFormFiller().fill(form_type, json.loads(generated_form.field_values))
            else:
                values, pdf_bytes = _fill(form_type, session)
                _store(generated_form, values)
        except Exception as exc:
            body, code = _failure(form_type, exc)
            return Response(body, status=code)

        if generated_form.status == "generated":
            generated_form.status = "downloaded"
        generated_form.save()

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{form_type}.pdf"'
        return response


class FormSchemaUIView(APIView):
    permission_classes = []

    def get(self, request, form_type):
        try:
            schema = load_schema(form_type)
        except FileNotFoundError as exc:
            raise NotFound(f"Schema for form {form_type} not found") from exc

        steps_dict = {}
        for field in schema.fields:
            if field.source == "asked" and field.ui:
                step_title = field.ui.step
                if step_title not in steps_dict:
                    steps_dict[step_title] = {"title": step_title, "fields": []}

                fields_list = steps_dict[step_title]["fields"]

                field_dict = {
                    "binding": field.binding,
                    "prompt": field.ui.prompt,
                    "widget": field.ui.widget,
                    "help_text": field.ui.help_text,
                    "conditional_on": field.conditional_on,
                }

                if field.repeat:
                    repeat_group = next(
                        (
                            f
                            for f in fields_list
                            if f.get("widget") == "repeat_group" and f.get("repeat") == field.repeat
                        ),
                        None,
                    )
                    if repeat_group:
                        if not any(
                            f.get("binding") == field.binding for f in repeat_group["fields"]
                        ):
                            repeat_group["fields"].append(field_dict)
                    else:
                        fields_list.append(
                            {
                                "widget": "repeat_group",
                                "repeat": field.repeat,
                                "repeat_capacity": field.repeat_capacity,
                                "conditional_on": field.conditional_on,
                                "fields": [field_dict],
                            }
                        )
                else:
                    fields_list.append(
                        {
                            **field_dict,
                            "repeat": field.repeat,
                            "repeat_capacity": field.repeat_capacity,
                        }
                    )

        steps_list = list(steps_dict.values())
        return Response({"form_type": form_type, "steps": steps_list})
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/content/management/commands/check_reading_level.py b/backend/apps/content/management/commands/check_reading_level.py
index caeb8f6..37847b2 100644
--- a/backend/apps/content/management/commands/check_reading_level.py
+++ b/backend/apps/content/management/commands/check_reading_level.py
@@ -153,11 +153,11 @@ def _collect_backend_texts() -> dict[str, str]:
     except (ImportError, AttributeError, OSError):
         pass

-    # UPL disclaimer from forms views
+    # UPL disclaimer from the forms app
     try:
-        from apps.forms.views import _UPL_DISCLAIMER
+        from apps.forms.constants import _UPL_DISCLAIMER

-        texts["forms.views._UPL_DISCLAIMER"] = _UPL_DISCLAIMER
+        texts["forms.constants._UPL_DISCLAIMER"] = _UPL_DISCLAIMER
     except (ImportError, AttributeError):
         pass

diff --git a/backend/apps/intake/management/commands/seed_demo_data.py b/backend/apps/intake/management/commands/seed_demo_data.py
index 97b9f9b..d3927a5 100644
--- a/backend/apps/intake/management/commands/seed_demo_data.py
+++ b/backend/apps/intake/management/commands/seed_demo_data.py
@@ -15,7 +15,7 @@ from django.db import transaction

 from apps.districts.models import District
 from apps.eligibility.services.means_test_calculator import MeansTestCalculator
-from apps.forms.registry import get_all_form_types, get_generator
+from apps.forms.registry import build_field_values, packet
 from apps.intake.models import (
     AssetInfo,
     DebtInfo,
@@ -596,11 +596,10 @@ class Command(BaseCommand):
                 status="pending",
             )

-        # Generate forms for eligible personas
+        # Check that every form in an eligible persona's packet resolves (none are stored)
         if result["passes_means_test"]:
-            for form_type in get_all_form_types():
+            for form_type in packet(session):
                 try:
-                    generator = get_generator(form_type, session)
-                    generator.generate()
+                    build_field_values(form_type, session)
                 except Exception as exc:
                     self.stderr.write(self.style.WARNING(f"    Skipped {form_type}: {exc}"))
diff --git a/backend/apps/intake/views.py b/backend/apps/intake/views.py
index 8e244d6..c822a9e 100644
--- a/backend/apps/intake/views.py
+++ b/backend/apps/intake/views.py
@@ -2,7 +2,7 @@
 API views for intake workflow.

 Provides REST API endpoints for multi-step bankruptcy intake process,
-including session management, means test calculation, and form preview.
+including session management and means test calculation.
 """

 from django.db import transaction
@@ -12,7 +12,6 @@ from rest_framework.permissions import IsAuthenticated
 from rest_framework.response import Response

 from apps.eligibility.services import MeansTestCalculator
-from apps.forms.services import Form101Generator

 from .models import (
     AssetInfo,
@@ -235,38 +234,6 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
                 status=status.HTTP_400_BAD_REQUEST,
             )

-    @action(detail=True, methods=["get"])
-    def preview_form_101(self, request, pk=None):
-        """
-        Preview Form 101 (Voluntary Petition) for this session.
-
-        GET /api/intake/sessions/{id}/preview_form_101/
-
-        Returns:
-            Form 101 data structure ready for display/preview
-        """
-        session = self.get_object()
-
-        try:
-            generator = Form101Generator(session)
-            preview_data = generator.preview()
-
-            return Response(
-                {
-                    "form_preview": preview_data,
-                    "session_id": session.id,
-                }
-            )
-
-        except ValueError as e:
-            return Response(
-                {
-                    "error": str(e),
-                    "message": "Unable to generate form preview. Please ensure all required information is provided.",
-                },
-                status=status.HTTP_400_BAD_REQUEST,
-            )
-
     @action(detail=True, methods=["get"])
     def summary(self, request, pk=None):
         """
PATCH
```

- [ ] **Step 4: Run the task's tests, the migration check and the suite**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_registry.py apps/forms/tests/test_form_views.py apps/forms/tests/test_download_action.py -q -p no:cacheprovider 2>&1 | tail -1
$PY manage.py makemigrations --check --dry-run
$PY -m ruff check apps/
$PY -m pytest -q -p no:cacheprovider 2>&1 | tail -2
```

Expected: `59 passed`, `No changes detected`, `All checks passed!`, then `1763 passed, 86 xfailed`.

- [ ] **Step 5: Commit**

```bash
set -o pipefail
git add \
  backend/apps/forms/constants.py \
  backend/apps/forms/migrations/0006_field_values.py \
  backend/apps/audit/tests/test_upl_compliance.py \
  backend/apps/content/management/commands/check_reading_level.py \
  backend/apps/eligibility/tests/test_means_test_calculator.py \
  backend/apps/forms/models.py \
  backend/apps/forms/registry.py \
  backend/apps/forms/serializers.py \
  backend/apps/forms/tests/conftest.py \
  backend/apps/forms/tests/test_download_action.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/tests/test_registry.py \
  backend/apps/forms/views.py \
  backend/apps/intake/management/commands/seed_demo_data.py \
  backend/apps/intake/tests/test_e2e_intake.py \
  backend/apps/intake/views.py
git commit -F - <<'MSG'
feat(forms): one generation path, the packet rules, and encrypted field values

build_field_values() resolves a form's schema after its preconditions, and
generate, generate_all, regenerate and download all use it. The registry says
which forms apply to a filer (103B with a fee waiver, 122A-2 at or above the
median, 122A-1Supp not yet) and what each needs first; a missing precondition
is a 422 in plain words. Resolved values are stored encrypted in field_values;
form_data is blanked and never returned (DIG-124). A filed form downloads
exactly what was filed. Adds GET /api/forms/packet/ and removes the preview
endpoints.
MSG
git status --short
```

### Task 7: Check the five personas' packets print the right figures (oracle tier 3)

_Built and verified as commit `8fb9009` on `plan/forms-step1`._

**Files:**

- Create: `backend/apps/forms/tests/test_oracle_tier3.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_known_defects.py`

**Interfaces:**

- Consumes: `build_field_values` (Task 6); `seed_demo_data --reset persona=<name>` and `loaddata ilnd_2025_data`; `case_param`, the recorder and `known_defects.json` (Task 5).
- Produces: `test_oracle_tier3.py`, which holds the `EXPECTED` tables (persona → form → full name → printed value), and a `known_defects.json` of 142 entries. **The tables encode the six readings listed above; confirm them with the owner before this task runs.**

- [ ] **Step 1: Write the persona tables and add tier 3 to the list check**

```python file=backend/apps/forms/tests/test_oracle_tier3.py
"""
Oracle tier 3: each seeded persona's packet prints the figures a correct filing must (spec §6).

Expected values are worked out by hand from each persona's data (the seed, which
matches docs/testing/persona-briefs/ except Priya's stale income line), never
from the app's derivations. Boxes are named from the verified field index, not
from the schema, so a value bound to the wrong line fails here. Money compares
as a number, so "3,200.00" equals "3200.00". A box expected to hold zero is not
asserted: step 2 decides where blank replaces 0.00.
"""

from decimal import Decimal, InvalidOperation
from functools import cache

import pytest
from django.core.management import call_command

from apps.districts.models import District
from apps.forms.registry import build_field_values
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.oracle import case_param
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import IntakeSession

TIER = "3"
BELOW_MEDIAN = "/12b less or equal to 13"
ABOVE_MEDIAN = "/12b more than 13"


def _common(first, last, street, zip_code):
    return {
        "Debtor1.First name": first,
        "Debtor1.Last name": last,
        "Debtor1.Street": street,
        "Debtor1.City": "Chicago",
        "Debtor1.State": "IL",
        "Debtor1.ZIP Code": zip_code,
        "Check Box1": "/Chapter 7",
    }


# persona → form_type → full name → printed value
EXPECTED = {
    "maria": {
        "form_101": _common("Maria", "Torres", "2145 W Division St Apt 3", "60622"),
        "form_106sum": {
            "1b": "6840.00",
            "1c": "6840.00",
            "3b": "20500.00",
            "3c": "20500.00",
            "4": "3200.00",
            "5": "2560.00",
        },
        "form_122a1": {
            "Debto1.Quest11": "3200.00",
            "Quest11": "3200.00",
            "12B": "38400.00",
            "13B": "3",
            "13C": "110712.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {"Amount 12": "3200.00"},
        "schedule_j": {
            "22a": "2560.00",
            "22c": "2560.00",
            "23a": "3200.00",
            "23b": "2560.00",
            "23c": "640.00",
        },
    },
    "james": {
        "form_101": _common("James", "Washington", "850 N State St Apt 1204", "60610"),
        "form_106sum": {
            "1b": "15200.00",
            "1c": "15200.00",
            "2": "8500.00",
            "3b": "9800.00",
            "3c": "18300.00",
            "4": "5833.00",
            "5": "3110.00",
        },
        "form_122a1": {
            "Debto1.Quest11": "5833.00",
            "Quest11": "5833.00",
            "12B": "69996.00",
            "13B": "1",
            "13C": "71304.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {"Amount 12": "5833.00"},
        "schedule_j": {
            "22a": "3110.00",
            "22c": "3110.00",
            "23a": "5833.00",
            "23b": "3110.00",
            "23c": "2723.00",
        },
    },
    "priya": {
        "form_101": _common("Priya", "Sharma", "456 W Fullerton Pkwy", "60614"),
        "form_106sum": {
            "1b": "8500.00",
            "1c": "8500.00",
            "3b": "57000.00",
            "3c": "57000.00",
            "4": "12000.00",
            "5": "6640.00",
        },
        "form_122a1": {
            "Debto1.Quest11": "12000.00",
            "Quest11": "12000.00",
            "12B": "144000.00",
            "13B": "4",
            "13C": "134366.00",
            "14a": ABOVE_MEDIAN,
        },
        "schedule_i": {"Amount 12": "12000.00"},
        "schedule_j": {
            "22a": "6640.00",
            "22c": "6640.00",
            "23a": "12000.00",
            "23b": "6640.00",
            "23c": "5360.00",
        },
    },
    "deshawn": {
        "form_101": _common("DeShawn", "Mitchell", "7823 S Sangamon St", "60620"),
        "form_106sum": {
            "1a": "180000.00",
            "1b": "20000.00",
            "1c": "200000.00",
            "2": "160000.00",
            "3b": "11700.00",
            "3c": "171700.00",
            "4": "3500.00",
            "5": "2295.00",
        },
        "form_122a1": {
            "Debto1.Quest11": "3500.00",
            "Quest11": "3500.00",
            "12B": "42000.00",
            "13B": "2",
            "13C": "91526.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {"Amount 12": "3500.00"},
        "schedule_j": {
            "22a": "2295.00",
            "22c": "2295.00",
            "23a": "3500.00",
            "23b": "2295.00",
            "23c": "1205.00",
        },
    },
    "sarah": {
        "form_101": _common("Sarah", "Chen", "1520 N Damen Ave Apt 2F", "60622"),
        "form_106sum": {
            "3b": "31400.00",
            "3c": "31400.00",
            "4": "2000.00",
            "5": "1280.00",
        },
        "form_122a1": {
            "Debto1.Quest11": "2000.00",
            "Quest11": "2000.00",
            "12B": "24000.00",
            "13B": "1",
            "13C": "71304.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {"Amount 12": "2000.00"},
        "schedule_j": {
            "22a": "1280.00",
            "22c": "1280.00",
            "23a": "2000.00",
            "23b": "1280.00",
            "23c": "720.00",
        },
    },
}


def _cases():
    for persona, forms in EXPECTED.items():
        for form_type, boxes in forms.items():
            for full_name, expected in boxes.items():
                yield case_param(form_type, full_name, TIER, persona, expected)


CASES = list(_cases())


@cache
def _printed(persona):
    """(form_type, full name) → what the persona's filled forms show there."""
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", "--reset", persona=persona, verbosity=0)
    session = IntakeSession.objects.filter(user__username=f"demo_{persona}").latest("id")
    printed = {}
    for form_type in EXPECTED[persona]:
        values = build_field_values(form_type, session)
        for w in read_widgets(PDFFormFiller().fill(form_type, values)):
            shown = w.state if w.state not in (None, "/Off") else w.value
            if shown is not None:
                printed.setdefault((form_type, w.full_name), set()).add(shown)
    return printed


def _amount(text):
    try:
        return Decimal(text.replace("$", "").replace(",", "").strip())
    except InvalidOperation:
        return None


@pytest.mark.django_db
@pytest.mark.parametrize("form_type,pdf_field,case,expected", CASES)
def test_persona_packet_prints_the_right_figure(form_type, pdf_field, case, expected):
    shown = _printed(case).get((form_type, pdf_field), set())
    if _amount(expected) is not None and not expected.startswith("/"):
        assert {_amount(s) for s in shown} == {
            _amount(expected)
        }, f"wrong_value: prints {sorted(shown)}, expected {expected}"
    else:
        assert expected in shown, f"wrong_value: prints {sorted(shown)}, expected {expected}"
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_known_defects.py b/backend/apps/forms/tests/test_known_defects.py
index d7e8630..039c2a9 100644
--- a/backend/apps/forms/tests/test_known_defects.py
+++ b/backend/apps/forms/tests/test_known_defects.py
@@ -10,11 +10,13 @@ import re

 from apps.forms.tests import test_oracle_tier1 as tier1
 from apps.forms.tests import test_oracle_tier2 as tier2
+from apps.forms.tests import test_oracle_tier3 as tier3
 from apps.forms.tests.oracle import DEFECT_CLASSES, KNOWN_DEFECTS

 ORACLE_CASES = {
     "1": tier1.TEXT_CASES + tier1.BOX_CASES + tier1.UNMAPPED_CASES,
     "2": tier2.CASES,
+    "3": tier3.CASES,
 }


PATCH
```

- [ ] **Step 2: Run tier 3 and watch it find the wrong values**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier3.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `57 failed`, each a value already ticketed. For example, 106Sum line 4 prints total liabilities, 122A-1's lines are shifted, and Schedule J's 22c, 23b and 23c are blank.

- [ ] **Step 3: Re-record the list with all three tiers**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY ../data/forms/field_index/tools/record_known_defects.py \
  apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py \
  apps/forms/tests/test_oracle_tier3.py | tail -1
```

Expected: `142 entries written to backend/apps/forms/tests/known_defects.json`. Check it:

```bash
set -o pipefail
shasum -a 256 -c <<'SUMS'
294b966fb8378ce4280cc7c427f7b40d5218ae7897b2a55fd5c166f72233a025  backend/apps/forms/tests/known_defects.json
SUMS
```

Expected: `OK`. By tier, the list holds 4 `unmapped_choice`, 81 `wrong_box` and 57 `wrong_value`.

- [ ] **Step 4: Run the oracle and the suite**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
$PY -m pytest -q -p no:cacheprovider 2>&1 | tail -2
```

Expected: `142 xfailed` with no failures, then `1832 passed, 143 xfailed`.

- [ ] **Step 5: Commit**

```bash
set -o pipefail
git add \
  backend/apps/forms/tests/test_oracle_tier3.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_known_defects.py
git commit -F - <<'MSG'
test(forms): check the five personas' packets print the right figures (oracle tier 3)

Each seeded persona's Form 101, 106Sum, 122A-1, Schedule I and Schedule J are
filled and read back against values worked out by hand from the persona briefs,
never from the app's derivations. The 57 wrong values found join
known_defects.json as strict xfails, 142 entries in all.
MSG
git status --short
```

### Task 8: Delete the 17 form generators and their tests

_Built and verified as commit `6af6cdd` on `plan/forms-step1`._

**Files:**

- Modify: `backend/apps/forms/services/__init__.py`
- Modify: `backend/apps/forms/tests/test_form_103b_schema.py`
- Modify: `backend/apps/forms/tests/test_form_106dec_schema.py`
- Modify: `backend/apps/forms/tests/test_form_106sum_schema.py`
- Modify: `backend/apps/forms/tests/test_form_121_schema.py`
- Modify: `backend/apps/forms/tests/test_form_122a1_schema.py`
- Modify: `backend/apps/forms/tests/test_schedule_i_schema.py`
- Delete: `backend/apps/forms/services/form_101_generator.py`
- Delete: `backend/apps/forms/services/form_103b_generator.py`
- Delete: `backend/apps/forms/services/form_106dec_generator.py`
- Delete: `backend/apps/forms/services/form_106sum_generator.py`
- Delete: `backend/apps/forms/services/form_107_generator.py`
- Delete: `backend/apps/forms/services/form_121_generator.py`
- Delete: `backend/apps/forms/services/form_122a1_generator.py`
- Delete: `backend/apps/forms/services/form_122a1_supp_generator.py`
- Delete: `backend/apps/forms/services/form_122a2_generator.py`
- Delete: `backend/apps/forms/services/schedule_ab_generator.py`
- Delete: `backend/apps/forms/services/schedule_c_generator.py`
- Delete: `backend/apps/forms/services/schedule_d_generator.py`
- Delete: `backend/apps/forms/services/schedule_ef_generator.py`
- Delete: `backend/apps/forms/services/schedule_g_generator.py`
- Delete: `backend/apps/forms/services/schedule_h_generator.py`
- Delete: `backend/apps/forms/services/schedule_i_generator.py`
- Delete: `backend/apps/forms/services/schedule_j_generator.py`
- Delete: `backend/apps/forms/tests/test_form_103b_generator.py`
- Delete: `backend/apps/forms/tests/test_form_106dec_generator.py`
- Delete: `backend/apps/forms/tests/test_form_106sum_generator.py`
- Delete: `backend/apps/forms/tests/test_form_107_generator.py`
- Delete: `backend/apps/forms/tests/test_form_121_generator.py`
- Delete: `backend/apps/forms/tests/test_form_122a1_generator.py`
- Delete: `backend/apps/forms/tests/test_schedule_ab_generator.py`
- Delete: `backend/apps/forms/tests/test_schedule_c_generator.py`
- Delete: `backend/apps/forms/tests/test_schedule_d_generator.py`
- Delete: `backend/apps/forms/tests/test_schedule_ef_generator.py`
- Delete: `backend/apps/forms/tests/test_schedule_i_generator.py`
- Delete: `backend/apps/forms/tests/test_schedule_j_generator.py`

**Interfaces:**

- Consumes: `resolve`, `load_schema` (existing); `build_field_values` (Task 6), which replaced every caller of a generator.
- Produces: `apps/forms/services/` holding only the fill engine (`fill_resolver.py`, `derivations.py`, `pdf_filler.py`). The row builders in the Schedule D, E/F and A/B generators stay in git history at `941c873`, for step 3 to lift from there. Schedule C's exemption picking is deleted (spec §7).

- [ ] **Step 1: Port the six per-form schema tests to the resolver**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_form_103b_schema.py b/backend/apps/forms/tests/test_form_103b_schema.py
index ca25471..bbceebd 100644
--- a/backend/apps/forms/tests/test_form_103b_schema.py
+++ b/backend/apps/forms/tests/test_form_103b_schema.py
@@ -8,7 +8,7 @@ from django.contrib.auth import get_user_model

 from apps.districts.models import District
 from apps.forms.schema import load_schema
-from apps.forms.services.form_103b_generator import Form103BGenerator
+from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import (
     DebtorInfo,
     FeeWaiverApplication,
@@ -72,21 +72,15 @@ class TestForm103BSchema:
             assert f.source in ("presume", "derived", "constant", "asked", "ingested")

     def test_resolver_produces_output(self, session_with_fw):
-        generator = Form103BGenerator(session_with_fw)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_103b"), session_with_fw)
         assert "Bankruptcy District Information" in field_map
         assert "Debtor 1" in field_map
         assert "Jane Doe" in field_map["Debtor 1"]

     def test_fee_waiver_fields(self, session_with_fw):
-        generator = Form103BGenerator(session_with_fw)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_103b"), session_with_fw)
         assert field_map["Total number of people"] == "2"
-        assert field_map["4 type"] == "1500.00"
-        assert field_map["5 Type"] == "1400.00"

     def test_empty_session(self, session):
-        generator = Form103BGenerator(session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_103b"), session)
         assert "Bankruptcy District Information" in field_map
-        assert field_map.get("Total number of people", "1") == "1"
diff --git a/backend/apps/forms/tests/test_form_106dec_schema.py b/backend/apps/forms/tests/test_form_106dec_schema.py
index db24a33..103769d 100644
--- a/backend/apps/forms/tests/test_form_106dec_schema.py
+++ b/backend/apps/forms/tests/test_form_106dec_schema.py
@@ -8,7 +8,7 @@ from django.contrib.auth import get_user_model

 from apps.districts.models import District
 from apps.forms.schema import load_schema
-from apps.forms.services.form_106dec_generator import Form106DecGenerator
+from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import DebtorInfo, IntakeSession

 User = get_user_model()
@@ -63,17 +63,14 @@ class TestForm106DecSchema:
         assert len(required) >= 2  # District and Debtor 1 at minimum

     def test_resolver_produces_output(self, session_with_debtor):
-        generator = Form106DecGenerator(session_with_debtor)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_106dec"), session_with_debtor)
         assert "Debtor 1" in field_map
         assert "Jane Marie Doe" in field_map["Debtor 1"]
         assert "Bankruptcy District Information" in field_map
         assert "Northern District of Illinois" in field_map["Bankruptcy District Information"]

     def test_resolver_without_debtor(self, session):
-        generator = Form106DecGenerator(session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_106dec"), session)
         assert "Bankruptcy District Information" in field_map
-        # Debtor 1 should be empty or absent when no debtor_info
-        debtor_val = field_map.get("Debtor 1", "")
-        assert debtor_val == "" or "Debtor 1" not in field_map
+        # No name is printed when there is no debtor_info
+        assert "Debtor 1" not in field_map
diff --git a/backend/apps/forms/tests/test_form_106sum_schema.py b/backend/apps/forms/tests/test_form_106sum_schema.py
index eb57942..ad59ce8 100644
--- a/backend/apps/forms/tests/test_form_106sum_schema.py
+++ b/backend/apps/forms/tests/test_form_106sum_schema.py
@@ -8,7 +8,7 @@ from django.contrib.auth import get_user_model

 from apps.districts.models import District
 from apps.forms.schema import load_schema
-from apps.forms.services.form_106sum_generator import Form106SumGenerator
+from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import (
     AssetInfo,
     DebtInfo,
@@ -103,8 +103,7 @@ class TestForm106SumSchema:
             assert f.source in ("presume", "derived", "constant", "asked", "ingested")

     def test_resolver_produces_output(self, populated_session):
-        generator = Form106SumGenerator(populated_session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_106sum"), populated_session)
         assert "Debtor 1" in field_map
         assert "Jane Doe" in field_map["Debtor 1"]
         assert "Bankruptcy District Information" in field_map
@@ -114,29 +113,23 @@ class TestForm106SumSchema:
         assert "8" in field_map  # CMI

     def test_asset_totals(self, populated_session):
-        generator = Form106SumGenerator(populated_session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_106sum"), populated_session)
         assert field_map["1a"] == "200000.00"  # real property
         assert field_map["1b"] == "15000.00"  # personal property
         assert field_map["1c"] == "215000.00"  # total assets

     def test_debt_totals(self, populated_session):
-        generator = Form106SumGenerator(populated_session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_106sum"), populated_session)
         assert field_map["2"] == "50000.00"  # secured
         assert field_map["3a"] == "5000.00"  # priority unsecured
         assert field_map["3b"] == "10000.00"  # nonpriority unsecured
-        assert field_map["3c"] == "15000.00"  # total unsecured
-        assert field_map["4"] == "65000.00"  # total debts

     def test_cmi(self, populated_session):
-        generator = Form106SumGenerator(populated_session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_106sum"), populated_session)
         # 1200 * 6 / 6 = 1200.00
         assert field_map["8"] == "1200.00"

     def test_empty_session(self, session):
-        generator = Form106SumGenerator(session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_106sum"), session)
         assert field_map["1a"] == "0.00"
         assert field_map["8"] == "0.00"
diff --git a/backend/apps/forms/tests/test_form_121_schema.py b/backend/apps/forms/tests/test_form_121_schema.py
index bfb283d..1938535 100644
--- a/backend/apps/forms/tests/test_form_121_schema.py
+++ b/backend/apps/forms/tests/test_form_121_schema.py
@@ -8,7 +8,7 @@ from django.contrib.auth import get_user_model

 from apps.districts.models import District
 from apps.forms.schema import load_schema
-from apps.forms.services.form_121_generator import Form121Generator
+from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import DebtorInfo, IntakeSession

 User = get_user_model()
@@ -58,8 +58,7 @@ class TestForm121Schema:
             assert f.source in ("presume", "derived", "constant", "asked", "ingested")

     def test_resolver_produces_output(self, session_with_ssn):
-        generator = Form121Generator(session_with_ssn)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_121"), session_with_ssn)
         assert "Debtor1.First name" in field_map
         assert field_map["Debtor1.First name"] == "Jane"
         assert field_map["Debtor1.Last name"] == "Doe"
@@ -67,11 +66,9 @@ class TestForm121Schema:
         assert field_map["Debtor1a.SSNum"] == "123-45-6789"

     def test_district_name(self, session_with_ssn):
-        generator = Form121Generator(session_with_ssn)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_121"), session_with_ssn)
         assert field_map["Bankruptcy District Information"] == "Northern District of Illinois"

     def test_without_debtor(self, session):
-        generator = Form121Generator(session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_121"), session)
         assert "Bankruptcy District Information" in field_map
diff --git a/backend/apps/forms/tests/test_form_122a1_schema.py b/backend/apps/forms/tests/test_form_122a1_schema.py
index 0e90831..5d2f483 100644
--- a/backend/apps/forms/tests/test_form_122a1_schema.py
+++ b/backend/apps/forms/tests/test_form_122a1_schema.py
@@ -1,14 +1,13 @@
 """Round-trip tests for Form 122A-1 schema-driven resolution."""

-from datetime import date
 from decimal import Decimal

 import pytest
 from django.contrib.auth import get_user_model

-from apps.districts.models import District, MedianIncome
+from apps.districts.models import District
 from apps.forms.schema import load_schema
-from apps.forms.services.form_122a1_generator import Form122A1Generator
+from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import IncomeInfo, IntakeSession

 User = get_user_model()
@@ -38,23 +37,6 @@ def session_with_income(session):
     return session


-@pytest.fixture
-def session_with_median(session):
-    MedianIncome.objects.create(
-        district=session.district,
-        effective_date=date(2025, 1, 1),
-        family_size_1=Decimal("55000.00"),
-        family_size_2=Decimal("65000.00"),
-        family_size_3=Decimal("75000.00"),
-        family_size_4=Decimal("85000.00"),
-        family_size_5=Decimal("95000.00"),
-        family_size_6=Decimal("105000.00"),
-        family_size_7=Decimal("115000.00"),
-        family_size_8=Decimal("125000.00"),
-    )
-    return session
-
-
 @pytest.mark.django_db
 class TestForm122A1Schema:
     def test_schema_loads(self):
@@ -67,26 +49,15 @@ class TestForm122A1Schema:
             assert f.source in ("presume", "derived", "constant", "asked", "ingested")

     def test_resolver_produces_output(self, session_with_income):
-        generator = Form122A1Generator(session_with_income)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_122a1"), session_with_income)
         assert "Bankruptcy District Information" in field_map
         assert "12B" in field_map  # annualized CMI

     def test_cmi_calculation(self, session_with_income):
-        generator = Form122A1Generator(session_with_income)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_122a1"), session_with_income)
         # 2000 * 6 / 6 = 2000 CMI, annualized = 24000
         assert field_map["12B"] == "24000.00"

-    def test_median_income(self, session_with_income, session_with_median):
-        session_with_income.district = session_with_median.district
-        session_with_income.save()
-        generator = Form122A1Generator(session_with_income)
-        field_map = generator.pdf_field_map()
-        assert field_map["13A"] == "55000.00"
-
     def test_empty_session(self, session):
-        generator = Form122A1Generator(session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("form_122a1"), session)
         assert "Bankruptcy District Information" in field_map
-        assert field_map.get("12B", "0.00") == "0.00"
diff --git a/backend/apps/forms/tests/test_schedule_i_schema.py b/backend/apps/forms/tests/test_schedule_i_schema.py
index 3c37e90..db1f0cf 100644
--- a/backend/apps/forms/tests/test_schedule_i_schema.py
+++ b/backend/apps/forms/tests/test_schedule_i_schema.py
@@ -8,7 +8,7 @@ from django.contrib.auth import get_user_model

 from apps.districts.models import District
 from apps.forms.schema import load_schema
-from apps.forms.services.schedule_i_generator import ScheduleIGenerator
+from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()
@@ -64,21 +64,18 @@ class TestScheduleISchema:
             assert f.source in ("presume", "derived", "constant", "asked", "ingested")

     def test_resolver_produces_output(self, session_with_income):
-        generator = ScheduleIGenerator(session_with_income)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("schedule_i"), session_with_income)
         assert "Bankruptcy District Information" in field_map
         assert "Debtor 1" in field_map
         assert "Jane Doe" in field_map["Debtor 1"]
         assert "Amount 12" in field_map

     def test_cmi_in_field_map(self, session_with_income):
-        generator = ScheduleIGenerator(session_with_income)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("schedule_i"), session_with_income)
         # 2000 * 6 / 6 = 2000
         assert field_map["Amount 12"] == "2000.00"
         assert field_map["Amount 10 Debtor 1"] == "2000.00"

     def test_empty_session(self, session):
-        generator = ScheduleIGenerator(session)
-        field_map = generator.pdf_field_map()
+        field_map = resolve(load_schema("schedule_i"), session)
         assert "Bankruptcy District Information" in field_map
PATCH
```

Each test changes from `XGenerator(session).pdf_field_map()` to `resolve(load_schema("<form_type>"), session)`. These are resolver tests; preconditions are tested in `test_registry.py`. The patch also removes the asserts that pinned known defects, and those that passed whatever the code did (ruling 12).

- [ ] **Step 2: Run them; they pass before the generators go**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m pytest apps/forms/tests/ -k schema -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: all selected tests pass (`40 passed`).

- [ ] **Step 3: Delete the generators and their tests**

```bash
set -o pipefail
git rm -q \
  backend/apps/forms/services/form_101_generator.py \
  backend/apps/forms/services/form_103b_generator.py \
  backend/apps/forms/services/form_106dec_generator.py \
  backend/apps/forms/services/form_106sum_generator.py \
  backend/apps/forms/services/form_107_generator.py \
  backend/apps/forms/services/form_121_generator.py \
  backend/apps/forms/services/form_122a1_generator.py \
  backend/apps/forms/services/form_122a1_supp_generator.py \
  backend/apps/forms/services/form_122a2_generator.py \
  backend/apps/forms/services/schedule_ab_generator.py \
  backend/apps/forms/services/schedule_c_generator.py \
  backend/apps/forms/services/schedule_d_generator.py \
  backend/apps/forms/services/schedule_ef_generator.py \
  backend/apps/forms/services/schedule_g_generator.py \
  backend/apps/forms/services/schedule_h_generator.py \
  backend/apps/forms/services/schedule_i_generator.py \
  backend/apps/forms/services/schedule_j_generator.py \
  backend/apps/forms/tests/test_form_103b_generator.py \
  backend/apps/forms/tests/test_form_106dec_generator.py \
  backend/apps/forms/tests/test_form_106sum_generator.py \
  backend/apps/forms/tests/test_form_107_generator.py \
  backend/apps/forms/tests/test_form_121_generator.py \
  backend/apps/forms/tests/test_form_122a1_generator.py \
  backend/apps/forms/tests/test_schedule_ab_generator.py \
  backend/apps/forms/tests/test_schedule_c_generator.py \
  backend/apps/forms/tests/test_schedule_d_generator.py \
  backend/apps/forms/tests/test_schedule_ef_generator.py \
  backend/apps/forms/tests/test_schedule_i_generator.py \
  backend/apps/forms/tests/test_schedule_j_generator.py
```

```python file=backend/apps/forms/services/__init__.py
"""
Form services: the schema-driven fill engine (fill_resolver, derivations) and the PDF filler.

A form's printed values come from apps.forms.registry.build_field_values().
"""
```

- [ ] **Step 4: Run the suite as CI does, with the coverage gate**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend && $PY -m ruff check apps/ && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | grep -E '^TOTAL|Required|passed'
```

Expected: `Required test coverage of 90% reached` (about 94.7%), then `1593 passed, 143 xfailed`.

- [ ] **Step 5: Run the backend search gate (spec §5.5)**

```bash
set -o pipefail
grep -rnE 'Generator\b|get_generator|build_draft_schema|pdf_field_map|form_data' --include='*.py' backend | grep -v '/migrations/'
```

Expected: exactly these five lines (ruling 11), and nothing else:

```text
backend/apps/forms/models.py:63:    form_data = models.JSONField(default=dict, help_text="Unused; see field_values")
backend/apps/forms/tests/test_form_views.py:489:            assert "form_data" not in body
backend/apps/forms/tests/test_form_views.py:499:                "SELECT field_values, form_data FROM generated_forms WHERE id = %s", [form.id]
backend/apps/forms/tests/test_form_views.py:501:            raw_values, raw_form_data = cursor.fetchone()
backend/apps/forms/tests/test_form_views.py:504:        assert json.loads(raw_form_data) == {}
```

- [ ] **Step 6: Commit**

```bash
set -o pipefail
git add \
  backend/apps/forms/services/__init__.py \
  backend/apps/forms/tests/test_form_103b_schema.py \
  backend/apps/forms/tests/test_form_106dec_schema.py \
  backend/apps/forms/tests/test_form_106sum_schema.py \
  backend/apps/forms/tests/test_form_121_schema.py \
  backend/apps/forms/tests/test_form_122a1_schema.py \
  backend/apps/forms/tests/test_schedule_i_schema.py
git commit -F - <<'MSG'
refactor(forms): delete the 17 form generators and their tests

Every generator's pdf_field_map() was the same three lines over the schema,
and build_field_values() replaces them. The per-form schema tests now call the
resolver directly; asserts that pinned known defects (103B line 4/5, 106Sum
3c/4, 122A-1 13A) and asserts that passed whatever the code did are removed.
The Schedule D, E/F and A/B row builders stay in git history at 941c873 for
step 3.
MSG
git status --short
```

### Task 9: Show the filer's packet on the dashboard

_Built and verified as commit `6f6f30e` on `plan/forms-step1`._

**Files:**

- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/forms/__tests__/FormCard.test.tsx`
- Modify: `frontend/src/pages/FormDashboard.tsx`
- Modify: `frontend/src/pages/__tests__/FormDashboard.test.tsx`
- Modify: `frontend/src/test/accessibility.test.tsx`
- Modify: `frontend/src/test/mocks/handlers.ts`
- Modify: `frontend/src/types/api.ts`
- Delete: `frontend/src/components/Form101Preview.tsx`

**Interfaces:**

- Consumes: `GET /api/forms/packet/?session=<id>` → `{session, form_types}` (Task 6).
- Produces: `FormPacketResponse` and `FormType` without `form_122b` in `src/types/api.ts`; `GeneratedForm` without `form_data`; `api.forms.packet(sessionId) -> Promise<FormType[]>`; an MSW handler for `/forms/packet/` returning the 14-form below-median packet (`mockPacket`). Removed: `api.forms.preview`, `api.forms.generateForm101`, `api.intake.previewForm101`, `Form101Preview.tsx`, and their MSW handlers.

- [ ] **Step 1: Write the failing dashboard test and update the mocks**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/forms/__tests__/FormCard.test.tsx b/frontend/src/components/forms/__tests__/FormCard.test.tsx
index a07f8f7..dc57665 100644
--- a/frontend/src/components/forms/__tests__/FormCard.test.tsx
+++ b/frontend/src/components/forms/__tests__/FormCard.test.tsx
@@ -11,7 +11,6 @@ const mockForm: GeneratedForm = {
   form_type_display: 'Form 101 - Voluntary Petition',
   status: 'generated',
   status_display: 'Generated',
-  form_data: {},
   pdf_file_path: '/media/forms/form_101_1.pdf',
   upl_disclaimer: 'This form was prepared using information you provided.',
   generated_by: 1,
diff --git a/frontend/src/pages/__tests__/FormDashboard.test.tsx b/frontend/src/pages/__tests__/FormDashboard.test.tsx
index d6b4476..2b3c5cb 100644
--- a/frontend/src/pages/__tests__/FormDashboard.test.tsx
+++ b/frontend/src/pages/__tests__/FormDashboard.test.tsx
@@ -107,15 +107,29 @@ describe('FormDashboard', () => {
   // Generate All
   // ---------------------------------------------------------------------------

-  it('renders Generate All button', async () => {
-    // Return empty forms list so all are "pending"
-    server.use(http.get('http://localhost:8000/api/forms/', () => HttpResponse.json([])));
+  it('offers only the forms in the filer’s packet', async () => {
+    // A stored form that no longer applies (122A-2 after income dropped) is neither shown nor counted
+    server.use(
+      http.get('http://localhost:8000/api/forms/packet/', () =>
+        HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
+      ),
+      http.get('http://localhost:8000/api/forms/', () =>
+        HttpResponse.json([
+          { id: 1, session: 1, form_type: 'form_101', status: 'generated' },
+          { id: 2, session: 1, form_type: 'form_122a2', status: 'generated' },
+        ])
+      )
+    );

     renderFormDashboard();

     await waitFor(() => {
-      expect(screen.getByRole('button', { name: /generate all 18 forms/i })).toBeInTheDocument();
+      expect(screen.getByRole('button', { name: /generate all 2 forms/i })).toBeInTheDocument();
     });
+    expect(screen.getByText('1 of 2 generated')).toBeInTheDocument();
+    expect(screen.getByText('Form 121 - SSN Statement')).toBeInTheDocument();
+    expect(screen.queryByText('Form 103B - Fee Waiver Application')).not.toBeInTheDocument();
+    expect(screen.queryByText('Form 122A-2 - Means Test Expenses')).not.toBeInTheDocument();
   });

   it('shows error banner when generate_all returns partial failures', async () => {
@@ -133,8 +147,8 @@ describe('FormDashboard', () => {
     renderFormDashboard();
     await waitFor(() => expect(screen.getByText('Your Court Forms')).toBeInTheDocument());

-    // Click "Generate All" — opens UPL confirmation modal
-    const generateAllBtn = screen.getByRole('button', { name: /generate all/i });
+    // Click "Generate All" (shown once the packet loads) — opens UPL confirmation modal
+    const generateAllBtn = await screen.findByRole('button', { name: /generate all/i });
     await userEvent.click(generateAllBtn);

     // Acknowledge the UPL disclaimer checkbox, then confirm
diff --git a/frontend/src/test/accessibility.test.tsx b/frontend/src/test/accessibility.test.tsx
index 85e5c5e..aac7d8a 100644
--- a/frontend/src/test/accessibility.test.tsx
+++ b/frontend/src/test/accessibility.test.tsx
@@ -176,7 +176,6 @@ describe('Accessibility: Form Components', () => {
       form_type_display: 'Form 101',
       status: 'generated',
       status_display: 'Generated',
-      form_data: {},
       pdf_file_path: '/forms/101.pdf',
       upl_disclaimer: 'Test disclaimer.',
       generated_by: 1,
diff --git a/frontend/src/test/mocks/handlers.ts b/frontend/src/test/mocks/handlers.ts
index 23fc06f..664bfc1 100644
--- a/frontend/src/test/mocks/handlers.ts
+++ b/frontend/src/test/mocks/handlers.ts
@@ -44,7 +44,6 @@ const mockGeneratedForm = {
   form_type_display: 'Form 101 - Voluntary Petition',
   status: 'generated' as const,
   status_display: 'Generated',
-  form_data: {},
   pdf_file_path: '/media/forms/form_101_1.pdf',
   upl_disclaimer: 'This form was prepared using information you provided.',
   generated_by: 1,
@@ -52,6 +51,24 @@ const mockGeneratedForm = {
   updated_at: '2026-01-20T10:00:00Z',
 };

+/** A below-median filer with no fee waiver: the 14 forms every packet holds */
+const mockPacket = [
+  'form_101',
+  'form_106dec',
+  'form_106sum',
+  'form_107',
+  'form_121',
+  'form_122a1',
+  'schedule_a_b',
+  'schedule_c',
+  'schedule_d',
+  'schedule_e_f',
+  'schedule_g',
+  'schedule_h',
+  'schedule_i',
+  'schedule_j',
+];
+
 const mockMeansTestResult = {
   passes_means_test: true,
   qualifies_for_fee_waiver: false,
@@ -178,13 +195,6 @@ export const handlers = [

   // -- Forms ---------------------------------------------------------------

-  http.post(`${API}/forms/generate_form_101/`, () =>
-    HttpResponse.json({
-      form: mockGeneratedForm,
-      message: 'Form generated.',
-    })
-  ),
-
   http.post(`${API}/forms/generate/`, async ({ request }) => {
     const body = (await request.json()) as { form_type?: string };
     return HttpResponse.json({
@@ -208,7 +218,7 @@ export const handlers = [

   http.get(`${API}/forms/`, () => HttpResponse.json([mockGeneratedForm])),

-  http.get(`${API}/forms/:id/preview/`, () => HttpResponse.json(mockGeneratedForm)),
+  http.get(`${API}/forms/packet/`, () => HttpResponse.json({ session: 1, form_types: mockPacket })),

   http.post(`${API}/forms/:id/mark_downloaded/`, () =>
     HttpResponse.json({ message: 'Marked as downloaded.' })
PATCH
```

The new test serves a two-form packet and a stored 122A-2 that no longer applies. The dashboard must offer "Generate All 2 Forms" and show `1 of 2 generated`, with no 103B or 122A-2 card. The partial-failure test now waits for the Generate All button, which appears once the packet has loaded.

- [ ] **Step 2: Run it and watch it fail**

```bash
set -o pipefail
cd frontend && ./node_modules/.bin/vitest run src/pages/__tests__/FormDashboard.test.tsx 2>&1 | tail -4
```

Expected: FAIL — the button reads "Generate All 18 Forms", not "Generate All 2 Forms".

- [ ] **Step 3: Render the dashboard from the packet, and remove the dead callers**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/api/client.ts b/frontend/src/api/client.ts
index 8136e84..b7f1e83 100644
--- a/frontend/src/api/client.ts
+++ b/frontend/src/api/client.ts
@@ -15,9 +15,9 @@ import type {
   UpdateStepRequest,
   UpdateStepResponse,
   CalculateMeansTestResponse,
-  GenerateFormRequest,
   GenerateFormResponse,
   GenerateAllFormsResponse,
+  FormPacketResponse,
   SessionSummaryResponse,
   AssetInfo,
   DebtInfo,
@@ -353,14 +353,6 @@ export const intakeAPI = {
     );
   },

-  /**
-   * Preview Form 101
-   * GET /api/intake/sessions/{id}/preview_form_101/
-   */
-  previewForm101: async (sessionId: number): Promise<unknown> => {
-    return apiFetch<unknown>(`/intake/sessions/${sessionId}/preview_form_101/`);
-  },
-
   /**
    * Get session summary
    * GET /api/intake/sessions/{id}/summary/
@@ -529,7 +521,7 @@ export const formsAPI = {
   },

   /**
-   * Generate all 13 forms atomically
+   * Generate every form in the session's packet
    * POST /api/forms/generate_all/
    */
   generateAll: async (sessionId: number): Promise<GenerateAllFormsResponse> => {
@@ -540,11 +532,12 @@ export const formsAPI = {
   },

   /**
-   * Preview form data without generating
-   * GET /api/forms/{id}/preview/
+   * The form types that apply to this filer, in filing order
+   * GET /api/forms/packet/?session={sessionId}
    */
-  preview: async (formId: number): Promise<GeneratedForm> => {
-    return apiFetch<GeneratedForm>(`/forms/${formId}/preview/`);
+  packet: async (sessionId: number): Promise<FormType[]> => {
+    const response = await apiFetch<FormPacketResponse>(`/forms/packet/?session=${sessionId}`);
+    return response.form_types;
   },

   /**
@@ -559,14 +552,6 @@ export const formsAPI = {
     return Array.isArray(response) ? response : (response.results ?? []);
   },

-  /** @deprecated Use generate() with form_type */
-  generateForm101: async (data: GenerateFormRequest): Promise<GenerateFormResponse> => {
-    return apiFetch<GenerateFormResponse>('/forms/generate_form_101/', {
-      method: 'POST',
-      body: JSON.stringify(data),
-    });
-  },
-
   markDownloaded: async (formId: number): Promise<{ message: string }> => {
     return apiFetch<{ message: string }>(`/forms/${formId}/mark_downloaded/`, {
       method: 'POST',
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
index 36686f1..e69cdaa 100644
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -1,7 +1,7 @@
 /**
- * FormDashboard - Checklist of all 13 bankruptcy forms with status tracking
+ * FormDashboard - Checklist of the forms in the filer's packet, with status tracking
  *
- * Reached after completing the intake wizard. Shows all required forms,
+ * Reached after completing the intake wizard. Shows the forms that apply to this filer,
  * their generation status, and actions for download/filing.
  * Includes UPL disclaimer on every form interaction.
  */
@@ -17,21 +17,15 @@ import { UPL_FORM_DISCLAIMER } from '../constants/upl';
 import { Button } from '../components/common';
 import { PostTaskSurvey } from '../components/survey/PostTaskSurvey';
 import type { GeneratedForm, FormType, GenerateAllFormsResponse } from '../types/api';
-import { FORM_TYPE_METADATA } from '../types/api';
 import { trackEvent } from '../utils/analytics';

-/** All form types in filing order */
-const ALL_FORM_TYPES: FormType[] = (
-  Object.entries(FORM_TYPE_METADATA) as [FormType, { order: number }][]
-)
-  .sort(([, a], [, b]) => a.order - b.order)
-  .map(([key]) => key);
-
 type GenerateAllError = GenerateAllFormsResponse['errors'][number];

 export function FormDashboard() {
   const { session, isLoading: sessionLoading } = useIntake();
   const [forms, setForms] = useState<GeneratedForm[]>([]);
+  // The form types that apply to this filer, in filing order
+  const [packet, setPacket] = useState<FormType[]>([]);
   const [isLoading, setIsLoading] = useState(true);
   const [error, setError] = useState<string | null>(null);
   const [showSurvey, setShowSurvey] = useState(false);
@@ -44,8 +38,12 @@ export function FormDashboard() {

     setIsLoading(true);
     try {
-      const loadedForms = await api.forms.listBySession(session.id);
+      const [loadedForms, packetTypes] = await Promise.all([
+        api.forms.listBySession(session.id),
+        api.forms.packet(session.id),
+      ]);
       setForms(loadedForms);
+      setPacket(packetTypes);
       setError(null);
     } catch {
       setError('Unable to load your forms. Please try refreshing the page.');
@@ -118,7 +116,8 @@ export function FormDashboard() {
   }

   const filedCount = forms.filter((f) => f.status === 'filed').length;
-  const generatedCount = forms.length;
+  const generatedCount = forms.filter((f) => packet.includes(f.form_type)).length;
+  const totalCount = packet.length;

   return (
     <div className="form-dashboard">
@@ -157,34 +156,39 @@ export function FormDashboard() {
         </div>
       )}

-      {/* Progress summary */}
-      <div className="form-dashboard-progress" aria-label="Form generation progress">
-        <div className="form-dashboard-progress-bar">
-          <div
-            className="form-dashboard-progress-fill"
-            style={{ width: `${(generatedCount / ALL_FORM_TYPES.length) * 100}%` }}
-            role="progressbar"
-            aria-valuenow={generatedCount}
-            aria-valuemin={0}
-            aria-valuemax={ALL_FORM_TYPES.length}
-            aria-label={`${generatedCount} of ${ALL_FORM_TYPES.length} forms generated`}
-          />
-        </div>
-        <p className="form-dashboard-progress-text">
-          {generatedCount} of {ALL_FORM_TYPES.length} generated
-          {filedCount > 0 && ` | ${filedCount} filed`}
-        </p>
-      </div>
-
-      {/* Generate All button */}
-      <div className="form-dashboard-generate-all">
-        <GenerateAllButton
-          onGenerateAll={handleGenerateAll}
-          generatedCount={generatedCount}
-          totalCount={ALL_FORM_TYPES.length}
-          disabled={isLoading}
-        />
-      </div>
+      {/* Nothing to count until the packet has loaded */}
+      {totalCount > 0 && (
+        <>
+          {/* Progress summary */}
+          <div className="form-dashboard-progress" aria-label="Form generation progress">
+            <div className="form-dashboard-progress-bar">
+              <div
+                className="form-dashboard-progress-fill"
+                style={{ width: `${(generatedCount / totalCount) * 100}%` }}
+                role="progressbar"
+                aria-valuenow={generatedCount}
+                aria-valuemin={0}
+                aria-valuemax={totalCount}
+                aria-label={`${generatedCount} of ${totalCount} forms generated`}
+              />
+            </div>
+            <p className="form-dashboard-progress-text">
+              {generatedCount} of {totalCount} generated
+              {filedCount > 0 && ` | ${filedCount} filed`}
+            </p>
+          </div>
+
+          {/* Generate All button */}
+          <div className="form-dashboard-generate-all">
+            <GenerateAllButton
+              onGenerateAll={handleGenerateAll}
+              generatedCount={generatedCount}
+              totalCount={totalCount}
+              disabled={isLoading}
+            />
+          </div>
+        </>
+      )}

       {/* Form cards grid */}
       {isLoading ? (
@@ -193,7 +197,7 @@ export function FormDashboard() {
         </div>
       ) : (
         <div className="form-dashboard-grid">
-          {ALL_FORM_TYPES.map((formType) => (
+          {packet.map((formType) => (
             <FormCard
               key={formType}
               formType={formType}
diff --git a/frontend/src/types/api.ts b/frontend/src/types/api.ts
index c004487..99cc74a 100644
--- a/frontend/src/types/api.ts
+++ b/frontend/src/types/api.ts
@@ -221,7 +221,7 @@ export interface MeansTestResult {
 // Form Generation
 // ============================================================================

-/** All 18 form types registered in the backend form registry */
+/** All 17 form types registered in the backend form registry */
 export type FormType =
   | 'form_101' // Voluntary Petition
   | 'form_103b' // Fee Waiver Application
@@ -232,7 +232,6 @@ export type FormType =
   | 'form_122a1' // Means Test
   | 'form_122a1_supp' // Means Test Supplement
   | 'form_122a2' // Means Test Expense Calculation
-  | 'form_122b' // Chapter 7 Statement of Exemption
   | 'schedule_a_b' // Property
   | 'schedule_c' // Exemptions
   | 'schedule_d' // Secured Creditors
@@ -251,7 +250,6 @@ export interface GeneratedForm {
   form_type_display: string;
   status: FormStatus;
   status_display: string;
-  form_data: Record<string, unknown>;
   pdf_file_path: string | null;
   upl_disclaimer?: string;
   generated_by: number;
@@ -309,11 +307,6 @@ export const FORM_TYPE_METADATA: Record<
     description: 'Chapter 7 means test expense calculation',
     order: 9,
   },
-  form_122b: {
-    label: 'Form 122B - Chapter 7 Exemption',
-    description: 'Statement that income is primarily consumer debt',
-    order: 10,
-  },
   schedule_a_b: {
     label: 'Schedule A/B - Property',
     description: 'List of all your property',
@@ -429,6 +422,12 @@ export interface GenerateAllFormsResponse {
   total_errors: number;
 }

+/** The forms that apply to this filer, in filing order */
+export interface FormPacketResponse {
+  session: number;
+  form_types: FormType[];
+}
+
 export interface SessionSummaryResponse {
   session: IntakeSession;
   progress: {
PATCH
```

```bash
set -o pipefail
git rm -q frontend/src/components/Form101Preview.tsx
```

The changes:

- The progress bar and the Generate All button render only once the packet has loaded. Otherwise they would announce "All 0 forms have been generated" while loading, and after a failed load.
- `generatedCount` counts only the stored forms that are in the packet.

- [ ] **Step 4: Run vitest, the type check, eslint and prettier**

```bash
set -o pipefail
cd frontend && ./node_modules/.bin/vitest run 2>&1 | grep -E 'Test Files|Tests '
./node_modules/.bin/tsc --noEmit -p tsconfig.app.json && echo TSC-OK
./node_modules/.bin/eslint src --max-warnings=0 && echo ESLINT-OK
./node_modules/.bin/prettier --check src > /dev/null && echo PRETTIER-OK
```

Expected: `27 passed` files, `248 passed` tests, then `TSC-OK`, `ESLINT-OK` and `PRETTIER-OK`.

- [ ] **Step 5: Run the full search gate (backend and frontend/src)**

```bash
set -o pipefail
grep -rnE 'Generator\b|get_generator|build_draft_schema|pdf_field_map|form_data' --include='*.py' backend | grep -v '/migrations/'
grep -rnE 'Generator\b|get_generator|build_draft_schema|pdf_field_map|form_data' frontend/src || echo 'frontend/src: none'
```

Expected: the same five backend lines as Task 8, then `frontend/src: none`.

- [ ] **Step 6: Commit**

```bash
set -o pipefail
git add \
  frontend/src/api/client.ts \
  frontend/src/components/forms/__tests__/FormCard.test.tsx \
  frontend/src/pages/FormDashboard.tsx \
  frontend/src/pages/__tests__/FormDashboard.test.tsx \
  frontend/src/test/accessibility.test.tsx \
  frontend/src/test/mocks/handlers.ts \
  frontend/src/types/api.ts
git commit -F - <<'MSG'
feat(dashboard): show the filer's packet, not a fixed list of 18 forms

The dashboard renders its cards and its "N of M" count from
GET /api/forms/packet/, so a filer sees only the forms that apply to them, and
a stored form that no longer applies is neither shown nor counted. Form 122B
and form_data leave the frontend types; the dead Form101Preview and the preview
and generate_form_101 client calls are removed.
MSG
git status --short
```

### Task 10: Each E2E journey expects its own packet size, and waits for each step to change

_Built and verified as commit `699adec` on `plan/forms-step1`._

**Files:**

- Create: `frontend/src/pages/__tests__/SOFAStep.test.tsx`
- Modify: `frontend/e2e/journeys/deshawn-assets.spec.ts`
- Modify: `frontend/e2e/journeys/james-borderline.spec.ts`
- Modify: `frontend/e2e/journeys/maria-happy-path.spec.ts`
- Modify: `frontend/e2e/journeys/sarah-simplest.spec.ts`
- Modify: `frontend/e2e/journeys/sofa-journey.spec.ts`
- Modify: `frontend/e2e/pages/dashboard.page.ts`
- Modify: `frontend/e2e/pages/wizard.page.ts`
- Modify: `frontend/src/pages/SOFAStep.tsx`

**Interfaces:**

- Consumes: the packet-driven dashboard (Task 9), whose progress text reads `<generated> of <packet size> generated`.
- Produces: `DashboardPage.generateAllForms(expectedCount: number)`, which now requires the count and waits for `${expectedCount} of ${expectedCount}`. `WizardPage.nextStep()` waits for the progress live region to name a new step, or for the page to leave `/intake`. Packet sizes: Sarah, Maria and DeShawn 15 (14 + Form 103B); James and the SOFA journey 14. Priya never reaches the dashboard.

- [ ] **Step 1: Write the failing SOFA test (DIG-131)**

```tsx file=frontend/src/pages/__tests__/SOFAStep.test.tsx
import { StrictMode } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse, delay } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider, useIntake } from '../../context/IntakeContext';
import { SOFAStep } from '../SOFAStep';

const emptyReport = {
  id: 1,
  session: 1,
  has_prior_income: false,
  has_creditor_payments: false,
  has_business: false,
  prior_income: [],
  creditor_payments: [],
};

/** The filer arrives from the wizard, so the session is already loaded when the page mounts. */
function SOFAStepWithSession() {
  const { session } = useIntake();
  return session ? <SOFAStep /> : null;
}

describe('SOFAStep', () => {
  it('keeps a section the filer ticked when an earlier load replies late', async () => {
    // StrictMode mounts the page twice, so the report is read twice; the first read replies last.
    let reads = 0;
    server.use(
      http.get('http://localhost:8000/api/intake/sofa-report/:sessionId/', async () => {
        reads += 1;
        if (reads === 1) await delay(300);
        return HttpResponse.json(emptyReport);
      })
    );
    localStorage.setItem('current_session_id', '1');

    render(
      <StrictMode>
        <MemoryRouter>
          <IntakeProvider>
            <SOFAStepWithSession />
          </IntakeProvider>
        </MemoryRouter>
      </StrictMode>
    );

    const priorIncome = { name: /i had income in the past 3 years/i };
    await userEvent.click(await screen.findByRole('checkbox', priorIncome));
    await new Promise((resolve) => setTimeout(resolve, 400));

    expect(reads).toBe(2);
    expect(screen.getByRole('checkbox', priorIncome)).toBeChecked();
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

```bash
set -o pipefail
cd frontend && ./node_modules/.bin/vitest run src/pages/__tests__/SOFAStep.test.tsx 2>&1 | tail -4
```

Expected: FAIL — the prior-income box is unchecked. Under StrictMode the page reads its report twice, and the first read's late reply undoes the tick.

- [ ] **Step 3: Ignore a superseded load, as `IntakeWizard` already does**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/SOFAStep.tsx b/frontend/src/pages/SOFAStep.tsx
index bf729e2..716ed9f 100644
--- a/frontend/src/pages/SOFAStep.tsx
+++ b/frontend/src/pages/SOFAStep.tsx
@@ -39,13 +39,16 @@ export function SOFAStep() {
   const [error, setError] = useState<string | null>(null);
   const [saved, setSaved] = useState(false);

-  // Load report on mount
+  // Load report on mount. A superseded load (StrictMode's second mount, or a new session)
+  // is ignored, so its late reply can't undo what the filer has already ticked.
   useEffect(() => {
     if (!session) return;
+    let cancelled = false;
     setLoading(true);
     sofaReportAPI
       .get(session.id)
       .then((data) => {
+        if (cancelled) return;
         // Ensure at least one empty row in each section when gated on
         const newReport = { ...data };
         if (newReport.has_prior_income && newReport.prior_income.length === 0) {
@@ -56,8 +59,16 @@ export function SOFAStep() {
         }
         setReport(newReport);
       })
-      .catch(() => setError('Could not load your financial history data.'))
-      .finally(() => setLoading(false));
+      .catch(() => {
+        if (!cancelled) setError('Could not load your financial history data.');
+      })
+      .finally(() => {
+        if (!cancelled) setLoading(false);
+      });
+
+    return () => {
+      cancelled = true;
+    };
   }, [session]);

   // ── Gate toggles ──────────────────────────────────────────────
PATCH
```

- [ ] **Step 4: Run vitest**

```bash
set -o pipefail
cd frontend && ./node_modules/.bin/vitest run 2>&1 | grep -E 'Tests '
```

Expected: `249 passed`.

- [ ] **Step 5: Give each journey its packet size, and make `nextStep()` wait for the step to change (DIG-130)**

```bash
git apply <<'PATCH'
diff --git a/frontend/e2e/journeys/deshawn-assets.spec.ts b/frontend/e2e/journeys/deshawn-assets.spec.ts
index 8d4ea05..c918cea 100644
--- a/frontend/e2e/journeys/deshawn-assets.spec.ts
+++ b/frontend/e2e/journeys/deshawn-assets.spec.ts
@@ -83,8 +83,8 @@ test.describe('DeShawn Mitchell — Assets', () => {
     );

     // Generate forms (passes means test)
-    await dashboard.generateAllForms();
+    await dashboard.generateAllForms(15); // 14 forms + Form 103B (fee waiver)
     const count = await dashboard.getGeneratedCount();
-    expect(count).toBe(18);
+    expect(count).toBe(15);
   });
 });
diff --git a/frontend/e2e/journeys/james-borderline.spec.ts b/frontend/e2e/journeys/james-borderline.spec.ts
index a5960dd..97b9793 100644
--- a/frontend/e2e/journeys/james-borderline.spec.ts
+++ b/frontend/e2e/journeys/james-borderline.spec.ts
@@ -77,9 +77,9 @@ test.describe('James Washington — Borderline', () => {
     await sofa.skipForNow();

     // Forms generated (passes means test). James doesn't qualify for the
-    // fee waiver, so Form 103B (the waiver application) is not generated.
-    await dashboard.generateAllForms(17);
+    // fee waiver, so Form 103B (the waiver application) is not in his packet.
+    await dashboard.generateAllForms(14);
     const count = await dashboard.getGeneratedCount();
-    expect(count).toBe(17);
+    expect(count).toBe(14);
   });
 });
diff --git a/frontend/e2e/journeys/maria-happy-path.spec.ts b/frontend/e2e/journeys/maria-happy-path.spec.ts
index 4e53daa..4c129be 100644
--- a/frontend/e2e/journeys/maria-happy-path.spec.ts
+++ b/frontend/e2e/journeys/maria-happy-path.spec.ts
@@ -86,9 +86,9 @@ test.describe('Maria Torres — Happy Path', () => {
     );

     // Dashboard — generate all forms
-    await dashboard.generateAllForms();
+    await dashboard.generateAllForms(15); // 14 forms + Form 103B (fee waiver)
     const count = await dashboard.getGeneratedCount();
-    expect(count).toBe(18);
+    expect(count).toBe(15);

     // UPL disclaimer visible on dashboard
     await expect(dashboard.uplDisclaimer()).toBeVisible();
diff --git a/frontend/e2e/journeys/sarah-simplest.spec.ts b/frontend/e2e/journeys/sarah-simplest.spec.ts
index deaa82d..bf83690 100644
--- a/frontend/e2e/journeys/sarah-simplest.spec.ts
+++ b/frontend/e2e/journeys/sarah-simplest.spec.ts
@@ -82,9 +82,9 @@ test.describe('Sarah Chen — Simplest Case', () => {
     );

     // Generate all forms
-    await dashboard.generateAllForms();
+    await dashboard.generateAllForms(15); // 14 forms + Form 103B (fee waiver)
     const count = await dashboard.getGeneratedCount();
-    expect(count).toBe(18);
+    expect(count).toBe(15);

     // Survey appears and can be completed
     expect(await dashboard.isSurveyVisible()).toBe(true);
diff --git a/frontend/e2e/journeys/sofa-journey.spec.ts b/frontend/e2e/journeys/sofa-journey.spec.ts
index 5c0d556..addf3e9 100644
--- a/frontend/e2e/journeys/sofa-journey.spec.ts
+++ b/frontend/e2e/journeys/sofa-journey.spec.ts
@@ -113,9 +113,9 @@ test.describe('SOFA — Form 107 Financial History', () => {

     // ── Form Generation ─────────────────────────────────────

-    await dashboard.generateAllForms(17); // James is not fee-waiver eligible → 17 forms (no 103B)
+    await dashboard.generateAllForms(14); // James is not fee-waiver eligible → 14 forms (no 103B)
     const count = await dashboard.getGeneratedCount();
-    expect(count).toBe(17);
+    expect(count).toBe(14);

     // ── Download Form 107 ───────────────────────────────────

diff --git a/frontend/e2e/pages/dashboard.page.ts b/frontend/e2e/pages/dashboard.page.ts
index 958bfcd..a5a9ae4 100644
--- a/frontend/e2e/pages/dashboard.page.ts
+++ b/frontend/e2e/pages/dashboard.page.ts
@@ -8,11 +8,10 @@ export class DashboardPage {
   constructor(private page: Page) {}

   /**
-   * @param expectedCount Forms that should generate. Sessions without a
-   * FeeWaiverApplication can't generate Form 103B (the waiver application
-   * itself), so non-waiver personas expect 17.
+   * @param expectedCount The persona's packet size: 14 forms for a below-median
+   * filer, plus Form 103B for one with a fee waiver application.
    */
-  async generateAllForms(expectedCount = 18) {
+  async generateAllForms(expectedCount: number) {
     const btn = this.page.getByRole('button', { name: /generate all/i });
     await btn.click();

@@ -23,9 +22,9 @@ export class DashboardPage {
       .getByRole('button', { name: /continue/i })
       .click();

-    // Bulk generation hits 18 endpoints; wait for the progress text to settle
+    // Wait until every form in the packet has generated
     await expect(this.page.locator('.form-dashboard-progress-text')).toContainText(
-      `${expectedCount} of 18`,
+      `${expectedCount} of ${expectedCount}`,
       { timeout: 60000 }
     );
   }
diff --git a/frontend/e2e/pages/wizard.page.ts b/frontend/e2e/pages/wizard.page.ts
index 59173ce..8cc633a 100644
--- a/frontend/e2e/pages/wizard.page.ts
+++ b/frontend/e2e/pages/wizard.page.ts
@@ -14,7 +14,18 @@ export class WizardPage {
   // ── Navigation ──────────────────────────────────────────────────

   async nextStep() {
+    const progress = this.page
+      .getByRole('navigation', { name: 'Intake progress' })
+      .locator('[aria-live="polite"]');
+    const [before] = await progress.allTextContents();
     await this.page.getByRole('button', { name: /continue/i }).click();
+    // Wait for the step to change, or for step 1's detour to /documents. A step's
+    // save can outlast the fixed delay below, and a click during it lands a step behind.
+    await expect(async () => {
+      const leftWizard = !new URL(this.page.url()).pathname.startsWith('/intake');
+      const [now] = await progress.allTextContents();
+      expect(leftWizard || (now !== undefined && now !== before)).toBe(true);
+    }).toPass({ timeout: 15_000 });
     // Wait for step transition (network + render)
     await this.page.waitForTimeout(500);
   }
PATCH
```

Two details:

- `nextStep()` reads the progress region with `allTextContents()`, never `textContent()`. `textContent()` waits for the element, and step 1's detour to `/documents` unmounts it.
- The 500 ms settle delay stays, because the eligibility-estimate assertions rely on it.

- [ ] **Step 6: Lint the E2E code**

```bash
set -o pipefail
cd frontend && ./node_modules/.bin/eslint e2e src --max-warnings=0 && ./node_modules/.bin/prettier --check e2e src > /dev/null && echo E2E-LINT-OK
```

Expected: `E2E-LINT-OK`. No tsconfig covers `e2e/`, so nothing type-checks it (DIG-132).

- [ ] **Step 7: Run the E2E suite against a database of its own**

```bash
set -o pipefail
source .claude/forms-step1.env
# A separate database keeps the shared dev database on main's migrations.
docker exec dignifi-db-1 dropdb -U dignifi --if-exists dignifi_forms_step1
docker exec dignifi-db-1 createdb -U dignifi dignifi_forms_step1
export DJANGO_SETTINGS_MODULE=config.settings.development DEBUG=True ALLOWED_HOSTS=localhost,127.0.0.1 \
  DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_forms_step1 \
  CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 \
  OCR_PROVIDER=openai OPENAI_API_KEY=e2e-dummy-key OPENAI_BASE_URL=http://127.0.0.1:4010/v1 PYTHONUNBUFFERED=1
(cd backend && $PY manage.py migrate -v0 && $PY manage.py loaddata ilnd_2025_data -v0 && $PY manage.py seed_demo_data -v0)
(cd backend && exec $PY manage.py runserver 127.0.0.1:8000 --noreload > ../.claude/e2e-backend.log 2>&1) &
BACKEND=$!
(cd frontend && exec ./node_modules/.bin/vite --host 127.0.0.1 --port 5173 --strictPort > ../.claude/e2e-vite.log 2>&1) &
VITE=$!
trap 'kill $BACKEND $VITE 2>/dev/null' EXIT
$PY - <<'WAIT'
import time, urllib.request
for url in ("http://127.0.0.1:8000/health/", "http://127.0.0.1:5173/"):
    for _ in range(60):
        try:
            urllib.request.urlopen(url, timeout=2)
            break
        except OSError:
            time.sleep(1)
    else:
        raise SystemExit(f"{url} never answered")
WAIT
cd frontend && ./node_modules/.bin/playwright test --config e2e/playwright.config.ts --reporter=line 2>&1 | tail -3
```

Expected:

- `7 passed`, in about 1.2 minutes. Main takes about 36 s; the difference is the PDF test-fill in `generate_all`.
- `migrate` also runs the forms system check against the development settings.
- If a journey fails, its trace is under `frontend/test-results/`. Read it before re-running; don't retry blindly.

- [ ] **Step 8: Commit**

```bash
set -o pipefail
git add \
  frontend/src/pages/__tests__/SOFAStep.test.tsx \
  frontend/e2e/journeys/deshawn-assets.spec.ts \
  frontend/e2e/journeys/james-borderline.spec.ts \
  frontend/e2e/journeys/maria-happy-path.spec.ts \
  frontend/e2e/journeys/sarah-simplest.spec.ts \
  frontend/e2e/journeys/sofa-journey.spec.ts \
  frontend/e2e/pages/dashboard.page.ts \
  frontend/e2e/pages/wizard.page.ts \
  frontend/src/pages/SOFAStep.tsx
git commit -F - <<'MSG'
test(e2e): each journey expects its own packet size, and waits for each step to change

Sarah, Maria and DeShawn generate 15 forms (14 plus Form 103B); James and the
SOFA journey generate 14. nextStep() waits for the wizard's progress text to
name the next step before its settle delay, so a slow save no longer leaves a
journey a step behind (DIG-130). The SOFA page ignores a superseded load, so
its late reply can't untick a section the filer just ticked (DIG-131).
MSG
git status --short
```

### Task 11: Update the docs, then run every gate

_Built and verified as commit `b9fcbd4` on `plan/forms-step1`._

**Files:**

- Modify: `CLAUDE.md`
- Modify: `docs/testing/persona-briefs/priya-sharma.md`

**Interfaces:**

- Consumes: everything above.
- Produces: a `CLAUDE.md` that describes the packet, the schema check, the known-defects list and `field_values`, with no mention of generators, `pdf_field_map` or a fixed 18-form packet; Priya's brief at $12,000 a month (DIG-129).

- [ ] **Step 1: Update CLAUDE.md and Priya's brief**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index d9f516d..5626f8e 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -27,10 +27,13 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Debt and asset amounts are readable, as strings** — the owner gets `DebtInfo.amount_owed` and `AssetInfo.current_value`/`amount_owed` back (SSN and `account_number` stay write-only). DRF sends decimals as strings (`"2500.00"`), so the wizard converts them with `hydrateAmounts` (`utils/parseAmount.ts`) as session data enters step state; a raw string in a step's `reduce` joins as text (`$02500.00100.50`). A stored amount wider than `DecimalField(12, 2)` makes every read of that session 500, so every write path must bound it (`DraftDebtCreator` stores it as 0; documents `validate` returns 400).
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data.
 - **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
-- **Form 103B needs a FeeWaiverApplication** — its generator raises without one. `generate_all` yields 17/18 forms for filers who don't qualify for the waiver. (103B is the only generator with a conditional precondition; Form 121's raises are about missing DebtorInfo / malformed SSN, which a complete intake always satisfies.)
+- **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 ≥ median_income_threshold` (never `above_median_calculated`, which is sticky, DIG-128); 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words; any other failure is a 500 logged by exception type only.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` PDF field is 4 chars (last-4 only); full SSN appears on Form 121. pypdf truncates from the front.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
-- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`.
+- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. `generate_all` covers only the packet and deletes the rows of forms that no longer apply. `GET /api/forms/packet/?session=<id>` returns `{session, form_types}` in filing order, and the dashboard renders from it.
+- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: template hash, full names, widget types, export states, `/Opt` values, duplicate bindings, TBD). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box, `{}` is unmapped and prints nothing.
+- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails today, each with its DIG ticket. Fixing a defect turns its xfail into a failure until you delete the entry. Regenerate it with `data/forms/field_index/tools/record_known_defects.py` (usage in its docstring) and review the diff by hand.
+- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, and the API never returns it. `form_data` is blank; its column is dropped one release after this code is live. A filed form downloads its stored `field_values`; an unfiled one is resolved fresh on every download.
 - **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
 - **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
 - **CI ruff is pinned** — `ci.yml` installs `ruff==0.8.5`. Unpinned ruff broke CI when new rules shipped.
@@ -73,9 +76,9 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.

 - **Backend:** Django 5.0 + DRF, Python 3.11, PostgreSQL 15, `encrypted-model-fields` (Fernet PII encryption)
 - **Frontend:** React 19 + Vite 7 + TypeScript, Context API (not Redux), react-router-dom v7
-- **PDF:** pypdf fills official AO court templates. Each generator in `backend/apps/forms/services/` implements `pdf_field_map() -> dict[str, str]` mapping session data to PDF field names. `PDFFormFiller.fill(form_type, field_map)` loads from `data/forms/pdfs/`.
+- **PDF:** pypdf fills official AO court templates. Each schema in `data/forms/schemas/` binds a field to a widget's full name in the field index (`data/forms/field_index/<template stem>.index.json`). `build_field_values(form_type, session)` checks the form's preconditions and resolves its schema; `PDFFormFiller().fill(form_type, values)` fills exactly those full names in the template from `data/forms/pdfs/` and raises `UnknownField` for any other name.
 - **PDF templates:** 67 official AO court PDFs in `data/forms/pdfs/` (committed). Baked into Heroku image.
-- **Forms:** 18 generators registered in `apps/forms/registry.py` (`FORM_REGISTRY` / `get_all_form_types()`). `generate_all` iterates the registry inside one `transaction.atomic()`.
+- **Forms:** 17 form types in `apps/forms/registry.py` (`FORM_REGISTRY` / `get_all_form_types()` / `packet(session)`). `generate_all` gives each form its own savepoint.
 - **OCR service:** provider-agnostic. `OCR_PROVIDER` selects `openai` (default, `gpt-4o`, `OPENAI_API_KEY`) or `gemini` (`gemini-2.0-flash`, `GEMINI_API_KEY`); `OCR_MODEL` overrides the model so a model change is a config var, not a deploy. No local model — both call a hosted API directly.
 - **Auth:** JWT (simplejwt). Access in memory, refresh in localStorage. `GET /api/token/obtain/` + `/api/token/refresh/`.
 - **E2E:** 5 AI persona briefs in `docs/testing/persona-briefs/` (deshawn, james, maria, priya, sarah) driving 7 journey specs — one per persona plus `sofa-journey.spec.ts` and `scanned-bill-journey.spec.ts` (an upload read through a fake OpenAI server). `seed_demo_data` creates synthetic sessions with all intake data.
@@ -90,8 +93,9 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - `apps/intake/serializers.py` — nested serializers; DRF silently drops unknown fields (mismatch with frontend)
 - `apps/intake/management/commands/seed_demo_data.py` — 5 AI personas
 - `apps/eligibility/services/means_test_calculator.py` — § 707(b) logic, annualizes CMI
-- `apps/forms/registry.py` — `FORM_REGISTRY` (18 form_type → generator) + `get_all_form_types()` in filing order
-- `apps/forms/services/` — 18 generators + `pdf_filler.py` (`FORM_TEMPLATES` + `PDFFormFiller`), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
+- `apps/forms/registry.py` — `FORM_REGISTRY` (17 form_type → `PacketForm(applies, requires)`) in filing order, `packet()`, `build_field_values()`
+- `apps/forms/services/` — `pdf_filler.py` (`PDFFormFiller`, exact full names), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
+- `apps/forms/field_index.py` + `apps/forms/checks.py` — the field index loader and the schema system check
 - `apps/forms/views.py` — GeneratedFormViewSet (generate, generate_all, download, mark_filed)
 - `apps/documents/services/providers/` — `base.py` (`BaseOCRProvider`), `openai_provider.py`, `gemini.py`, `prompts/`
 - `apps/documents/services/` — `processor.py` (DocumentProcessor), `draft_debt.py`, `aggregator.py` (AggregateIngestionService)
PATCH
```

```bash
git apply <<'PATCH'
diff --git a/docs/testing/persona-briefs/priya-sharma.md b/docs/testing/persona-briefs/priya-sharma.md
--- a/docs/testing/persona-briefs/priya-sharma.md
+++ b/docs/testing/persona-briefs/priya-sharma.md
@@ -6,7 +6,7 @@

 - 43 years old, married with two children (ages 10 and 7)
 - Husband works as a software engineer; you work part-time as a tutor
-- Combined monthly take-home: about $10,000 (annual ~$120,000)
+- Combined monthly take-home: about $12,000 (annual ~$144,000)
 - Live in Lincoln Park — a nice neighborhood, but the medical bills are crushing
 - Your daughter had a complicated surgery and recovery ($35,000 in medical debt)

@@ -47,7 +47,7 @@
 | Address | 456 W Fullerton Pkwy, Chicago, IL 60614 |
 | Marital status | Married Filing Jointly |
 | Dependents | 2 |
-| Monthly income | $10,000 |
+| Monthly income | $12,000 |
 | Rent/mortgage | $2,800 |
 | Utilities | $250 |
 | Home maintenance | $100 |
PATCH
```

```bash
set -o pipefail
source .claude/forms-step1.env
# the brief's tables were never prettier-formatted; the pre-commit hook would realign them anyway
$PRECOMMIT run prettier --files docs/testing/persona-briefs/priya-sharma.md CLAUDE.md || true
$PRECOMMIT run prettier --files docs/testing/persona-briefs/priya-sharma.md CLAUDE.md
```

Expected: the second prettier run passes.

- [ ] **Step 2: Run every gate on the finished branch**

```bash
set -o pipefail
source .claude/forms-step1.env
cd backend
$PY -m ruff check .
$PY manage.py makemigrations --check --dry-run
$PY manage.py check
$PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | grep -E '^TOTAL|Required|passed'
cd ../frontend
./node_modules/.bin/vitest run 2>&1 | grep -E 'Tests '
./node_modules/.bin/tsc --noEmit -p tsconfig.app.json && ./node_modules/.bin/eslint . --max-warnings=0 && ./node_modules/.bin/prettier --check src e2e > /dev/null && echo FRONTEND-GATES-OK
```

Expected:

- `All checks passed!`;
- `No changes detected`;
- `System check identified no issues (0 silenced).`;
- `Required test coverage of 90% reached` with `1593 passed, 143 xfailed`;
- `249 passed`;
- `FRONTEND-GATES-OK`.

- [ ] **Step 3: Commit**

```bash
set -o pipefail
git add \
  CLAUDE.md \
  docs/testing/persona-briefs/priya-sharma.md
git commit -F - <<'MSG'
docs: describe the packet, the schema check, known defects and field_values; fix Priya's income (DIG-129)

CLAUDE.md no longer describes generators, pdf_field_map or a fixed 18-form
packet. Priya's brief now says $12,000 a month, matching the seed and the E2E
fixture; prettier realigns the brief's tables.
MSG
git status --short
```

---

## Controller notes (for the session running the plan, not for implementer subagents)

- **After each task's commit:** compare the tree with that task's verified commit: `git diff --stat <verified commit> HEAD -- . ':!docs/superpowers/plans'`. Empty output means the transcription matches; any difference is a transcription error to fix before review. If the owner rejects a tier 3 reading, every comparison from Task 7 on is expected to differ, so re-baseline from there.
- **Before Task 7:** have the owner's answer on the six readings. A rejected reading changes Task 7's `EXPECTED` table and its re-recorded `known_defects.json`, and nothing else.
- **After Task 3, comment in Plane (project DIG):**
  - On DIG-52 and DIG-61: the conversion removed 50 Schedule J TBD rows, including lines 4–9, 11, 13, 22b, 22c, 23b and 23c. The list is in `conversion_report.json` → `forms.schedule_j.tbd_removed`. Step 2 rebinds them.
  - On DIG-68: Form 121's `Check Box1` is held unmapped (ruling 4).
- **After Task 10:** comment the fixing commit on DIG-130 and DIG-131.
- **After Task 11:** comment on DIG-129, DIG-125 and DIG-127. On DIG-124, comment that the code fix is on the branch; the ticket stays open until step 1 is live.
- **PR description:** report the known-defects list by tier and class, as spec §8.3 requires. Tier 1: 4 `unmapped_choice` (DIG-68). Tier 2: 81 `wrong_box`. Tier 3: 57 `wrong_value`. 142 entries in all.
- **One release after step 1 is live:** add the migration that drops the `form_data` column (spec §5.5). Until then, the old code serving traffic during a release phase still reads it.
- **Keep `proto/forms-step1` and `plan/forms-step1`** (local branches) until the plan has been executed and reviewed. They are the reference builds.
