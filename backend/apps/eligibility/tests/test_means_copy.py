"""
The server's two refusal sentences for the means test are also the browser's: the filer reads
`FORM_122A2_CANT_PRINT_YET` and `NO_MEANS_TEST_TABLE` on the dashboard in `copy.ts`'s words, and
`upl-means-test-copy.test.ts` scores the words the filer sees. A sentence reworded on one side
only would put two different sentences in front of the filer for one refusal (3h1 plan R8).
"""

import re

import pytest
from django.conf import settings

from apps.districts.means_standards import NO_MEANS_TEST_TABLE
from apps.forms.registry import FORM_122A2_CANT_PRINT_YET
from apps.forms.services.means_cells import LINE_43_POINTER

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


def _copy_sentence(name: str) -> str:
    text = (FRONTEND / "constants" / "copy.ts").read_text()
    match = re.search(rf"^export const {name} =\s*(?:'([^'\n]*)'|\"([^\"\n]*)\");$", text, re.M)
    assert match, f"copy.ts has no single-literal `export const {name}`"
    return match.group(1) if match.group(1) is not None else match.group(2)


@pytest.mark.parametrize(
    ("name", "server_sentence"),
    [
        ("MEANS_CANT_PRINT_YET", FORM_122A2_CANT_PRINT_YET),
        ("MEANS_TABLE_MISSING", NO_MEANS_TEST_TABLE),
        ("MEANS_LINE_43_POINTER", LINE_43_POINTER),
    ],
)
def test_the_dashboard_reads_the_refusal_the_server_sends(name, server_sentence):
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")

    assert _copy_sentence(name) == server_sentence
