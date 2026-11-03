from django.db import migrations
from django.db.models import F


def forward(apps, schema_editor):
    """Take-home pay is step 3, so every step from Expenses (3) to Review (8) moves up one.

    A value outside 1-8, stored before update_step checked its range (DIG-151), is left alone.
    One UPDATE, so no row is moved twice.
    """
    IntakeSession = apps.get_model("intake", "IntakeSession")
    IntakeSession.objects.filter(current_step__gte=3, current_step__lte=8).update(
        current_step=F("current_step") + 1
    )


def reverse(apps, schema_editor):
    """Moves 4-9 down one. A 3 (Take-home pay) stays 3, the old Expenses, the step after it."""
    IntakeSession = apps.get_model("intake", "IntakeSession")
    IntakeSession.objects.filter(current_step__gte=4, current_step__lte=9).update(
        current_step=F("current_step") - 1
    )


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0027_expenseinfo_schedule_j_lines"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
