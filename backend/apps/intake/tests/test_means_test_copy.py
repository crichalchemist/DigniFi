"""Every sentence the server sends the page or the dashboard is the sentence copy.ts holds."""

import re

import pytest

from apps.eligibility.tests.test_means_copy import FRONTEND, _copy_sentence
from apps.intake import means_page, means_test

COPY_TS = FRONTEND / "constants" / "copy.ts"
SERVER_GAPS = sorted(name for name in dir(means_test) if name.startswith("MEANS_GAP_"))
SERVER_SENTENCES = [
    *SERVER_GAPS,
    "MEANS_TOO_LONG",
    "MEANS_LETTER",
    "MEANS_EXPLANATION_TOO_LONG",
    "MEANS_EXPLANATION_LETTER",
    "MEANS_POLISH_IDENTIFIER",
    "MEANS_POLISH_PHRASE",
    "MEANS_POLISH_BLANK",
    "MEANS_POLISH_NO_REWRITE",
    "MEANS_POLISH_UNAVAILABLE",
]

# the page's reference sentences: the server sends them in a 400's body and the page reads them
# by their words (DIG-513), so they are pinned apart from the gaps
PAGE_SENTENCES = [
    ("MEANS_NOT_A_COUNTED_DEBT", means_page.NOT_A_COUNTED_DEBT),
    ("MEANS_NOT_A_LINE_11_VEHICLE", means_page.NOT_A_LINE_11_VEHICLE),
    ("MEANS_NOT_AN_OPEN_DEBT", means_page.NOT_AN_OPEN_DEBT),
]


@pytest.fixture(autouse=True)
def _frontend_is_here():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")


@pytest.mark.parametrize("name", SERVER_SENTENCES)
def test_the_page_shows_the_sentence_the_server_sends(name):
    assert _copy_sentence(name) == getattr(means_test, name)


@pytest.mark.parametrize(("name", "sentence"), PAGE_SENTENCES)
def test_the_page_shows_the_reference_sentence_the_server_sends(name, sentence):
    assert _copy_sentence(name) == sentence


@pytest.mark.parametrize("name", [name for name, _ in PAGE_SENTENCES])
def test_every_reference_sentence_carries_its_counsel_mark_on_the_line_above(name):
    lines = COPY_TS.read_text().split("\n")
    at = next(n for n, line in enumerate(lines) if line.startswith(f"export const {name} ="))
    assert lines[at - 1] == "// DRAFT: counsel C-24"


def test_copy_ts_has_exactly_the_servers_gaps_and_no_other_gap():
    names = re.findall(r"^export const (MEANS_GAP_[A-Z0-9_]+) =", COPY_TS.read_text(), re.M)
    assert sorted(names) == SERVER_GAPS
    assert len(names) == 42


def test_every_gap_carries_its_counsel_mark_on_the_line_above():
    lines = COPY_TS.read_text().split("\n")
    for number, line in enumerate(lines):
        match = re.match(r"export const (MEANS_GAP_[A-Z0-9_]+) =", line)
        if match is None:
            continue
        spouse = match.group(1).startswith("MEANS_GAP_SPOUSE_")
        expected = "// DRAFT: counsel C-34" if spouse else "// DRAFT: counsel C-24"
        assert lines[number - 1] == expected, match.group(1)


@pytest.mark.parametrize(
    ("name", "mark"),
    [
        ("MEANS_TOO_LONG", "// DRAFT: counsel C-24"),
        ("MEANS_LETTER", "// DRAFT: counsel C-24"),
        ("MEANS_EXPLANATION_TOO_LONG", "// DRAFT: counsel C-31"),
        ("MEANS_EXPLANATION_LETTER", "// DRAFT: counsel C-31"),
        ("MEANS_POLISH_IDENTIFIER", "// DRAFT: counsel C-33"),
        ("MEANS_POLISH_PHRASE", "// DRAFT: counsel C-33"),
        ("MEANS_POLISH_BLANK", "// DRAFT: counsel C-33"),
        ("MEANS_POLISH_NO_REWRITE", "// DRAFT: counsel C-33"),
        ("MEANS_POLISH_UNAVAILABLE", "// DRAFT: counsel C-33"),
    ],
)
def test_the_other_server_sentences_carry_their_counsel_mark_on_the_line_above(name, mark):
    lines = COPY_TS.read_text().split("\n")
    at = next(n for n, line in enumerate(lines) if line.startswith(f"export const {name} ="))
    assert lines[at - 1] == mark


def test_the_page_stops_offering_rows_where_the_server_stops_taking_them():
    page = FRONTEND / "pages" / "MeansTestPage.tsx"
    found = re.search(r"^const MAX_LIST_ROWS = (\d+);", page.read_text(), re.M)
    assert found is not None
    assert int(found.group(1)) == means_test.MAX_ROWS
