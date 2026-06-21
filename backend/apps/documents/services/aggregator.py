import json
import logging
from decimal import Decimal

from apps.documents.models import DocumentType, IngestedAggregate, OCRResult, OCRStatus

logger = logging.getLogger(__name__)


class AggregateIngestionService:
    @classmethod
    def recalculate(cls, session_id: int) -> None:
        try:
            results = list(
                OCRResult.objects.filter(
                    document__session_id=session_id, status=OCRStatus.COMPLETED
                ).select_related("document")
            )

            # Group by document type
            by_type = {}
            for res in results:
                by_type.setdefault(res.document.document_type, []).append(res)

            # Recalculate each type
            if DocumentType.PAY_STUB in by_type:
                cls._calc_paystubs(session_id, by_type[DocumentType.PAY_STUB])
            else:
                IngestedAggregate.objects.filter(
                    session_id=session_id, ingest_key__startswith="paystub."
                ).delete()

        except Exception as exc:
            logger.exception(
                "Failed to recalculate ingestion aggregates for session %s: %s", session_id, exc
            )

    @classmethod
    def _calc_paystubs(cls, session_id: int, results: list[OCRResult]) -> None:
        from apps.documents.schemas.paystub import PayStubExtraction

        total_monthly_gross = Decimal("0")
        valid_stubs = 0
        most_recent_end = None
        most_recent_employer: str = ""

        for ocr in results:
            try:
                data = json.loads(ocr.extracted_data or "{}")
                parsed = PayStubExtraction(**data)

                days = (parsed.pay_period_end - parsed.pay_period_start).days + 1
                if days <= 0:
                    continue

                daily_gross = parsed.gross_pay / Decimal(str(days))
                monthly_gross = daily_gross * Decimal("30.41667")

                total_monthly_gross += monthly_gross
                valid_stubs += 1

                if most_recent_end is None or parsed.pay_period_end > most_recent_end:
                    most_recent_end = parsed.pay_period_end
                    most_recent_employer = parsed.employer_name or ""
            except Exception as e:
                logger.warning("Skipping invalid paystub OCRResult %s: %s", ocr.id, e)

        if valid_stubs > 0:
            avg_monthly_gross = (total_monthly_gross / Decimal(str(valid_stubs))).quantize(
                Decimal("0.01")
            )
            IngestedAggregate.objects.update_or_create(
                session_id=session_id,
                ingest_key="paystub.gross",
                defaults={"value": str(avg_monthly_gross)},
            )
            IngestedAggregate.objects.update_or_create(
                session_id=session_id,
                ingest_key="paystub.employer_name",
                defaults={"value": most_recent_employer},
            )
        else:
            IngestedAggregate.objects.filter(
                session_id=session_id, ingest_key__startswith="paystub."
            ).delete()
