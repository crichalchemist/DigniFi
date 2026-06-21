import json
import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.documents.models import DocumentType, OCRResult, OCRStatus, UploadedDocument
from apps.documents.services.aggregator import AggregateIngestionService
from apps.documents.services.draft_debt import DraftDebtCreator
from apps.documents.services.processor import DocumentProcessor
from apps.documents.services.providers.gemini import GeminiProvider
from apps.intake.models import IntakeSession

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def _get_processor() -> DocumentProcessor:
    provider = GeminiProvider(
        model=getattr(settings, "LLM_MODEL", "gemini-2.0-flash"),
    )
    return DocumentProcessor(provider=provider)


def _run_processing(doc_id: int) -> None:
    try:
        doc = UploadedDocument.objects.select_related("session").get(pk=doc_id)
        ocr = OCRResult.objects.get(document=doc)
        ocr.status = OCRStatus.PROCESSING
        ocr.save(update_fields=["status"])

        file_bytes = doc.file.read()
        processor = _get_processor()
        result = processor.process(file_bytes, doc.mime_type, doc.document_type)

        if result.error:
            ocr.status = OCRStatus.FAILED
            ocr.error_message = result.error
            ocr.extracted_data = "{}"
            ocr.overall_confidence = 0
        else:
            ocr.status = OCRStatus.COMPLETED
            ocr.extracted_data = json.dumps(result.fields)
            ocr.confidence_scores = result.confidence
            ocr.overall_confidence = result.confidence.get("overall", 0)

            if doc.document_type == DocumentType.CREDITOR_BILL:
                try:
                    DraftDebtCreator().create_from_result(result, doc.session, doc)
                except Exception as exc:
                    logger.warning("DraftDebtCreator failed for doc %s: %s", doc_id, exc)

        ocr.save()

        if ocr.status == OCRStatus.COMPLETED:
            try:
                AggregateIngestionService.recalculate(doc.session_id)
            except Exception as exc:
                logger.warning("Recalculate failed for doc %s: %s", doc_id, exc)

    except Exception as exc:
        logger.exception("Processing failed for document %s: %s", doc_id, exc)
        try:
            OCRResult.objects.filter(document_id=doc_id).update(
                status=OCRStatus.FAILED, error_message=str(exc)
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
    def validate(self, request, pk=None):
        try:
            doc = UploadedDocument.objects.select_related("ocr_result", "session").get(
                pk=pk, session__user=request.user
            )
        except UploadedDocument.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        fields = request.data.get("fields", {})
        ocr = doc.ocr_result
        existing = json.loads(ocr.extracted_data or "{}")
        existing.update(fields)
        ocr.extracted_data = json.dumps(existing)
        ocr.user_validated = True
        ocr.validation_changes = list(fields.keys())
        ocr.save()

        if doc.document_type == DocumentType.CREDITOR_BILL:
            doc.draft_debts.filter(is_draft=True).update(
                **{k: v for k, v in fields.items() if k in ("creditor_name", "amount_owed")}
            )

        try:
            AggregateIngestionService.recalculate(doc.session_id)
        except Exception as exc:
            logger.warning("Recalculate failed on validate for doc %s: %s", pk, exc)

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
    return {
        "status": ocr.status,
        "extracted_data": json.loads(ocr.extracted_data or "{}"),
        "confidence_scores": ocr.confidence_scores,
        "overall_confidence": float(ocr.overall_confidence),
        "user_validated": ocr.user_validated,
        "error_message": ocr.error_message,
    }
