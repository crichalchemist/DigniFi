"""
API views for intake workflow.

Provides REST API endpoints for multi-step bankruptcy intake process,
including session management and means test calculation.
"""

from dataclasses import asdict
from decimal import Decimal

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.districts.dated_tables import NoTableInForce, fill_date
from apps.districts.exemptions import NoExemptionCatalog, exemption_catalog_in_force
from apps.eligibility.cmi import (
    IncomeNotSplit,
    counted_spouse_income,
    income_step_gaps,
    income_window,
)
from apps.eligibility.services import MeansTestCalculator
from apps.forms.registry import PreconditionMissing, _needs_county, _needs_ssn
from apps.forms.services.exemption_items import exemption_items

from .asset_lines import asset_step_gaps
from .claims import claim_step_gaps
from .exemptions import ordered_claims
from .filing_fee import filing_fee_information
from .income import deductions_blank, schedule_i_line4
from .locking import lock_session
from .models import (
    AssetInfo,
    Codebtor,
    DebtInfo,
    ExecutoryContract,
    ExemptionAnswers,
    ExemptionClaim,
    FilingFee,
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
    ExemptionsSerializer,
    FilingFeeSerializer,
    IntakeSessionSerializer,
    SOFAReportSerializer,
    _save_rows_by_id,
)


def _save_list(session, model, row_serializer, rows, scoped=None):
    """Save the whole list the Contracts or Codebtors step shows (DIG-147).

    The session is locked first, so a check that reads the stored rows sees the last save's.
    Every row is checked before anything is written, so one bad row saves nothing. Then a
    row carrying one of this session's ids updates in place, any other row is created, and
    a stored row the list left out is deleted (see _save_rows_by_id). Returns the saved rows
    in the order sent, each with its id, so the wizard pairs them by position (3c spec §6.3).
    ``scoped`` names the foreign keys a row may carry, as _save_rows_by_id takes it.
    """
    with transaction.atomic():
        lock_session(session.pk)
        serializer = row_serializer(data=rows, many=True, context={"session": session})
        serializer.is_valid(raise_exception=True)
        saved = _save_rows_by_id(session, model, serializer.validated_data, scoped)
        session.reopen()
    return Response(row_serializer(saved, many=True).data)


