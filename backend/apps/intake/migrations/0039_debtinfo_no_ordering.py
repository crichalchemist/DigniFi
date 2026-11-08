from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0038_claims_encrypt_swap"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="debtinfo",
            options={},
        ),
    ]
