# Data Retention Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Actually delete intake data and uploaded documents once they pass a retention window, and tell users the truth about it — with the policy windows and user-facing messaging marked **draft pending legal review** so the system is operational before public launch without making promises legal hasn't signed off on.

**Architecture:** A Django management command `purge_expired_data` (run daily via Heroku Scheduler in production, manually/locally otherwise) hard-deletes: (1) `UploadedDocument`s past their existing `delete_after` timestamp, and (2) `IntakeSession`s past a configurable window — abandoned (never completed) after N days, completed after M days — cascading their child PII rows. Because Django does not delete `FileField` bytes on row deletion, the command explicitly removes files from storage first. Retention windows live in settings (documented draft defaults). Honest, draft-flagged retention copy is added to the Terms page. A legal-review checklist is recorded as a deferred gate that must be cleared before general-public launch.

**Tech Stack:** Python 3.11, Django 5, Django management commands, pytest. No new dependencies (Heroku Scheduler is a zero-cost add-on provisioned out-of-band).

---

## Background: verified facts (2026-06-13)

- `apps/documents/models.py` → `UploadedDocument`: `file = FileField(upload_to="documents/%Y/%m/")`, `uploaded_at` (auto), `delete_after` (defaults `now + 22 days` in `save()`), `deleted_at` (nullable, currently unused), indexed on `delete_after`. Has a `OneToOne` `OCRResult` (CASCADE) and `session`/`uploaded_by` FKs (CASCADE). **Nothing ever deletes expired rows or files today** — `delete_after` is decorative.
- `apps/intake/models.py` → `IntakeSession`: `created_at` (auto_now_add), `completed_at` (nullable), `status` (default `"started"`). Child models (`DebtorInfo`, `IncomeInfo`, `ExpenseInfo`, `AssetInfo`, `DebtInfo`, `FeeWaiverApplication`) are `OneToOne`/`FK` with `on_delete=CASCADE`, and hold the encrypted PII. Deleting a session removes them all.
- Management-command pattern exists: `apps/intake/management/commands/seed_demo_data.py`, `apps/content/management/commands/check_reading_level.py`.
- **No scheduler infrastructure** in the repo (empty `Procfile`, no celery/cron/APScheduler in requirements; `heroku.yml` runs the container). Production scheduling will use the **Heroku Scheduler** add-on invoking `python manage.py purge_expired_data` daily.
- DRF throttle rates live in the settings _base_ module (per CLAUDE.md). Locate it with `grep -rl "DEFAULT_THROTTLE_RATES" backend` — that file is where retention settings go.

Key correctness note: keying "completed vs abandoned" off `completed_at IS NULL` (not the `status` string) avoids depending on the exact status enum value.

## File Structure

- **Modify** the settings base module (found via grep) — add draft `RETENTION_*` day windows.
- **Create** `backend/apps/intake/management/commands/purge_expired_data.py` — the purge command (`--dry-run`, counts, file deletion, transaction).
- **Create** `backend/apps/intake/tests/test_purge_expired_data.py` — pytest coverage (deletes expired, keeps fresh, dry-run is a no-op, files removed).
- **Modify** `frontend/src/pages/TermsPage.tsx` — add an honest, draft-flagged retention section whose numbers match the settings defaults.
- **Create** `docs/internal/data-retention-legal-review.md` — the deferred legal-review gate (checklist that must clear before public launch).
- **Modify** project `CLAUDE.md` — document the command + Heroku Scheduler setup as a gotcha/ops note.

---

## Task 1: Add draft retention windows to settings

**Files:**

- Modify: the settings base module (locate: `grep -rl "DEFAULT_THROTTLE_RATES" backend`)

- [ ] **Step 1: Locate the settings base file**

Run: `grep -rln "DEFAULT_THROTTLE_RATES" backend`
Expected: one path, e.g. `backend/<project>/settings/base.py`. Use that path below.

- [ ] **Step 2: Add the retention settings block**

Append to the located settings base module:

