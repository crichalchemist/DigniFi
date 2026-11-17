"""What each `means.` binding prints, from the calculator's record alone: a sentinel prints blank,
never 0.00 (H16), and an unknown spelling is a ValueError, never a blank box.

The grammar is closed (3h3 plan R2): `means.line_<key>` for every `LINE_KEYS` entry but the
last, which is spelled `means.page_1`; `means.line_43_pointer_<n>` and `means.line_43_amount_<n>`,
n 1 to 4, the form's own line 43 rows; and a list cell `means.line_<group>[].<attr>` over the six
slot groups and line 43. Nothing here derives, rounds or compares: a cell formats what
`MeansLines` holds, and `line_43_rows_to_print` alone decides whether line 43's rows print (R4).
"""

from __future__ import annotations

import re
from collections.abc import Callable

from apps.eligibility.means_lines import (
    LINE_KEYS,
    MISSING,
    SKIPPED,
    MeansLines,
    MeansRow,
    line_43_rows_to_print,
)
from apps.forms.services.derivations import _fmt, money_or_blank

# DRAFT: counsel C-31
LINE_43_POINTER = "See line 43.{n} on the attached sheet."

_PREFIX = "means."
_LINE_43_ROW = re.compile(r"line_43_(pointer|amount)_([1-4])")
_LIST_CELL = re.compile(r"line_(3|9b|13b|13e|33d|34|43)\[\]\.(\w+)")

# The keys that print as the text the calculator holds: a slot's vehicle, a count, a yes/no
# answer and the outcome. Every other LINE_KEYS entry is money and goes straight to _money.
_TEXT_KEYS = ("13_vehicle_1", "13_vehicle_2")
_COUNT_KEYS = ("5", "7b", "7e")
_ANSWER_KEYS = (
    "2", "2_filing", "3_answer", "25_answer", "25_spends", "34_answer", "35_answer",
    "36_answer", "42", "43",
)  # fmt: skip
_AS_TEXT = frozenset((*_TEXT_KEYS, *_COUNT_KEYS, *_ANSWER_KEYS, "page_1"))
_LINE_11 = {0: "0", 1: "1"}  # any larger count is "2_or_more"
_LINE_40 = {"1": "1", "2": "2", "On": "between"}


def _blank(value) -> bool:
    return value is MISSING or value is SKIPPED


def _money(value) -> str:
    """A money line or a row's amount: blank for a sentinel, else the figure to the cent."""
    return "" if _blank(value) else _fmt(value)


def _scalar(key: str, value) -> str:
    if key in _AS_TEXT:
        return "" if _blank(value) else str(value)
    if key == "36_multiplier":
        return "" if _blank(value) else f"{value.normalize():f}%"
    if key == "11":
        return "" if _blank(value) else _LINE_11.get(value, "2_or_more")
    if key == "40":
        return "" if _blank(value) else _LINE_40[value]
    return _money(value)


def _label(row: MeansRow) -> str:
    return row.label


def _amount(row: MeansRow) -> str:
    return _money(row.amount)


def _property(row: MeansRow) -> str:
    return row.property


def _flag(row: MeansRow) -> str:
    return row.flag or ""


def _cure(row: MeansRow) -> str:
    return money_or_blank(row.cure)


def _explanation(row: MeansRow) -> str:
    return row.label.strip()  # the PUT stores it untrimmed


def _line_43_amount(row: MeansRow) -> str:
    return money_or_blank(row.amount)  # a printing row's amount is given (R4)


_ROW_CELLS: dict[str, dict[str, Callable[[MeansRow], str]]] = {
    "3": {"purpose": _label, "amount": _amount},
    "9b": {"creditor": _label, "amount": _amount},
    "13b": {"creditor": _label, "amount": _amount},
    "13e": {"creditor": _label, "amount": _amount},
    "33d": {
        "creditor": _label,
        "property": _property,
        "taxes_or_insurance": _flag,
        "amount": _amount,
    },
    "34": {"creditor": _label, "property": _property, "cure": _cure, "amount": _amount},
    "43": {"explanation": _explanation, "amount": _line_43_amount},
}


def _rows(group: str, lines: MeansLines) -> tuple[MeansRow, ...]:
    return line_43_rows_to_print(lines) if group == "43" else lines.rows[group]


def means_value(binding: str, lines: MeansLines) -> str | list[str]:
    """What `binding` prints from `lines`: a scalar as text, a list cell as one str per row.

    Raises ValueError for any spelling outside the grammar, as every namespace does.
    """
    spelling = binding[len(_PREFIX) :] if binding.startswith(_PREFIX) else ""
    row_match = _LINE_43_ROW.fullmatch(spelling)
    if row_match:
        kind, n = row_match[1], int(row_match[2])
        rows = line_43_rows_to_print(lines)
        if n > len(rows):
            return ""
        return LINE_43_POINTER.format(n=n) if kind == "pointer" else _line_43_amount(rows[n - 1])
    cell_match = _LIST_CELL.fullmatch(spelling)
    if cell_match:
        cell = _ROW_CELLS[cell_match[1]].get(cell_match[2])
        if cell is not None:
            return [cell(row) for row in _rows(cell_match[1], lines)]
    elif spelling == "page_1":
        return _scalar("page_1", lines.lines["page_1"])
    elif spelling.startswith("line_"):
        key = spelling[len("line_") :]
        if key in LINE_KEYS and key != "page_1":
            return _scalar(key, lines.lines[key])
    raise ValueError(f"unrecognized binding: {binding!r}")
