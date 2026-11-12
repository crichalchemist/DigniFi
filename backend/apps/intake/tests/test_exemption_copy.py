"""The exemption page's own sentences (3g spec §5, plan 3g1 Task 1).

Business intent: every sentence DigniFi writes about a law is information about the law, never
a word to the filer and never a dollar figure that could read as a number to enter. Each is
marked for counsel's review, and each law in force has a summary.
"""

import re

import pytest
from django.conf import settings

from apps.districts.exemptions import exemption_catalog_in_force

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"
# Later tasks extend this with each marked sentence they add.
DRAFT_NAMES = ["EXEMPTION_LAW_SUMMARIES"]


def _copy_source() -> str:
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    return (FRONTEND / "constants" / "copy.ts").read_text()


def _copy_sentence(name: str) -> str:
    """A sentence from the wizard's copy.ts."""
    found = re.search(rf"export const {name} =\s*(['\"])(.*?)\1;", _copy_source(), re.DOTALL)
    assert found, name
    return found.group(2)


def _summaries_block() -> str:
    found = re.search(
        r"export const EXEMPTION_LAW_SUMMARIES: Record<string, string> = \{(.*?)\n\};",
        _copy_source(),
        re.DOTALL,
    )
    assert found
    return found.group(1)


def _summaries() -> dict[str, str]:
    # Each entry is `key: 'text',` or `key:\n    'text',` in single or double quotes.
    pairs = re.findall(r"^\s+(\w+):\s*(['\"])(.*?)\2,\s*$", _summaries_block(), re.M | re.S)
    return {key: text for key, _quote, text in pairs}


@pytest.mark.django_db
def test_every_law_in_force_has_a_summary_and_every_summary_a_law():
    keys = set(re.findall(r"^\s+(\w+):", _summaries_block(), re.M))

    assert keys == {law.key for law in exemption_catalog_in_force().laws.all()}
    assert set(_summaries()) == keys


def test_no_law_summary_speaks_to_the_filer_or_names_a_dollar_figure():
    # B4: the catalog's limit sentence gives the figures, and no summary says "you".
    summaries = _summaries()
    assert summaries
    for key, text in summaries.items():
        assert not re.search(r"\byou\b", text, re.I), key
        assert "$" not in text, key


def test_every_exemption_law_sentence_is_marked_draft_for_counsel():
    # P17: counsel reads every sentence DigniFi writes about a law.
    lines = _copy_source().splitlines()
    for name in DRAFT_NAMES:
        index = next(i for i, line in enumerate(lines) if line.startswith(f"export const {name}"))
        assert lines[index - 1] == "// DRAFT: counsel C-8", name


@pytest.mark.parametrize(
    "name",
    [
        "EXEMPTION_GAP_LINE_1",
        "EXEMPTION_GAP_NO_CLAIMS",
        "EXEMPTION_GAP_NO_ITEMS",
        "EXEMPTION_GAP_ITEM_GONE",
        "EXEMPTION_GAP_LAW",
        "EXEMPTION_GAP_LAW_CHANGED",
        "EXEMPTION_GAP_AMOUNT_KIND",
        "EXEMPTION_GAP_AMOUNT",
        "EXEMPTION_GAP_DESCRIPTION",
        "EXEMPTION_GAP_LINE_3",
        "EXEMPTION_GAP_LINE_3_1",
    ],
)
def test_the_page_and_the_server_word_each_gap_alike(name):
    from apps.intake import exemptions

    assert _copy_sentence(name) == getattr(exemptions, name)
