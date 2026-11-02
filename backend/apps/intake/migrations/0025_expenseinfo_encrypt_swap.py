"""Drop the plaintext expense columns and take their names (3e2 spec §3.2, step 3).

The AlterFields give each amount back its default of 0 and NOT NULL, so an empty body
still saves the row with $0 amounts (DIG-153).
"""

from django.db import migrations

import apps.intake.fields


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0024_expenseinfo_encrypt_copy"),
    ]

    operations = [
        migrations.RemoveField(model_name="expenseinfo", name="rent_or_mortgage"),
        migrations.RemoveField(model_name="expenseinfo", name="utilities"),
        migrations.RemoveField(model_name="expenseinfo", name="home_maintenance"),
        migrations.RemoveField(model_name="expenseinfo", name="vehicle_payment"),
        migrations.RemoveField(model_name="expenseinfo", name="vehicle_insurance"),
        migrations.RemoveField(model_name="expenseinfo", name="vehicle_maintenance"),
        migrations.RemoveField(model_name="expenseinfo", name="food_and_groceries"),
        migrations.RemoveField(model_name="expenseinfo", name="clothing"),
        migrations.RemoveField(model_name="expenseinfo", name="medical_expenses"),
        migrations.RemoveField(model_name="expenseinfo", name="childcare"),
        migrations.RemoveField(model_name="expenseinfo", name="child_support_paid"),
        migrations.RemoveField(model_name="expenseinfo", name="insurance_not_deducted"),
        migrations.RemoveField(model_name="expenseinfo", name="other_expenses"),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="rent_or_mortgage_encrypted",
            new_name="rent_or_mortgage",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="utilities_encrypted",
            new_name="utilities",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="home_maintenance_encrypted",
            new_name="home_maintenance",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="vehicle_payment_encrypted",
            new_name="vehicle_payment",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="vehicle_insurance_encrypted",
            new_name="vehicle_insurance",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="vehicle_maintenance_encrypted",
            new_name="vehicle_maintenance",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="food_and_groceries_encrypted",
            new_name="food_and_groceries",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="clothing_encrypted",
            new_name="clothing",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="medical_expenses_encrypted",
            new_name="medical_expenses",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="childcare_encrypted",
            new_name="childcare",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="child_support_paid_encrypted",
            new_name="child_support_paid",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="insurance_not_deducted_encrypted",
            new_name="insurance_not_deducted",
        ),
        migrations.RenameField(
            model_name="expenseinfo",
            old_name="other_expenses_encrypted",
            new_name="other_expenses",
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="rent_or_mortgage",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0, decimal_places=2, help_text="Monthly housing payment", max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="utilities",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0, decimal_places=2, help_text="Gas, electric, water, etc.", max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="home_maintenance",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0, decimal_places=2, help_text="Repairs and upkeep", max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="vehicle_payment",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0, decimal_places=2, help_text="Car loan or lease payment", max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="vehicle_insurance",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0, decimal_places=2, max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="vehicle_maintenance",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0, decimal_places=2, help_text="Gas, repairs, registration", max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="food_and_groceries",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0, decimal_places=2, max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="clothing",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0, decimal_places=2, max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="medical_expenses",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0,
                decimal_places=2,
                help_text="Out-of-pocket healthcare costs",
                max_digits=10,
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="childcare",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0, decimal_places=2, max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="child_support_paid",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0,
                decimal_places=2,
                help_text="Court-ordered support payments",
                max_digits=10,
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="insurance_not_deducted",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0,
                decimal_places=2,
                help_text="Health, life, or disability insurance not deducted from paycheck",
                max_digits=10,
            ),
        ),
        migrations.AlterField(
            model_name="expenseinfo",
            name="other_expenses",
            field=apps.intake.fields.EncryptedDecimalField(
                default=0,
                decimal_places=2,
                help_text="Other necessary monthly expenses",
                max_digits=10,
            ),
        ),
    ]
