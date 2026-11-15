"""Load the Bankruptcy Code dollar amounts for cases filed on or after 2025-04-01."""

from datetime import date
from decimal import Decimal

from django.db import migrations

# Kept here, not imported, because a migration must keep running the code it shipped with.
AMOUNTS_2025 = {
    "effective_date": date(2025, 4, 1),
    "valid_through": date(2028, 3, 31),
    "source_url": (
        "https://www.federalregister.gov/documents/2025/02/04/2025-02207/"
        "adjustment-of-certain-dollar-amounts-applicable-to-bankruptcy-cases"
    ),
    "presumption_low": Decimal("10275"),
    "presumption_high": Decimal("17150"),
    "education_per_child_monthly": Decimal("214.58"),  # the form's own figure for $2,575 a year
    "chapter_13_unsecured_limit": Decimal("526700"),
    "chapter_13_secured_limit": Decimal("1580125"),
}


def load_2025(apps, schema_editor):
    apps.get_model("districts", "Section104Amounts").objects.create(**AMOUNTS_2025)


def unload_2025(apps, schema_editor):
    apps.get_model("districts", "Section104Amounts").objects.filter(
        effective_date=AMOUNTS_2025["effective_date"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("districts", "0010_means_standards_2026"),
    ]

    operations = [
        migrations.RunPython(load_2025, unload_2025),
    ]
