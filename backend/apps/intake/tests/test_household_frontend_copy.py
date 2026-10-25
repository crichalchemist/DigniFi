"""
Step 1's county list is typed twice, once in the server (ILND_COUNTIES) and once in the
wizard's constants. A county spelled differently on one side would make every step 1 save a
400, so this pins the two lists to each other.
"""

import re

import pytest
from django.conf import settings

from apps.districts.counties import ILND_COUNTIES

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


def test_step_one_offers_the_counties_the_server_takes():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    text = (FRONTEND / "constants" / "counties.ts").read_text()
    assert re.findall(r"^  '([^']+)',$", text, re.M) == list(ILND_COUNTIES)
