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


def test_frontend_offers_exactly_the_payment_choices_the_server_accepts():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    server = set(FilingFee.PAYMENT_CHOICES)
    words = (FRONTEND / "constants" / "formText.ts").read_text()
    block = re.search(
        r"export const PAYMENT_CHOICE_WORDS: Record<PaymentChoice, string> = \{(.*?)^\};",
        words,
        re.M | re.S,
    )
    assert block, "PAYMENT_CHOICE_WORDS not found in formText.ts"
    assert set(re.findall(r"^  (\w+): ", block.group(1), re.M)) == server
    types = (FRONTEND / "types" / "api.ts").read_text()
    union = re.search(r"^export type PaymentChoice = ([^;]+);", types, re.M)
    assert union, "PaymentChoice not found in api.ts"
    assert set(re.findall(r"'(\w+)'", union.group(1))) == server