```python
# ---------------------------------------------------------------------------
# Data retention (DRAFT — pending legal review before public launch)
# ---------------------------------------------------------------------------
# Windows after which the purge_expired_data management command permanently
# deletes intake data. Documents have their own per-row `delete_after`
# (default 22 days, set on the model). These numbers MUST match the figures
# stated in the user-facing Terms retention section.
RETENTION_ABANDONED_DAYS = int(os.environ.get("RETENTION_ABANDONED_DAYS", 30))
RETENTION_COMPLETED_DAYS = int(os.environ.get("RETENTION_COMPLETED_DAYS", 90))
```

(If the settings module does not already `import os`, add it at the top with the other stdlib imports.)

- [ ] **Step 3: Verify settings load**

Run: `cd backend && python manage.py check`
Expected: "System check identified no issues".

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "feat(retention): add draft RETENTION_* windows to settings

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Write the purge_expired_data command (TDD)

**Files:**

- Create: `backend/apps/intake/management/commands/purge_expired_data.py`
- Create: `backend/apps/intake/tests/test_purge_expired_data.py`

- [ ] **Step 1: Write the failing test**

Create `backend/apps/intake/tests/test_purge_expired_data.py`:

```python
"""Tests for the purge_expired_data retention command."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.intake.models import IntakeSession
from apps.documents.models import UploadedDocument

pytestmark = pytest.mark.django_db


def _backdate(queryset, **fields):
    """Set auto_now_add/managed timestamps by going around the ORM's auto fields."""
    queryset.update(**fields)


def test_purges_expired_documents_and_keeps_fresh(django_user_model, district, make_session):
    now = timezone.now()
    session = make_session()  # fixture: a session with required FKs

    expired = UploadedDocument.objects.create(
        session=session,
        uploaded_by=session.user,
        document_type="creditor_bill",
        user_declared_type="creditor_bill",
        file="documents/2025/01/old.pdf",
        original_filename="old.pdf",
        file_size=10,
        mime_type="application/pdf",
        delete_after=now - timedelta(days=1),
    )
    fresh = UploadedDocument.objects.create(
        session=session,
        uploaded_by=session.user,
        document_type="creditor_bill",
        user_declared_type="creditor_bill",
        file="documents/2026/06/new.pdf",
        original_filename="new.pdf",
        file_size=10,
        mime_type="application/pdf",
        delete_after=now + timedelta(days=10),
    )

    call_command("purge_expired_data", stdout=StringIO())

    assert not UploadedDocument.objects.filter(pk=expired.pk).exists()
    assert UploadedDocument.objects.filter(pk=fresh.pk).exists()


def test_purges_abandoned_and_completed_sessions_by_window(make_session, settings):
    settings.RETENTION_ABANDONED_DAYS = 30
    settings.RETENTION_COMPLETED_DAYS = 90
    now = timezone.now()

    abandoned_old = make_session()
    IntakeSession.objects.filter(pk=abandoned_old.pk).update(
        created_at=now - timedelta(days=31), completed_at=None
    )
    abandoned_recent = make_session()
    IntakeSession.objects.filter(pk=abandoned_recent.pk).update(
        created_at=now - timedelta(days=5), completed_at=None
    )
    completed_old = make_session()
    IntakeSession.objects.filter(pk=completed_old.pk).update(
        completed_at=now - timedelta(days=91)
    )

    call_command("purge_expired_data", stdout=StringIO())

    assert not IntakeSession.objects.filter(pk=abandoned_old.pk).exists()
    assert IntakeSession.objects.filter(pk=abandoned_recent.pk).exists()
    assert not IntakeSession.objects.filter(pk=completed_old.pk).exists()


def test_dry_run_deletes_nothing(make_session):
    now = timezone.now()
    s = make_session()
    IntakeSession.objects.filter(pk=s.pk).update(created_at=now - timedelta(days=999))

    out = StringIO()
    call_command("purge_expired_data", "--dry-run", stdout=out)

    assert IntakeSession.objects.filter(pk=s.pk).exists()
    assert "DRY RUN" in out.getvalue()
```

