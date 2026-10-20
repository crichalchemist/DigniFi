"""
time_packet: how long one session's Generate All and each form's download take (spec §7).

    python manage.py time_packet --session <id> [--budget-generate 5] [--budget-download 3]

It runs the views' own code: Generate All's preparation and each packet form's check,
then each form's download, which prepares, resolves and draws the form again. A filed
form isn't checked, as Generate All returns it untouched, and its download draws what was
filed, or, with nothing stored, the current intake, as the download view does. Generate All is timed cold, as the first work of a fresh
process, the way a dyno meets its first request after waking. Each download is timed after
it, with the caches Generate All warmed, so only a filed form, which Generate All doesn't
check, is drawn cold. Both are judged against the budgets (DIG-137). Everything runs in
one transaction that is rolled back, so it writes nothing (R13).
"""

import json
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.forms.models import GeneratedForm
from apps.forms.registry import packet
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.views import _generate_and_persist, _prepare, _resolve
from apps.intake.models import IntakeSession


class Command(BaseCommand):
    help = "Time one session's Generate All and each form's download. Writes nothing."
    # The system checks build every template's widget map, which would warm the caches a
    # dyno's first request meets cold.
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--session", type=int, required=True, help="the IntakeSession id")
        parser.add_argument(
            "--budget-generate", type=float, default=5.0, help="seconds for Generate All"
        )
        parser.add_argument(
            "--budget-download", type=float, default=3.0, help="seconds for each download"
        )

    def handle(self, *args, **options):
        # Each CommandError is raised `from None`: --traceback, or Sentry, would otherwise
        # print the exception it replaces, whose sentence can quote the filer's letter.
        try:
            session = IntakeSession.objects.get(id=options["session"])
        except IntakeSession.DoesNotExist:
            raise CommandError(f"No session {options['session']}.") from None

        checks, downloads = {}, {}
        with transaction.atomic():
            started = time.perf_counter()
            try:
                _prepare(session)
                form_types = packet(session)
            except Exception as exc:
                raise CommandError(f"The session was refused: {type(exc).__name__}") from None
            filed = {
                form.form_type: form
                for form in GeneratedForm.objects.filter(session=session, status="filed")
            }
            for form_type in form_types:
                if form_type in filed:
                    continue  # Generate All returns a filed form untouched
                form_started = time.perf_counter()
                try:
                    with transaction.atomic():  # a savepoint per form, as Generate All has
                        _generate_and_persist(session, form_type, session.user)
                except Exception as exc:
                    # The type only: a refusal's sentence can quote the filer's letter.
                    raise CommandError(f"{form_type} was refused: {type(exc).__name__}") from None
                checks[form_type] = time.perf_counter() - form_started
            generate_all = time.perf_counter() - started

            for form_type in form_types:
                form_started = time.perf_counter()
                try:
                    if form_type in filed and filed[form_type].field_values:
                        # As the download view: a filed form draws what was filed
                        values = json.loads(filed[form_type].field_values)
                    else:
                        _prepare(session)
                        values = _resolve(form_type, session)
                    pdf = PDFFormFiller().fill(form_type, values)
                except Exception as exc:
                    raise CommandError(f"{form_type} was refused: {type(exc).__name__}") from None
                downloads[form_type] = (time.perf_counter() - form_started, len(pdf))
            transaction.set_rollback(True)  # write nothing (R13)

        self.stdout.write(
            f"{'form':<16}{'check s':>9}{'download s':>12}{'PDF KB':>9}{'template KB':>13}"
        )
        for form_type in form_types:
            seconds, size = downloads[form_type]
            template = Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
            check = f"{checks[form_type]:.2f}" if form_type in checks else "filed"
            self.stdout.write(
                f"{form_type:<16}{check:>9}{seconds:>12.2f}"
                f"{size / 1024:>9.0f}{template.stat().st_size / 1024:>13.0f}"
            )
        slowest = max(downloads, key=lambda form_type: downloads[form_type][0])
        self.stdout.write(
            f"Generate All: {generate_all:.2f} s (budget {options['budget_generate']:g} s)\n"
            f"Downloads: {sum(s for s, _ in downloads.values()):.2f} s in all; the slowest, "
            f"{slowest}, {downloads[slowest][0]:.2f} s (budget {options['budget_download']:g} s each)"
        )

        missed = []
        if generate_all > options["budget_generate"]:
            missed.append(
                f"Generate All took {generate_all:.2f} s, over its "
                f"{options['budget_generate']:g} s budget"
            )
        missed += [
            f"the download of {form_type} took {seconds:.2f} s, over its "
            f"{options['budget_download']:g} s budget"
            for form_type, (seconds, _) in downloads.items()
            if seconds > options["budget_download"]
        ]
        if missed:
            raise CommandError("; ".join(missed) + ".")
