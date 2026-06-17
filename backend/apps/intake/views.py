"""
API views for intake workflow.

Provides REST API endpoints for multi-step bankruptcy intake process,
including session management, means test calculation, and form preview.
"""

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.eligibility.services import MeansTestCalculator
from apps.forms.services import Form101Generator

from .models import (
    AssetInfo,
    DebtInfo,
    FeeWaiverApplication,
    FormAnswer,
    IntakeSession,
    SOFAReport,
)
from .serializers import (
    AssetInfoSerializer,
    BulkAnswerPayloadSerializer,
    DebtInfoSerializer,
    FeeWaiverApplicationSerializer,
    IntakeSessionSerializer,
    SOFAReportSerializer,
)


class IntakeSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for intake session management.

    Provides endpoints for:
    - Creating new intake sessions
    - Updating session data (step-by-step)
    - Retrieving session status
    - Calculating means test
    - Previewing Form 101
    """

    serializer_class = IntakeSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only sessions for the authenticated user."""
        return (
            IntakeSession.objects.filter(user=self.request.user)
            .select_related("district", "debtor_info", "income_info", "expense_info")
            .prefetch_related("assets", "debts")
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create new intake session for authenticated user.

        POST /api/intake/sessions/
        {
            "district": 1,  // District ID (e.g., ILND)
            "current_step": 1
        }
        """
        # Ensure user is set to authenticated user
        data = request.data.copy()
        data["user"] = request.user.id
        data["status"] = "started"

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {
                "session": serializer.data,
                "message": "Intake session started successfully",
            },
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/intake/sessions/{id}/

        After saving, bulk-clear is_draft on all DebtInfo rows for this session
        when the 'debts' key is present in the request payload.
        """
        instance = self.get_object()
        response = super().partial_update(request, *args, **kwargs)
        if "debts" in request.data:
            DebtInfo.objects.filter(session=instance, is_draft=True).update(is_draft=False)
        return response

    @action(detail=True, methods=["post"])
    def update_step(self, request, pk=None):
        """
        Update current step in intake wizard.

        POST /api/intake/sessions/{id}/update_step/
        {
            "current_step": 2,
            "data": {...}  // Step-specific data
        }
        """
        session = self.get_object()

        current_step = request.data.get("current_step")
        if current_step:
            session.current_step = current_step
            session.status = "in_progress"
            session.save()

        # Update with any provided data
        if "data" in request.data:
            serializer = self.get_serializer(session, data=request.data["data"], partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(
            {
                "session": IntakeSessionSerializer(session).data,
                "message": f"Updated to step {current_step}",
            }
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """
        Mark intake session as completed.

        POST /api/intake/sessions/{id}/complete/

        Validates that all required data is present before completion.
        """
        session = self.get_object()

        # Validate session is complete
        errors = []

        if not hasattr(session, "debtor_info"):
            errors.append("Debtor information is required")

        if not hasattr(session, "income_info"):
            errors.append("Income information is required")

        if not hasattr(session, "expense_info"):
            errors.append("Expense information is required")

        if errors:
            return Response(
                {
                    "errors": errors,
                    "message": "Please complete all required sections before finalizing",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark as completed
        from django.utils import timezone

        session.status = "completed"
        session.completed_at = timezone.now()
        session.save()

        return Response(
            {
                "session": IntakeSessionSerializer(session).data,
                "message": "Intake session completed successfully",
            }
        )

    @action(detail=True, methods=["post"])
    def calculate_means_test(self, request, pk=None):
        """
        Calculate means test for this intake session.

        POST /api/intake/sessions/{id}/calculate_means_test/

        Returns:
            {
                "passes_means_test": bool,
                "qualifies_for_fee_waiver": bool,
                "cmi": Decimal,
                "median_income_threshold": Decimal,
                "message": str (UPL-compliant),
                "details": {...}
            }
        """
        session = self.get_object()

        try:
            calculator = MeansTestCalculator(session)
            result = calculator.calculate()

            return Response(
                {
                    "means_test_result": result,
                    "session_id": session.id,
                }
            )

        except ValueError as e:
            return Response(
                {
                    "error": str(e),
                    "message": "Unable to calculate means test. Please ensure all income information is provided.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def preview_form_101(self, request, pk=None):
        """
        Preview Form 101 (Voluntary Petition) for this session.

        GET /api/intake/sessions/{id}/preview_form_101/

        Returns:
            Form 101 data structure ready for display/preview
        """
        session = self.get_object()

        try:
            generator = Form101Generator(session)
            preview_data = generator.preview()

            return Response(
                {
                    "form_preview": preview_data,
                    "session_id": session.id,
                }
            )

        except ValueError as e:
            return Response(
                {
                    "error": str(e),
                    "message": "Unable to generate form preview. Please ensure all required information is provided.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """
        Get comprehensive session summary.

        GET /api/intake/sessions/{id}/summary/

        Returns:
            Complete session data including:
            - Debtor information
            - Financial overview
            - Means test result (if calculated)
            - Form generation status
        """
        session = self.get_object()

        # Build summary
        summary_data = {
            "session": IntakeSessionSerializer(session).data,
            "progress": {
                "current_step": session.current_step,
                "status": session.status,
                "completion_percentage": self._calculate_completion_percentage(session),
            },
        }

        # Add means test if calculated
        if hasattr(session, "means_test"):
            summary_data["means_test"] = {
                "passes": session.means_test.passes_means_test,
                "qualifies_fee_waiver": session.means_test.qualifies_for_fee_waiver,
            }

        # Add form generation status
        summary_data["forms"] = {
            "generated_count": session.generated_forms.count(),
            "forms": list(session.generated_forms.values("form_type", "status")),
        }

        return Response(summary_data)

    @action(detail=True, methods=["post"], url_path="answers/bulk", url_name="bulk-answers")
    def bulk_answers(self, request, pk=None):
        session = self.get_object()
        serializer = BulkAnswerPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answers_data = serializer.validated_data["answers"]
        created_count = 0
        updated_count = 0

        for ans in answers_data:
            obj, created = FormAnswer.objects.update_or_create(
                session=session,
                form_type=ans["form_type"],
                field_key=ans["field_key"],
                defaults={"value": ans["value"]},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        return Response({"status": "success", "created": created_count, "updated": updated_count})

    def _calculate_completion_percentage(self, session):
        """Calculate how complete the intake session is."""
        completed_sections = 0
        total_sections = 5  # debtor, income, expenses, assets, debts

        if hasattr(session, "debtor_info"):
            completed_sections += 1
        if hasattr(session, "income_info"):
            completed_sections += 1
        if hasattr(session, "expense_info"):
            completed_sections += 1
        if session.assets.exists():
            completed_sections += 1
        if session.debts.exists():
            completed_sections += 1

        return int((completed_sections / total_sections) * 100)


class AssetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing assets within an intake session.

    Provides CRUD operations for individual assets (property, vehicles, accounts).
    """

    serializer_class = AssetInfoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only assets for user's intake sessions."""
        return AssetInfo.objects.filter(session__user=self.request.user).select_related("session")


class DebtViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing debts/creditors within an intake session.

    Provides CRUD operations for individual creditor entries.
    Uses trauma-informed language ("amounts owed" vs "debts").
    """

    serializer_class = DebtInfoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only debts for user's intake sessions."""
        return DebtInfo.objects.filter(session__user=self.request.user).select_related("session")


class FeeWaiverViewSet(viewsets.ModelViewSet):
    """CRUD for fee waiver applications, scoped to authenticated user's sessions."""

    serializer_class = FeeWaiverApplicationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return FeeWaiverApplication.objects.filter(session__user=self.request.user).select_related(
            "session"
        )

    def perform_create(self, serializer):
        # FeeWaiverApplication is OneToOne with IntakeSession — second POST from
        # the same session would raise IntegrityError. Use update_or_create so
        # reloading the FeeWaiverPage is safe.
        from rest_framework.exceptions import PermissionDenied

        session = serializer.validated_data["session"]
        if session.user != self.request.user:
            raise PermissionDenied()
        instance, _ = FeeWaiverApplication.objects.update_or_create(
            session=session,
            defaults={k: v for k, v in serializer.validated_data.items() if k != "session"},
        )
        serializer.instance = instance


class SOFAReportViewSet(viewsets.GenericViewSet):
    """
    Retrieve and update SOFA Report (Form 107 data) for a session.

    GET  /api/sofa-report/{session_pk}/        → report or 404
    PATCH /api/sofa-report/{session_pk}/        → create/update report + nested rows
    """

    serializer_class = SOFAReportSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def retrieve(self, request, pk=None):
        session = IntakeSession.objects.filter(pk=pk, user=request.user).first()
        if not session:
            return Response(
                {"detail": "Session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        report, _ = SOFAReport.objects.get_or_create(session=session)
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        session = IntakeSession.objects.filter(pk=pk, user=request.user).first()
        if not session:
            return Response(
                {"detail": "Session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        report, _ = SOFAReport.objects.get_or_create(session=session)
        serializer = self.get_serializer(report, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
