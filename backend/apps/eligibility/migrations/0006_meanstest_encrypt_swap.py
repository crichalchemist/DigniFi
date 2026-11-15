"""Drop the plaintext means test columns, take their names and set the final field definitions
(3h1 spec §7.5, step 3).

Written by hand: from 0004's state makemigrations would see each encrypted copy as removed and
the old column as altered in place, which would drop the encrypted values.
"""

from decimal import Decimal

import encrypted_model_fields.fields
from django.db import migrations

import apps.intake.fields

UNUSED = "Unused since 3h1; the housekeeping PR drops it."
OLD_COLUMNS = [
    "calculated_cmi",
    "median_income_threshold",
    "total_allowable_expenses",
    "disposable_income",
    "priority_debts_monthly",
    "passes_above_median",
    "above_median_calculated",
]


def _unused_decimal():
    return apps.intake.fields.EncryptedDecimalField(
        decimal_places=2, default=Decimal("0"), help_text=UNUSED, max_digits=12
    )


def _unused_boolean():
    return encrypted_model_fields.fields.EncryptedBooleanField(default=False, help_text=UNUSED)


class Migration(migrations.Migration):
    dependencies = [
        ("eligibility", "0005_meanstest_encrypt_copy"),
    ]

    operations = [
        *[migrations.RemoveField(model_name="meanstest", name=name) for name in OLD_COLUMNS],
        *[
            migrations.RenameField(
                model_name="meanstest", old_name=f"{name}_encrypted", new_name=name
            )
            for name in OLD_COLUMNS
        ],
        migrations.AlterField(
            model_name="meanstest",
            name="calculated_cmi",
            field=apps.intake.fields.EncryptedDecimalField(
                decimal_places=2, help_text="Current Monthly Income", max_digits=12
            ),
        ),
        migrations.AlterField(
            model_name="meanstest",
            name="median_income_threshold",
            field=apps.intake.fields.EncryptedDecimalField(
                decimal_places=2, help_text="Median income for family size", max_digits=12
            ),
        ),
        migrations.AlterField(
            model_name="meanstest", name="total_allowable_expenses", field=_unused_decimal()
        ),
        migrations.AlterField(
            model_name="meanstest", name="disposable_income", field=_unused_decimal()
        ),
        migrations.AlterField(
            model_name="meanstest", name="priority_debts_monthly", field=_unused_decimal()
        ),
        migrations.AlterField(
            model_name="meanstest", name="passes_above_median", field=_unused_boolean()
        ),
        migrations.AlterField(
            model_name="meanstest", name="above_median_calculated", field=_unused_boolean()
        ),
    ]
