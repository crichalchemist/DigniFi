"""
Form 108's "[explain]" words across its two boxes (forms step 4e, 4e-R5, R-EXPLAIN).

Explain1 is the short box after the printed "Retain the property and [explain]:", and Explain2 the
line under it. The four rows' Explain1 boxes are 50.5 pt wide to 0.1 pt, so row 1a's stands for
all four.
"""

TEMPLATE = "form_b108.pdf"
EXPLAIN_1 = "Explain1 1a"


def _fits_explain_1(text: str) -> bool:
    """The text prints in Explain1, letters and size alike, down to 6 pt (check()'s own test)."""
    # Imported here: pdf_filler imports fill_resolver, whose CLAIM_CELLS imports this module.
    from functools import partial

    from apps.forms.services.pdf_filler import _as_printed, _refused_letter
    from apps.forms.services.text_fit import fit, font_for, printable
    from apps.forms.services.widgets import template_widgets

    (widget,) = [w for w in template_widgets(TEMPLATE) if w.full_name == EXPLAIN_1]
    printed = _as_printed(text)
    prints = partial(printable, font_for(TEMPLATE, widget.font))
    if _refused_letter(printed, prints, widget.comb) is not None:
        return False
    return fit(widget, TEMPLATE, printed) is not None


def split_explain(text: str) -> tuple[str, str]:
    """Explain1 takes the longest run of whole leading words that fits its box, letters and
    size alike, down to 6 pt (check()'s own test, text_fit.fit); Explain2 takes the rest.
    A first word that doesn't fit leaves Explain1 blank. Spaces are split on as typed and the
    join drops only the one space at the break, so the non-blank halves joined by one space
    are the text: " ".join(p for p in split_explain(text) if p) == text."""
    words = text.split(" ")
    cut = 0
    for n in range(1, len(words) + 1):
        if _fits_explain_1(" ".join(words[:n])):
            cut = n
        else:
            break
    return " ".join(words[:cut]), " ".join(words[cut:])
