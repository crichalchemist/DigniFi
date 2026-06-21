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

    def create_from_credit_report(
        self,
        result: "CreditReportExtraction",  # noqa: F821
        session: IntakeSession,
        source_document: UploadedDocument,
    ) -> list:
        """Create draft DebtInfo records from each non-zero tradeline."""
        created = []
        for tradeline in result.tradelines:
            if tradeline.amount_owed == 0:
                continue
            debt = DebtInfo.objects.create(
                session=session,
                source_document=source_document,
                is_draft=True,
                creditor_name=tradeline.creditor_name[:255],
                account_number=tradeline.account_number or "",
                amount_owed=tradeline.amount_owed,
                debt_type=self._map_account_type(tradeline.account_type),
                is_secured=tradeline.account_type in ("auto_loan", "mortgage"),
                priority_classification=self._priority_for_type(tradeline.account_type),
                data_source="credit_report",
            )
            created.append(debt)
        return created

    @staticmethod
    def _map_account_type(account_type: str) -> str:
        mapping = {
            "credit_card": "credit_card",
            "auto_loan": "auto_loan",
            "student_loan": "student_loan",
            "mortgage": "mortgage",
            "medical": "medical",
            "personal_loan": "personal_loan",
        }
        return mapping.get(account_type, "other")

    @staticmethod
    def _priority_for_type(account_type: str) -> str:
        return "secured" if account_type in ("auto_loan", "mortgage") else "unsecured"
