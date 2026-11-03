"""Copy each income amount into its encrypted column (3e2 spec §3.2, step 2).

The save encrypts. An empty amount stays NULL and the old six-month total becomes JSON
text, NULL staying NULL. Undoing it refuses, naming the table and row and never the
value, when a value can't be read with this FIELD_ENCRYPTION_KEY.
"""

import json

from django.core.exceptions import ValidationError
from django.db import migrations

TABLE = "income_info"
FIELDS = [
    "monthly_gross_wages",
    "monthly_overtime",
    "monthly_tips",
    "monthly_rental_income",
    "monthly_pension",
    "monthly_social_security",
    "monthly_unemployment",
    "monthly_child_support",
    "monthly_alimony",
    "monthly_other_income",
]
ENCRYPTED = [f"{name}_encrypted" for name in [*FIELDS, "monthly_income"]]


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
    IncomeInfo = apps.get_model("intake", "IncomeInfo")
    for row in IncomeInfo.objects.all():
        for name in FIELDS:
            setattr(row, f"{name}_encrypted", getattr(row, name))
        months = row.monthly_income
        row.monthly_income_encrypted = None if months is None else json.dumps(months)
        row.save(update_fields=ENCRYPTED)


def copy_back(apps, schema_editor):
    """Undo the copy. A value that can't be read with this key stops the undo, never turns
    into NULL: the library hands an undecryptable value on, and loading it fails or gives None.
    """
    IncomeInfo = apps.get_model("intake", "IncomeInfo")
    for pk in list(IncomeInfo.objects.values_list("pk", flat=True)):
        try:
            row = IncomeInfo.objects.get(pk=pk)
        except ValidationError:
            raise _unreadable(pk) from None
        for name in FIELDS:
            value = getattr(row, f"{name}_encrypted")
            if value is None and _raw_is_set(schema_editor, pk, f"{name}_encrypted"):
                raise _unreadable(pk)
            setattr(row, name, value)
        text = row.monthly_income_encrypted
        if text is None:
            row.monthly_income = None
        else:
            try:
                row.monthly_income = json.loads(text)
            except ValueError:
                raise _unreadable(pk) from None
        row.save(update_fields=[*FIELDS, "monthly_income"])


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0020_incomeinfo_encrypt_add"),
    ]

    operations = [
        migrations.RunPython(copy_forward, copy_back),
    ]
