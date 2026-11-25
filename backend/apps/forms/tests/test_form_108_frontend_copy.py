"""
Your Plans shows Form 108's own words beside DigniFi's (forms step 4e, R-FORM-WORDS): the title, the
deadline sentence (E6), the Part headings, the column heads, the four choices, Part 2's sentence and
the labels each row's name and property sit under. They live in formText.ts, unscored, because
they are the form's words and not DigniFi's to simplify, so each must be found on the template as
written: a word changed on the step would put words in the form's mouth.
"""

import re

import pypdf
import pytest

from apps.intake.tests.test_petition_frontend_copy import (
    FRONTEND,
    PDFS,
    _form_text_strings,
    _squeezed,
    _string_record,
)

TEMPLATE = "form_b108.pdf"

# Every formText.ts constant named FORM_108_ is a quotation of Form 108 and must be listed here
OWNED = re.compile(r"^export const (FORM_108_\w*)\b", re.M)

QUOTES = [
    "FORM_108_TITLE",
    "FORM_108_DEADLINE",
    "FORM_108_PART_1_HEADING",
    "FORM_108_INTENTION_QUESTION",
    "FORM_108_INTENTIONS",
    "FORM_108_EXEMPT_QUESTION",
    "FORM_108_CREDITOR_LABEL",
    "FORM_108_PROPERTY_LABEL",
    "FORM_108_PART_2_HEADING",
    "FORM_108_ASSUME_SENTENCE",
    "FORM_108_ASSUMED_QUESTION",
    "FORM_108_ASSUMED",
    "FORM_108_LESSOR_LABEL",
    "FORM_108_LEASED_PROPERTY_LABEL",
]


@pytest.fixture(autouse=True)
def _frontend_is_here():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")


def _pages() -> list[str]:
    return [page.extract_text() for page in pypdf.PdfReader(PDFS / TEMPLATE).pages]


def test_every_form_108_quote_is_pinned():
    # A new quotation of Form 108 can't reach the step unread against its template
    source = (FRONTEND / "constants" / "formText.ts").read_text()
    assert sorted(OWNED.findall(source)) == sorted(QUOTES)


@pytest.mark.parametrize("name", QUOTES)
def test_the_plans_words_are_the_forms_own(name):
    # The text layer splits words ("Reaffir mation", "infor mation"), so the words are compared with
    # no spaces at all, across both pages; a record's values are each one quotation
    text_layer = _squeezed(" ".join(_pages()))
    for text in _form_text_strings(name):
        assert _squeezed(text) in text_layer, f"{name}: {text!r} is not on {TEMPLATE}"


def test_the_revision_the_wizard_names_is_the_one_form_108_prints():
    mark = re.search(
        r"^Statement of Intention for Individuals Filing Under Chapter 7 (\d{2}/\d{2}) *$",
        _pages()[0],
        re.M,
    )
    assert mark, "Form 108's page 1 has no title line with an edition mark"
    revisions = _string_record(FRONTEND / "constants" / "formText.ts", "FORM_REVISIONS")
    assert revisions["form_108"] == mark.group(1) == "12/15"
