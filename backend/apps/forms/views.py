"""
API views for bankruptcy form generation.

One path fills every form: registry.build_parts() resolves a session's values,
PDFFormFiller checks that the template can print them, and they are kept as an
encrypted parts document (GeneratedForm.field_values) that the API never returns.
Generate, Generate All and Regenerate only check; Download draws (3a2 spec §7).
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

from apps.districts.dated_tables import NoTableInForce, fill_date
from apps.eligibility.cmi import IncomeNotSplit, answered_window, income_step_gaps, income_window
from apps.eligibility.models import MeansTest
from apps.eligibility.services import MeansTestCalculator
from apps.intake.asset_lines import AssetStepGap
from apps.intake.claims import ClaimStepGap
from apps.intake.completion import Gap, completion_gaps
from apps.intake.locking import lock_session
from apps.intake.models import IntakeSession

from .models import GeneratedForm
from .registry import (
    FORM_REGISTRY,
    PreconditionMissing,
    build_parts,
    get_all_form_types,
    packet,
    payment_choice,
)
from .schema import load_schema
from .serializers import GeneratedFormSerializer
from .services.fill_resolver import UnmappedChoice
from .services.pdf_filler import (
    PDFFormFiller,
    TemplateHasNoForm,
    UnknownField,
    UnprintableLetter,
    ValueTooLong,
)

logger = logging.getLogger(__name__)

# A form filed on the retired 06/24 Form 101 holds box names the 11/26 template lacks (4b-R7).
# Wording approved by the owner on 2026-11-21 (4b-i Ruling T6-sentence).
FILED_ON_EARLIER_REVISION = (
    "This form was filed on an older version of Form 101. "
    "DigniFi can no longer print it. Keep the copy you gave the court."
)

# Form 122A-1 and the two forms that can be its partner: 122A-2, which works its result out, or
# 122A-1Supp, which says to submit it with the signed 122A-1 (D4). A packet holds one of them.
MEANS_FORMS = ("form_122a1", "form_122a2", "form_122a1_supp")

# How mark_pair_filed's reply names each partner.
_PARTNER_NAMES = {"form_122a2": "Form 122A-2", "form_122a1_supp": "Form 122A-1Supp"}


class NotInPacket(Exception):
    """The form isn't part of this filer's packet (registry applies() is false)."""


class FormIsFiled(Exception):
    """The form is marked filed, so it keeps the values it was filed with (spec §5.5)."""


class MeansPairTie(Exception):
    """One form of the means pair can't be marked filed while the other is unfiled (H43)."""


class SuppPairTie(Exception):
    """Form 122A-1 or Form 122A-1Supp can't be marked filed while the other is unfiled (D4)."""


class IntakeNotFinished(Exception):
    """The filer hasn't completed the intake, so an empty list can't yet mean "none"."""

    page = "/intake"  # where the filer finishes it


# DRAFT: counsel C-24
MEANS_PAIR_REFUSAL = "File Form 122A-1 and Form 122A-2 together."

# DRAFT: counsel C-39
MEANS_SUPP_PAIR_REFUSAL = "File Form 122A-1 and Form 122A-1Supp together."


class _PairRefused(Exception):
    """A refusal carried out of the pair action's transaction, so the rollback comes first.

    form_type is the form refused, or None when _prepare refused the whole call; exc is what
    _failure turns into the body. The message is the exception's type only, never filer data.
    """

    def __init__(self, form_type: str | None, exc: Exception):
        super().__init__(type(exc).__name__)
        self.form_type = form_type
        self.exc = exc


