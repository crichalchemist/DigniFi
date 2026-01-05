"""
API views for bankruptcy form generation.

Provides REST API endpoints for generating, previewing, and downloading
Official Bankruptcy Forms.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import GeneratedForm
from .serializers import GeneratedFormSerializer
from .services import Form101Generator
from apps.intake.models import IntakeSession


class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing generated bankruptcy forms.

    Provides endpoints for:
    - Listing all forms for user's sessions
    - Retrieving specific form details
    - Downloading form PDFs (future)
    - Regenerating forms
    """

    serializer_class = GeneratedFormSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only forms for the authenticated user's sessions."""
        return GeneratedForm.objects.filter(
            session__user=self.request.user
        ).select_related("session", "generated_by")

    @action(detail=False, methods=["post"])
    def generate_form_101(self, request):
        """
        Generate Form 101 (Voluntary Petition) for a session.

        POST /api/forms/generate_form_101/
        {
            "session_id": 1
        }

        Returns:
            Generated form data and metadata
        """
        session_id = request.data.get("session_id")

        if not session_id:
            return Response(
                {"error": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Verify user owns this session
        try:
            session = IntakeSession.objects.get(id=session_id, user=request.user)
        except IntakeSession.DoesNotExist:
            return Response(
                {"error": "Session not found or you don't have permission"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate form
        try:
            generator = Form101Generator(session)
            form_result = generator.generate(user=request.user)

            return Response(
                {
                    "form": form_result,
                    "message": "Form 101 generated successfully",
                }
            )

        except ValueError as e:
            return Response(
                {
                    "error": str(e),
                    "message": "Unable to generate form. Please ensure all required information is provided.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """
        Regenerate an existing form with updated data.

        POST /api/forms/{id}/regenerate/

        Useful when session data has been updated after form generation.
        """
        generated_form = self.get_object()

        try:
            # Get the appropriate generator based on form type
            if generated_form.form_type == "form_101":
                generator = Form101Generator(generated_form.session)
                form_result = generator.generate(user=request.user)

                return Response(
                    {
                        "form": form_result,
                        "message": "Form regenerated successfully",
                    }
                )
            else:
                return Response(
                    {
                        "error": f"Form type {generated_form.form_type} not yet supported"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except ValueError as e:
            return Response(
                {
                    "error": str(e),
                    "message": "Unable to regenerate form",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """
        Get form data for preview (without generating PDF).

        GET /api/forms/{id}/preview/

        Returns form data structure for display in UI.
        """
        generated_form = self.get_object()

        return Response(
            {
                "form_id": generated_form.id,
                "form_type": generated_form.form_type,
                "form_name": generated_form.get_form_type_display(),
                "status": generated_form.status,
                "data": generated_form.form_data,
                "generated_at": generated_form.generated_at.isoformat(),
            }
        )

    @action(detail=True, methods=["post"])
    def mark_downloaded(self, request, pk=None):
        """
        Mark form as downloaded.

        POST /api/forms/{id}/mark_downloaded/

        Updates form status to track user interaction.
        """
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
        """
        Mark form as filed with court.

        POST /api/forms/{id}/mark_filed/

        Updates form status to indicate filing completed.
        """
        generated_form = self.get_object()

        generated_form.status = "filed"
        generated_form.save()

        return Response(
            {
                "form_id": generated_form.id,
                "status": generated_form.status,
                "message": "Form marked as filed with court",
            }
        )
