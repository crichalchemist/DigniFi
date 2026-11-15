"""Copy each means test column into its encrypted column (3h1 spec §7.5, step 2).

The save encrypts. Undoing it refuses, naming the table and row and never the value, when a
value can't be read with this FIELD_ENCRYPTION_KEY: the library hands an undecryptable value
on as it is, so each stored value is checked before it is turned back into plaintext.
"""

from decimal import Decimal

from cryptography.fernet import InvalidToken
from django.db import migrations
from encrypted_model_fields.fields import decrypt_str

TABLE = "means_tests"
FIELDS = [
    "calculated_cmi",
    "median_income_threshold",
    "total_allowable_expenses",
    "disposable_income",
    "priority_debts_monthly",
    "passes_above_median",
    "above_median_calculated",
]
ENCRYPTED = [f"{name}_encrypted" for name in FIELDS]
OLD_DEFAULTS = {
    "calculated_cmi": Decimal("0"),
    "median_income_threshold": Decimal("0"),
    "total_allowable_expenses": Decimal("0"),
    "disposable_income": Decimal("0"),
    "priority_debts_monthly": Decimal("0"),
    "passes_above_median": False,
    "above_median_calculated": False,
}
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


def _pks(MeansTest):
    return list(MeansTest.objects.order_by("pk").values_list("pk", flat=True))


def copy_forward(apps, schema_editor):
    MeansTest = apps.get_model("eligibility", "MeansTest")
    pks = _pks(MeansTest)
    for start in range(0, len(pks), BATCH):
        for row in MeansTest.objects.filter(pk__in=pks[start : start + BATCH]):
            for name in FIELDS:
                setattr(row, f"{name}_encrypted", getattr(row, name))
            row.save(update_fields=ENCRYPTED)


def _no_result(pk):
    return RuntimeError(
        f"{TABLE} row {pk}'s result could not be worked out, and the column before 3h1 "
        "has no empty value. Delete that row before 0004 is undone "
        "(the means test works it out again)."
    )


def copy_back(apps, schema_editor):
    MeansTest = apps.get_model("eligibility", "MeansTest")
    pks = _pks(MeansTest)
    for pk in pks:
        if _raw(schema_editor, pk, "passes_means_test") is None:
            raise _no_result(pk)
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
            row = MeansTest.objects.get(pk=pk)
            for name in FIELDS:
                value = getattr(row, f"{name}_encrypted")
                setattr(row, name, OLD_DEFAULTS[name] if value is None else value)
            row.save(update_fields=FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        ("eligibility", "0004_meanstest_encrypt_add"),
    ]

    operations = [
        migrations.RunPython(copy_forward, copy_back),
    ]
