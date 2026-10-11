"""Form 122B is the Chapter 11 means-test statement; it leaves the Chapter 7 packet (DIG-125)."""

from django.db import migrations, models


def delete_form_122b_rows(apps, schema_editor):
    GeneratedForm = apps.get_model("forms", "GeneratedForm")
    GeneratedForm.objects.filter(form_type="form_122b").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0004_add_five_form_types"),
    ]

    operations = [
        migrations.RunPython(delete_form_122b_rows, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="generatedform",
            name="form_type",
            field=models.CharField(
                choices=[
                    ("form_101", "Form 101 - Voluntary Petition"),
                    ("form_103b", "Form 103B - Fee Waiver Application"),
                    ("form_106dec", "Form 106Dec - Declaration"),
                    ("form_106sum", "Form 106Sum - Summary of Assets/Liabilities"),
                    ("form_107", "Form 107 - Statement of Financial Affairs"),
                    ("form_121", "Form 121 - SSN Statement"),
                    ("form_122a1", "Form 122A-1 - Means Test"),
                    ("form_122a1_supp", "Form 122A-1 Supplement"),
                    ("form_122a2", "Form 122A-2 - Means Test Calculation"),
                    ("schedule_a_b", "Schedule A/B - Property"),
                    ("schedule_c", "Schedule C - Exemptions"),
                    ("schedule_d", "Schedule D - Secured Creditors"),
                    ("schedule_e_f", "Schedule E/F - Unsecured Creditors"),
                    ("schedule_g", "Schedule G - Executory Contracts/Leases"),
                    ("schedule_h", "Schedule H - Codebtors"),
                    ("schedule_i", "Schedule I - Income"),
                    ("schedule_j", "Schedule J - Expenses"),
                ],
                help_text="Type of bankruptcy form",
                max_length=20,
            ),
        ),
    ]
