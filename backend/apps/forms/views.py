"""
API views for bankruptcy form generation.

One path fills every form: registry.build_parts() resolves a session's values,
PDFFormFiller checks that the template can print them, and they are kept as an
encrypted parts document (GeneratedForm.field_values) that the API never returns.
Generate, Generate All and Regenerate only check; Download draws (spec §7).
"""

import json
import logging

import django_filters
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.districts.dated_tables import NoTableInForce
from apps.eligibility.cmi import IncomeNotSplit
from apps.eligibility.models import MeansTest
from apps.eligibility.services import MeansTestCalculator
from apps.intake.models import IntakeSession

from .models import GeneratedForm
from .registry import (
    FORM_REGISTRY,
    PreconditionMissing,
    build_parts,
    get_all_form_types,
    packet,
)
from .schema import load_schema
from .serializers import GeneratedFormSerializer
from .services.fill_resolver import UnmappedChoice
from .services.pdf_filler import (
    PDFFormFiller,
    TemplateHasNoForm,
    UnprintableLetter,
    ValueTooLong,
)

logger = logging.getLogger(__name__)


class NotInPacket(Exception):
    """The form isn't part of this filer's packet (registry applies() is false)."""


class FormIsFiled(Exception):
    """The form is marked filed, so it keeps the values it was filed with (spec §5.5)."""


class IntakeNotFinished(Exception):
    """The filer hasn't completed the intake, so an empty list can't yet mean "none"."""

    page = "/intake"  # where the filer finishes it


# Failures a filer can act on: 422 in plain words (spec §5.7). Anything else is a 500.
# PreconditionMissing, IncomeNotSplit and NoTableInForce carry their own plain reasons
# (registry.py, eligibility/cmi.py, districts/dated_tables.py, which logs its own
# refusal), and so do UnprintableLetter and ValueTooLong (pdf_filler.py), which name the
# letter and the box. Every other class gets a fixed sentence, because their messages
# name form keys and PDF widgets. None names the form: the dashboard shows
# its label beside the error.
_FAILURE_SENTENCES = {
    IntakeNotFinished: "Finish your intake before preparing your forms.",
    NotInPacket: "This form isn't part of your packet, based on the answers you've given.",
    FormIsFiled: "This form is marked as filed, so it keeps the answers it was filed with.",
    UnmappedChoice: (
        "One of your answers doesn't match a choice printed on this form, "
        "so it can't be filled in yet."
    ),
    TemplateHasNoForm: "This form's blank court template can't be filled in right now.",
}


def _failure(form_type: str | None, exc: Exception) -> tuple[dict, int]:
    """The error body and status for a form that could not be filled.

    form_type is None when the whole call is refused before any form is filled (Generate
    All, the packet list): the body then names no form. A refusal the filer fixes on a
    wizard step or a page also carries that `step` or `page` (forms step 3a1 spec §4.3).
    """
    if isinstance(
        exc,
        PreconditionMissing | IncomeNotSplit | NoTableInForce | UnprintableLetter | ValueTooLong,
    ):
        error = str(exc)
    else:
        error = _FAILURE_SENTENCES.get(type(exc))
    code = status.HTTP_422_UNPROCESSABLE_ENTITY
    if error is None:
        # Type only: a message or traceback can quote filer data, and logs reach Sentry (DIG-105).
        logger.error("Filling %s failed: %s", form_type or "the packet", type(exc).__name__)
        error = "This form couldn't be prepared. Please try again later."
        code = status.HTTP_500_INTERNAL_SERVER_ERROR
    body = {"error": error} if form_type is None else {"form_type": form_type, "error": error}
    if code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        # Only a refusal: an unexpected exception's own step or page attribute means nothing here.
        for key in ("step", "page"):
            if getattr(exc, key, None):
                body[key] = getattr(exc, key)
    return body, code


