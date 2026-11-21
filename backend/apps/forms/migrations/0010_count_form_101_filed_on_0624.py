"""Forms step 4b: count the Form 101 rows filed on the retired 06/24 revision (4b-R7).

A filed form keeps the values it was filed with, and those name boxes the 11/26 template lacks,
so its download is a 422 saying DigniFi can no longer print it and the filer should keep the
copy they gave the court (only a filed Form 101 gets it; any other filed form whose stored keys
the template lacks stays a logged 500). The count tells an operator how many filers that
reaches. It holds no filer value.
"""

from django.db import migrations

# The 11/26 template's hash, the `template_version` of data/forms/schemas/form_101.json.
NEW_HASH = "f9b8f6b2d11540fce286914c153003aa058ca125b6171e78f3bb440f810c5950"


def count(apps, schema_editor):
    GeneratedForm = apps.get_model("forms", "GeneratedForm")
    AuditLog = apps.get_model("audit", "AuditLog")
    n = (
        GeneratedForm.objects.filter(status="filed", form_type="form_101")
        .exclude(template_version=NEW_HASH)
        .count()
    )
    AuditLog.objects.create(
        user=None,
        action="form_101_filed_on_0624",
        resource_type="GeneratedForm",
        details={"count": n},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("forms", "0009_flag_forms_filed_before_means_test"),
        ("audit", "0003_fix_user_agent_default"),
    ]

    operations = [
        migrations.RunPython(count, migrations.RunPython.noop),
    ]
