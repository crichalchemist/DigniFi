"""The Income step's list of business and rental entries (3e2 spec §4.2): the constants only."""

ENTRY_KINDS = ("business", "rental")
ENTRY_KEYS = ("kind", "description", "gross", "expenses", "current_gross", "current_expenses")
ENTRY_AMOUNT_KEYS = ("gross", "expenses", "current_gross", "current_expenses")
MAX_ENTRIES = 10
