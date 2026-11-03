"""Add an encrypted column beside each plaintext expense column (3e2 spec §3.2, step 1)."""

from django.db import migrations

import apps.intake.fields


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0022_incomeinfo_encrypt_swap"),
    ]

    operations = [
        migrations.AddField(
            model_name="expenseinfo",
            name="rent_or_mortgage_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Monthly housing payment",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="utilities_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Gas, electric, water, etc.",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="home_maintenance_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Repairs and upkeep",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="vehicle_payment_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Car loan or lease payment",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="vehicle_insurance_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="vehicle_maintenance_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Gas, repairs, registration",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="food_and_groceries_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="clothing_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="medical_expenses_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Out-of-pocket healthcare costs",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="childcare_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="child_support_paid_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Court-ordered support payments",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="insurance_not_deducted_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Health, life, or disability insurance not deducted from paycheck",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="expenseinfo",
            name="other_expenses_encrypted",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Other necessary monthly expenses",
                max_digits=10,
                null=True,
            ),
        ),
    ]
