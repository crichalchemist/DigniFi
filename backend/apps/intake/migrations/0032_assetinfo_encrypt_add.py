"""Add Schedule A/B's columns and an encrypted column beside each plaintext asset column
(3b spec §3.1, step 1).

Written by hand with the copy and the swap in the two migrations after it, so no
RunPython shares a transaction with an ALTER TABLE.
"""

import encrypted_model_fields.fields
from django.db import migrations, models

import apps.intake.fields


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0031_delete_feewaiverapplication"),
    ]

    operations = [
        # A default, so undoing the swap can put the plaintext columns back on a table with rows.
        migrations.AlterField(
            model_name="assetinfo",
            name="description",
            field=models.CharField(
                default="",
                help_text="Brief description (e.g., '2015 Honda Civic', '123 Main St')",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="assetinfo",
            name="financial_institution",
            field=models.CharField(
                blank=True, default="", help_text="Bank or institution name", max_length=100
            ),
        ),
        migrations.AddField(
            model_name="assetinfo",
            name="description_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(
                blank=True,
                default="",
                help_text="Brief description (e.g., '2015 Honda Civic', '123 Main St')",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="assetinfo",
            name="financial_institution_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(
                blank=True,
                default="",
                help_text="Bank or institution name",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="assetinfo",
            name="ab_line",
            field=encrypted_model_fields.fields.EncryptedCharField(
                blank=True, max_length=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="assetinfo",
            name="details",
            field=encrypted_model_fields.fields.EncryptedTextField(blank=True, default="{}"),
        ),
        migrations.AddField(
            model_name="assetinfo",
            name="entire_value",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Value of the entire property, when the filer owns a share",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="assetinfo",
            name="current_value",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Current fair market value",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="assetinfo",
            name="asset_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("real_property", "Real Estate/Home"),
                    ("vehicle", "Vehicle"),
                    ("bank_account", "Bank Account"),
                    ("retirement_account", "Retirement Account (401k, IRA)"),
                    ("personal_property", "Personal Property (furniture, jewelry, collectibles)"),
                    ("other", "Other Asset"),
                ],
                max_length=30,
                null=True,
            ),
        ),
        migrations.AlterModelOptions(name="assetinfo", options={}),
    ]
