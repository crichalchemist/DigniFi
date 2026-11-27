"""
Form 108's "[explain]" words across its two boxes (forms step 4e, 4e-R5, R-EXPLAIN).

Explain1 is the short box after the printed "Retain the property and [explain]:", and Explain2 the
line under it. The four rows' Explain1 boxes are 50.5 pt wide to 0.1 pt, so row 1a's stands for
all four. Form 107 line 9's case title splits across its two boxes the same way (4f-i, R-15).
"""

TEMPLATE = "form_b108.pdf"
EXPLAIN_1 = "Explain1 1a"


def _fits(text: str, template: str, box: str) -> bool:
    """The text prints in the box, letters and size alike, down to 6 pt (check()'s own test)."""
    # Imported here: pdf_filler imports fill_resolver, whose CLAIM_CELLS imports this module.
    from functools import partial

    from apps.forms.services.pdf_filler import _as_printed, _refused_letter
    from apps.forms.services.text_fit import fit, font_for, printable
    from apps.forms.services.widgets import template_widgets

    (widget,) = [w for w in template_widgets(template) if w.full_name == box]
    printed = _as_printed(text)
    prints = partial(printable, font_for(template, widget.font))
    if _refused_letter(printed, prints, widget.comb) is not None:
        return False
    return fit(widget, template, printed) is not None


def _fits_explain_1(text: str) -> bool:
    """The text prints in Explain1, letters and size alike, down to 6 pt (check()'s own test)."""
    return _fits(text, TEMPLATE, EXPLAIN_1)


def split_at_box(text: str, template: str, box: str) -> tuple[str, str]:
    """The box takes the longest run of whole leading words that fits it, letters and size
    alike, down to 6 pt (check()'s own test, text_fit.fit); the second half takes the rest.
    A first word that doesn't fit leaves the first half blank. Spaces are split on as typed and
    the join drops only the one space at the break, so the non-blank halves joined by one space
    are the text: " ".join(p for p in split_at_box(text, template, box) if p) == text."""
    words = text.split(" ")
    cut = 0
    for n in range(1, len(words) + 1):
        if _fits(" ".join(words[:n]), template, box):
            cut = n
        else:
            break
    return " ".join(words[:cut]), " ".join(words[cut:])


def split_explain(text: str) -> tuple[str, str]:
    """Explain1 takes the longest run of whole leading words that fits its box (split_at_box);
    Explain2 takes the rest."""
    return split_at_box(text, TEMPLATE, EXPLAIN_1)
