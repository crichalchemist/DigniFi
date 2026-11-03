"""Load the 2026 HHS poverty guidelines (91 FR 1797, Federal Register doc. 2026-00755)."""

from datetime import date

from django.db import migrations

# Kept here, not imported, because a migration must keep running the code it shipped with.
GUIDELINE_2026 = {
    "first_person": 15960,
    "each_additional": 5680,
    # The publication date: the AO's instructions compare with the guideline "last published"
    # (3f spec §5). HHS's own effective date is 2026-01-13.
    "effective_date": date(2026, 1, 15),
    "valid_through": date(2027, 1, 31),
    "source_url": (
        "https://www.federalregister.gov/documents/2026/01/15/2026-00755/"
        "annual-update-of-the-hhs-poverty-guidelines"
    ),
}


def load_2026(apps, schema_editor):
    apps.get_model("districts", "PovertyGuideline").objects.create(**GUIDELINE_2026)


def unload_2026(apps, schema_editor):
    apps.get_model("districts", "PovertyGuideline").objects.filter(
        effective_date=GUIDELINE_2026["effective_date"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("districts", "0004_povertyguideline"),
    ]

    operations = [
        migrations.RunPython(load_2026, unload_2026),
    ]
