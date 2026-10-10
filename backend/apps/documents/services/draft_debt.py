from decimal import Decimal, InvalidOperation

from apps.documents.models import DocumentType, UploadedDocument
from apps.documents.services.processor import ExtractionResult
from apps.intake.models import DebtInfo, IntakeSession

_VALID_DEBT_TYPES = {c[0] for c in DebtInfo.DEBT_TYPE_CHOICES}

# DebtInfo.amount_owed is read back through DecimalField(max_digits=12, decimal_places=2),
# which raises on NaN, Infinity or a 13th digit and would 500 every read of the session.
_MAX_AMOUNT = Decimal("1e10")
_CENTS = Decimal("0.01")


def _bounded_amount(value: object) -> Decimal:
    """The amount in cents, or 0 when it is not a number, negative, non-finite or >= 1e10."""
    try:
        amount = Decimal(str(value)).quantize(_CENTS)
    except InvalidOperation:  # not a number, infinite, or too many digits to round
        return Decimal("0")
    if amount.is_nan() or amount.is_signed() or amount >= _MAX_AMOUNT:
        return Decimal("0")
    return amount


class DraftDebtCreator:
    def create_from_result(
        self,
        result: ExtractionResult,
        session: IntakeSession,
        source_document: UploadedDocument,
    ) -> DebtInfo | None:
        """Create a draft debt from a scanned bill; None when the bill names no creditor.

        A bill with a creditor but no readable balance still becomes a draft, with
        amount 0, for the filer to complete in the Amounts Owed step.
        """
        if result.detected_type != DocumentType.CREDITOR_BILL:
            raise ValueError(
                f"DraftDebtCreator only handles CREDITOR_BILL, got {result.detected_type}"
            )

        fields = result.fields
        creditor_name = fields.get("creditor_name")
        creditor_name = creditor_name.strip() if isinstance(creditor_name, str) else ""
        if not creditor_name:
            return None

        debt_type = fields.get("creditor_type", "other")
        if debt_type not in _VALID_DEBT_TYPES:
            debt_type = "other"

        return DebtInfo.objects.create(
            session=session,
            creditor_name=creditor_name[:255],
            debt_type=debt_type,
            account_number=str(fields.get("account_number") or ""),
            amount_owed=_bounded_amount(fields.get("amount_owed")),
            data_source="uploaded_document",
            is_draft=True,
            source_document=source_document,
        )

    def create_from_credit_report(
        self,
        result: "CreditReportExtraction",  # noqa: F821
        session: IntakeSession,
        source_document: UploadedDocument,
    ) -> list[DebtInfo]:
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
                amount_owed=_bounded_amount(tradeline.amount_owed),
                debt_type=self._map_account_type(tradeline.account_type),
                is_secured=tradeline.account_type in ("auto_loan", "mortgage"),
                is_in_collections=tradeline.account_status in ("in_collections", "charged_off"),
                priority_classification=self._priority_for_type(tradeline.account_type),
                data_source="credit_report",
            )
            created.append(debt)
        return created

    @staticmethod
    def _map_account_type(account_type: str | None) -> str:
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
    def _priority_for_type(account_type: str | None) -> str:
        return "secured" if account_type in ("auto_loan", "mortgage") else "unsecured"
