"""
The filing-fee page stops each text at the length its box on Form 103B can print. The limits
are measured once, on FilingFee (3f spec §6.4), and copied into the page's constants: a copy
that drifted would let the page send a text the server refuses, or cut one the box would print.
"""

import re

import pytest
from django.conf import settings

from apps.intake.models import FilingFee

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


def test_the_filing_fee_page_stops_each_text_where_its_box_does():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    text = (FRONTEND / "constants" / "filingFee.ts").read_text()
    copied = {key: int(n) for key, n in re.findall(r"^  (\w+): (\d+),$", text, re.M)}
    assert copied == dict(FilingFee.TEXT_LIMITS)