# Failures a filer can act on: 422 in plain words (spec §5.7). Anything else is a 500.
# PreconditionMissing, IncomeNotSplit, Gap, AssetStepGap, ClaimStepGap and NoTableInForce carry
# their own plain reasons
# (registry.py, eligibility/cmi.py, districts/dated_tables.py, which logs its own
# refusal), and so do UnprintableLetter and ValueTooLong (pdf_filler.py), which name the
# letter and the box. Every other class gets a fixed sentence, because their messages
# name form keys and PDF widgets. None names the form: the dashboard shows
# its label beside the error.
_FAILURE_SENTENCES = {
    IntakeNotFinished: "Finish your intake before preparing your forms.",
    NotInPacket: "This form isn't part of your packet, based on the answers you've given.",
    FormIsFiled: "This form is marked as filed, so it keeps the answers it was filed with.",
    MeansPairTie: MEANS_PAIR_REFUSAL,
    SuppPairTie: MEANS_SUPP_PAIR_REFUSAL,
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
        PreconditionMissing | IncomeNotSplit | Gap
        # AssetStepGap and ClaimStepGap no longer arrive from _prepare, which raises a Gap (4a).
        | AssetStepGap | ClaimStepGap | NoTableInForce | UnprintableLetter | ValueTooLong,
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
    since changed never decides which forms they get (DIG-160). Raises the first gap the
    Income step leaves (an IncomeStepGap, 3e1 spec §9.2), and NoTableInForce when no median
    income table is in force on the fill date, which operations must fix.
    """
    gaps = income_step_gaps(session)
    if gaps:
        raise gaps[0]
    MeansTestCalculator(session).calculate()


def _means_reply(session: IntakeSession) -> dict:
    """What the packet list says of the stored means test, from one read (3h1 R14).

    `tables` is the median table the means test recorded, then every table it read for Form
    122A-2; `outcome`, `family_size`, `tables_gap` and `open_on` are None when there is no means
    test. A row saved before 3h1 replies with `outcome` and `tables_gap` None and its stored
    `family_size` (calculation_details has held it since 3e1). `open_on` is "debts" while the
    result waits on the Amounts Owed step (4d-R27), and None for a row saved before 4d.
    """
    means_test = MeansTest.objects.filter(session=session).first()
    details = means_test.get_calculation_details() if means_test else {}
    median = details.get("median_table")
    return {
        "tables": ([median] if median else []) + list(details.get("tables") or []),
        "outcome": means_test.outcome if means_test else None,
        "family_size": details.get("family_size"),
        "tables_gap": details.get("tables_gap"),
        "open_on": details.get("open_on"),
    }


def _income_period(session: IntakeSession) -> dict:
    """The six months the filer last confirmed on the Income step, and the six months in force.

    `answered_for` is None with no income row or no confirmation yet (3e2 spec §10).
    """
    start, end = income_window(fill_date())
    period_end = getattr(getattr(session, "income_info", None), "income_period_end", None)
    answered_for = None
    if period_end is not None:
        answered_start, answered_end = answered_window(period_end)
        answered_for = {"start": answered_start.isoformat(), "end": answered_end.isoformat()}
    return {
        "answered_for": answered_for,
        "now": {"start": start.isoformat(), "end": end.isoformat()},
    }


def _means_debts_answered(session: IntakeSession, form_types: list[str]) -> dict | None:
    """When the filer last answered the secured-debt questions, and today (the fill date).

    None unless Form 122A-2 is in the packet and the answers carry a date.
    """
    if "form_122a2" not in form_types:
        return None
    record = getattr(session, "means_test_answers", None)
    answered_on = None if record is None else record.answered_on()
    if answered_on is None:
        return None
    return {"answered_on": answered_on.isoformat(), "now": fill_date().isoformat()}


def _prepare(session: IntakeSession) -> None:
    """Refuse an unfinished intake and the first gate gap, then work the means test out again.
    Once per call.

    The gate list is Complete's own (`completion_gaps`, 4a-R1), first gate first, so a session
    completed before a rule existed is refused in the words Complete would use, and its callers
    don't work the means test out while a gate is open; the packet list, which never calls this,
    still does. Its callers are Generate, Generate All, Regenerate, an unfiled download, Mark as
    Filed on an unfiled means form (`MEANS_FORMS`), `mark_pair_filed` and the `time_packet`
    command.
    """
    _check_finished(session)
    gates = [gap for gap in completion_gaps(session) if gap.kind == Gap.GATE]
    if gates:
        raise gates[0]
    _recalculate_means_test(session)


def _means_partner(session: IntakeSession) -> str | None:
    """The form Form 122A-1 is filed with: Form 122A-2 or Form 122A-1Supp, whichever the packet
    holds (never both), or None when it holds neither (below the median, no Supp outcome).

    It reads the stored means test, so _prepare() runs first.
    """
    forms = packet(session)
    if "form_122a2" in forms:
        return "form_122a2"
    if "form_122a1_supp" in forms:
        return "form_122a1_supp"
    return None


def _resolve(form_type: str, session: IntakeSession) -> dict:
    """The parts a form that applies to this filer prints. _prepare() runs first."""
    if not FORM_REGISTRY[form_type].applies(session):
        raise NotInPacket()
    return build_parts(form_type, session)


def _store(generated_form: GeneratedForm, document: dict) -> None:
    generated_form.field_values = json.dumps(document)
    generated_form.template_version = load_schema(generated_form.form_type).template_version


def _generate_and_persist(session: IntakeSession, form_type: str, user) -> GeneratedForm:
    """Check that the form prints its values, without drawing it, and keep them (3a2 spec §7).

    _prepare() runs first. The save is conditional on the row not being filed: a row marked
    filed while this ran keeps its filed document, and the generate answers FormIsFiled (H43).
    """
    if GeneratedForm.objects.filter(session=session, form_type=form_type, status="filed").exists():
        raise FormIsFiled()
    document = _resolve(form_type, session)
    PDFFormFiller().check(form_type, document)
    generated_form, _ = GeneratedForm.objects.get_or_create(
        session=session, form_type=form_type, defaults={"generated_by": user}
    )
    _store(generated_form, document)
    changed = (
        GeneratedForm.objects.filter(pk=generated_form.pk)
        .exclude(status="filed")
        .update(
            field_values=generated_form.field_values,
            template_version=generated_form.template_version,
            status="generated",
            generated_by=user,
            updated_at=timezone.now(),
        )
    )
    if changed != 1:
        raise FormIsFiled()
    generated_form.refresh_from_db()
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
      POST /api/forms/mark_pair_filed/       Mark Form 122A-1 and Form 122A-2 filed together
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
        test recorded, and is `[]` when there is no means test or it recorded none. `income_period` says which six
        months the filer last confirmed on the Income step and which are in force now.
        `payment_choice` is the Form 101 line 8 answer, or null before the filer chooses.
        `outcome`, `family_size` and `tables_gap` are the stored means test's result (3h1 R14),
        and `open_on` names the step the result waits on (4d-R27); `tables` also lists the tables Form 122A-2's figures were read from.
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
        form_types = packet(session)
        return Response(
            {
                "session": session.id,
                "form_types": form_types,
                "income_period": _income_period(session),
                "means_debts_answered": _means_debts_answered(session, form_types),
                "payment_choice": payment_choice(session),
                **_means_reply(session),
            }
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
        un-filed, not deleted (DIG-155). An unfinished intake, a gate gap, or a means
        test that can't be worked out, gets one refusal for the whole packet, before
        anything is deleted.
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
    # Mark the means pair filed together
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="mark_pair_filed")
    def mark_pair_filed(self, request):
        """
        Mark Form 122A-1 and its partner filed together, or neither (H43, D4).

        POST /api/forms/mark_pair_filed/
        { "session_id": 1 }

        In one locked transaction: the intake's checks and the means test once, then the partner
        is read from the packet (`_means_partner`: Form 122A-2 or Form 122A-1Supp), and each form
        of the pair not already filed is resolved and checked, the partner first so its gap names
        it, and only then written, each by one update conditional on the row not being filed.
        With no partner in the packet (below the median, no Supp outcome) the pair is 122A-2's,
        which is then refused as not in the packet. A form of the pair with no row gets one; a
        form already filed is left as it is. A refusal rolls every write back, the means test
        worked out again included, and names the form it is about, or no form when the whole call
        is refused.
        """
        session, err = _session_or_error(request, request.data.get("session_id"))
        if err:
            return err
        try:
            with transaction.atomic():
                locked = lock_session(session.pk)
                try:
                    _prepare(locked)
                except Exception as exc:
                    raise _PairRefused(None, exc) from exc
                pair = ("form_122a1", _means_partner(locked) or "form_122a2")
                rows = {
                    ft: GeneratedForm.objects.filter(session=locked, form_type=ft).first()
                    for ft in pair
                }
                documents = {}
                for ft in reversed(pair):  # the partner first: its gap names it
                    if rows[ft] is not None and rows[ft].status == "filed":
                        continue
                    try:
                        document = _resolve(ft, locked)
                        PDFFormFiller().check(ft, document)
                    except Exception as exc:
                        raise _PairRefused(ft, exc) from exc
                    documents[ft] = document
                # writes only after every check
                for ft in (ft for ft in pair if ft in documents):
                    document = documents[ft]
                    # get_or_create: a Generate takes no lock, so its row can land between the
                    # read above and this write; that row is then filed, not made again
                    row = (
                        rows[ft]
                        or GeneratedForm.objects.get_or_create(
                            session=locked, form_type=ft, defaults={"generated_by": request.user}
                        )[0]
                    )
                    _store(row, document)
                    changed = (
                        GeneratedForm.objects.filter(pk=row.pk)
                        .exclude(status="filed")
                        .update(
                            field_values=row.field_values,
                            template_version=row.template_version,
                            status="filed",
                            updated_at=timezone.now(),
                        )
                    )
                    if changed != 1:
                        raise _PairRefused(ft, FormIsFiled())
                    row.refresh_from_db()
                    rows[ft] = row
        except _PairRefused as refused:
            body, code = _failure(refused.form_type, refused.exc)
            return Response(body, status=code)
        return Response(
            {
                "forms": [GeneratedFormSerializer(rows[ft]).data for ft in pair],
                "message": f"Form 122A-1 and {_PARTNER_NAMES[pair[1]]} marked as filed with court",
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
        """Mark form as filed with the court.

        A 122A-1, 122A-2 or 122A-1Supp not yet filed is worked out again first, as its unfiled
        download is, so the hold can't be gone around with a copy made before it (3h1 R7). Then,
        when the packet holds a partner for 122A-1 (`_means_partner`: 122A-2 above the median, or
        the Supp under one of its outcomes) and the row is 122A-1 or that partner, it is refused
        while the other form of the pair is unfiled or has no row: the two are marked together
        through mark_pair_filed (H43, D4). A means form outside the packet is refused as not in
        it. The document it was checked with is the one filed, and the one conditional update is
        the only write to the GeneratedForm row. `_prepare` also saves the means test it works
        out again, even when the filing is then refused. Any other row, or one already filed, is
        marked as before.
        """
        generated_form = self.get_object()

        if generated_form.form_type in MEANS_FORMS and generated_form.status != "filed":
            status_read = generated_form.status
            try:
                _prepare(generated_form.session)
                partner = _means_partner(generated_form.session)
                pair = ("form_122a1", partner)
                if partner is not None and generated_form.form_type in pair:
                    other = pair[1] if generated_form.form_type == pair[0] else pair[0]
                    if not GeneratedForm.objects.filter(
                        session=generated_form.session, form_type=other, status="filed"
                    ).exists():
                        raise MeansPairTie() if partner == "form_122a2" else SuppPairTie()
                document = _resolve(generated_form.form_type, generated_form.session)
                PDFFormFiller().check(generated_form.form_type, document)
                _store(generated_form, document)
            except Exception as exc:
                body, code = _failure(generated_form.form_type, exc)
                return Response(body, status=code)
            GeneratedForm.objects.filter(pk=generated_form.pk, status=status_read).update(
                field_values=generated_form.field_values,
                template_version=generated_form.template_version,
                status="filed",
                updated_at=timezone.now(),
            )
            generated_form.refresh_from_db(fields=["status"])
        else:
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
        filed form with no stored values is drawn as one not yet filed, through the completion gap
        list (`_prepare`) and the packet check, from the current intake, and the parts it draws are kept
        as its filed ones if it is still filed when the draw ends.
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
            if (
                filed
                and form_type == "form_101"
                and isinstance(exc, UnknownField)
                and generated_form.template_version != load_schema(form_type).template_version
            ):
                # B62, DIG-155: the stored values name a box the current template lacks (a Form
                # 101 filed on 06/24). They stay as filed: a filed row is never regenerated
                # (FormIsFiled). An unfiled form is resolved fresh and never meets this. A row
                # filed on the live template's hash is a defect of ours, so it falls through to
                # the logged 500 (PF2-9).
                logger.warning("filed form_101 on an earlier template revision")
                return Response(
                    {"form_type": form_type, "error": FILED_ON_EARLIER_REVISION},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
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
