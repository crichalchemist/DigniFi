"""
API views for intake workflow.

Provides REST API endpoints for multi-step bankruptcy intake process,
including session management and means test calculation.
"""

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.districts.dated_tables import NoTableInForce
from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income
from apps.eligibility.services import MeansTestCalculator
from apps.forms.registry import PreconditionMissing, _needs_ssn

from .locking import lock_session
from .models import (
    AssetInfo,
    Codebtor,
    DebtInfo,
    ExecutoryContract,
    FeeWaiverApplication,
    FormAnswer,
    IntakeSession,
    SOFAReport,
)
from .serializers import (
    AssetInfoSerializer,
    BulkAnswerPayloadSerializer,
    CodebtorRowSerializer,
    CodebtorSerializer,
    DebtInfoSerializer,
    ExecutoryContractRowSerializer,
    ExecutoryContractSerializer,
    FeeWaiverApplicationSerializer,
    IntakeSessionSerializer,
    SOFAReportSerializer,
    _save_rows_by_id,
)


def _save_list(session, model, row_serializer, rows):
    """Save the whole list the Contracts or Codebtors step shows (DIG-147).

    Every row is checked before anything is written, so one bad row saves nothing. Then a
    row carrying one of this session's ids updates in place, any other row is created, and
    a stored row the list left out is deleted (see _save_rows_by_id). Returns the saved
    rows in id order, so the wizard keeps their ids for the next save.
    """
    serializer = row_serializer(data=rows, many=True)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        lock_session(session.pk)
        _save_rows_by_id(session, model, serializer.validated_data)
        session.reopen()
    saved = model.objects.filter(session=session).order_by("id")
    return Response(row_serializer(saved, many=True).data)


def _assert_session_owned(session, user):
    """Reject writes that attach a row to another user's intake session (IDOR guard).

    ``get_queryset`` scopes reads, but DRF never consults it on create/update — a
    client-supplied ``session`` PK must be checked explicitly. Mirrors the guard in
    ``FeeWaiverViewSet.perform_create``.
    """
    from rest_framework.exceptions import PermissionDenied

    if session.user != user:
        raise PermissionDenied("You do not have access to this session.")


