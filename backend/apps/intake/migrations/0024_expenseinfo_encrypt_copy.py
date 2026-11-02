"""Copy each expense amount into its encrypted column (3e2 spec §3.2, step 2).

The save encrypts. Undoing it refuses, naming the table and row and never the value,
when a value can't be read with this FIELD_ENCRYPTION_KEY.
"""

from django.core.exceptions import ValidationError
from django.db import migrations

TABLE = "expense_info"
FIELDS = [
    "rent_or_mortgage",
    "utilities",
    "home_maintenance",
    "vehicle_payment",
    "vehicle_insurance",
    "vehicle_maintenance",
    "food_and_groceries",
    "clothing",
    "medical_expenses",
    "childcare",
    "child_support_paid",
    "insurance_not_deducted",
    "other_expenses",
]
ENCRYPTED = [f"{name}_encrypted" for name in FIELDS]


def _unreadable(pk):
    return RuntimeError(
        f"{TABLE} row {pk} can't be read with this FIELD_ENCRYPTION_KEY, "
        "so the migration stopped before losing it."
    )


def _raw_is_set(schema_editor, pk, column):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"SELECT 1 FROM {TABLE} WHERE id = %s AND {column} IS NOT NULL", [pk])
        return cursor.fetchone() is not None


def copy_forward(apps, schema_editor):
    ExpenseInfo = apps.get_model("intake", "ExpenseInfo")
    for row in ExpenseInfo.objects.all():
        for name in FIELDS:
            setattr(row, f"{name}_encrypted", getattr(row, name))
        row.save(update_fields=ENCRYPTED)


def copy_back(apps, schema_editor):
    """Undo the copy. A value that can't be read with this key stops the undo, never turns
    into NULL: the library hands an undecryptable value on, and loading it fails or gives None.
    """
    ExpenseInfo = apps.get_model("intake", "ExpenseInfo")
    for pk in list(ExpenseInfo.objects.values_list("pk", flat=True)):
        try:
            row = ExpenseInfo.objects.get(pk=pk)
        except ValidationError:
            raise _unreadable(pk) from None
        for name in FIELDS:
            value = getattr(row, f"{name}_encrypted")
            if value is None and _raw_is_set(schema_editor, pk, f"{name}_encrypted"):
                raise _unreadable(pk)
            setattr(row, name, value)
        row.save(update_fields=FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0023_expenseinfo_encrypt_add"),
    ]

    operations = [
        migrations.RunPython(copy_forward, copy_back),
    ]