def _assert_session_owned(session, user):
    """Reject writes that attach a row to another user's intake session (IDOR guard).

    ``get_queryset`` scopes reads, but DRF never consults it on create/update — a
    client-supplied ``session`` PK must be checked explicitly.
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


TAKE_HOME_PAY_NOT_ENTERED = (
    "Enter what is taken out of your pay on the Take-home pay step. "
    "If nothing is, enter $0 in one box."
)
SPOUSE_TAKE_HOME_PAY_NOT_ENTERED = (
    "Enter what is taken out of your spouse's pay on the Take-home pay step. "
    "If nothing is, enter $0 in one box."
)
EXPENSES_INCLUDE_OTHERS_UNANSWERED = (
    "Answer whether your expenses include anyone else's, on the Expenses step."
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
            .select_related(
                "district",
                "debtor_info",
                "income_info",
                "expense_info",
                "household",
                "spouse_income",
                "claim_answers",
            )
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

        # Only one of the wizard's 9 steps; anything else is a client fault (DIG-151).
        current_step = request.data.get("current_step")
        if (
            not isinstance(current_step, int)
            or isinstance(current_step, bool)
            or not 1 <= current_step <= 9
        ):
            return Response(
                {"current_step": ["Must be a whole number from 1 to 9."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.current_step = current_step
        session.status = "in_progress"
        session.save()

        # Continue from Amounts Owed confirms every scanned debt, before any data this request
        # carries is saved, so the rows that save loads (and the reply) read confirmed.
        if current_step == 7:
            DebtInfo.objects.filter(session=session, is_draft=True).update(is_draft=False)

        # Continue from the Income step records the window the filer confirmed (3e2 spec §4.4)
        income_info = getattr(session, "income_info", None)
        if current_step == 3 and income_info is not None:
            income_info.income_period_end = income_window(fill_date())[1]
            income_info.save(update_fields=["income_period_end"])

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

        Refuses with a 400 naming the step that fixes each gap (forms step 3a1 spec §4.2), in
        wizard order except the claims tail: the legacy gaps, then the line 4 question, come after
        Codebtors' gaps, out of wizard order on purpose. The session stays locked from the checks to the status
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
            _needs_county(session)
        except PreconditionMissing as exc:
            errors.append({"step": exc.step, "message": str(exc)})

        # Every gap the Income step leaves, in order: the same check the means test refuses
        # with (3e1 spec §9.1).
        errors.extend(
            [{"step": gap.step, "message": str(gap)} for gap in income_step_gaps(session)]
        )

        # Take-home pay and Schedule J line 3 are Complete's alone: the means test and the forms
        # don't read them (3e2 spec §8).
        for row, message in (
            (getattr(session, "income_info", None), TAKE_HOME_PAY_NOT_ENTERED),
            (counted_spouse_income(session), SPOUSE_TAKE_HOME_PAY_NOT_ENTERED),
        ):
            if row is not None and schedule_i_line4(row) > 0 and deductions_blank(row):
                errors.append({"step": "take_home_pay", "message": message})

        if not hasattr(session, "expense_info"):
            errors.append(
                {
                    "step": "expense_info",
                    "message": "Go through the Expenses step, even if you have no expenses to enter.",
                }
            )
        elif session.expense_info.expenses_include_others is None:
            errors.append({"step": "expense_info", "message": EXPENSES_INCLUDE_OTHERS_UNANSWERED})

        # Schedule A/B's walk: every gap, after Schedule J line 3 and before the scanned debts,
        # which is wizard order (3b spec §7).
        errors.extend([{"step": gap.step, "message": str(gap)} for gap in asset_step_gaps(session)])

        # The claims steps' walk (3c3): Assets' "Do you live here?" first, then the Debts block
        # (a scanned debt the filer hasn't confirmed first, DIG-163), Contracts and Codebtors; then,
        # out of wizard order on purpose (3c4), the legacy gaps and the line 4 question.
        errors.extend({"step": gap.step, "message": str(gap)} for gap in claim_step_gaps(session))

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
                session,
                ExecutoryContract,
                ExecutoryContractRowSerializer,
                request.data,
                scoped={"vehicle_asset_id": AssetInfo, "owed_debt_id": DebtInfo},
            )
        with transaction.atomic():
            lock_session(session.pk)
            serializer = ExecutoryContractSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
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
        with transaction.atomic():
            lock_session(session.pk)
            serializer = CodebtorSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
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

    @action(detail=True, methods=["get", "put"], url_path="filing-fee", url_name="filing-fee")
    def filing_fee(self, request, pk=None):
        """GET or PUT /api/intake/sessions/{id}/filing-fee/ (3f spec §6.5).

        In any status. A PUT sets only the answers it sends, under the session lock, and never
        reopens a completed intake: how the fee is paid is not intake data. Both reply with the
        eight answers, information and information_gap.
        """
        session = self.get_object()  # another user's session is a 404
        if request.method == "PUT":
            serializer = FilingFeeSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            with transaction.atomic():
                lock_session(session.pk)
                row, _ = FilingFee.objects.get_or_create(session=session)
                for name, value in serializer.validated_data.items():
                    setattr(row, name, value)
                row.save()
        row = FilingFee.objects.filter(session=session).first() or FilingFee(session=session)
        information, gap = filing_fee_information(session)
        return Response(
            {**FilingFeeSerializer(row).data, "information": information, "information_gap": gap}
        )

    @action(detail=True, methods=["get", "put"], url_path="exemptions", url_name="exemptions")
    def exemptions(self, request, pk=None):
        """GET or PUT /api/intake/sessions/{id}/exemptions/ (3g1 spec §5).

        In any status. A PUT sets only the answers it sends and saves the whole claim list when
        it sends one, under the session lock, and never reopens a completed intake: Schedule C's
        answers are not intake data. Both reply with the answers, the claims, the property list
        and the list of laws in force (or why there is none).
        """
        session = self.get_object()  # another user's session is a 404
        try:
            catalog = exemption_catalog_in_force()
        except NoExemptionCatalog:
            catalog = None
        sent_claims = None
        if request.method == "PUT":
            law_keys = set(catalog.laws.values_list("key", flat=True)) if catalog else set()
            serializer = ExemptionsSerializer(data=request.data, context={"law_keys": law_keys})
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            with transaction.atomic():
                lock_session(session.pk)
                claims = data.get("claims")
                if (
                    data.get("no_claims")
                    and claims is None
                    and ExemptionClaim.objects.filter(session=session).exists()
                ):
                    return Response(
                        {
                            "no_claims": [
                                "You can't be claiming no property and also claim property."
                            ]
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if claims:
                    # A row sent by id with some keys only sets those keys on the stored row,
                    # so the per-row checks can't see the merged claim: check it here, before
                    # anything is written (spec 5.2: a law or another law, never both; a dollar
                    # amount only under dollars).
                    stored_rows = {c.pk: c for c in ExemptionClaim.objects.filter(session=session)}
                    merged_errors = {}
                    for index, claim in enumerate(claims):
                        old = stored_rows.get(claim.get("id"))
                        if old is None:
                            continue
                        law = claim["law"] if "law" in claim else old.law
                        other_law = claim.get("other_law", old.other_law) or ""
                        kind = claim["amount_kind"] if "amount_kind" in claim else old.amount_kind
                        amount = claim["amount"] if "amount" in claim else old.amount
                        problems = {}
                        if law is not None and other_law.strip():
                            problems["other_law"] = ["Choose a law or type another law, not both."]
                        if kind == "fair_market_value" and amount is not None:
                            problems["amount"] = [
                                "A claim of the full fair market value takes no dollar amount."
                            ]
                        if problems:
                            merged_errors[str(index)] = problems
                    if merged_errors:
                        return Response(
                            {"claims": merged_errors}, status=status.HTTP_400_BAD_REQUEST
                        )
                answers, _ = ExemptionAnswers.objects.get_or_create(session=session)
                for name in ("line_1", "line_3", "line_3_1", "no_claims"):
                    if name in data:
                        setattr(answers, name, data[name])
                if claims:
                    answers.no_claims = False
                answers.save()
                if claims is not None:
                    rows = []
                    for claim in claims:
                        row = dict(claim)
                        if "asset" in row:
                            row["asset_id"] = row.pop("asset")
                        rows.append(row)
                    sent_claims = _save_rows_by_id(
                        session, ExemptionClaim, rows, scoped={"asset_id": AssetInfo}
                    )
        session = IntakeSession.objects.get(pk=session.pk)
        answers = ExemptionAnswers.objects.filter(session=session).first()
        items = exemption_items(session)
        item_ids = {item.id for item in items}
        stored = sent_claims
        if stored is None:
            stored = ordered_claims(ExemptionClaim.objects.filter(session=session), items)
        return Response(
            {
                "line_1": answers.line_1 if answers else None,
                "line_3": answers.line_3 if answers else None,
                "line_3_1": answers.line_3_1 if answers else None,
                "no_claims": bool(answers.no_claims) if answers else False,
                "claims": [
                    {
                        "id": claim.pk,
                        "asset": claim.asset_id if claim.asset_id in item_ids else None,
                        "law": claim.law,
                        "other_law": claim.other_law or "",
                        "amount_kind": claim.amount_kind,
                        "amount": (
                            None
                            if claim.amount is None
                            else str(Decimal(str(claim.amount)).quantize(Decimal("0.01")))
                        ),
                        "short_description": claim.short_description,
                    }
                    for claim in stored
                ],
                "items": [asdict(item) for item in items],
                "catalog": (
                    None
                    if catalog is None
                    else {
                        "effective_date": catalog.effective_date.isoformat(),
                        "source_url": catalog.source_url,
                        "laws": [
                            {
                                "key": law.key,
                                "citation": law.citation,
                                "jurisdiction": law.jurisdiction,
                                "limit_text": law.limit_text,
                            }
                            for law in catalog.laws.order_by("position")
                        ],
                    }
                ),
                "catalog_gap": None if catalog is not None else "no_table",
            }
        )

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
        if not asset_step_gaps(session):
            completed_sections += 1
        if not any(gap.step == "debts" for gap in claim_step_gaps(session)):
            completed_sections += 1

        return int((completed_sections / total_sections) * 100)


class AssetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing assets within an intake session.

    Provides CRUD operations for individual Schedule A/B rows. A create needs an `ab_line`
    (the base serializer's rule), so this path can't make an old row.
    """

    serializer_class = AssetInfoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only assets for user's intake sessions."""
        return (
            AssetInfo.objects.filter(session__user=self.request.user)
            .select_related("session")
            .order_by("pk")
        )

    @transaction.atomic
    def perform_create(self, serializer):
        _assert_session_owned(serializer.validated_data["session"], self.request.user)
        lock_session(serializer.validated_data["session"].pk)
        serializer.save()
        serializer.instance.session.reopen()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        PUT and PATCH /api/intake/assets/{id}/

        Validation reads the stored row's details, so the sessions are locked before it runs,
        in id order: the row's, and the one a move names when it is the filer's own (DIG-188).
        get_object comes first: another user's row is a 404.
        """
        from rest_framework.exceptions import NotFound

        row = self.get_object()
        locked = {row.session_id}
        # A body that isn't an object, or a session that isn't a number, locks only the row's own
        # session, and the serializer refuses it.
        target = request.data.get("session") if isinstance(request.data, dict) else None
        if target is not None:
            try:
                target_id = int(str(target))
            except ValueError:
                pass
            else:
                locked |= set(
                    IntakeSession.objects.filter(pk=target_id, user=request.user).values_list(
                        "pk", flat=True
                    )
                )
        for session_id in sorted(locked):
            lock_session(session_id)
        # Moved or deleted while the locks were awaited: its new session is not locked here.
        if not AssetInfo.objects.filter(pk=row.pk, session_id__in=locked).exists():
            raise NotFound()
        return super().update(request, *args, **kwargs)

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
        return (
            DebtInfo.objects.filter(session__user=self.request.user)
            .select_related("session")
            .order_by("pk")
        )

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
