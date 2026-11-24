"""
The means pair's server sentences are also the browser's: `FORM_122A2_LINE_MISSING`,
`NO_MEANS_TEST_TABLE`, `MEANS_PAIR_REFUSAL`, `MEANS_SUPP_PAIR_REFUSAL` and
`FORM_122A2_MILITARY_OPEN` are read on the dashboard in `copy.ts`'s words,
`LINE_43_POINTER` is printed on the form and scored there, and `upl-means-test-copy.test.ts`
scores the words the filer sees. A sentence reworded on one side only would put two different
sentences in front of the filer for one refusal (3h1 plan R8). The Income step's gaps
(`apps/eligibility/cmi.py`) are the server's alone and are not pinned here. The browser's
`MeansOutcome` type is pinned to the server's `OUTCOMES` too.
"""

import re

import pytest
from django.conf import settings

from apps.districts.means_standards import NO_MEANS_TEST_TABLE
from apps.eligibility.means_lines import OUTCOMES
from apps.forms.registry import FORM_122A2_LINE_MISSING, FORM_122A2_MILITARY_OPEN
from apps.forms.services.means_cells import LINE_43_POINTER
from apps.forms.views import MEANS_PAIR_REFUSAL, MEANS_SUPP_PAIR_REFUSAL

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


def _copy_sentence(name: str) -> str:
    text = (FRONTEND / "constants" / "copy.ts").read_text()
    match = re.search(rf"^export const {name} =\s*(?:'([^'\n]*)'|\"([^\"\n]*)\");$", text, re.M)
    assert match, f"copy.ts has no single-literal `export const {name}`"
    return match.group(1) if match.group(1) is not None else match.group(2)


@pytest.mark.parametrize(
    ("name", "server_sentence"),
    [
        ("MEANS_LINE_MISSING", FORM_122A2_LINE_MISSING),
        ("MEANS_TABLE_MISSING", NO_MEANS_TEST_TABLE),
        ("MEANS_LINE_43_POINTER", LINE_43_POINTER),
        ("MEANS_PAIR_REFUSAL", MEANS_PAIR_REFUSAL),
        ("MEANS_SUPP_PAIR_REFUSAL", MEANS_SUPP_PAIR_REFUSAL),
        ("MEANS_MILITARY_OPEN", FORM_122A2_MILITARY_OPEN),
    ],
)
def test_the_dashboard_reads_the_refusal_the_server_sends(name, server_sentence):
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")

    assert _copy_sentence(name) == server_sentence


def test_the_browsers_outcome_type_is_the_servers():
    # Enum drift is silent at runtime (an outcome the browser doesn't know shows no words), so
    # `MeansOutcome` in api.ts holds exactly the outcomes the server stores (4d).
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")

    text = (FRONTEND / "types" / "api.ts").read_text()
    match = re.search(r"^export type MeansOutcome =([^;]*);", text, re.M)
    assert match, "api.ts has no `export type MeansOutcome`"
    assert set(re.findall(r"'([^']*)'", match.group(1))) == set(OUTCOMES)
