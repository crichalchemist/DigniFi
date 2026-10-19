"""
time_packet times one session's Generate All and each form's download (spec §7, DIG-137).

It runs on the Eco dyno before a deploy, against a real filer's database, so it must
leave every row as it found it, and a budget it misses must say which.
"""

from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.districts.models import District
from apps.eligibility.models import MeansTest
from apps.forms.models import GeneratedForm
from apps.forms.registry import packet
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    """A completed intake with no means test and no forms yet, so any row it wrote would show."""
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    session = IntakeSession.objects.create(
        user=User.objects.create_user(username="timed", password="pw"),
        district=District.objects.get(code="ilnd"),
        status="completed",
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Ana",
        last_name="Okafor",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
    return session


def test_time_packet_writes_nothing(session):
    out = StringIO()

    call_command(
        "time_packet", session=session.id, budget_generate=600, budget_download=600, stdout=out
    )

    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)
    # It timed every form of the packet, which the means test it worked out decided: one
    # row each of form, check s, download s, PDF KB and template KB.
    printed = out.getvalue()
    assert "Generate All: " in printed
    form_types = packet(session)
    rows = [line.split() for line in printed.splitlines()]
    timed = {row[0]: row[1:] for row in rows if row and row[0] in form_types}
    assert set(timed) == set(form_types)
    # Each download drew its form: a check alone makes no PDF, which prints as 0 KB.
    assert all(
        float(pdf_kb) > 0 and float(template_kb) > 0 for _, _, pdf_kb, template_kb in timed.values()
    )


def test_time_packet_refuses_an_unfinished_intake_and_writes_nothing(session):
    session.status = "in_progress"
    session.save()

    with pytest.raises(CommandError) as refused:
        call_command("time_packet", session=session.id, stdout=StringIO())

    assert str(refused.value) == "The session was refused: IntakeNotFinished"
    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)


def test_time_packet_refusal_writes_nothing_and_keeps_the_filers_letter_out(session):
    # An invented surname: ą is outside the court form's font, which would print "?".
    debtor = session.debtor_info
    debtor.last_name = "Wąsowicz"
    debtor.save()

    with pytest.raises(CommandError) as refused:
        call_command("time_packet", session=session.id, stdout=StringIO())

    # The type only: a refusal's sentence quotes the filer's letter.
    message = str(refused.value)
    assert message == "form_101 was refused: UnprintableLetter"
    assert "ą" not in message
    assert "Wąsowicz" not in message
    # Even the means test it worked out before the refusal is rolled back.
    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)


def test_time_packet_names_the_budget_it_missed(session):
    with pytest.raises(CommandError) as missed:
        call_command(
            "time_packet",
            session=session.id,
            budget_generate=0,
            budget_download=0,
            stdout=StringIO(),
        )

    assert "Generate All took " in str(missed.value)
    assert "the download of form_101 took " in str(missed.value)
    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)
