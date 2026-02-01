# backend/apps/documents/models.py
"""Document intelligence models for OCR processing."""

from django.db import models


class DocumentType(models.TextChoices):
    """Supported document types for OCR processing."""

    # Chapter 7 (Individual) Documents
    PAY_STUB = 'pay_stub', 'Pay Stub'
    BANK_STATEMENT = 'bank_statement', 'Bank Statement'
    CREDIT_COUNSELING_CERT = 'credit_cert', 'Credit Counseling Certificate'
    CREDIT_REPORT = 'credit_report', 'Credit Report'
    TAX_RETURN_PERSONAL = 'tax_return_personal', 'Personal Tax Return (1040)'
    SPECIAL_CIRCUMSTANCES = 'special_circumstances', 'Supporting Document'

    # Chapter 11 (Business) Documents
    BALANCE_SHEET = 'balance_sheet', 'Balance Sheet'
    PROFIT_LOSS = 'profit_loss', 'Profit & Loss Statement'
    CASH_FLOW = 'cash_flow', 'Cash Flow Statement'
    TAX_RETURN_BUSINESS = 'tax_return_business', 'Business Tax Return'
    ACCOUNTS_RECEIVABLE = 'accounts_receivable', 'Accounts Receivable Aging'
    ACCOUNTS_PAYABLE = 'accounts_payable', 'Accounts Payable Aging'
    OPERATING_AGREEMENT = 'operating_agreement', 'Operating Agreement'
    CORPORATE_RESOLUTION = 'corporate_resolution', 'Corporate Resolution'

    # Dual-use (Both chapters)
    LEASE_AGREEMENT = 'lease_agreement', 'Lease Agreement'
    LOAN_AGREEMENT = 'loan_agreement', 'Loan Agreement'
    JUDGMENT = 'judgment', 'Court Judgment'
    LIEN_NOTICE = 'lien_notice', 'Lien Notice'


class OCRStatus(models.TextChoices):
    """Processing status for OCR jobs."""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    VALIDATED = 'validated', 'Validated by User'
