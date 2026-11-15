"""Every sentence the server sends the page or the dashboard is the sentence copy.ts holds."""

import re

import pytest

from apps.eligibility.tests.test_means_copy import FRONTEND, _copy_sentence
from apps.intake import means_test

COPY_TS = FRONTEND / "constants" / "copy.ts"
SERVER_GAPS = sorted(name for name in dir(means_test) if name.startswith("MEANS_GAP_"))
SERVER_SENTENCES = [
    *SERVER_GAPS,
    "MEANS_TOO_LONG",
    "MEANS_EXPLANATION_TOO_LONG",
    "MEANS_EXPLANATION_LETTER",
]


@pytest.fixture(autouse=True)
def _frontend_is_here():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")


@pytest.mark.parametrize("name", SERVER_SENTENCES)
def test_the_page_shows_the_sentence_the_server_sends(name):
    assert _copy_sentence(name) == getattr(means_test, name)


def test_copy_ts_has_exactly_the_servers_gaps_and_no_other_gap():
    names = re.findall(r"^export const (MEANS_GAP_[A-Z0-9_]+) =", COPY_TS.read_text(), re.M)
    assert sorted(names) == SERVER_GAPS
    assert len(names) == 41


def test_every_gap_carries_its_counsel_mark_on_the_line_above():
    lines = COPY_TS.read_text().split("\n")
    for number, line in enumerate(lines):
        match = re.match(r"export const (MEANS_GAP_[A-Z0-9_]+) =", line)
        if match is None:
            continue
        spouse = match.group(1).startswith("MEANS_GAP_SPOUSE_")
        expected = "// DRAFT: counsel C-34" if spouse else "// DRAFT: counsel C-24"
        assert lines[number - 1] == expected, match.group(1)
