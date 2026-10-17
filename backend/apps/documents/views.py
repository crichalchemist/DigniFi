import json
import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from pydantic import ValidationError
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.documents.models import (
    DocumentType,
    OCRFailureReason,
    OCRResult,
    OCRStatus,
    UploadedDocument,
)
from apps.documents.schemas.credit_report import CreditReportExtraction
from apps.documents.schemas.paystub import PayStubExtraction
from apps.documents.services.aggregator import AggregateIngestionService
from apps.documents.services.draft_debt import DraftDebtCreator
from apps.documents.services.processor import DocumentProcessor, ExtractionResult
from apps.documents.services.providers.base import BaseOCRProvider
from apps.intake.locking import lock_session
from apps.intake.models import IntakeSession

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def _get_processor() -> DocumentProcessor:
    # Providers are imported lazily so the documents URLconf doesn't pull an OCR SDK
    # at module load (and so a missing SDK/key surfaces at OCR time, not app boot).
    provider_name = settings.OCR_PROVIDER.lower()

    if provider_name == "openai":
        from apps.documents.services.providers.openai_provider import OpenAIProvider

        provider: BaseOCRProvider = OpenAIProvider(model=settings.OCR_MODEL or "gpt-4o")
    elif provider_name == "gemini":
        from apps.documents.services.providers.gemini import GeminiProvider

        provider = GeminiProvider(model=settings.OCR_MODEL or "gemini-2.0-flash")
    else:
        raise ImproperlyConfigured(
            f"Unknown OCR_PROVIDER {provider_name!r}; expected 'openai' or 'gemini'."
        )

    return DocumentProcessor(provider=provider)


def _record_findings(doc: UploadedDocument, result: ExtractionResult) -> bool:
    """Store what a scan found. False when it found nothing the filer can use.

    Empty means unread, judged per type: a bill needs a creditor name, a pay stub
    must pass PayStubExtraction (gross pay and both pay-period dates required), the
    check the income aggregate applies, and a credit report needs one readable
    account. Other types are not judged and count as read.

    A draft debt or pay-stub figures change the intake, so they reopen a completed one.
    """
    if doc.document_type == DocumentType.CREDITOR_BILL:
        if DraftDebtCreator().create_from_result(result, doc.session, doc) is None:
            return False
        doc.session.reopen()
        return True
    if doc.document_type == DocumentType.PAY_STUB:
        try:
            PayStubExtraction.model_validate(result.fields)
        except ValidationError:
            return False
        doc.session.reopen()
        return True
    if doc.document_type == DocumentType.CREDIT_REPORT:
        report = CreditReportExtraction.model_validate(result.fields)
        if not report.tradelines:
            return False
        # A report whose accounts are all paid off is read, and adds no debts.
        if DraftDebtCreator().create_from_credit_report(report, doc.session, doc):
            doc.session.reopen()
        return True
    return True


def _run_processing(doc_id: int) -> None:
    try:
        doc = UploadedDocument.objects.select_related("session").get(pk=doc_id)
        ocr = OCRResult.objects.get(document=doc)
        ocr.status = OCRStatus.PROCESSING
        ocr.save(update_fields=["status"])

        file_bytes = doc.file.read()
        processor = _get_processor()
        result = processor.process(file_bytes, doc.mime_type, doc.document_type)

        # The findings are intake data, so their writes lock the session (DIG-188): only
        # here, after the call to the hosted model, and only on this worker thread. The
        # upload request waits for this thread, so a lock taken there would deadlock.
        with transaction.atomic():
            lock_session(doc.session_id)
            if result.error:
                ocr.status = OCRStatus.FAILED
                ocr.failure_reason = OCRFailureReason.PROCESSING_ERROR
                ocr.error_message = result.error
                ocr.extracted_data = "{}"
                ocr.overall_confidence = 0
            else:
                ocr.extracted_data = json.dumps(result.fields)
                ocr.confidence_scores = result.confidence
                ocr.overall_confidence = result.confidence.get("overall", 0)
                if _record_findings(doc, result):
                    ocr.status = OCRStatus.COMPLETED
                else:
                    ocr.status = OCRStatus.FAILED
                    ocr.failure_reason = OCRFailureReason.NOTHING_FOUND

            ocr.save()

            if ocr.status == OCRStatus.COMPLETED:
                try:
                    # Its own savepoint: recalculate logs and swallows its errors, and on
                    # Postgres one failed statement would otherwise roll the findings back.
                    with transaction.atomic():
                        AggregateIngestionService.recalculate(doc.session_id)
                except Exception as exc:
                    logger.warning("Recalculate failed for doc %s: %s", doc_id, type(exc).__name__)

    except Exception as exc:
        # Type only, no traceback: logs reach Sentry, and exception text can quote filer data.
        logger.error("Processing failed for document %s: %s", doc_id, type(exc).__name__)
        try:
            # The class name only: a pydantic error's text quotes the document's values.
            OCRResult.objects.filter(document_id=doc_id).update(
                status=OCRStatus.FAILED,
                failure_reason=OCRFailureReason.PROCESSING_ERROR,
                error_message=type(exc).__name__,
            )
        except Exception:
            pass


class DocumentViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        file = request.FILES.get("file")
        document_type = request.data.get("document_type")
        session_id = request.data.get("session_id")

        if not file or not document_type or not session_id:
            return Response(
                {"error": "file, document_type, and session_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.content_type not in ALLOWED_MIME_TYPES:
            return Response(
                {"error": f"Unsupported file type: {file.content_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            intake_session = IntakeSession.objects.get(pk=session_id, user=request.user)
        except IntakeSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        doc = UploadedDocument.objects.create(
            session=intake_session,
            uploaded_by=request.user,
            document_type=document_type,
            user_declared_type=document_type,
            original_filename=file.name,
            file_size=file.size,
            mime_type=file.content_type,
            file=file,
        )
        OCRResult.objects.create(
            document=doc,
            status=OCRStatus.PENDING,
            ocr_provider=settings.OCR_PROVIDER.lower(),
            extracted_data="{}",
            confidence_scores={},
            overall_confidence=0,
        )

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_run_processing, doc.id)

        return Response({"id": doc.id, "status": "processing"}, status=status.HTTP_202_ACCEPTED)

    def list(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"error": "session_id required"}, status=status.HTTP_400_BAD_REQUEST)
        docs = (
            UploadedDocument.objects.filter(session_id=session_id, session__user=request.user)
            .select_related("ocr_result")
            .order_by("-uploaded_at")
        )
        return Response([_serialize_doc(d) for d in docs])

    def retrieve(self, request, pk=None):
        try:
            doc = UploadedDocument.objects.select_related("ocr_result").get(
                pk=pk, session__user=request.user
            )
        except UploadedDocument.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_doc(doc))

    @action(detail=True, methods=["post"], url_path="validate")
    @transaction.atomic
    def validate(self, request, pk=None):
        try:
            doc = UploadedDocument.objects.select_related("ocr_result", "session").get(
                pk=pk, session__user=request.user
            )
        except UploadedDocument.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        fields = request.data.get("fields", {})
        draft_fields = {k: v for k, v in fields.items() if k in ("creditor_name", "amount_owed")}
        if "amount_owed" in draft_fields:
            # Amounts are readable on every session read, and DecimalField(12, 2) cannot
            # represent a wider value, so refuse it here before anything is written.
            try:
                draft_fields["amount_owed"] = serializers.DecimalField(
                    max_digits=12, decimal_places=2
                ).run_validation(draft_fields["amount_owed"])
            except serializers.ValidationError as exc:
                return Response({"amount_owed": exc.detail}, status=status.HTTP_400_BAD_REQUEST)

        # A correction changes the draft debt and the pay-stub figures (DIG-188).
        lock_session(doc.session_id)
        ocr = doc.ocr_result
        ocr.refresh_from_db()  # the findings as stored once the lock is held
        existing = json.loads(ocr.extracted_data or "{}")
        existing.update(fields)
        ocr.extracted_data = json.dumps(existing)
        ocr.user_validated = True
        ocr.validation_changes = list(fields.keys())
        ocr.save()

        if doc.document_type == DocumentType.CREDITOR_BILL:
            doc.draft_debts.filter(is_draft=True).update(**draft_fields)
        # A bill's draft debt and a pay stub's figures are intake data.
        if doc.document_type in (DocumentType.CREDITOR_BILL, DocumentType.PAY_STUB):
            doc.session.reopen()

        try:
            with transaction.atomic():  # its own savepoint, as in _run_processing
                AggregateIngestionService.recalculate(doc.session_id)
        except Exception as exc:
            logger.warning("Recalculate failed on validate for doc %s: %s", pk, type(exc).__name__)

        return Response(_serialize_ocr(ocr))


def _serialize_doc(doc: UploadedDocument) -> dict:
    result = {
        "id": doc.id,
        "document_type": doc.document_type,
        "original_filename": doc.original_filename,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "ocr_result": None,
    }
    if hasattr(doc, "ocr_result") and doc.ocr_result is not None:
        result["ocr_result"] = _serialize_ocr(doc.ocr_result)
    return result


def _serialize_ocr(ocr: OCRResult) -> dict:
    # Never error_message (operations text) or extracted_data (decrypted PII): the
    # upload page reads only status and failure_reason.
    return {
        "status": ocr.status,
        "failure_reason": ocr.failure_reason,
        "confidence_scores": ocr.confidence_scores,
        "overall_confidence": float(ocr.overall_confidence),
        "user_validated": ocr.user_validated,
    }
