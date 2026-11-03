"""Carry each fee-waiver application into the filing fee's line 8 answer (3f spec §4).

Forward: each session with a FeeWaiverApplication and no FilingFee gets a FilingFee whose
payment_choice is "waiver", so its packet keeps 103B once the application table goes. A
session that already has a FilingFee keeps it as it is, whatever it holds.

Reverse: each FilingFee whose payment_choice is "waiver", on a session with no application,
gets a bare one-person FeeWaiverApplication. The typed answers (household size, take-home
pay, non-cash help) don't come back on undo: they now come from the household list,
Schedule I and 8f. The FilingFee rows the forward created stay, since they can't be told
from the filer's own.

payment_choice is encrypted with a fresh IV on every write, so it is compared in Python,
never filtered on in SQL.
"""

from django.db import migrations


def carry_waiver_choice(apps, schema_editor) -> None:
    FeeWaiverApplication = apps.get_model("intake", "FeeWaiverApplication")
    FilingFee = apps.get_model("intake", "FilingFee")
    has_fee = set(FilingFee.objects.values_list("session_id", flat=True))
    for session_id in FeeWaiverApplication.objects.values_list("session_id", flat=True):
        if session_id not in has_fee:
            FilingFee.objects.create(session_id=session_id, payment_choice="waiver")


def restore_bare_applications(apps, schema_editor) -> None:
    FeeWaiverApplication = apps.get_model("intake", "FeeWaiverApplication")
    FilingFee = apps.get_model("intake", "FilingFee")
    has_application = set(FeeWaiverApplication.objects.values_list("session_id", flat=True))
    for fee in FilingFee.objects.all():
        if fee.payment_choice == "waiver" and fee.session_id not in has_application:
            FeeWaiverApplication.objects.create(session_id=fee.session_id, household_size=1)


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0029_filingfee"),
    ]

    operations = [
        migrations.RunPython(carry_waiver_choice, restore_bare_applications),
    ]
