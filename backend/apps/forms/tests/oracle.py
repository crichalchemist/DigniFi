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
