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


def is_entry_answered(entry, *, current):
    """Whether an entry has every answer it needs: current amounts too while `current` is true."""
    needed = [entry.get("kind"), entry.get("gross"), entry.get("expenses")]
    if current:
        needed += [entry.get("current_gross"), entry.get("current_expenses")]
    return (entry.get("description") or "").strip() != "" and all(n is not None for n in needed)


def current_given(row):
    """Whether the row has any current figure, in a box or in an entry."""
    if any(getattr(row, field) is not None for field in row.CURRENT_FIELDS):
        return True
    return any(
        entry.get("current_gross") is not None or entry.get("current_expenses") is not None
        for entry in row.get_entries() or []
    )


def schedule_i_line4(row):
    """Schedule I line 4: wages, overtime and tips as Schedule I reads them, a blank as 0."""
    return sum(
        (
            getattr(row, schedule_i_field(row, field)) or Decimal("0")
            for field in ("monthly_gross_wages", "monthly_overtime", "monthly_tips")
        ),
        Decimal("0"),
    )


def deductions_blank(row):
    """Whether the filer left all eight deductions empty."""
    return all(getattr(row, field) is None for field in row.DEDUCTION_FIELDS)


def _money(value):
    """A statement cell's amount: two places, a null as 0.00."""
    return str(Decimal(value or "0").quantize(Decimal("0.01")))


def statement_rows(filer, spouse):
    """
    The rows of Schedule I's line 8a statement (3e2 spec 9.2): the filer's entries, then the
    spouse's when `spouse` is not None, in stored order. Each is {owner, description, gross,
    expenses, net} in the figures Schedule I uses, as two-place strings; net is the entry's own
    subtraction and may be negative. After a person's entries comes one floor row per kind
    whose summed net is below 0, business before rental.
    """
    rows = []
    for row, owner in ((filer, "Debtor 1"), (spouse, "Non-filing spouse")):
        if row is None:
            continue
        entries = row.get_entries() or []
        current = uses_current(row)
        gross_key, expenses_key = (
            ("current_gross", "current_expenses") if current else ("gross", "expenses")
        )
        for entry in entries:
            gross = Decimal(entry.get(gross_key) or "0")
            expenses = Decimal(entry.get(expenses_key) or "0")
            label = "Business" if entry["kind"] == "business" else "Rental property"
            rows.append(
                {
                    "owner": owner,
                    "description": f"{label}: {entry['description']}",
                    "gross": _money(gross),
                    "expenses": _money(expenses),
                    "net": _money(gross - expenses),
                }
            )
        for kind, label in (("business", "Business"), ("rental", "Rental property")):
            net = kind_net(entries, kind, current=current)
            if net < 0:
                rows.append(
                    {
                        "owner": owner,
                        # DRAFT: counsel C-12
                        "description": f"{label} total below $0, brought up to $0.00",
                        "gross": "",
                        "expenses": "",
                        "net": _money(-net),
                    }
                )
    return rows
