"""
time_packet times one session's Generate All and each form's download (spec §7, DIG-137).

It runs on the Eco dyno before a deploy, against a real filer's database, so it must
leave every row as it found it, and a budget it misses must say which.
"""

import json
import traceback
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
from apps.forms.registry import build_parts, packet
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


def _printed_with_traceback(error):
    """What --traceback prints for the error: every exception chained to it, too."""
    return "".join(traceback.format_exception(error))


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
    # Nothing chained: --traceback prints only the command's own error.
    assert (refused.value.__cause__, refused.value.__suppress_context__) == (None, True)
    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)


def test_time_packet_names_a_session_it_cannot_find(db):
    with pytest.raises(CommandError) as refused:
        call_command("time_packet", session=404, stdout=StringIO())

    assert str(refused.value) == "No session 404."
    assert (refused.value.__cause__, refused.value.__suppress_context__) == (None, True)


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
    # Not even chained to it, where --traceback, or Sentry, would print it.
    assert refused.value.__cause__ is None
    assert "ą" not in _printed_with_traceback(refused.value)
    # Even the means test it worked out before the refusal is rolled back.
    assert (GeneratedForm.objects.count(), MeansTest.objects.count()) == (0, 0)


def _file(session, form_type, values):
    return GeneratedForm.objects.create(
        session=session,
        form_type=form_type,
        status="filed",
        generated_by=session.user,
        field_values=json.dumps(values),
    )


def _timed(session, out):
    """Each packet form's row of the table: check s, download s, PDF KB and template KB."""
    rows = [line.split() for line in out.getvalue().splitlines()]
    timed = {row[0]: row[1:] for row in rows if row and row[0] in packet(session)}
    assert set(timed) == set(packet(session))
    return timed


def test_time_packet_times_a_session_with_a_filed_form_and_draws_what_was_filed(session):
    # Generate All returns a filed form untouched, and its download draws what was filed.
    filed = _file(session, "form_101", build_parts("form_101", session))
    # A form generated, not filed, is checked again, as Generate All checks it.
    generated = GeneratedForm.objects.create(
        session=session,
        form_type="form_121",
        status="generated",
        generated_by=session.user,
        field_values=json.dumps(build_parts("form_121", session)),
    )
    # Since filing, the filer's email became one Form 101, the one form that prints it,
    # can't print: drawn from the intake, Form 101 would be refused.
    debtor = session.debtor_info
    debtor.email = "ana.wąs@example.org"
    debtor.save()
    out = StringIO()

    call_command(
        "time_packet", session=session.id, budget_generate=600, budget_download=600, stdout=out
    )

    timed = _timed(session, out)
    check, _, pdf_kb, _ = timed["form_101"]
    assert (check, float(pdf_kb) > 0) == ("filed", True)
    assert float(timed["form_121"][0]) >= 0  # a time, not "filed"
    assert sorted(GeneratedForm.objects.values_list("id", "status", "field_values")) == sorted(
        [
            (filed.id, "filed", filed.field_values),
            (generated.id, "generated", generated.field_values),
        ]
    )
    assert MeansTest.objects.count() == 0


def test_time_packet_draws_a_filed_form_stored_without_values_from_the_intake(session):
    # As the download view does: a filed form whose values were never stored is resolved
    # from the intake and drawn.
    filed = GeneratedForm.objects.create(
        session=session,
        form_type="form_101",
        status="filed",
        generated_by=session.user,
        field_values="",
    )
    out = StringIO()

    call_command(
        "time_packet", session=session.id, budget_generate=600, budget_download=600, stdout=out
    )

    check, _, pdf_kb, _ = _timed(session, out)["form_101"]
    assert (check, float(pdf_kb) > 0) == ("filed", True)
    assert list(GeneratedForm.objects.values_list("id", "status", "field_values")) == [
        (filed.id, "filed", "")
    ]
    assert MeansTest.objects.count() == 0


def test_time_packet_keeps_the_filers_letter_out_of_a_filed_forms_refusal(session):
    # Values filed before 3a2 were never checked; their download refuses a letter.
    _file(session, "form_101", {"Debtor1.Last name": "Wąsowicz"})

    with pytest.raises(CommandError) as refused:
        call_command("time_packet", session=session.id, stdout=StringIO())

    assert str(refused.value) == "form_101 was refused: UnprintableLetter"
    assert refused.value.__cause__ is None
    assert "ą" not in _printed_with_traceback(refused.value)
    assert MeansTest.objects.count() == 0


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
