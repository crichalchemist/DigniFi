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
