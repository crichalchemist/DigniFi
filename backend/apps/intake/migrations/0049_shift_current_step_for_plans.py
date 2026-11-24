from django.db import migrations


def forward(apps, schema_editor):
    """Your Plans is step 9, so Review moves from 9 to 10.

    A value outside 1-9, stored before update_step checked its range (DIG-151), is left alone.
    """
    IntakeSession = apps.get_model("intake", "IntakeSession")
    IntakeSession.objects.filter(current_step=9).update(current_step=10)


def reverse(apps, schema_editor):
    """Moves 10 back to 9. A 9 (Your Plans) stays 9, the old Review, the step after it."""
    IntakeSession = apps.get_model("intake", "IntakeSession")
    IntakeSession.objects.filter(current_step=10).update(current_step=9)


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0048_intention_answers"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
