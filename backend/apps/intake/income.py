"""The Income step's list of business and rental entries (3e2 spec §4.2).

Pure: rows are taken by duck type and entries as stored, so this module imports no model.
"""

from decimal import Decimal

ENTRY_KINDS = ("business", "rental")
ENTRY_KEYS = ("kind", "description", "gross", "expenses", "current_gross", "current_expenses")
ENTRY_AMOUNT_KEYS = ("gross", "expenses", "current_gross", "current_expenses")
MAX_ENTRIES = 10


def kind_sums(entries, kind, *, current=False):
    """One kind's gross sum and expenses sum over the list, a blank counting as 0."""
    gross_key, expenses_key = (
        ("current_gross", "current_expenses")
        if current
        else (
            "gross",
            "expenses",
        )
    )
    gross = Decimal("0")
    expenses = Decimal("0")
    for entry in entries or []:
        if entry.get("kind") != kind:
            continue
        if entry.get(gross_key) is not None:
            gross += Decimal(entry[gross_key])
        if entry.get(expenses_key) is not None:
            expenses += Decimal(entry[expenses_key])
    return gross, expenses


def kind_net(entries, kind, *, current=False):
    """One kind's gross sum less its expenses sum. May be below 0."""
    gross, expenses = kind_sums(entries, kind, current=current)
    return gross - expenses


def floored_net(entries, kind, *, current=False):
    """The kind's net as CMI counts it: never below $0.00 (owner answer 1, C-12)."""
    return max(Decimal("0.00"), kind_net(entries, kind, current=current))


def has_entry_figures(entries):
    """Whether any entry has a gross or an expenses amount."""
    return any(
        entry.get("gross") is not None or entry.get("expenses") is not None
        for entry in entries or []
    )


def uses_current(row):
    """Whether Schedule I reads the row's current figures."""
    return row.income_now_different == "yes"


def schedule_i_field(row, field):
    """The field Schedule I reads: the current one while the filer said income is different now."""
    return "current_" + field if uses_current(row) else field
