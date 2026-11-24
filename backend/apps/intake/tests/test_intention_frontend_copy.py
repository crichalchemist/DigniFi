"""
Your Plans asks Form 108's questions in the browser and the server judges them, so a few things are
typed on both sides: the sentences naming an open row (copy.ts, mirrored from intentions.py), the
choice words a save sends (types/api.ts, from IntentionAnswers and the exempt states), and the
cases the two sides' gap helpers both run (intentionGapCases.json). A sentence worded differently
on one side tells the filer one thing on the step and another on Review; a choice spelled
differently makes every save of the step a 400.
"""

import json
import re

import pytest

from apps.intake import exemptions, intentions, schedule_i
from apps.intake.models import IntentionAnswers
from apps.intake.tests.test_petition_frontend_copy import FRONTEND, _copy_sentences

CASES = FRONTEND / "components" / "wizard" / "steps" / "plans" / "intentionGapCases.json"
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


def test_the_too_long_sentence_is_the_schedule_i_one():
    # One string, one browser constant (SCHEDULE_I_DETAIL_TOO_LONG): the dashboard's blank count
    # already leaves it out
    assert intentions.DETAIL_TOO_LONG is schedule_i.DETAIL_TOO_LONG
    assert not any("TOO_LONG" in name for name in _server_sentences())
