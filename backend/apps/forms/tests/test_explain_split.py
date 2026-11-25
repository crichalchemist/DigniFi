"""
Form 108's "[explain]" words across its two boxes (forms step 4e, 4e-R5, R-EXPLAIN).

Business intent: the filer's own words print whole, in the order typed, across Explain1 (a short
box after the printed "Retain the property and [explain]:") and Explain2 (the line under it). The
break falls only at a space, so no word is cut, and Explain1 takes as many leading words as it can
print, so the second box never starts with words the first had room for.
"""

import pytest

from apps.forms.services.explain_split import _fits_explain_1, split_explain

# Twenty synthetic texts: short and long, one word and many, a double space, a word wider than
# Explain1, and words with leading and trailing spaces.
TEXTS = [
    "I will keep paying.",
    "Keep",
    "My brother Mateo, the co-owner, keeps paying the loan.",
    "I am current on the mortgage and will keep paying as agreed",
    "Pay  as agreed",
    "Supercalifragilisticexpialidocious and more",
    "A b c d e f g h i j k l m n o p q r s t u v w x y z",
    "I keep it",
    "Demo words that run long enough to need both boxes on the form",
    "12345 67890 12345",
    "Keep the car and keep paying the lender every month",
    "x",
    "Two words",
    "The co-owner pays",
    " leading space kept",
    "trailing space kept ",
    "Continue paying the lender under the contract terms",
    "WWWWWWWW WWWW",
    "I will refinance",
    "Keep paying, as before.",
]


@pytest.mark.parametrize("text", TEXTS)
def test_the_split_keeps_every_word_and_breaks_only_at_a_space(text):
    first, second = split_explain(text)

    assert " ".join(part for part in (first, second) if part) == text
    if first and second:
        # The break is one space: neither half was cut inside a word.
        assert first + " " + second == text


@pytest.mark.parametrize("text", TEXTS)
def test_explain_1_holds_the_longest_run_of_words_that_fits_at_6_pt(text):
    first, second = split_explain(text)

    assert _fits_explain_1(first)
    if second:
        next_word = second.split(" ")[0]
        one_more = f"{first} {next_word}" if first else next_word
        assert not _fits_explain_1(one_more)


def test_a_first_word_too_wide_for_explain_1_leaves_it_blank():
    text = "Supercalifragilisticexpialidocious and more"
    assert not _fits_explain_1("Supercalifragilisticexpialidocious")

    assert split_explain(text) == ("", text)


def test_an_empty_text_splits_into_two_blanks():
    assert split_explain("") == ("", "")
