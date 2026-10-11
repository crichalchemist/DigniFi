"""
The known-defects list names only defects the oracle still finds (spec §6).

A strict xfail already fails when a listed defect is fixed. These tests catch
the other way an entry goes stale: its case no longer exists (a binding was
renamed or removed), or it lacks a defect class and ticket.
"""

import re

from apps.forms.tests import test_oracle_tier1 as tier1
from apps.forms.tests import test_oracle_tier2 as tier2
from apps.forms.tests import test_oracle_tier3 as tier3
from apps.forms.tests.oracle import DEFECT_CLASSES, KNOWN_DEFECTS

ORACLE_CASES = {
    "1": tier1.TEXT_CASES + tier1.BOX_CASES + tier1.UNMAPPED_CASES,
    "2": tier2.CASES,
    "3": tier3.CASES,
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
