"""Which of the filer's own petition answers check() refuses as too long where they print
(forms step 4b-ii, Rulings PF2-1 and PF2-10 a and d).

Each box is measured by `PDFFormFiller.check()` itself, on what its binding prints (the
derivation's own output: a street's Number and Street, the venue reason's wrapped lines), so
Review's too-long line and Generate's refusal can never disagree. A row past a list's slots is
measured on the attached sheet as `sheets.plan_sheet` measures it, through check() too.
"""

from collections.abc import Collection

from apps.forms.schema import FieldSpec, GroupSpec, load_schema
from apps.forms.services.derivations import DERIVATIONS
from apps.forms.services.fill_resolver import _emit, _key, _scalar_value, resolve_binding
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong

# The forms whose boxes print a petition answer; Task 10 adds Form 103B's line 20.
MEASURED_FORMS = ("form_101",)

# The derivations that print a petition key's text, by rule: each street's Number box too, which
# has no cap of its own (PF2-10d), and the venue reason's four lines.
_KEY_OF_RULE = {
    f"{prefix}_{part}": f"{prefix}_street"
    for prefix in ("mailing", "business", "hazard")
    for part in ("number", "street")
}
_KEY_OF_RULE.update({f"venue_reason_line_{n}": "venue_reason" for n in range(1, 5)})

PETITION = "petition."

# What a too-long box names: (key, None, None) for a text key, (list, attr, row) for a row cell,
# the row its place in the list, counted from 1 (owner ruling Q5).
Measured = tuple[str, str | None, int | None]
# The petition key, or row cell, a box prints: (key, None) or (list, attr).
Cell = tuple[str, str | None]


def _measured(field: FieldSpec) -> Cell | None:
    """The petition key, or row cell, a field's box prints; None for any other box."""
    if field.binding and field.binding.startswith(PETITION):
        key, _, attr = field.binding[len(PETITION) :].partition("[].")
        return key, attr or None
    if field.source == "derived" and field.rule in _KEY_OF_RULE:
        return _KEY_OF_RULE[field.rule], None
    return None


def _refused(form_type: str, values: dict) -> bool:
    """Whether check() refuses the values as too long. A letter the box can't print is refused
    first, before any measure, with its own sentence at Generate, so it is not too long here."""
    try:
        PDFFormFiller().check(form_type, values)
    except ValueTooLong:
        return True
    except UnprintableLetter:
        return False
    return False


def _sheet_refusals(
    form_type: str, group: GroupSpec, capacity: int, session, keys: Collection[str]
) -> set[Measured]:
    """The cells check() refuses on the sheet that prints the group's rows past its slots."""
    columns = [_measured_column(c.binding) for c in group.sheet.columns]
    if not any(column[0] in keys for column in columns):
        return set()
    cells_by_column = [resolve_binding(c.binding, session) for c in group.sheet.columns]
    by_label = {c.label: i for i, c in enumerate(group.sheet.columns)}
    found = set()
    for position in range(capacity + 1, max(map(len, cells_by_column), default=0) + 1):
        cells = [col[position - 1] if position <= len(col) else "" for col in cells_by_column]
        part = {
            "kind": "sheet",
            "group": group.name,
            "title": group.sheet.title,
            "columns": [{"label": c.label, "width": c.width} for c in group.sheet.columns],
            "name": DERIVATIONS["full_name"](session),
            "rows": [{"line": group.number.format(n=position), "cells": cells}],
            "line_width": group.sheet.line_width,
        }
        # One refusal names one column; blank that cell and measure the row again, so a second
        # cell too wide in the same row is found too.
        while True:
            try:
                PDFFormFiller().check(form_type, {"version": 2, "parts": [part]})
            except (ValueTooLong, UnprintableLetter) as refusal:
                index = by_label.get(refusal.label)
                # The filer's name in the sheet's header is no cell; nor is a label whose cell is
                # already blank (a header label equal to a column's), which would be refused the
                # same way on every measure, for ever.
                if index is None or cells[index] == "":
                    break
                if isinstance(refusal, ValueTooLong):
                    found.add((*columns[index], position))
                cells[index] = ""
                continue
            break
    return {cell for cell in found if cell[0] in keys}


def _measured_column(binding: str) -> Cell:
    key, _, attr = binding[len(PETITION) :].partition("[].")
    return key, attr


def too_long(session, keys: Collection[str]) -> dict[Measured, frozenset[str]]:
    """
    Each text key of `keys` that check() refuses as too long in a box it prints in, as
    (key, None, None), and each row cell of a list in `keys` refused in its slot box or on its
    sheet, as (list, attr, row) with the row counted from 1, so the filer is told which row to
    shorten, over every form in MEASURED_FORMS, each to the form types that refuse it
    (two forms can print one cell, and only a refusing form's box is too small). Whether the box
    shows at all is the caller's to judge (petition.text_shows); a box is measured on what it
    would print.
    """
    found: dict[Measured, set[str]] = {}
    for form_type in MEASURED_FORMS:
        schema = load_schema(form_type)
        capacities: dict[str, int] = {}
        refused: set[Measured] = set()
        for field in schema.fields:
            measured = _measured(field)
            if measured is None or measured[0] not in keys:
                continue
            if field.repeat is None:
                row = None
                value = _emit(field, _scalar_value(field, session))
            else:
                row = field.row
                capacities[field.repeat] = field.repeat_capacity or 0
                cells = resolve_binding(field.binding, session)
                value = _emit(field, cells[field.row - 1]) if field.row <= len(cells) else None
            if value is not None and _refused(form_type, {_key(field): value}):
                refused.add((*measured, row))
        for name, capacity in capacities.items():
            group = schema.groups.get(name)
            if group is not None and group.sheet is not None:
                refused |= _sheet_refusals(form_type, group, capacity, session, keys)
        for measured in refused:
            found.setdefault(measured, set()).add(form_type)
    return {measured: frozenset(forms) for measured, forms in found.items()}
