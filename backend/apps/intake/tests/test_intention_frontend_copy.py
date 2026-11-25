"""
Your Plans asks Form 108's questions in the browser and the server judges them, so a few things are
typed on both sides: the sentences naming an open row (copy.ts, mirrored from intentions.py), the
choice words a save sends (types/api.ts, from IntentionAnswers and the exempt states), the
too-long notes' caps, boxes and labels (claimTextLimits.ts and copy.ts, from form_108.limits.json),
and the cases the two sides' gap helpers both run (intentionGapCases.json). A sentence worded
differently on one side tells the filer one thing on the step and another on Review; a choice
spelled differently makes every save of the step a 400.
"""

import json
import re

import pytest
from django.conf import settings

from apps.intake import exemptions, intentions, schedule_i
from apps.intake.models import IntentionAnswers
from apps.intake.tests.test_petition_frontend_copy import FRONTEND, _copy_sentences
from apps.intake.tests.test_schedule_i_frontend_copy import _quoted_record

CASES = FRONTEND / "components" / "wizard" / "steps" / "plans" / "intentionGapCases.json"
SCHEMAS = settings.BASE_DIR.parent / "data" / "forms" / "schemas"
PREFIXES = ("INTENTION_GAP_", "LEASE_GAP_")


@pytest.fixture(autouse=True)
def _frontend_is_here():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")


def _server_sentences() -> dict[str, str]:
    return {
        name: value
        for name, value in vars(intentions).items()
        if name.startswith(PREFIXES) and isinstance(value, str)
    }


def test_the_gap_sentences_are_the_browsers():
    # Both directions, so a sentence one side adds and the other lacks fails
    browser = {}
    for prefix in PREFIXES:
        browser |= _copy_sentences(prefix)
    assert browser == _server_sentences()
    # the five approved sentences (E7, E8), so a reader that matched nothing can't pass
    assert len(_server_sentences()) == 5


def _literals(name: str) -> tuple[str, ...]:
    """The single-quoted literals of one `export type NAME = 'a' | 'b';` union in types/api.ts."""
    source = (FRONTEND / "types" / "api.ts").read_text()
    match = re.search(rf"^export type {name} =(.*?);", source, re.M | re.S)
    assert match, f"api.ts has no {name}"
    return tuple(re.findall(r"'([^']+)'", match.group(1)))


def test_the_choice_words_are_the_browsers():
    assert _literals("Intention") == IntentionAnswers.INTENTIONS
    assert _literals("Assumed") == IntentionAnswers.ASSUMED
    exempt_states = tuple(
        value
        for name, value in vars(exemptions).items()
        if re.fullmatch(r"EXEMPT_[A-Z_]+", name) and isinstance(value, str)
    )
    assert len(exempt_states) == 5
    assert _literals("ExemptState") == exempt_states


def test_the_case_file_is_what_the_server_says():
    cases = json.loads(CASES.read_text())
    helpers = {"secured": intentions.intention_row_gap, "lease": intentions.lease_row_gap}
    for case in cases:
        sentence = helpers[case["kind"]](case["row"], case["entry"])
        expected = None if case["expect"] is None else getattr(intentions, case["expect"])
        expected = None if expected is None else expected.format(name=case["row"])
        assert sentence == expected, case["name"]
    # every sentence and "no gap" are each pinned on both sides
    assert {case["expect"] for case in cases} == {*_server_sentences(), None}


def test_the_browsers_caps_and_labels_are_the_tools():
    # Amounts Owed's, Contracts & Leases' and Your Plans' too-long notes count against these caps
    # and name these labels; a cap or a box list that drifted would show a note Review never lists,
    # or miss one it does
    limits = json.loads((SCHEMAS / "form_108.limits.json").read_text())
    source = (FRONTEND / "constants" / "claimTextLimits.ts").read_text()
    caps = re.search(r"^export const CLAIM_BOX_CAPS\b[^\n]*= \{\n(.*?)^\};", source, re.M | re.S)
    assert caps, "claimTextLimits.ts has no CLAIM_BOX_CAPS"
    pairs = re.findall(r"^  '([^']+)': (\d+),$", caps[1], re.M)
    browser_caps = {key: int(cap) for key, cap in pairs}
    assert browser_caps == limits["boxes"]
    assert len(browser_caps) == 11
    boxes = re.search(r"^export const ROW_BOXES\b[^\n]*= \{\n(.*?)^\};", source, re.M | re.S)
    assert boxes, "claimTextLimits.ts has no ROW_BOXES"
    browser_boxes = {
        tuple(key.split(":")): tuple(re.findall(r"'([^']+)'", keys))
        # a box key holds "[]" itself, so the list is read as quoted strings up to its own "]"
        for key, keys in re.findall(r"'(\w+:\w+)': \[((?:\s*'[^']+',?)+)\s*\]", boxes[1])
    }
    assert browser_boxes == intentions.ROW_BOXES
    # The forms a note names, in packet order: the order is the sentence's, so compared as a list
    words = re.search(r"^const FORM_WORDS\b[^\n]*= \{\n(.*?)^\};", source, re.M | re.S)
    assert words, "claimTextLimits.ts has no FORM_WORDS"
    browser_words = re.findall(r"^  (\w+): '([^']+)',$", words[1], re.M)
    assert browser_words == list(intentions.FORM_WORDS.items())
    assert len(browser_words) == 4
    labels = _quoted_record(FRONTEND / "constants" / "copy.ts", "CLAIM_TEXT_LABELS")
    assert labels == limits["labels"] == intentions.CLAIM_TEXT_LABELS
    assert set(labels) == set(intentions.CLAIM_TEXT_KEYS)


def test_the_too_long_sentence_is_the_schedule_i_one():
    # One string, one browser constant (SCHEDULE_I_DETAIL_TOO_LONG): the dashboard's blank count
    # already leaves it out
    assert intentions.DETAIL_TOO_LONG is schedule_i.DETAIL_TOO_LONG
    assert not any("TOO_LONG" in name for name in _server_sentences())
