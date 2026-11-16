"""Whether a 122A-2 page answer prints whole in every box it could print in, at 6 pt as `PDFFormFiller._plan` composes it, so a saved answer never fails at Generate (H28, H49, H56)."""

from collections.abc import Iterable, Mapping, Sequence
from functools import partial

from apps.forms.services.pdf_filler import _as_printed, _refused_letter
from apps.forms.services.sheets import _lines, inner_width
from apps.forms.services.text_fit import fit, font_for, printable
from apps.forms.services.widgets import template_widgets
from apps.intake.means_test import (
    MEANS_EXPLANATION_LETTER,
    MEANS_EXPLANATION_TOO_LONG,
    MEANS_LETTER,
    MEANS_TOO_LONG,
    PROPERTY_CHOICES,
)

TEMPLATE = "b_122a-2_0425-form.pdf"

# Line 3's purpose boxes.
LINE_3_PURPOSE = ("Quest3A", "Quest3B", "Quest3C")

# Line 13's descriptions, then 33d's and 34's property boxes.
VEHICLE_DESCRIPTION = (
    "Describe Vehicle 1 1",
    "Describe Vehicle 2 1",
    "undefined_72",
    "undefined_75",
    "undefined_78",
    "secures the debt",
    "undefined_85",
    "undefined_89",
)

# Every box a spouse loan's creditor could print in (lines 9b, 13, 33d and 34).
LOAN_CREDITOR = (
    "Quest9B creditor name1",
    "Quest9B creditor name2",
    "Quest9B creditor name3",
    "Quest13B Creditor for vehicle 1-1",
    "Quest13B Creditor for vehicle 1-2",
    "Quest13E.Creditor1",
    "Quest13E.Creditor2",
    "undefined_71",
    "undefined_74",
    "undefined_77",
    "undefined_81",
    "undefined_84",
    "undefined_88",
)

# Every box a spouse loan's property words could print in (33d and 34).
LOAN_PROPERTY = (
    "undefined_72",
    "undefined_75",
    "undefined_78",
    "secures the debt",
    "undefined_85",
    "undefined_89",
)

# Each list the page draws only under its question's Yes, by that question's key.
LIST_ANSWERS = {
    "line_3_rows": "line_3_answer",
    "spouse_vehicles": "spouse_vehicles_answer",
    "spouse_loans": "spouse_loans_answer",
    "line_43_circumstances": "line_43_answer",
}

# 504 pt less a 46 pt line column and a 96 pt amount column (H30); 3h3's schema shares them.
LINE_43_EXPLANATION_WIDTH = 362.0
LINE_43_EXPLANATION_LINES = 36


def _widget(name: str):
    found = [w for w in template_widgets(TEMPLATE) if w.full_name == name and w.drawn]
    if len(found) != 1:
        raise ValueError(f"Form 122A-2 has no single drawn box {name}")
    return found[0]


def _letters_print(name: str, text: str) -> bool:
    widget = _widget(name)
    prints = partial(printable, font_for(TEMPLATE, widget.font))
    return _refused_letter(_as_printed(text), prints, widget.comb) is None


def _fits(name: str, text: str) -> bool:
    if not _letters_print(name, text):
        return False
    return fit(_widget(name), TEMPLATE, _as_printed(text)) is not None


def fits_every(text: str, names: Sequence[str]) -> bool:
    """The text prints, letters and size alike, in each named box of Form 122A-2."""
    return all(_fits(name, text) for name in names)


def box_refusal(text: str, names: Sequence[str]) -> str | None:
    """The sentence refusing words that can't print in every named box, else None (F10): a letter
    no box's font has first, then a box too small for the words."""
    if not all(_letters_print(name, text) for name in names):
        return MEANS_LETTER
    if not fits_every(text, names):
        return MEANS_TOO_LONG
    return None


def _row_refusals(list_key: str, row: Mapping) -> dict[str, list[str]]:
    words = []
    if list_key == "line_3_rows":
        words.append(("purpose", LINE_3_PURPOSE))
    elif list_key == "spouse_vehicles":
        words.append(("description", VEHICLE_DESCRIPTION))
    elif list_key == "spouse_loans":
        if row.get("on_amounts_owed") == "no":
            words.append(("creditor", LOAN_CREDITOR))
        if row.get("secured_by") in PROPERTY_CHOICES:
            words.append(("property", LOAN_PROPERTY))
    out = {}
    for field, names in words:
        text = row.get(field)
        refusal = box_refusal(text, names) if text and text.strip() else None
        if refusal is not None:
            out[field] = [refusal]
    if list_key == "line_43_circumstances":
        text = row.get("explanation")
        refusal = explanation_refusal(text) if text and text.strip() else None
        if refusal is not None:
            out["explanation"] = [refusal]
    return out


def shown_box_refusals(answers: Mapping, lists: Iterable[str]) -> dict:
    """The refusals of the boxes the page answers show in the named lists, as a 400 keys a row's
    errors: {list: {index: {field: [sentence]}}} (F1). A list counts only under its question's
    Yes, a spouse loan's creditor only under "on your Amounts Owed step" No and its property only
    under home or other: only those boxes are drawn and can print. A hidden box saves as typed."""
    errors = {}
    for list_key in lists:
        if answers.get(LIST_ANSWERS[list_key]) != "yes":
            continue
        rows = {}
        for index, row in enumerate(answers.get(list_key) or []):
            refusals = _row_refusals(list_key, row)
            if refusals:
                rows[index] = refusals
        if rows:
            errors[list_key] = rows
    return errors


def merge_row_errors(errors: dict, more: Mapping) -> None:
    """Add `shown_box_refusals`' row errors to a 400's errors, beside any a row already has."""
    for list_key, rows in more.items():
        held = errors.setdefault(list_key, {})
        for index, fields in rows.items():
            held.setdefault(index, {}).update(fields)


def explanation_refusal(text: str) -> str | None:
    """The sentence refusing a line 43 explanation that can't print, else None (R22)."""
    prints = partial(printable, font_for(TEMPLATE, "/Helv"))
    if _refused_letter(_as_printed(text), prints) is not None:
        return MEANS_EXPLANATION_LETTER
    lines = _lines(text, inner_width(LINE_43_EXPLANATION_WIDTH))
    if lines is None or len(lines) > LINE_43_EXPLANATION_LINES:
        return MEANS_EXPLANATION_TOO_LONG
    return None
