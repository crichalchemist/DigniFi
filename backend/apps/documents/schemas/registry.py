"""
Schema registry mapping document types to extraction schemas.

Used by DocumentOCRService to select the appropriate schema
for each document type.
"""

from apps.documents.models import DocumentType
from .paystub import PayStubExtraction
from .business import BalanceSheetExtraction, ProfitLossExtraction

# Map document types to their extraction schemas
SCHEMA_MAP = {
    # Chapter 7 (Individual)
    DocumentType.PAY_STUB: PayStubExtraction,
    # Chapter 11 (Business)
    DocumentType.BALANCE_SHEET: BalanceSheetExtraction,
    DocumentType.PROFIT_LOSS: ProfitLossExtraction,

    # TODO: Add remaining schemas as they're created:
    # DocumentType.BANK_STATEMENT: BankStatementExtraction,
    # DocumentType.CREDIT_COUNSELING_CERT: CreditCertExtraction,
    # DocumentType.CREDIT_REPORT: CreditReportExtraction,
    # DocumentType.TAX_RETURN_PERSONAL: PersonalTaxReturnExtraction,
    # DocumentType.TAX_RETURN_BUSINESS: BusinessTaxReturnExtraction,
    # etc.
}


def get_schema_for_type(document_type: str):
    """
    Get extraction schema class for document type.

    Args:
        document_type: DocumentType choice value

    Returns:
        Pydantic schema class

    Raises:
        KeyError: If document type not yet supported
    """
    if document_type not in SCHEMA_MAP:
        raise KeyError(
            f"No extraction schema defined for document type: {document_type}. "
            f"Available types: {list(SCHEMA_MAP.keys())}"
        )

    return SCHEMA_MAP[document_type]
