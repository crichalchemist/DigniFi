"""
Health check and metrics views for DigniFi.

Provides liveness (/health/), detailed readiness (/health/detailed/),
and admin-only metrics (/metrics/) endpoints.
"""

import shutil
import time
from collections import Counter
from functools import reduce
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.db.models import Count
from django.http import JsonResponse


# Module-level start time — captured once when the process loads.
_START_TIME = time.monotonic()

# Application version — bump on each release.
VERSION = "0.2.0"


def _check_database() -> dict:
    """Pure check: database connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_disk_space(directory: Path) -> dict:
    """Pure check: disk space for a given directory."""
    try:
        usage = shutil.disk_usage(str(directory))
        free_mb = usage.free / (1024 * 1024)
        total_mb = usage.total / (1024 * 1024)
        return {
            "status": "ok" if free_mb > 100 else "warning",
            "free_mb": round(free_mb, 1),
            "total_mb": round(total_mb, 1),
            "percent_used": round((usage.used / usage.total) * 100, 1),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_uptime() -> dict:
    """Pure check: process uptime in seconds."""
    uptime_seconds = round(time.monotonic() - _START_TIME, 1)
    return {"status": "ok", "uptime_seconds": uptime_seconds}


def health_check(request):
    """Lightweight liveness probe — checks DB only."""
    db = _check_database()
    overall = "ok" if db["status"] == "ok" else "error"

    return JsonResponse({
        "status": overall,
        "database": db["status"],
    })


def health_check_detailed(request):
    """Comprehensive readiness probe — DB, disk, version, uptime."""
    checks = {
        "database": _check_database(),
        "disk_generated_forms": _check_disk_space(
            getattr(settings, "PDF_OUTPUT_DIRECTORY", Path("/tmp"))
        ),
        "disk_media": _check_disk_space(
            getattr(settings, "MEDIA_ROOT", Path("/tmp"))
        ),
        "uptime": _check_uptime(),
    }

    statuses = [c["status"] for c in checks.values()]
    overall = reduce(
        lambda acc, s: "error" if s == "error" else ("warning" if s == "warning" else acc),
        statuses,
        "ok",
    )

    return JsonResponse({
        "status": overall,
        "version": VERSION,
        "checks": checks,
    })


def _collect_session_metrics() -> dict:
    """Aggregate intake session counts by status."""
    from apps.intake.models import IntakeSession

    counts = dict(
        IntakeSession.objects.values_list("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )
    return {
        "active": counts.get("started", 0) + counts.get("in_progress", 0),
        "completed": counts.get("completed", 0),
        "abandoned": counts.get("abandoned", 0),
        "total": sum(counts.values()),
    }


def _collect_form_metrics() -> dict:
    """Aggregate generated form counts by type and status."""
    from apps.forms.models import GeneratedForm

    by_type = dict(
        GeneratedForm.objects.values_list("form_type")
        .annotate(count=Count("id"))
        .values_list("form_type", "count")
    )
    by_status = dict(
        GeneratedForm.objects.values_list("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )
    return {
        "by_type": by_type,
        "by_status": by_status,
        "total": sum(by_type.values()),
    }


@staff_member_required
def metrics(request):
    """Admin-only metrics: sessions, forms, uptime."""
    return JsonResponse({
        "version": VERSION,
        "uptime": _check_uptime(),
        "sessions": _collect_session_metrics(),
        "forms": _collect_form_metrics(),
    })
