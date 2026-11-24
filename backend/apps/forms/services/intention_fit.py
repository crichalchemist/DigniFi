"""Which claims texts check() refuses as too long where their own rows print (forms step 4e,
4e-R4, 4e-R5, E4, R-EXPLAIN).

A creditor's name, a property description, a lessor's name, a leased property's description and
the "[explain]" words are each measured by `PDFFormFiller.check()` itself, in every box that prints
them, on the forms the row's own list prints on: a secured row on Form 108 and Schedule D, a
priority or unsecured row on Schedule E/F, a lease on Schedule G and, when Form 108 asks about it,
Form 108; never a form the row doesn't reach. A row past a group's slots is measured in each slot
box of its column on the copies of the group's extra page (the copies repeat the same boxes, so
the narrowest governs), or on Form 108's attached sheet. Only a too-long refusal counts: a letter
the form can't print keeps Generate's own refusal, as `petition_fit` measures only fit.
"""

import re
from collections.abc import Collection

from apps.forms.schema import FieldSpec, FormSchema, GroupSpec, load_schema
from apps.forms.services.fill_resolver import CLAIM_CELLS, _emit, _key
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong
from apps.intake.claim_rows import claim_rows, one_read_of_claims

# The forms whose boxes print a claims text, in packet order. Form 108 is measured only while it
# is in the packet; the three schedules are in every packet.
MEASURED_FORMS = ("form_108", "schedule_d", "schedule_e_f", "schedule_g")

# (list, cell) -> the text it prints: the row's stored field, or Form 108's "[explain]" words,
# which Explain1 and Explain2 split and the Part 1 sheet prints whole.
TEXT_OF_CELL = {
    ("secured", "name"): "creditor_name",
    ("priority", "name"): "creditor_name",
    ("unsecured", "name"): "creditor_name",
    ("secured", "property"): "collateral_description",
    ("contracts", "name"): "counterparty_name",
    ("contracts", "purpose"): "description",
    ("leases", "name"): "counterparty_name",
    ("leases", "purpose"): "description",
    ("secured", "explain"): "explain",
    ("secured", "explain_1"): "explain",
    ("secured", "explain_2"): "explain",
}

# The sheet's header names the filer; a neutral name here, so the filer's own name can never mask
# or fake the refusal of the one cell measured.
_SHEET_NAME = "Debtor 1"

_CLAIM_BINDING = re.compile(r"claims\.(\w+)\[\]\.(\w+)")

# (kind, pk, text): kind "debt" or "lease", the row's model id and the text measured.
Measured = tuple[str, int, str]


def _cell_of(binding: str | None) -> tuple[str, str] | None:
    match = _CLAIM_BINDING.fullmatch(binding or "")
    return (match[1], match[2]) if match else None


def _measured(list_name: str, row, text: str) -> Measured | None:
    """The row's key, or None for a contract that isn't a lease (4e-R4 leaves its texts out)."""
    if list_name in ("contracts", "leases"):
        if row.contract.contract_type != "lease":
            return None
        return ("lease", row.contract.pk, text)
    return ("debt", row.debt.pk, text)


def _refused(form_type: str, values: dict) -> bool:
    """Whether check() refuses the values as too long. A letter the box can't print is refused
    first, before any measure, with its own sentence at Generate, so it is not too long here."""
    if not values:
        return False
    try:
        PDFFormFiller().check(form_type, values)
    except ValueTooLong:
        return True
    except UnprintableLetter:
        return False
    return False


def _values(fields: list[FieldSpec], row) -> dict:
    """What a row prints in one slot's boxes of a text (Explain1 and Explain2 together)."""
    values = {}
    for field in fields:
        list_name, attr = _cell_of(field.binding)
        value = _emit(field, CLAIM_CELLS[list_name][attr](row))
        if value is not None:
            values[_key(field)] = value
    return values


