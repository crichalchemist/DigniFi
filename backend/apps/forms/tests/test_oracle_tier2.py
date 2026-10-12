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
