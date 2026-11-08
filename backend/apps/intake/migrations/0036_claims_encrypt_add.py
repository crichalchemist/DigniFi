"""Add an encrypted column beside each plaintext debt, contract and codebtor column (3c2 spec
section 6.1, step 1).

Written by hand with the copy and the swap in the two migrations after it, so no
RunPython shares a transaction with an ALTER TABLE.
"""

import encrypted_model_fields.fields
from django.db import migrations, models

import apps.intake.fields

RELATIONSHIP_CHOICES = [
    ("spouse", "Spouse"),
    ("former_spouse", "Former Spouse"),
    ("relative", "Relative"),
    ("friend", "Friend"),
    ("business_partner", "Business Partner"),
    ("other", "Other"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0035_assetlineanswers"),
    ]

    operations = [
        # A default on each NOT NULL plaintext text column, so undoing the swap can put it back
        # on a table with rows.
        migrations.AlterField(
            model_name="debtinfo",
            name="creditor_name",
            field=models.CharField(
                default="",
                help_text="Name of creditor or collection agency",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="debtinfo",
            name="notes",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Additional context about this amount owed",
            ),
        ),
        migrations.AlterField(
            model_name="debtinfo",
            name="collateral_description",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Description of collateral if secured debt (e.g., '2020 Honda Civic VIN: 12345')",
            ),
        ),
        migrations.AlterField(
            model_name="executorycontract",
            name="counterparty_name",
            field=models.CharField(
                default="",
                help_text="Name of other party to the contract or lease",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="executorycontract",
            name="description",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Brief description of the contract or lease",
            ),
        ),
        migrations.AlterField(
            model_name="codebtor",
            name="name",
            field=models.CharField(default="", help_text="Full name of codebtor", max_length=255),
        ),
        migrations.AlterField(
            model_name="codebtor",
            name="street_address",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="codebtor",
            name="city",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="codebtor",
            name="state",
            field=models.CharField(blank=True, default="", max_length=2),
        ),
        migrations.AlterField(
            model_name="codebtor",
            name="zip_code",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
        # Each twin is the field's final definition, so the swap's rename leaves the migration
        # state equal to the models. The three required names take a one-off default.
        migrations.AddField(
            model_name="debtinfo",
            name="creditor_name_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(
                default="", help_text="Name of creditor", max_length=255
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="debtinfo",
            name="monthly_payment_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Minimum monthly payment if still paying",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="debtinfo",
            name="notes_encrypted",
            field=encrypted_model_fields.fields.EncryptedTextField(
                blank=True,
                help_text="Additional context about this amount owed",
            ),
        ),
        migrations.AddField(
            model_name="debtinfo",
            name="collateral_description_encrypted",
            field=encrypted_model_fields.fields.EncryptedTextField(
                blank=True,
                help_text="Description of collateral if secured debt (e.g., '2020 Honda Civic VIN: 12345')",
            ),
        ),
        migrations.AddField(
            model_name="debtinfo",
            name="date_incurred_encrypted",
            field=encrypted_model_fields.fields.EncryptedTextField(
                blank=True,
                help_text="When debt was incurred",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="executorycontract",
            name="counterparty_name_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(
                default="",
                help_text="Name of other party to the contract or lease",
                max_length=255,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="executorycontract",
            name="description_encrypted",
            field=encrypted_model_fields.fields.EncryptedTextField(
                blank=True,
                help_text="Brief description of the contract or lease",
            ),
        ),
        migrations.AddField(
            model_name="codebtor",
            name="name_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(
                default="", help_text="Full name of codebtor", max_length=255
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="codebtor",
            name="street_address_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="codebtor",
            name="city_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="codebtor",
            name="state_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(blank=True, max_length=2),
        ),
        migrations.AddField(
            model_name="codebtor",
            name="zip_code_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name="codebtor",
            name="relationship_encrypted",
            field=encrypted_model_fields.fields.EncryptedCharField(
                choices=RELATIONSHIP_CHOICES, default="other", max_length=20
            ),
        ),
    ]
