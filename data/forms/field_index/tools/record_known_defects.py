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
        rows = _audit(form_type).get(old, [])
        cited = re.findall(r"DIG-\d+", " ".join(r.get("known") or "" for r in rows))
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
