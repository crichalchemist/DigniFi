"""
Step 1's county list is typed twice, once in the server (ILND_COUNTIES) and once in the
wizard's constants. A county spelled differently on one side would make every step 1 save a
400, so this pins the two lists to each other. The household list's relationship words are
pinned the same way, since the step's list and the forms print one map (3e1 spec §4.2).
"""

import re

import pytest
from django.conf import settings

from apps.districts.counties import ILND_COUNTIES
from apps.intake.household import RELATIONSHIP_WORDS

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


def test_step_one_offers_the_counties_the_server_takes():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    text = (FRONTEND / "constants" / "counties.ts").read_text()
    assert re.findall(r"^  '([^']+)',$", text, re.M) == list(ILND_COUNTIES)


def test_the_income_step_offers_the_words_the_forms_print():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    text = (FRONTEND / "constants" / "household.ts").read_text()
    assert re.findall(r"^  (\w+): '([^']+)',$", text, re.M) == list(RELATIONSHIP_WORDS.items())
