# backend/apps/documents/models.py
"""Document intelligence models for OCR processing."""

from django.db import models
from django.contrib.auth import get_user_model
# from encrypted_model_fields.fields import EncryptedFileField  # Not available, use FileField
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


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


class UploadedDocument(models.Model):
    """
    Encrypted storage for user-uploaded documents.

    Documents are automatically deleted after 22 days or when
    bankruptcy forms are filed, whichever comes first.
    """

    # Relations
    session = models.ForeignKey(
        'intake.IntakeSession',
        on_delete=models.CASCADE,
        related_name='uploaded_documents'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_documents'
    )

    # Document metadata
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        help_text="Final document type (after validation)"
    )
    user_declared_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        help_text="Type user selected before upload"
    )
    detected_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        blank=True,
        null=True,
        help_text="Type detected by OCR (for validation)"
    )

    # File storage (TODO: Add encryption at storage layer)
    file = models.FileField(upload_to='documents/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="Size in bytes")
    mime_type = models.CharField(max_length=100)

    # Lifecycle management
    uploaded_at = models.DateTimeField(auto_now_add=True)
    delete_after = models.DateTimeField(
        help_text="Auto-delete after 22 days or form filing"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'uploaded_documents'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['session', 'document_type']),
            models.Index(fields=['delete_after']),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.get_document_type_display()})"

    def save(self, *args, **kwargs):
        """Set delete_after date on creation."""
        if not self.delete_after:
            self.delete_after = timezone.now() + timedelta(days=22)
        super().save(*args, **kwargs)


class OCRResult(models.Model):
    """
    Extracted data from OCR processing.

    Stores encrypted JSON of extracted fields with confidence scores.
    """

    # Relations
    document = models.OneToOneField(
        UploadedDocument,
        on_delete=models.CASCADE,
        related_name='ocr_result'
    )

    # Processing metadata
    status = models.CharField(
        max_length=20,
        choices=OCRStatus.choices,
        default=OCRStatus.PENDING
    )
    ocr_provider = models.CharField(
        max_length=50,
        default='clarifai',
        help_text="OCR provider used (clarifai or vllm)"
    )

    # Extracted data (encrypted JSON)
    extracted_data = models.TextField(
        help_text="JSON structure of extracted fields"
    )
    confidence_scores = models.JSONField(
        default=dict,
        help_text="Per-field confidence scores (0-100)"
    )
    overall_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Overall confidence score (0-100)"
    )

    # User validation
    user_validated = models.BooleanField(default=False)
    validation_changes = models.JSONField(
        default=list,
        help_text="List of fields user corrected after extraction"
    )

    # Timing & errors
    processed_at = models.DateTimeField(auto_now_add=True)
    processing_duration = models.FloatField(
        null=True,
        help_text="Seconds to process"
    )
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'ocr_results'
        ordering = ['-processed_at']

    def __str__(self):
        return f"OCR for {self.document.original_filename} ({self.status})"
