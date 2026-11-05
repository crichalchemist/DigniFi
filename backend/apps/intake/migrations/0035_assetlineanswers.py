"""The filer's Yes and No answers to Schedule A/B's lines (3b spec §3.2)."""

import django.db.models.deletion
import encrypted_model_fields.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0034_assetinfo_encrypt_swap"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetLineAnswers",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("answers", encrypted_model_fields.fields.EncryptedTextField(default="{}")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "session",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="asset_lines",
                        to="intake.intakesession",
                    ),
                ),
            ],
            options={"db_table": "asset_line_answers"},
        ),
    ]
