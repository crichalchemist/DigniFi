"""
API views for bankruptcy form generation.

Uses a registry-based dispatch pattern so one endpoint serves all 14 form
types. DB persistence lives here; generators stay pure (data in → data out).
"""

import json
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import GeneratedForm
from .serializers import GeneratedFormSerializer
from .registry import FORM_REGISTRY, get_generator, get_all_form_types
from apps.intake.models import IntakeSession


# UPL-compliant disclaimer appended to every preview response
_UPL_DISCLAIMER = (
    "This is a preview based on the information you provided. "
    "This software provides legal information, not legal advice. "
    "You are responsible for reviewing all information for accuracy before filing."
)


def _resolve_session(request) -> tuple[IntakeSession | None, Response | None]:
    """
    Extract and validate session_id from request data.

    Returns (session, None) on success or (None, error_response) on failure.
    """
    session_id = request.data.get("session_id")
    if not session_id:
        return None, Response(
            {"error": "session_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        session = IntakeSession.objects.get(id=session_id, user=request.user)
        return session, None
    except IntakeSession.DoesNotExist:
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


def _json_safe(data: dict) -> dict:
    """
    Round-trip through DjangoJSONEncoder to convert Decimal → str.

    Generators return Decimal for financial precision; JSONField needs
    natively serializable types.
    """
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def _generate_and_persist(
    session: IntakeSession,
    form_type: str,
    user,
) -> GeneratedForm:
    """Run generator and persist result to DB. Returns the GeneratedForm."""
    generator = get_generator(form_type, session)
    form_data = _json_safe(generator.generate())

    generated_form, _ = GeneratedForm.objects.update_or_create(
        session=session,
        form_type=form_type,
        defaults={
            "form_data": form_data,
            "status": "generated",
            "generated_by": user,
        },
    )
    return generated_form


class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for bankruptcy form generation and management.

    Endpoints:
      POST /api/forms/generate/       Generate a single form
      POST /api/forms/generate_all/   Generate all 14 forms for a session
      POST /api/forms/preview/        Preview form data without persisting
      POST /api/forms/{id}/regenerate/ Regenerate an existing form
      POST /api/forms/{id}/mark_downloaded/
      POST /api/forms/{id}/mark_filed/
    """

    serializer_class = GeneratedFormSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only forms for the authenticated user's sessions."""
        return GeneratedForm.objects.filter(
            session__user=self.request.user
        ).select_related("session", "generated_by")

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
        session, err = _resolve_session(request)
        if err:
            return err

        form_type = request.data.get("form_type")
        err = _validate_form_type(form_type)
        if err:
            return err

        try:
            generated_form = _generate_and_persist(session, form_type, request.user)
            serializer = self.get_serializer(generated_form)
            return Response({
                "form": serializer.data,
                "message": f"{generated_form.get_form_type_display()} generated successfully",
            })
        except (ValueError, KeyError) as e:
            return Response(
                {
                    "error": str(e),
                    "message": "Unable to generate form. Please ensure all required information is provided.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ------------------------------------------------------------------
    # Generate all forms for a session
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="generate_all")
    def generate_all(self, request):
        """
        Generate all 14 bankruptcy forms for a session in one request.

        POST /api/forms/generate_all/
        { "session_id": 1 }

        Wraps all writes in a single transaction — either all succeed or
        none persist.
        """
        session, err = _resolve_session(request)
        if err:
            return err

        results = []
        errors = []

        with transaction.atomic():
            for form_type in get_all_form_types():
                try:
                    generated_form = _generate_and_persist(
                        session, form_type, request.user
                    )
                    results.append(self.get_serializer(generated_form).data)
                except Exception as e:
                    errors.append({"form_type": form_type, "error": str(e)})

        return Response({
            "generated": results,
            "errors": errors,
            "total_generated": len(results),
            "total_errors": len(errors),
        })

    # ------------------------------------------------------------------
    # Preview (no DB write)
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """
        Preview form data without persisting to DB.

        POST /api/forms/preview/
        { "session_id": 1, "form_type": "form_101" }
        """
        session, err = _resolve_session(request)
        if err:
            return err

        form_type = request.data.get("form_type")
        err = _validate_form_type(form_type)
        if err:
            return err

        try:
            generator = get_generator(form_type, session)
            preview_data = _json_safe(generator.preview())
            return Response({
                "form_type": form_type,
                "preview": True,
                "data": preview_data,
                "upl_disclaimer": _UPL_DISCLAIMER,
            })
        except (ValueError, KeyError) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
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
            generator = get_generator(
                generated_form.form_type, generated_form.session
            )
            form_data = _json_safe(generator.generate())

            generated_form.form_data = form_data
            generated_form.status = "generated"
            generated_form.generated_by = request.user
            generated_form.save()

            serializer = self.get_serializer(generated_form)
            return Response({
                "form": serializer.data,
                "message": "Form regenerated successfully",
            })
        except (ValueError, KeyError) as e:
            return Response(
                {"error": str(e), "message": "Unable to regenerate form"},
                status=status.HTTP_400_BAD_REQUEST,
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

        return Response({
            "form_id": generated_form.id,
            "status": generated_form.status,
            "message": "Form marked as downloaded",
        })

    @action(detail=True, methods=["post"])
    def mark_filed(self, request, pk=None):
        """Mark form as filed with the court."""
        generated_form = self.get_object()

        generated_form.status = "filed"
        generated_form.save()

        return Response({
            "form_id": generated_form.id,
            "status": generated_form.status,
            "message": "Form marked as filed with court",
        })