def _session_or_error(
    request, session_id, param: str = "session_id"
) -> tuple[IntakeSession | None, Response | None]:
    """The requesting user's session, or (None, a 400/404 Response). param names the input."""
    if not session_id:
        return None, Response(
            {"error": f"{param} is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        return IntakeSession.objects.get(id=session_id, user=request.user), None
    except (IntakeSession.DoesNotExist, ValueError):
        return None, Response(
            {"error": "Session not found or you don't have permission"},
            status=status.HTTP_404_NOT_FOUND,
        )


def _validate_form_type(form_type: str | None) -> Response | None:
    """Return an error Response if form_type is missing or unknown, else None."""
    if not form_type:
        return Response(
            {"error": "form_type is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if form_type not in FORM_REGISTRY:
        return Response(
            {
                "error": f"Unknown form_type: {form_type}",
                "valid_types": get_all_form_types(),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def _check_finished(session: IntakeSession) -> None:
    """Refuse an intake the filer hasn't completed (step 2 spec §5.3).

    Only the intake's complete action sets "completed", and an edit to intake data
    after it sets the intake back to in progress.
    """
    if session.status != "completed":
        raise IntakeNotFinished()


def _recalculate_means_test(session: IntakeSession) -> None:
    """Work the means test out again from the stored intake (step 2 spec §5.6).

    It runs before the packet is decided, so a result worked out from income the filer has
    since changed never decides which forms they get (DIG-160). Raises IncomeNotSplit when
    the income isn't entered by source, and NoTableInForce when no median income table is in
    force on the fill date, which operations must fix.
    """
    if getattr(session, "income_info", None) is None:
        # No income at all is income not entered by source, as derivations._cmi rules.
        raise IncomeNotSplit()
    MeansTestCalculator(session).calculate()


def _tables_used(session: IntakeSession) -> list[dict]:
    """The dated tables the session's means test used (forms step 3a1 spec §3.6).

    Empty when there is no means test, or a stored one that predates the record.
    """
    means_test = MeansTest.objects.filter(session=session).first()
    table = means_test.get_calculation_details().get("median_table") if means_test else None
    return [table] if table else []


def _prepare(session: IntakeSession) -> None:
    """Refuse an unfinished intake, then work its means test out again. Once per call."""
    _check_finished(session)
    _recalculate_means_test(session)


def _resolve(form_type: str, session: IntakeSession) -> dict:
    """The parts a form that applies to this filer prints. _prepare() runs first."""
    if not FORM_REGISTRY[form_type].applies(session):
        raise NotInPacket()
    return build_parts(form_type, session)


def _store(generated_form: GeneratedForm, document: dict) -> None:
    generated_form.field_values = json.dumps(document)
    generated_form.template_version = load_schema(generated_form.form_type).template_version


def _generate_and_persist(session: IntakeSession, form_type: str, user) -> GeneratedForm:
    """Check that the form prints its values, without drawing it, and keep them (spec §7).

    _prepare() runs first.
    """
    if GeneratedForm.objects.filter(session=session, form_type=form_type, status="filed").exists():
        raise FormIsFiled()
    document = _resolve(form_type, session)
    PDFFormFiller().check(form_type, document)
    generated_form, _ = GeneratedForm.objects.get_or_create(
        session=session, form_type=form_type, defaults={"generated_by": user}
    )
    _store(generated_form, document)
    generated_form.status = "generated"
    generated_form.generated_by = user
    generated_form.save()
    return generated_form


class GeneratedFormFilter(django_filters.FilterSet):
    """GET /api/forms/?session=<id>, as the dashboard asks."""

    # Only the requester's own sessions are valid choices, so another user's session id
    # gets the same 400 as one that doesn't exist: the list never says which ids exist.
    session = django_filters.ModelChoiceFilter(
        queryset=lambda request: IntakeSession.objects.filter(user=request.user)
    )

    class Meta:
        model = GeneratedForm
        fields = ["session"]


class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for bankruptcy form generation and management.

    Endpoints:
      GET  /api/forms/packet/?session=<id>  The packet's form types and its median table
      POST /api/forms/generate/              Generate a single form
      POST /api/forms/generate_all/          Generate every form in the packet
      POST /api/forms/{id}/regenerate/       Regenerate an existing form
      GET  /api/forms/{id}/download/         Draw and stream the PDF
      POST /api/forms/{id}/mark_downloaded/
      POST /api/forms/{id}/mark_filed/
    """

    serializer_class = GeneratedFormSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = GeneratedFormFilter

    def get_queryset(self):
        """Return only forms for the authenticated user's sessions."""
        return GeneratedForm.objects.filter(session__user=self.request.user).select_related(
            "session", "generated_by"
        )

    # ------------------------------------------------------------------
    # The packet
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"])
    def packet(self, request):
        """
        The ordered form types that apply to this filer.

        GET /api/forms/packet/?session=1

        For a completed intake the means test is worked out again first, and a refusal
        covers the whole list. An unfinished intake gets the packet its stored data gives,
        and is never refused (step 2 spec §5.3, §5.6). `tables` holds the median table the means
        test recorded, and is `[]` when there is no means test or it recorded none.
        """
        session, err = _session_or_error(request, request.query_params.get("session"), "session")
        if err:
            return err
        if session.status == "completed":
            try:
                _recalculate_means_test(session)
            except Exception as exc:
                body, code = _failure(None, exc)
                return Response(body, status=code)
        return Response(
            {"session": session.id, "form_types": packet(session), "tables": _tables_used(session)}
        )

    # ------------------------------------------------------------------
    # Generate single form
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """
        Generate a single bankruptcy form.

        POST /api/forms/generate/
        { "session_id": 1, "form_type": "form_101" }
        """
        session, err = _session_or_error(request, request.data.get("session_id"))
        if err:
            return err

        form_type = request.data.get("form_type")
        err = _validate_form_type(form_type)
        if err:
            return err

        try:
            _prepare(session)
            generated_form = _generate_and_persist(session, form_type, request.user)
        except Exception as exc:
            body, code = _failure(form_type, exc)
            return Response(body, status=code)
        return Response(
            {
                "form": self.get_serializer(generated_form).data,
                "message": f"{generated_form.get_form_type_display()} generated successfully",
            }
        )

    # ------------------------------------------------------------------
    # Generate all forms for a session
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="generate_all")
    def generate_all(self, request):
        """
        Generate every form in the filer's packet.

        POST /api/forms/generate_all/
        { "session_id": 1 }

        Each form gets its own savepoint, so one form's failure can't undo the
        others. Rows for forms that no longer apply are deleted. A filed form is
        returned as it is, in the packet or out of it: not resolved again, not
        un-filed, not deleted (DIG-155). An unfinished intake, or a means test that
        can't be worked out, gets one refusal for the whole packet, before anything
        is deleted.
        """
        session, err = _session_or_error(request, request.data.get("session_id"))
        if err:
            return err
        try:
            _prepare(session)
        except Exception as exc:
            body, code = _failure(None, exc)
            return Response(body, status=code)

        form_types = packet(session)
        GeneratedForm.objects.filter(session=session).exclude(form_type__in=form_types).exclude(
            status="filed"
        ).delete()
        filed = {
            f.form_type: f for f in GeneratedForm.objects.filter(session=session, status="filed")
        }

        results = []
        errors = []
        for form_type in form_types:
            if form_type in filed:
                results.append(self.get_serializer(filed[form_type]).data)
                continue
            try:
                with transaction.atomic():
                    generated_form = _generate_and_persist(session, form_type, request.user)
                results.append(self.get_serializer(generated_form).data)
            except Exception as exc:
                errors.append(_failure(form_type, exc)[0])
        # Filed forms that left the packet go last: the dashboard replaces its list with
        # `generated`, so a form missing from it would vanish from the dashboard.
        results += [
            self.get_serializer(form).data
            for form_type, form in filed.items()
            if form_type not in form_types
        ]

        return Response(
            {
                "generated": results,
                "errors": errors,
                "total_generated": len(results),
                "total_errors": len(errors),
            }
        )

    # ------------------------------------------------------------------
    # Regenerate existing form
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """
        Regenerate an existing form with updated session data.

        POST /api/forms/{id}/regenerate/
        """
        generated_form = self.get_object()
        try:
            _prepare(generated_form.session)
            generated_form = _generate_and_persist(
                generated_form.session, generated_form.form_type, request.user
            )
        except Exception as exc:
            body, code = _failure(generated_form.form_type, exc)
            return Response(body, status=code)
        return Response(
            {
                "form": self.get_serializer(generated_form).data,
                "message": "Form regenerated successfully",
            }
        )

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"])
    def mark_downloaded(self, request, pk=None):
        """Mark form as downloaded by the user."""
        generated_form = self.get_object()

        if generated_form.status == "generated":
            generated_form.status = "downloaded"
            generated_form.save()

        return Response(
            {
                "form_id": generated_form.id,
                "status": generated_form.status,
                "message": "Form marked as downloaded",
            }
        )

    @action(detail=True, methods=["post"])
    def mark_filed(self, request, pk=None):
        """Mark form as filed with the court."""
        generated_form = self.get_object()

        generated_form.status = "filed"
        generated_form.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "form_id": generated_form.id,
                "status": generated_form.status,
                "message": "Form marked as filed with court",
            }
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """
        Draw the official AO template and stream it.

        A form not yet filed is resolved, checked and drawn fresh, so the filer always
        downloads their current answers, and its parts are stored again if its status is
        still the one read before drawing: a form marked filed meanwhile keeps the values
        it was filed with. A filed form draws its stored parts, or its values stored before
        3a2, so it matches what was filed, even after it has left the packet (DIG-155). A
        filed form with no stored values is drawn as one not yet filed, through the completion
        and packet checks, from the current intake, and the parts it draws are kept as its
        filed ones.
        """
        generated_form = self.get_object()
        form_type = generated_form.form_type
        session = generated_form.session
        filed = generated_form.status == "filed" and bool(generated_form.field_values)

        try:
            if filed:
                pdf_bytes = PDFFormFiller().fill(form_type, json.loads(generated_form.field_values))
            else:
                _prepare(session)
                document = _resolve(form_type, session)
                pdf_bytes = PDFFormFiller().fill(form_type, document)
                _store(generated_form, document)
        except Exception as exc:
            body, code = _failure(form_type, exc)
            if filed:
                # No step or page changes the values a form was filed with (R46).
                body.pop("step", None)
                body.pop("page", None)
            return Response(body, status=code)

        if not filed:
            # Only over the status read before drawing: a form marked filed meanwhile keeps
            # the values it was filed with (DIG-155).
            status_read = generated_form.status
            GeneratedForm.objects.filter(pk=generated_form.pk, status=status_read).update(
                field_values=generated_form.field_values,
                template_version=generated_form.template_version,
                status="downloaded" if status_read == "generated" else status_read,
                updated_at=timezone.now(),
            )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{form_type}.pdf"'
        return response


class FormSchemaUIView(APIView):
    permission_classes = []

    def get(self, request, form_type):
        try:
            schema = load_schema(form_type)
        except FileNotFoundError as exc:
            raise NotFound(f"Schema for form {form_type} not found") from exc

        steps_dict = {}
        for field in schema.fields:
            if field.source == "asked" and field.ui:
                step_title = field.ui.step
                if step_title not in steps_dict:
                    steps_dict[step_title] = {"title": step_title, "fields": []}

                fields_list = steps_dict[step_title]["fields"]

                field_dict = {
                    "binding": field.binding,
                    "prompt": field.ui.prompt,
                    "widget": field.ui.widget,
                    "help_text": field.ui.help_text,
                    "conditional_on": field.conditional_on,
                }

                if field.repeat:
                    repeat_group = next(
                        (
                            f
                            for f in fields_list
                            if f.get("widget") == "repeat_group" and f.get("repeat") == field.repeat
                        ),
                        None,
                    )
                    if repeat_group:
                        if not any(
                            f.get("binding") == field.binding for f in repeat_group["fields"]
                        ):
                            repeat_group["fields"].append(field_dict)
                    else:
                        fields_list.append(
                            {
                                "widget": "repeat_group",
                                "repeat": field.repeat,
                                "repeat_capacity": field.repeat_capacity,
                                "conditional_on": field.conditional_on,
                                "fields": [field_dict],
                            }
                        )
                else:
                    fields_list.append(
                        {
                            **field_dict,
                            "repeat": field.repeat,
                            "repeat_capacity": field.repeat_capacity,
                        }
                    )

        steps_list = list(steps_dict.values())
        return Response({"form_type": form_type, "steps": steps_list})
