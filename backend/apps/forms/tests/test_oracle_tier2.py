"""
Oracle tier 2: each binding targets the box the verified audit says it should (spec §6).

A case is keyed on its box and its binding key, `<source>:<producer>` (step 2
spec §7.2), so a binding re-ruled in place or moved onto a listed box is a new
case and never keeps an old verdict. Bindings join their audit rows through the
conversion report's old→new name map, on (box, key). A binding is asserted only
where the audit was checked against the page image: a verification.json row, or
an index basis of adjudicated or sampled_ok on the row's own box. With no row
for its box and key, a binding that a checked row with its key places on this
box was moved here, and passes; a constant never was. Everything else is
unverified and not asserted.
"""

import json
import re
from functools import cache

import pytest
from django.conf import settings

from apps.forms.field_index import load_index
from apps.forms.registry import get_all_form_types
from apps.forms.schema import FieldSpec, load_schema
from apps.forms.tests.oracle import case_param

TIER = "2"
CHECKED_BASES = {"adjudicated", "sampled_ok"}
LEAVE_BLANK = "leave blank"
ASSERTED_CASES = 425


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


def _binding_key(binding):
    """`<source>:<producer>`, the producer empty for signature and presume (step 2 spec §7.2)."""
    if binding.source in ("signature", "presume"):
        return f"{binding.source}:"
    producer = binding.rule or binding.binding or binding.value or binding.ingest_key or ""
    return f"{binding.source}:{producer}"


def _audit_key(row):
    """An audit row's producer spelled as a binding key (step 2 spec §7.2)."""
    producer = re.sub(r"^(rule:|rule |binding:|ingest_key:)", "", row["producer"])
    producer = re.sub(r" \(.*\)$", "", producer)
    return f"{row['source']}:{'' if producer == row['source'] else producer}"


def _checked(form_type, old):
    """(target, verdicts) of the audit row on box `old`, or None if nobody checked it."""
    verified = _verification().get((form_type, old))
    if verified:
        target, verdicts = verified["correct_target"], verified["final_verdicts"]
    else:
        row = _audit(form_type)[old]
        box = _renamed(form_type).get(old, old)
        widgets = load_index(load_schema(form_type).template_filename).get(box, ())
        if not {w.basis for w in widgets} & CHECKED_BASES:
            return None
        target, verdicts = row["correct_target"], row["verdicts"]
    # "Executed on (needs filler change: ...)" → "Executed on"
    return re.sub(r"\s*\(.*\)$", "", target or ""), verdicts


def _expected_target(form_type, binding):
    """The full name the audit wants, LEAVE_BLANK, None for "not this box", or "" if unasserted."""
    pdf_field, key = binding.pdf_field, _binding_key(binding)
    old = {new: old for old, new in _renamed(form_type).items()}.get(pdf_field, pdf_field)
    row = _audit(form_type).get(old)
    if row is not None and _audit_key(row) == key:
        checked = _checked(form_type, old)
        if checked is None:
            return ""
        target, verdicts = checked
        if not target:
            # Right box when the audit found no box fault; a wrong box with no recorded target.
            return None if "wrong_box" in verdicts else pdf_field
        return target
    # Moved here. A constant is excluded: a /Yes the audit placed for one question
    # proves nothing about another.
    if binding.source != "constant":
        for other, other_row in _audit(form_type).items():
            if _audit_key(other_row) != key:
                continue
            checked = _checked(form_type, other)
            if checked and checked[0] == pdf_field:
                return pdf_field
    return ""


def _cases():
    for form_type in get_all_form_types():
        for f in load_schema(form_type).fields:
            target = _expected_target(form_type, f)
            if target != "":
                yield case_param(form_type, f.pdf_field, TIER, _binding_key(f), target)


CASES = list(_cases())


@pytest.mark.parametrize("form_type,pdf_field,case,target", CASES)
def test_binding_targets_the_box_the_audit_verified(form_type, pdf_field, case, target):
    assert target != LEAVE_BLANK, "wrong_box: the audit says this box stays blank"
    assert target is not None, "wrong_box: the audit says this is the wrong box"
    assert pdf_field == target, f"wrong_box: the audit says it belongs in {target!r}"


def test_tier2_coverage_changes_only_on_purpose():
    # A review tripwire, not a correctness test (step 2 spec §7.4): a commit that
    # changes how many cases tier 2 asserts updates ASSERTED_CASES and says why.
    assert len(CASES) == ASSERTED_CASES, "tier 2 coverage changed: update ASSERTED_CASES on purpose"


def _field(**kw):
    # Built from literals that match the audit row, not read from the schema, so
    # these tests outlive 2b moving or deleting the bindings they describe. Every
    # producer starts empty: _binding_key takes the first one that isn't.
    base = {
        "pdf_field": "F",
        "type": "text",
        "source": "derived",
        "page": 1,
        "label": "",
        "required": False,
        "conditional_on": None,
        "value": None,
        "rule": None,
        "ingest_key": None,
        "binding": None,
        "repeat": None,
        "repeat_capacity": None,
        "row": None,
        "legal_review": False,
    }
    base.update(kw)
    return FieldSpec(**base)


def test_a_binding_re_ruled_in_place_does_not_inherit_the_old_verdict():
    # The audit judged rent on Schedule J box 10 (Personal care); another rule there is unjudged.
    re_ruled = _field(pdf_field="10", rule="schedule_j_personal_care")
    assert _expected_target("schedule_j", re_ruled) == ""


def test_a_binding_moved_to_the_box_the_audit_named_is_asserted_and_passes():
    # The audit's checked row says rent belongs on line 4, which has no audit row of its own.
    moved = _field(pdf_field="4", rule="schedule_j_rent_or_mortgage")
    assert _expected_target("schedule_j", moved) == "4"


def test_a_binding_moved_to_a_box_the_audit_did_not_name_stays_unasserted():
    # That checked row names line 4, not line 7, which has no audit row of its own either.
    moved = _field(pdf_field="7", rule="schedule_j_rent_or_mortgage")
    assert _expected_target("schedule_j", moved) == ""


def test_a_constant_the_audit_placed_elsewhere_proves_nothing_here():
    # The audit moved Form 101's /Yes from Check Box16 to Check Box18 for one question only.
    constant = _field(pdf_field="Check Box18", type="checkbox", source="constant", value="/Yes")
    assert _expected_target("form_101", constant) == ""


@pytest.mark.parametrize(
    "producer,rule",
    [
        ("rule district_name", "district_name"),  # Form 107
        ("rule:full_name (conditional_on has_joint_filer)", "full_name"),  # Schedules G-J
    ],
)
def test_an_audit_row_spelled_loosely_joins_the_binding_it_names(producer, rule):
    row = {"source": "derived", "producer": producer}
    assert _audit_key(row) == _binding_key(_field(rule=rule))
