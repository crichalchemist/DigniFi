"""Copy each debt, contract and codebtor column into its encrypted twin (3c2 spec section 6.1,
step 2).

The save encrypts. Undoing it refuses, naming the table and row and never the value, when a
value can't be read with this FIELD_ENCRYPTION_KEY: the library hands an undecryptable value
on as it is, so each stored value is checked before it is turned back into plaintext. A debt's
date becomes text going forward; going back, text that is no single date becomes no date (R4).
"""

import datetime

from cryptography.fernet import InvalidToken
from django.db import migrations
from encrypted_model_fields.fields import decrypt_str

TABLES = {  # model: (table, columns)
    "DebtInfo": (
        "debt_info",
        [
            "creditor_name",
            "monthly_payment",
            "notes",
            "collateral_description",
            "date_incurred",
        ],
    ),
    "ExecutoryContract": ("executory_contracts", ["counterparty_name", "description"]),
    "Codebtor": (
        "codebtors",
        ["name", "street_address", "city", "state", "zip_code", "relationship"],
    ),
}
NULLABLE = {"monthly_payment", "date_incurred"}
BATCH = 500


def _forward(name, value):
    if name == "date_incurred" and value is not None:
        return value.isoformat()
    return value


def _back(name, value):
    if name == "date_incurred":
        try:
            return datetime.date.fromisoformat(value) if value else None
        except ValueError:
            return None  # text such as "2019–2025" names no single date (B11)
    return value if name in NULLABLE else (value or "")


def _unreadable(table, pk):
    return RuntimeError(
        f"{table} row {pk} can't be read with this FIELD_ENCRYPTION_KEY, "
        "so the migration stopped before losing it."
    )


def _raw(schema_editor, table, pk, column):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM {table} WHERE id = %s", [pk])
        return cursor.fetchone()[0]


def _pks(Model):
    return list(Model.objects.order_by("pk").values_list("pk", flat=True))


def copy_forward(apps, schema_editor):
    for model_name, (_table, columns) in TABLES.items():
        Model = apps.get_model("intake", model_name)
        pks = _pks(Model)
        encrypted = [f"{name}_encrypted" for name in columns]
        for start in range(0, len(pks), BATCH):
            for row in Model.objects.filter(pk__in=pks[start : start + BATCH]):
                for name in columns:
                    setattr(row, f"{name}_encrypted", _forward(name, getattr(row, name)))
                row.save(update_fields=encrypted)


def copy_back(apps, schema_editor):
    for model_name, (table, columns) in TABLES.items():
        Model = apps.get_model("intake", model_name)
        pks = _pks(Model)
        encrypted = [f"{name}_encrypted" for name in columns]
        for start in range(0, len(pks), BATCH):
            for pk in pks[start : start + BATCH]:
                # Every twin of the row is checked before any of its columns is saved.
                for column in encrypted:
                    raw = _raw(schema_editor, table, pk, column)
                    if raw is None:
                        continue
                    try:
                        decrypt_str(raw)
                    except InvalidToken:
                        raise _unreadable(table, pk) from None
                row = Model.objects.get(pk=pk)
                for name in columns:
                    setattr(row, name, _back(name, getattr(row, f"{name}_encrypted")))
                row.save(update_fields=columns)


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0036_claims_encrypt_add"),
    ]

    operations = [
        migrations.RunPython(copy_forward, copy_back),
    ]
