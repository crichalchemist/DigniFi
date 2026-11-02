"""Add an encrypted column beside each plaintext income column (3e2 spec §3.2, step 1).

Written by hand with the copy and the swap in the two migrations after it, so no
RunPython shares a transaction with an ALTER TABLE.
"""

import encrypted_model_fields.fields
from django.db import migrations

import apps.intake.fields


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0019_remove_incomeinfo_number_of_dependents"),
    ]

    operations = [
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_gross_wages_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_overtime_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_tips_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_rental_income_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="After the property's costs",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_pension_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_social_security_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_unemployment_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_child_support_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Child support received",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_alimony_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, help_text="Alimony received", max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_other_income_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_income_encrypted",
            field=encrypted_model_fields.fields.EncryptedTextField(
                blank=True, help_text="6-month income array", null=True
            ),
        ),
    ]