def _lock_for_row_update(serializer):
    """Lock the sessions a per-item asset or debt update changes, then read the row again.

    A row moved to another of the filer's sessions changes both, so both are locked, in id
    order, so two moves between the same sessions can't wait on each other (DIG-188). A row
    that another save deleted or moved while this one waited is a 404, as a missing row is.
    """
    from rest_framework.exceptions import NotFound

    row = serializer.instance
    session = serializer.validated_data.get("session")
    moved_to = session.pk if session is not None else row.session_id
    locked = sorted({row.session_id, moved_to})
    for session_id in locked:
        lock_session(session_id)
    try:
        row.refresh_from_db()  # the row as stored once the lock is held
    except row.DoesNotExist:
        raise NotFound() from None
    if row.session_id not in locked:
        raise NotFound()  # moved meanwhile: locking its session now would break id order


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
        serializer = self.get_serializer(data=request.data)
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
    def update(self, request, *args, **kwargs):
        """
        PUT /api/intake/sessions/{id}/, and every PATCH through partial_update.

        Locks the session before the save reads it and its stored rows, so two saves of one
        session run one after the other (DIG-188).
        """
        lock_session(self.get_object().pk)  # get_object first: another user's session is a 404
        return super().update(request, *args, **kwargs)

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
            for debt in response.data["debts"]:
                debt["is_draft"] = False
        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_step(self, request, pk=None):
        """
        Update current step in intake wizard.

        POST /api/intake/sessions/{id}/update_step/
        {
            "current_step": 2,
            "data": {...}  // Step-specific data
        }
        """
        session = lock_session(self.get_object().pk)

        # Only one of the wizard's 8 steps; anything else is a client fault (DIG-151).
        current_step = request.data.get("current_step")
        if (
            not isinstance(current_step, int)
            or isinstance(current_step, bool)
            or not 1 <= current_step <= 8
        ):
            return Response(
                {"current_step": ["Must be a whole number from 1 to 8."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
    @transaction.atomic
    def complete(self, request, pk=None):
        """
        Mark intake session as completed.

        POST /api/intake/sessions/{id}/complete/

        Refuses with a 400 naming, in wizard order, the step that fixes each gap
        (forms step 3a1 spec §4.2). The session stays locked from the checks to the status
        write, so a save can't land between them, and a save that waited reopens it.
        """
        session = lock_session(self.get_object().pk)

        # Validate session is complete
        errors = []

        # The forms' own identity checks, so Complete and the forms say the same thing.
        try:
            _needs_ssn(session)  # checks the name and address first
        except PreconditionMissing as exc:
            errors.append({"step": exc.step, "message": str(exc)})

        try:
            income_info = getattr(session, "income_info", None)
            if income_info is None:
                raise IncomeNotSplit()  # no income at all is income not entered by source
            current_monthly_income(income_info)
        except IncomeNotSplit as exc:
            errors.append({"step": exc.step, "message": str(exc)})

        if not hasattr(session, "expense_info"):
            errors.append(
                {
                    "step": "expense_info",
                    "message": "Go through the Expenses step, even if you have no expenses to enter.",
                }
            )

        # A scanned debt stays off the forms until the filer saves the Amounts Owed step
        # (DIG-163). An upload after Complete reopens the intake, and Review is one press away.
        if session.debts.filter(is_draft=True).exists():
            errors.append(
                {
                    "step": "debts",
                    "message": "Check the debts read from your documents on the Amounts Owed step.",
                }
            )

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
        session.save(update_fields=["status", "completed_at"])

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

        # Only these two refusals carry their own plain words for the filer in `error`, as in
        # the forms views. Any other ValueError's text is for operations (no income row yet
        # reads "IntakeSession must have income_info..."), so it stays out of the response.
        except (IncomeNotSplit, NoTableInForce) as e:
            return Response(
                {
                    "error": str(e),
                    "message": "Unable to calculate means test. Please ensure all income information is provided.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError:
            return Response(
                {
                    "message": "Unable to calculate means test. Please ensure all income information is provided.",
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

        # Ensure SOFAReport exists
        sofa_report, _ = SOFAReport.objects.get_or_create(session=session)

        models_to_save = {}
        cached_collections = {}

        with transaction.atomic():
            for ans in answers_data:
                binding = ans["binding"]
                val = ans["value"]

                if binding.startswith("answer:"):
                    form_type, _, key = binding[len("answer:") :].partition(".")
                    obj, created = FormAnswer.objects.update_or_create(
                        session=session,
                        form_type=form_type,
                        field_key=key,
                        defaults={"value": val},
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                elif binding.startswith("sofa."):
                    path = binding[len("sofa.") :]
                    if "parsed_array_binding" in ans:
                        # Array binding: sofa.prior_income[0].source
                        coll_name, idx, attr = ans["parsed_array_binding"]

                        manager = getattr(sofa_report, coll_name, None)
                        if manager is not None:
                            if coll_name not in cached_collections:
                                cached_collections[coll_name] = list(manager.all().order_by("id"))
                            items = cached_collections[coll_name]

                            if idx > len(items):
                                from rest_framework.exceptions import ValidationError

                                raise ValidationError(
                                    f"Cannot skip index in collection {coll_name}. Expected index {len(items)} but got {idx}"
                                )
                            if idx == len(items):
                                new_item = manager.model(report=sofa_report)
                                items.append(new_item)
                                models_to_save[id(new_item)] = new_item
                                created_count += 1
                            else:
                                updated_count += 1

                            setattr(items[idx], attr, val)
                            models_to_save[id(items[idx])] = items[idx]
                    else:
                        # Scalar binding: sofa.has_prior_income
                        if hasattr(sofa_report, path):
                            setattr(sofa_report, path, val)
                            models_to_save[id(sofa_report)] = sofa_report
                            updated_count += 1

            for model_obj in models_to_save.values():
                model_obj.save()

        return Response({"status": "success", "created": created_count, "updated": updated_count})

    @action(detail=True, methods=["get", "post", "put"], url_path="contracts", url_name="contracts")
    def contracts(self, request, pk=None):
        session = self.get_object()
        if request.method == "GET":
            contracts = ExecutoryContract.objects.filter(session=session).order_by("id")
            serializer = ExecutoryContractSerializer(contracts, many=True)
            return Response(serializer.data)
        if request.method == "PUT":
            return _save_list(
                session, ExecutoryContract, ExecutoryContractRowSerializer, request.data
            )
        serializer = ExecutoryContractSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            lock_session(session.pk)
            serializer.save(session=session)
            session.reopen()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path="contracts/(?P<contract_id>[0-9]+)",
        url_name="contract-detail",
    )
    @transaction.atomic
    def delete_contract(self, request, pk=None, contract_id=None):
        session = lock_session(self.get_object().pk)
        try:
            contract = ExecutoryContract.objects.get(pk=contract_id, session=session)
            contract.delete()
            session.reopen()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ExecutoryContract.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get", "post", "put"], url_path="codebtors", url_name="codebtors")
    def codebtors(self, request, pk=None):
        session = self.get_object()
        if request.method == "GET":
            codebtors = Codebtor.objects.filter(session=session).order_by("id")
            serializer = CodebtorSerializer(codebtors, many=True)
            return Response(serializer.data)
        if request.method == "PUT":
            return _save_list(session, Codebtor, CodebtorRowSerializer, request.data)
        serializer = CodebtorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            lock_session(session.pk)
            serializer.save(session=session)
            session.reopen()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path="codebtors/(?P<codebtor_id>[0-9]+)",
        url_name="codebtor-detail",
    )
    @transaction.atomic
    def delete_codebtor(self, request, pk=None, codebtor_id=None):
        session = lock_session(self.get_object().pk)
        try:
            codebtor = Codebtor.objects.get(pk=codebtor_id, session=session)
            codebtor.delete()
            session.reopen()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Codebtor.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"], url_path="dischargeability", url_name="dischargeability")
    def dischargeability(self, request, pk=None):
        session = self.get_object()
        from apps.eligibility.services.dischargeability_service import DischargeabilityService

        svc = DischargeabilityService(session)
        results = svc.evaluate()
        return Response(results)

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

    @transaction.atomic
    def perform_create(self, serializer):
        _assert_session_owned(serializer.validated_data["session"], self.request.user)
        lock_session(serializer.validated_data["session"].pk)
        serializer.save()
        serializer.instance.session.reopen()

    @transaction.atomic
    def perform_update(self, serializer):
        session = serializer.validated_data.get("session")
        if session is not None:
            _assert_session_owned(session, self.request.user)
        _lock_for_row_update(serializer)
        # A row moved to another of the filer's sessions changes both.
        serializer.instance.session.reopen()
        serializer.save()
        serializer.instance.session.reopen()

    @transaction.atomic
    def perform_destroy(self, instance):
        lock_session(instance.session_id)
        instance.delete()
        instance.session.reopen()


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

    @transaction.atomic
    def perform_create(self, serializer):
        _assert_session_owned(serializer.validated_data["session"], self.request.user)
        lock_session(serializer.validated_data["session"].pk)
        serializer.save()
        serializer.instance.session.reopen()

    @transaction.atomic
    def perform_update(self, serializer):
        session = serializer.validated_data.get("session")
        if session is not None:
            _assert_session_owned(session, self.request.user)
        _lock_for_row_update(serializer)
        # A row moved to another of the filer's sessions changes both.
        serializer.instance.session.reopen()
        serializer.save()
        serializer.instance.session.reopen()

    @transaction.atomic
    def perform_destroy(self, instance):
        lock_session(instance.session_id)
        instance.delete()
        instance.session.reopen()


class FeeWaiverViewSet(viewsets.ModelViewSet):
    """CRUD for fee waiver applications, scoped to authenticated user's sessions.

    GET /api/intake/fee-waiver/?session={id} reads one session's application, so the page
    opens with the answers already sent (DIG-157). The read never creates one: an
    application puts Form 103B in the packet.
    """

    serializer_class = FeeWaiverApplicationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["session"]

    def get_queryset(self):
        return (
            FeeWaiverApplication.objects.filter(session__user=self.request.user)
            .select_related("session")
            .order_by("id")
        )

    def perform_update(self, serializer):
        # A PATCH can't move the application onto another user's session (DIG-178).
        session = serializer.validated_data.get("session")
        if session is not None:
            _assert_session_owned(session, self.request.user)
        serializer.save()

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
