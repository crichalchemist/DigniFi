"""Give a utilities or insurance figure saved before the split its printed words (4c2 R3).

Before 4c2, Schedule J printed "Utilities (combined)" and "Insurance (combined)" beside lines
6d and 15d whatever the filer typed. Those words are now the filer's own Specify text, so a
figure saved before the split keeps printing exactly what it did.

Forward: a row whose utilities (insurance_not_deducted) is above $0 and whose Specify text is
blank gets the words. Reverse: a text equal to the words is blanked; any other text is kept.

The amounts are encrypted, so rows are read in Python, never filtered in SQL. An amount that
reads as None (unreadable) is treated as $0. Only the columns the migration needs are loaded,
so a column it never touches can't stop it.
"""

from django.db import migrations

# DRAFT: counsel C-47
UTILITIES_WORDS = "Utilities (combined)"
# DRAFT: counsel C-47
INSURANCE_WORDS = "Insurance (combined)"


def label_combined_figures(apps, schema_editor) -> None:
    ExpenseInfo = apps.get_model("intake", "ExpenseInfo")
    rows = ExpenseInfo.objects.only(
        "pk", "utilities", "insurance_not_deducted", "utilities_specify", "insurance_specify"
    )
    for row in rows:
        changed = []
        if (row.utilities or 0) > 0 and row.utilities_specify == "":
            row.utilities_specify = UTILITIES_WORDS
            changed.append("utilities_specify")
        if (row.insurance_not_deducted or 0) > 0 and row.insurance_specify == "":
            row.insurance_specify = INSURANCE_WORDS
            changed.append("insurance_specify")
        if changed:
            row.save(update_fields=changed)


def unlabel_combined_figures(apps, schema_editor) -> None:
    ExpenseInfo = apps.get_model("intake", "ExpenseInfo")
    for row in ExpenseInfo.objects.only("pk", "utilities_specify", "insurance_specify"):
        changed = []
        if row.utilities_specify == UTILITIES_WORDS:
            row.utilities_specify = ""
            changed.append("utilities_specify")
        if row.insurance_specify == INSURANCE_WORDS:
            row.insurance_specify = ""
            changed.append("insurance_specify")
        if changed:
            row.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0046_expenseinfo_split_utilities_and_insurance"),
    ]

    operations = [
        migrations.RunPython(label_combined_figures, unlabel_combined_figures),
    ]
