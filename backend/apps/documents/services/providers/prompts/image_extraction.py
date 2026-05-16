from apps.documents.models import DocumentType

_FIELD_HINTS = {
    DocumentType.CREDITOR_BILL: (
        "creditor_name (string), account_number (string or null), "
        "amount_owed (decimal string), minimum_payment (decimal string or null), "
        "due_date (YYYY-MM-DD or null), creditor_type (one of: credit_card, "
        "medical, personal_loan, student_loan, auto_loan, mortgage, utility, other)"
    ),
    DocumentType.PAY_STUB: (
        "employer_name (string), gross_pay (decimal string), "
        "pay_period_start (YYYY-MM-DD), pay_period_end (YYYY-MM-DD), "
        "ytd_gross (decimal string or null), net_pay (decimal string or null), "
        "deductions_total (decimal string or null)"
    ),
}

_DEFAULT_FIELDS = "all visible fields as key-value pairs"


def build_image_extraction_prompt(document_type: str) -> str:
    fields = _FIELD_HINTS.get(document_type, _DEFAULT_FIELDS)
    return (
        f"You are a document data extraction assistant for a legal filing platform. "
        f'Extract the following fields from this {document_type.replace("_", " ")} image. '
        f"Return ONLY a valid JSON object with these fields: {fields}, "
        f"confidence_score (integer 0-100 reflecting your extraction confidence). "
        f"If a field is not visible or not applicable, set it to null. "
        f"Do not include any text outside the JSON object."
    )
