from decimal import Decimal, InvalidOperation

from apps.documents.models import DocumentType, UploadedDocument
from apps.documents.services.processor import ExtractionResult
from apps.intake.models import DebtInfo, IntakeSession

_VALID_DEBT_TYPES = {c[0] for c in DebtInfo.DEBT_TYPE_CHOICES}


class DraftDebtCreator:
    def create_from_result(
        self,
        result: ExtractionResult,
        session: IntakeSession,
        source_document: UploadedDocument,
    ) -> DebtInfo:
        if result.detected_type != DocumentType.CREDITOR_BILL:
            raise ValueError(
                f"DraftDebtCreator only handles CREDITOR_BILL, got {result.detected_type}"
            )

        fields = result.fields
        debt_type = fields.get("creditor_type", "other")
        if debt_type not in _VALID_DEBT_TYPES:
            debt_type = "other"

        try:
            amount_owed = Decimal(str(fields.get("amount_owed", "0")))
        except InvalidOperation:
            amount_owed = Decimal("0")

        return DebtInfo.objects.create(
            session=session,
            creditor_name=fields.get("creditor_name", "Unknown Creditor")[:255],
            debt_type=debt_type,
            account_number=fields.get("account_number") or "",
            amount_owed=amount_owed,
            data_source="uploaded_document",
            is_draft=True,
            source_document=source_document,
        )
