"""Stored car loans and mortgages become secured, the rule the Debts step applies (DIG-26).

The API dropped the step's secured flag until now, so every debt the wizard saved is unsecured.
"""

from django.db import migrations


def secure_car_loans_and_mortgages(apps, schema_editor):
    DebtInfo = apps.get_model("intake", "DebtInfo")
    DebtInfo.objects.filter(debt_type__in=["auto_loan", "mortgage"]).update(is_secured=True)


class Migration(migrations.Migration):

    dependencies = [
        ("intake", "0011_assetinfo_personal_property"),
    ]

    operations = [
        migrations.RunPython(secure_car_loans_and_mortgages, migrations.RunPython.noop),
    ]
