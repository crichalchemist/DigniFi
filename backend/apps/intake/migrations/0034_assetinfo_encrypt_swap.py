"""Drop the plaintext asset columns and take their names (3b spec §3.1, step 3)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0033_assetinfo_encrypt_copy"),
    ]

    operations = [
        migrations.RemoveField(model_name="assetinfo", name="description"),
        migrations.RemoveField(model_name="assetinfo", name="financial_institution"),
        migrations.RenameField(
            model_name="assetinfo",
            old_name="description_encrypted",
            new_name="description",
        ),
        migrations.RenameField(
            model_name="assetinfo",
            old_name="financial_institution_encrypted",
            new_name="financial_institution",
        ),
    ]
