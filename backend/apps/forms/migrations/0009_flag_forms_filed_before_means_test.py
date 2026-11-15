"""Forms step 3h1: flag the means test forms filed before Form 122A-2 printed every line (O11).

A 122A-2, or a 122A-1 that ticked box 2 (the presumption box), marked filed before 3h holds
what DigniFi stored then. The flag lets the dashboard say so. Nothing is flagged again later.
"""

import json

from django.db import migrations

PRESUMPTION_BOX = "/Presumption of abuse applies"


def parts_of(values):
    """The parts a stored document holds: a parts document's own, or a flat dict as one."""
    if values.get("version") == 2:
        return values["parts"]
    return [{"kind": "form", "values": values}]


def stored_box_2(document):
    for part in parts_of(document):
        if part.get("kind") == "form":
            return part["values"].get("CheckBox1") == PRESUMPTION_BOX
    return False


def flag(apps, schema_editor):
    GeneratedForm = apps.get_model("forms", "GeneratedForm")
    rows = GeneratedForm.objects.filter(status="filed", form_type__in=("form_122a1", "form_122a2"))
    for row in rows:
        if not row.field_values:  # encrypted, so judged here and not in SQL
            continue
        try:
            document = json.loads(row.field_values)
        except ValueError:
            # The decoder's message holds only a position, but the error keeps the text, which
            # holds filer data, in its `doc`: `from None` keeps the error off the chain.
            raise RuntimeError(
                f"generated_forms row {row.pk} holds field_values that can't be read as JSON, "
                "which can mean this FIELD_ENCRYPTION_KEY isn't the one that saved them."
            ) from None
        if row.form_type == "form_122a2" or stored_box_2(document):
            row.filed_before_means_test = True
            row.save(update_fields=["filed_before_means_test"])


class Migration(migrations.Migration):

    dependencies = [
        ("forms", "0008_generatedform_filed_before_means_test"),
    ]

    operations = [
        migrations.RunPython(flag, migrations.RunPython.noop),
    ]
