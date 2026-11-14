"""Add an encrypted column beside each plaintext means test column, and the outcome (3h1 spec §7.5,
step 1).

The copy and the swap are the two migrations after it, so no RunPython shares a transaction
with an ALTER TABLE.
"""

from decimal import Decimal

import encrypted_model_fields.fields
from django.db import migrations, models

import apps.intake.fields

UNUSED = "Unused since 3h1; the housekeeping PR drops it."


def _decimal(help_text):
    return apps.intake.fields.EncryptedDecimalField(
        blank=True, decimal_places=2, help_text=help_text, max_digits=12, null=True
    )


class Migration(migrations.Migration):
    dependencies = [
        ("eligibility", "0003_remove_meanstest_qualifies_for_fee_waiver"),
    ]

    operations = [
        # A default, so undoing the swap can put the plaintext columns back on a table with rows.
        migrations.AlterField(
            model_name="meanstest",
            name="calculated_cmi",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="Current Monthly Income",
                max_digits=12,
            ),
        ),
        migrations.AlterField(
            model_name="meanstest",
            name="median_income_threshold",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="Median income for family size",
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name="meanstest",
            name="calculated_cmi_encrypted",
            field=_decimal("Current Monthly Income"),
        ),
        migrations.AddField(
            model_name="meanstest",
            name="median_income_threshold_encrypted",
            field=_decimal("Median income for family size"),
        ),
        migrations.AddField(
            model_name="meanstest",
            name="total_allowable_expenses_encrypted",
            field=_decimal(UNUSED),
        ),
        migrations.AddField(
            model_name="meanstest",
            name="disposable_income_encrypted",
            field=_decimal(UNUSED),
        ),
        migrations.AddField(
            model_name="meanstest",
            name="priority_debts_monthly_encrypted",
            field=_decimal(UNUSED),
        ),
        migrations.AddField(
            model_name="meanstest",
            name="passes_above_median_encrypted",
            field=encrypted_model_fields.fields.EncryptedBooleanField(
                blank=True, null=True, help_text=UNUSED
            ),
        ),
        migrations.AddField(
            model_name="meanstest",
            name="above_median_calculated_encrypted",
            field=encrypted_model_fields.fields.EncryptedBooleanField(
                blank=True, null=True, help_text=UNUSED
            ),
        ),
        migrations.AlterField(
            model_name="meanstest",
            name="passes_means_test",
            field=models.BooleanField(
                null=True,
                help_text=(
                    "Kept one release; nothing reads it for a decision. True at or below the "
                    "median or with no presumption, False under a presumption, empty while the "
                    "result can't be worked out (DIG-226)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="meanstest",
            name="outcome",
            field=encrypted_model_fields.fields.EncryptedCharField(
                blank=True,
                help_text=(
                    "at_or_below_median, cannot_work_out, no_presumption or presumption; "
                    "empty until worked out after 3h1."
                ),
                max_length=20,
                null=True,
            ),
        ),
    ]
