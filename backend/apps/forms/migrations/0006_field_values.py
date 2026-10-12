"""Forms step 1: encrypted field_values replaces form_data, which is blanked (DIG-124)."""

import encrypted_model_fields.fields
from django.db import migrations, models


def blank_form_data(apps, schema_editor):
    GeneratedForm = apps.get_model("forms", "GeneratedForm")
    GeneratedForm.objects.update(form_data={})


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0005_remove_form_122b"),
    ]

    operations = [
        migrations.AddField(
            model_name="generatedform",
            name="field_values",
            field=encrypted_model_fields.fields.EncryptedTextField(
                blank=True, default="", help_text="Encrypted JSON"
            ),
        ),
        migrations.AlterField(
            model_name="generatedform",
            name="form_data",
            field=models.JSONField(default=dict, help_text="Unused; see field_values"),
        ),
        migrations.RunPython(blank_form_data, migrations.RunPython.noop),
    ]
