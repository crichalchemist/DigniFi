"""The order Schedules D and E/F list claims in (3c spec §6.2). Pure: no models."""

import unicodedata


def _letters(name):
    """A creditor's name as it sorts: its letters, without accents, ignoring case."""
    decomposed = unicodedata.normalize("NFKD", name.strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def ordered_debts(rows):
    """The rows alphabetical by creditor name, ignoring case and accents, then by id.

    Sorted in Python: the name is ciphertext in the table.
    """
    return sorted(rows, key=lambda row: (_letters(row.creditor_name), row.pk))