> If a `make_session`/`district` fixture does not already exist in `apps/intake/tests/conftest.py`, add a minimal one there that creates a `User`, a `District` (ID 1 / ILND via the existing fixture), and an `IntakeSession`. Reuse the existing test fixtures from the intake test suite — do not invent new model shapes.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest apps/intake/tests/test_purge_expired_data.py -v`
Expected: FAIL — `CommandError: Unknown command: 'purge_expired_data'`.

- [ ] **Step 3: Implement the command**

Create `backend/apps/intake/management/commands/purge_expired_data.py`:

```python
"""Permanently delete intake data and uploaded documents past their retention window.

DRAFT retention policy — windows are configurable via settings and pending legal
review (see docs/internal/data-retention-legal-review.md). Run daily in production
via Heroku Scheduler:  python manage.py purge_expired_data
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.documents.models import UploadedDocument
from apps.intake.models import IntakeSession

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete intake sessions and uploaded documents past their retention window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without deleting anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()
        abandoned_days = getattr(settings, "RETENTION_ABANDONED_DAYS", 30)
        completed_days = getattr(settings, "RETENTION_COMPLETED_DAYS", 90)

        expired_docs = UploadedDocument.objects.filter(delete_after__lt=now)
        abandoned = IntakeSession.objects.filter(
            completed_at__isnull=True,
            created_at__lt=now - timedelta(days=abandoned_days),
        )
        completed = IntakeSession.objects.filter(
            completed_at__isnull=False,
            completed_at__lt=now - timedelta(days=completed_days),
        )

        doc_count = expired_docs.count()
        abandoned_count = abandoned.count()
        completed_count = completed.count()

        prefix = "DRY RUN — would delete" if dry_run else "Deleting"
        self.stdout.write(
            f"{prefix}: {doc_count} expired document(s), "
            f"{abandoned_count} abandoned session(s) (> {abandoned_days}d), "
            f"{completed_count} completed session(s) (> {completed_days}d)."
        )

        if dry_run:
            return

        with transaction.atomic():
            # 1) Remove file bytes for standalone expired documents, then rows.
            self._delete_files(expired_docs)
            expired_docs.delete()

            # 2) Sessions cascade-delete their child PII rows AND document rows,
            #    but Django does NOT delete FileField bytes on cascade — remove
            #    those files explicitly before deleting the sessions.
            purged_sessions = abandoned.union(completed)
            session_ids = list(purged_sessions.values_list("id", flat=True))
            self._delete_files(
                UploadedDocument.objects.filter(session_id__in=session_ids)
            )
            IntakeSession.objects.filter(id__in=session_ids).delete()

        logger.info(
            "purge_expired_data: deleted %d docs, %d abandoned, %d completed sessions",
            doc_count,
            abandoned_count,
            completed_count,
        )
        self.stdout.write(self.style.SUCCESS("Retention purge complete."))

    def _delete_files(self, queryset):
        """Delete the stored file for each document (no-op if already gone)."""
        for doc in queryset.iterator():
            if doc.file:
                doc.file.delete(save=False)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest apps/intake/tests/test_purge_expired_data.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the full intake + documents suites for regressions**

Run: `cd backend && python -m pytest apps/intake apps/documents -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/intake/management/commands/purge_expired_data.py backend/apps/intake/tests/test_purge_expired_data.py backend/apps/intake/tests/conftest.py
git commit -m "feat(retention): purge_expired_data command enforces retention windows

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Honest, draft-flagged retention copy in the Terms page

**Files:**

- Modify: `frontend/src/pages/TermsPage.tsx`

- [ ] **Step 1: Add a retention section whose numbers match the settings defaults**

In `frontend/src/pages/TermsPage.tsx`, add a section (matching the existing `.legal-*` section markup already in the file). The figures (22 / 30 / 90 days) MUST equal the model default and `RETENTION_ABANDONED_DAYS` / `RETENTION_COMPLETED_DAYS`:

```tsx
<section className="legal-section">
  <h2 className="legal-section-title">How long we keep your information</h2>
  <p>We keep your information only as long as needed to provide this service:</p>
  <ul className="legal-list">
    <li>Documents you upload are deleted automatically about 22 days after upload.</li>
    <li>If you start but don’t finish an intake, we delete it after about 30 days.</li>
    <li>Completed intakes are deleted after about 90 days.</li>
  </ul>
  <p className="legal-note">
    These retention periods are a <strong>draft</strong> and may change pending legal review before
    this service is offered to the general public.
  </p>
</section>
```

- [ ] **Step 2: Typecheck + tests**

Run: `cd frontend && npx tsc --noEmit && npx vitest run src/pages/__tests__`
Expected: tsc clean; existing page tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/TermsPage.tsx
git commit -m "docs(retention): state draft retention windows in Terms (pending review)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Document the deferred legal-review gate

**Files:**

- Create: `docs/internal/data-retention-legal-review.md`

- [ ] **Step 1: Write the legal-review checklist**

Create `docs/internal/data-retention-legal-review.md`:

```markdown
# Data Retention — Legal Review Gate (DEFERRED until pre-public-launch)

**Status:** Retention is _operationally enforced_ (see `purge_expired_data`) with
draft windows. The items below MUST be reviewed and signed off by qualified legal
counsel **before** the service is made available to the general public.

## Draft windows currently enforced

- Uploaded documents: ~22 days after upload (`UploadedDocument.delete_after`).
- Abandoned intakes: 30 days after creation (`RETENTION_ABANDONED_DAYS`).
- Completed intakes: 90 days after completion (`RETENTION_COMPLETED_DAYS`).

## Must clear before public launch

- [ ] Are these windows defensible for bankruptcy-related PII (SSN, income, creditors)?
- [ ] Right-to-deletion: do users have an on-request deletion path (CCPA / state law)?
- [ ] Completeness: does deletion reach backups, logs, audit records, and any
      derived data (OCR extractions, generated PDFs)?
- [ ] Do we need to retain anything for a minimum period (e.g., filing records)?
- [ ] Breach-notification obligations and timelines.
- [ ] Reconcile this copy with the Terms page retention section (numbers must match).
- [ ] UPL review of all retention-related user-facing language.

## Operational notes

- Schedule in production: Heroku Scheduler → daily `python manage.py purge_expired_data`.
- Verify safely first with `python manage.py purge_expired_data --dry-run`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/internal/data-retention-legal-review.md
git commit -m "docs(retention): record deferred legal-review gate for public launch

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Wire production scheduling + document ops

**Files:**

- Modify: project `CLAUDE.md` (Gotchas/ops)

- [ ] **Step 1: Provision Heroku Scheduler (out-of-band, requires the user)**

This needs the user's Heroku credentials — surface it as a manual step, do not attempt to run it autonomously:

```
heroku addons:create scheduler:standard -a <app>
heroku addons:open scheduler -a <app>
# Add job: `python manage.py purge_expired_data`, daily.
```

- [ ] **Step 2: Add an ops note to CLAUDE.md**

Add under "Gotchas" (or a new "Ops" subsection):

```markdown
- **Data retention is enforced by a scheduled command, not the app** — `python manage.py purge_expired_data` (daily via Heroku Scheduler) hard-deletes expired uploaded documents and intake sessions (cascading PII). Windows: docs ~22d, abandoned intakes `RETENTION_ABANDONED_DAYS` (30), completed `RETENTION_COMPLETED_DAYS` (90). Django does NOT delete FileField bytes on cascade, so the command removes files explicitly. Policy is DRAFT pending legal review (`docs/internal/data-retention-legal-review.md`). Dry-run first: `--dry-run`.
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(retention): document purge command + Heroku Scheduler setup

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Checklist (run before handing off)

1. **Spec coverage:** retention _enforced_ operationally (Tasks 1–2) ✓; _included now_ with messaging (Task 3) ✓; legal review _deferred but tracked_ (Task 4) ✓; scheduling documented (Task 5) ✓.
2. **Placeholder scan:** the settings path is discovered via grep (Task 1 Step 1), not hard-coded; the `make_session` fixture instruction says reuse existing intake fixtures. Confirm those before writing.
3. **Number consistency:** 22 / 30 / 90 appear identically in settings defaults, the command behavior, the Terms copy, the legal-review doc, and the CLAUDE.md note. If you change a window, change all five.
4. **File-bytes deletion:** the command deletes `FileField` files for BOTH standalone expired documents AND documents belonging to cascade-deleted sessions — confirm both `_delete_files` calls are present.
5. **Safety:** all deletions are inside a single `transaction.atomic()`; `--dry-run` returns before any deletion.
