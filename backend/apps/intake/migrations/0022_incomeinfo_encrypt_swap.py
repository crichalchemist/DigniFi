"""Drop the plaintext income columns and take their names (3e2 spec §3.2, step 3)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0021_incomeinfo_encrypt_copy"),
    ]

    operations = [
        migrations.RemoveField(model_name="incomeinfo", name="monthly_gross_wages"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_overtime"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_tips"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_rental_income"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_pension"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_social_security"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_unemployment"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_child_support"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_alimony"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_other_income"),
        migrations.RemoveField(model_name="incomeinfo", name="monthly_income"),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_gross_wages_encrypted",
            new_name="monthly_gross_wages",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_overtime_encrypted",
            new_name="monthly_overtime",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_tips_encrypted",
            new_name="monthly_tips",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_rental_income_encrypted",
            new_name="monthly_rental_income",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_pension_encrypted",
            new_name="monthly_pension",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_social_security_encrypted",
            new_name="monthly_social_security",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_unemployment_encrypted",
            new_name="monthly_unemployment",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_child_support_encrypted",
            new_name="monthly_child_support",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_alimony_encrypted",
            new_name="monthly_alimony",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_other_income_encrypted",
            new_name="monthly_other_income",
        ),
        migrations.RenameField(
            model_name="incomeinfo",
            old_name="monthly_income_encrypted",
            new_name="monthly_income",
        ),
    ]