def _slot_refusals(form_type: str, schema: FormSchema, rows, texts) -> set[Measured]:
    """The rows whose text a slot box of their column refuses."""
    # (group, list, text) -> {slot row: the boxes that print the text on that slot}
    slots: dict[tuple[str, str, str], dict[int, list[FieldSpec]]] = {}
    for field in schema.fields:
        cell = _cell_of(field.binding) if field.repeat else None
        text = TEXT_OF_CELL.get(cell)
        if text is None or text not in texts:
            continue
        by_row = slots.setdefault((field.repeat, cell[0], text), {})
        by_row.setdefault(field.row, []).append(field)
    found = set()
    for (group_name, list_name, text), by_row in slots.items():
        extra_page = schema.groups[group_name].extra_page
        for position, row in enumerate(getattr(rows, list_name), start=1):
            measured = _measured(list_name, row, text)
            if measured is None:
                continue
            if position in by_row:
                boxes = [by_row[position]]
            elif extra_page is not None:
                boxes = [f for f in by_row.values() if f[0].page == extra_page]
            else:
                continue  # past a sheet group's slots: the sheet measures it
            if any(_refused(form_type, _values(fields, row)) for fields in boxes):
                found.add(measured)
    return found


def _sheet_refusals(
    form_type: str, schema: FormSchema, group: GroupSpec, rows, texts
) -> set[Measured]:
    """The rows past a sheet group's slots whose text the sheet's column refuses, one cell at a
    time, the others blank, as sheets.plan_sheet measures it through check()."""
    capacity = max(
        (f.repeat_capacity or 0 for f in schema.fields if f.repeat == group.name), default=0
    )
    columns = group.sheet.columns
    found = set()
    for index, column in enumerate(columns):
        cell = _cell_of(column.binding)
        text = TEXT_OF_CELL.get(cell)
        if text is None or text not in texts:
            continue
        list_name, attr = cell
        for position, row in enumerate(getattr(rows, list_name), start=1):
            measured = _measured(list_name, row, text)
            value = CLAIM_CELLS[list_name][attr](row)
            if position <= capacity or measured is None or not value:
                continue
            cells = [""] * len(columns)
            cells[index] = value
            part = {
                "kind": "sheet",
                "group": group.name,
                "title": group.sheet.title,
                "columns": [{"label": c.label, "width": c.width} for c in columns],
                "name": _SHEET_NAME,
                "rows": [{"line": group.number.format(n=position), "cells": cells}],
                "line_width": group.sheet.line_width,
            }
            try:
                PDFFormFiller().check(form_type, {"version": 2, "parts": [part]})
            except ValueTooLong as refusal:
                if refusal.label == column.label:
                    found.add(measured)
            except UnprintableLetter:
                pass
    return found


def too_long_texts(session, texts: Collection[str]) -> dict[Measured, frozenset[str]]:
    """
    Each text of `texts` that check() refuses as too long in a box its row prints in, keyed
    (kind, pk, text), to the form types that refuse it (two forms can print one text, and only a
    refusing form's box is too small). Whether the text shows is the caller's to judge (the
    "[explain]" words under a stored retain_explain only, 4e-R16); a box is measured on what it
    would print.
    """
    # Here, not at the top: the registry imports most of the forms app, this module's own
    # imports among them.
    from apps.forms.registry import FORM_REGISTRY

    found: dict[Measured, set[str]] = {}
    with one_read_of_claims():
        rows = claim_rows(session)
        for form_type in MEASURED_FORMS:
            if not FORM_REGISTRY[form_type].applies(session):
                continue
            schema = load_schema(form_type)
            refused = _slot_refusals(form_type, schema, rows, texts)
            for group in schema.groups.values():
                if group.sheet is not None:
                    refused |= _sheet_refusals(form_type, schema, group, rows, texts)
            for measured in refused:
                found.setdefault(measured, set()).add(form_type)
    return {measured: frozenset(forms) for measured, forms in found.items()}
