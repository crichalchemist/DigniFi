"""Copy each asset's description and institution into its encrypted column (3b spec §3.1, step 2).

The save encrypts. Undoing it refuses, naming the table and row and never the value, when a
value can't be read with this FIELD_ENCRYPTION_KEY: the library hands an undecryptable value
on as it is, so each stored value is checked before it is turned back into plaintext.
"""

from cryptography.fernet import InvalidToken
from django.db import migrations
from encrypted_model_fields.fields import decrypt_str

TABLE = "asset_info"
FIELDS = ["description", "financial_institution"]
ENCRYPTED = [f"{name}_encrypted" for name in FIELDS]
BATCH = 500


def _unreadable(pk):
    return RuntimeError(
        f"{TABLE} row {pk} can't be read with this FIELD_ENCRYPTION_KEY, "
        "so the migration stopped before losing it."
    )


def _raw(schema_editor, pk, column):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM {TABLE} WHERE id = %s", [pk])
        return cursor.fetchone()[0]


def _pks(AssetInfo):
    return list(AssetInfo.objects.order_by("pk").values_list("pk", flat=True))


def copy_forward(apps, schema_editor):
    AssetInfo = apps.get_model("intake", "AssetInfo")
    pks = _pks(AssetInfo)
    for start in range(0, len(pks), BATCH):
        for row in AssetInfo.objects.filter(pk__in=pks[start : start + BATCH]):
            for name in FIELDS:
                setattr(row, f"{name}_encrypted", getattr(row, name))
            row.save(update_fields=ENCRYPTED)


def copy_back(apps, schema_editor):
    AssetInfo = apps.get_model("intake", "AssetInfo")
    pks = _pks(AssetInfo)
    for start in range(0, len(pks), BATCH):
        for pk in pks[start : start + BATCH]:
            for column in ENCRYPTED:
                raw = _raw(schema_editor, pk, column)
                if raw is None:
                    continue
                try:
                    decrypt_str(raw)
                except InvalidToken:
                    raise _unreadable(pk) from None
            row = AssetInfo.objects.get(pk=pk)
            for name in FIELDS:
                setattr(row, name, getattr(row, f"{name}_encrypted") or "")
            row.save(update_fields=FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0032_assetinfo_encrypt_add"),
    ]

    operations = [
        migrations.RunPython(copy_forward, copy_back),
    ]
