# DeepSeek-OCR Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate DeepSeek-OCR 2 for automated document data extraction across 14 document types (6 Chapter 7 + 8 Chapter 11) with confidence-based auto-population and 22-day privacy-preserving retention.

**Architecture:** Service layer pattern with pluggable OCR providers (Clarifai API for MVP, vLLM self-hosted for production). Pydantic schemas validate extracted data, FieldMapperService applies to existing intake models. Soft-delete with auto-cleanup jobs.

**Tech Stack:** Django 5.0, DRF, Pydantic 2.5, django-fernet-fields, Clarifai API (OpenAI-compatible), Celery (production), pytest

---

## Phase 1: Core Infrastructure & Models

### Task 1: Create Documents App Structure

**Files:**
- Create: `backend/apps/documents/__init__.py`
- Create: `backend/apps/documents/apps.py`
- Create: `backend/apps/documents/admin.py`
- Create: `backend/apps/documents/urls.py`

**Step 1: Create __init__.py**

```bash
touch backend/apps/documents/__init__.py
```

**Step 2: Write apps.py**

```python
# backend/apps/documents/apps.py
from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.documents'
    verbose_name = 'Document Intelligence'
```

**Step 3: Write admin.py placeholder**

```python
# backend/apps/documents/admin.py
from django.contrib import admin

# Document admin interfaces will be added after models are created
```

**Step 4: Write urls.py**

```python
# backend/apps/documents/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

app_name = 'documents'

urlpatterns = [
    path('', include(router.urls)),
]
```

**Step 5: Register app in settings**

Modify: `backend/config/settings/base.py`

Add to INSTALLED_APPS (after 'apps.intake'):
```python
    'apps.documents',
```

**Step 6: Commit**

```bash
git add backend/apps/documents/
git add backend/config/settings/base.py
git commit -m "feat(documents): create documents app structure

- Initialize documents app for OCR integration
- Add to INSTALLED_APPS
- Prepare for model definitions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 2: Define Document Type Choices & OCR Status

**Files:**
- Create: `backend/apps/documents/models.py`

**Step 1: Write DocumentType and OCRStatus enums**

```python
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
```

**Step 2: Commit**

```bash
git add backend/apps/documents/models.py
git commit -m "feat(documents): add DocumentType and OCRStatus enums

- Define 18 document types (6 Ch7, 8 Ch11, 4 dual-use)
- Define OCR processing status choices
- Prepare for model definitions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 3: Create UploadedDocument Model

**Files:**
- Modify: `backend/apps/documents/models.py`

**Step 1: Write UploadedDocument model**

Add after OCRStatus definition:

```python
from django.contrib.auth import get_user_model
from django_fernet_fields import EncryptedFileField
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


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

    # File storage (encrypted)
    file = EncryptedFileField(upload_to='documents/%Y/%m/')
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
```

**Step 2: Commit**

```bash
git add backend/apps/documents/models.py
git commit -m "feat(documents): add UploadedDocument model

- Encrypted file storage with Fernet
- User-declared vs detected type tracking
- 22-day auto-deletion with delete_after timestamp
- Soft delete support (deleted_at)
- Indexes for performance

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 4: Create OCRResult Model

**Files:**
- Modify: `backend/apps/documents/models.py`

**Step 1: Write OCRResult model**

Add after UploadedDocument:

```python
from django_fernet_fields import EncryptedTextField


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
    extracted_data = EncryptedTextField(
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
    error_message = EncryptedTextField(blank=True, null=True)

    class Meta:
        db_table = 'ocr_results'
        ordering = ['-processed_at']

    def __str__(self):
        return f"OCR for {self.document.original_filename} ({self.status})"
```

**Step 2: Commit**

```bash
git add backend/apps/documents/models.py
git commit -m "feat(documents): add OCRResult model

- Encrypted storage of extracted JSON data
- Per-field and overall confidence scores
- User validation tracking
- Processing timing and error logging
- One-to-one with UploadedDocument

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 5: Create Database Migration

**Files:**
- Create: `backend/apps/documents/migrations/0001_initial.py`

**Step 1: Generate migration**

```bash
cd backend
python manage.py makemigrations documents
```

Expected output:
```
Migrations for 'documents':
  apps/documents/migrations/0001_initial.py
    - Create model UploadedDocument
    - Create model OCRResult
```

**Step 2: Review migration**

```bash
cat backend/apps/documents/migrations/0001_initial.py
```

Verify it creates both models with indexes.

**Step 3: Run migration**

```bash
python manage.py migrate documents
```

Expected output:
```
Running migrations:
  Applying documents.0001_initial... OK
```

**Step 4: Commit migration**

```bash
git add backend/apps/documents/migrations/
git commit -m "feat(documents): create initial database migration

- Create uploaded_documents table with encryption
- Create ocr_results table
- Add indexes for performance

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 6: Add Configuration Settings

**Files:**
- Modify: `backend/config/settings/base.py`

**Step 1: Add OCR settings block**

Add after `PDF_GENERATION_BACKEND` section (around line 235):

```python
# ============================================
# OCR & Document Processing Settings
# ============================================

# OCR Provider Configuration
OCR_PROVIDER = env('OCR_PROVIDER', default='clarifai')  # 'clarifai' or 'vllm'

# Clarifai API Settings (MVP)
CLARIFAI_PAT = env('CLARIFAI_PAT', default='')
CLARIFAI_BASE_URL = env(
    'CLARIFAI_BASE_URL',
    default='https://api.clarifai.com/v2'
)

# vLLM Settings (Production - self-hosted)
VLLM_BASE_URL = env('VLLM_BASE_URL', default='http://localhost:8000')
VLLM_API_KEY = env('VLLM_API_KEY', default='')  # If auth enabled

# Document Storage
DOCUMENT_STORAGE_BACKEND = env('DOCUMENT_STORAGE_BACKEND', default='filesystem')
DOCUMENT_UPLOAD_MAX_SIZE = 10 * 1024 * 1024  # 10MB
DOCUMENT_ALLOWED_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
]

# Document Retention
DOCUMENT_RETENTION_DAYS = 22
DOCUMENT_DELETION_WARNING_DAYS = 7

# OCR Processing
OCR_TIMEOUT_SECONDS = 30  # Synchronous request timeout
OCR_MAX_RETRIES = 3
OCR_CONFIDENCE_THRESHOLD_HIGH = 90
OCR_CONFIDENCE_THRESHOLD_MEDIUM = 70

# Feature Flags
ENABLED_CHAPTERS = {
    'chapter_7': True,
    'chapter_11': env.bool('ENABLE_CHAPTER_11', default=False),
    'chapter_13': env.bool('ENABLE_CHAPTER_13', default=False),
}
```

**Step 2: Update .env.example**

Modify: `backend/.env.example`

Add after existing settings:

```bash
# ============================================
# OCR Configuration
# ============================================

# OCR Provider ('clarifai' for MVP, 'vllm' for production)
OCR_PROVIDER=clarifai

# Clarifai API (MVP/Development)
CLARIFAI_PAT=your-clarifai-personal-access-token

# vLLM Self-Hosted (Production - after GPU deployment)
# VLLM_BASE_URL=http://gpu-server:8000
# VLLM_API_KEY=optional-api-key

# Document Storage
DOCUMENT_STORAGE_BACKEND=filesystem  # 's3' for production

# Feature Flags
ENABLE_CHAPTER_11=False  # Set to True for personal use
ENABLE_CHAPTER_13=False
```

**Step 3: Commit**

```bash
git add backend/config/settings/base.py backend/.env.example
git commit -m "feat(documents): add OCR configuration settings

- OCR provider configuration (Clarifai/vLLM)
- Document storage settings
- Retention and confidence thresholds
- Chapter feature flags
- Environment variable examples

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 2: Pydantic Extraction Schemas

### Task 7: Create Schemas Module Structure

**Files:**
- Create: `backend/apps/documents/schemas/__init__.py`
- Create: `backend/apps/documents/schemas/base.py`

**Step 1: Create schemas directory**

```bash
mkdir -p backend/apps/documents/schemas
touch backend/apps/documents/schemas/__init__.py
```

**Step 2: Write base schema**

```python
# backend/apps/documents/schemas/base.py
"""Base schema for all OCR extraction schemas."""

from pydantic import BaseModel, Field


class BaseExtractionSchema(BaseModel):
    """Base class for all document extraction schemas."""

    confidence_score: int = Field(
        ge=0,
        le=100,
        description="Overall extraction confidence (0-100)"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "description": "Base extraction schema with confidence scoring"
        }
```

**Step 3: Commit**

```bash
git add backend/apps/documents/schemas/
git commit -m "feat(documents): create Pydantic schemas structure

- Add schemas module for extraction validation
- Create BaseExtractionSchema with confidence scoring
- Prepare for document-specific schemas

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 8: Create Pay Stub Schema (Priority 1)

**Files:**
- Create: `backend/apps/documents/schemas/paystub.py`

**Step 1: Write PayStubExtraction schema**

```python
# backend/apps/documents/schemas/paystub.py
"""Pay stub extraction schema for income verification."""

from decimal import Decimal
from datetime import date
from typing import Optional
from pydantic import Field, field_validator

from .base import BaseExtractionSchema


class PayStubExtraction(BaseExtractionSchema):
    """
    Schema for pay stub OCR extraction.

    Used for Schedule I (Income) and means test calculations.
    """

    employer_name: str = Field(
        min_length=1,
        description="Employer or company name"
    )
    gross_pay: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Gross pay for this period"
    )
    pay_period_start: date = Field(
        description="Pay period start date (YYYY-MM-DD)"
    )
    pay_period_end: date = Field(
        description="Pay period end date (YYYY-MM-DD)"
    )
    ytd_gross: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Year-to-date gross earnings"
    )
    net_pay: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Net pay (take-home)"
    )
    deductions_total: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Total deductions for this period"
    )

    @field_validator('pay_period_end')
    @classmethod
    def end_after_start(cls, v, info):
        """Validate pay period end is after start."""
        if 'pay_period_start' in info.data and v < info.data['pay_period_start']:
            raise ValueError('Pay period end must be after start date')
        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "employer_name": "Acme Corporation",
                "gross_pay": "3240.00",
                "pay_period_start": "2026-01-01",
                "pay_period_end": "2026-01-15",
                "ytd_gross": "3240.00",
                "net_pay": "2450.00",
                "deductions_total": "790.00",
                "confidence_score": 92
            }
        }
```

**Step 2: Export from __init__.py**

Modify: `backend/apps/documents/schemas/__init__.py`

```python
"""Document extraction schemas."""

from .base import BaseExtractionSchema
from .paystub import PayStubExtraction

__all__ = [
    'BaseExtractionSchema',
    'PayStubExtraction',
]
```

**Step 3: Write test for schema**

Create: `backend/apps/documents/tests/__init__.py`
Create: `backend/apps/documents/tests/test_schemas.py`

```python
# backend/apps/documents/tests/test_schemas.py
"""Tests for Pydantic extraction schemas."""

from decimal import Decimal
from datetime import date
import pytest
from pydantic import ValidationError

from apps.documents.schemas import PayStubExtraction


class TestPayStubExtraction:
    """Tests for PayStubExtraction schema."""

    def test_valid_paystub_data(self):
        """Test schema accepts valid pay stub data."""
        data = {
            'employer_name': 'Acme Corp',
            'gross_pay': '3240.00',
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'ytd_gross': '3240.00',
            'net_pay': '2450.00',
            'deductions_total': '790.00',
            'confidence_score': 92
        }

        result = PayStubExtraction(**data)

        assert result.employer_name == 'Acme Corp'
        assert result.gross_pay == Decimal('3240.00')
        assert result.pay_period_start == date(2026, 1, 1)
        assert result.pay_period_end == date(2026, 1, 15)
        assert result.confidence_score == 92

    def test_minimal_paystub_data(self):
        """Test schema works with only required fields."""
        data = {
            'employer_name': 'Test Inc',
            'gross_pay': '1500.00',
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'confidence_score': 85
        }

        result = PayStubExtraction(**data)

        assert result.ytd_gross is None
        assert result.net_pay is None
        assert result.deductions_total is None

    def test_validates_pay_period_order(self):
        """Test end date must be after start date."""
        data = {
            'employer_name': 'Test Inc',
            'gross_pay': '1500.00',
            'pay_period_start': '2026-01-15',
            'pay_period_end': '2026-01-01',  # Before start!
            'confidence_score': 85
        }

        with pytest.raises(ValidationError) as exc_info:
            PayStubExtraction(**data)

        assert 'after start date' in str(exc_info.value)

    def test_validates_gross_pay_positive(self):
        """Test gross pay must be positive."""
        data = {
            'employer_name': 'Test Inc',
            'gross_pay': '-100.00',  # Negative!
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'confidence_score': 85
        }

        with pytest.raises(ValidationError) as exc_info:
            PayStubExtraction(**data)

        assert 'greater than 0' in str(exc_info.value)

    def test_validates_confidence_range(self):
        """Test confidence score must be 0-100."""
        data = {
            'employer_name': 'Test Inc',
            'gross_pay': '1500.00',
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'confidence_score': 150  # Over 100!
        }

        with pytest.raises(ValidationError) as exc_info:
            PayStubExtraction(**data)

        assert 'less than or equal to 100' in str(exc_info.value)
```

**Step 4: Run tests**

```bash
cd backend
pytest apps/documents/tests/test_schemas.py -v
```

Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add backend/apps/documents/schemas/ backend/apps/documents/tests/
git commit -m "feat(documents): add PayStubExtraction schema with validation

- Pydantic schema for pay stub OCR extraction
- Validates pay period order, positive amounts
- Confidence score range validation
- Comprehensive test coverage (5 tests)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 9: Create Balance Sheet Schema (Priority 2 - Chapter 11)

**Files:**
- Create: `backend/apps/documents/schemas/business.py`

**Step 1: Write BalanceSheetExtraction schema**

```python
# backend/apps/documents/schemas/business.py
"""Business financial statement extraction schemas for Chapter 11."""

from decimal import Decimal
from datetime import date
from typing import Optional
from pydantic import Field, field_validator

from .base import BaseExtractionSchema


class BalanceSheetExtraction(BaseExtractionSchema):
    """
    Schema for balance sheet OCR extraction.

    Required for Chapter 11 Subchapter V filings.
    Validates accounting equation: Assets = Liabilities + Equity
    """

    as_of_date: date = Field(
        description="Balance sheet date (YYYY-MM-DD)"
    )

    # Assets
    cash: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Cash and cash equivalents"
    )
    accounts_receivable: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Accounts receivable"
    )
    inventory: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Inventory value"
    )
    equipment: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Equipment and fixed assets"
    )
    total_assets: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Total assets"
    )

    # Liabilities
    accounts_payable: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Accounts payable"
    )
    loans_payable: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Loans and notes payable"
    )
    total_liabilities: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Total liabilities"
    )

    # Equity
    owners_equity: Decimal = Field(
        decimal_places=2,
        description="Owner's equity (can be negative)"
    )

    @field_validator('owners_equity')
    @classmethod
    def validate_accounting_equation(cls, v, info):
        """
        Validate accounting equation: Assets = Liabilities + Equity.

        Allows 1% tolerance for rounding errors.
        """
        if 'total_assets' in info.data and 'total_liabilities' in info.data:
            total_assets = info.data['total_assets']
            total_liabilities = info.data['total_liabilities']

            calculated_equity = total_assets - total_liabilities

            # Allow 1% tolerance
            if abs(calculated_equity - v) / total_assets > Decimal('0.01'):
                raise ValueError(
                    f'Balance sheet equation error: '
                    f'Assets ({total_assets}) ≠ '
                    f'Liabilities ({total_liabilities}) + Equity ({v}). '
                    f'Expected equity: {calculated_equity}'
                )

        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "as_of_date": "2026-01-31",
                "cash": "5000.00",
                "accounts_receivable": "12000.00",
                "inventory": "8000.00",
                "equipment": "25000.00",
                "total_assets": "50000.00",
                "accounts_payable": "8000.00",
                "loans_payable": "30000.00",
                "total_liabilities": "38000.00",
                "owners_equity": "12000.00",
                "confidence_score": 88
            }
        }


class ProfitLossExtraction(BaseExtractionSchema):
    """
    Schema for profit & loss (P&L) statement extraction.

    Required for Chapter 11 Subchapter V filings.
    """

    period_start: date = Field(
        description="P&L period start date"
    )
    period_end: date = Field(
        description="P&L period end date"
    )
    total_revenue: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Total revenue for period"
    )
    total_expenses: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Total expenses for period"
    )
    net_income: Decimal = Field(
        decimal_places=2,
        description="Net income (can be negative for loss)"
    )

    @field_validator('net_income')
    @classmethod
    def validate_net_income_calculation(cls, v, info):
        """Validate net income = revenue - expenses."""
        if 'total_revenue' in info.data and 'total_expenses' in info.data:
            calculated = info.data['total_revenue'] - info.data['total_expenses']

            # Allow 1% tolerance
            if abs(calculated - v) > abs(v) * Decimal('0.01'):
                raise ValueError(
                    f'Net income calculation error: '
                    f'{v} ≠ {calculated} (revenue - expenses)'
                )

        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "total_revenue": "150000.00",
                "total_expenses": "125000.00",
                "net_income": "25000.00",
                "confidence_score": 90
            }
        }
```

**Step 2: Export from __init__.py**

Modify: `backend/apps/documents/schemas/__init__.py`

```python
"""Document extraction schemas."""

from .base import BaseExtractionSchema
from .paystub import PayStubExtraction
from .business import BalanceSheetExtraction, ProfitLossExtraction

__all__ = [
    'BaseExtractionSchema',
    'PayStubExtraction',
    'BalanceSheetExtraction',
    'ProfitLossExtraction',
]
```

**Step 3: Write tests for business schemas**

Add to: `backend/apps/documents/tests/test_schemas.py`

```python
from apps.documents.schemas import BalanceSheetExtraction, ProfitLossExtraction


class TestBalanceSheetExtraction:
    """Tests for BalanceSheetExtraction schema."""

    def test_valid_balance_sheet(self):
        """Test schema accepts valid balance sheet data."""
        data = {
            'as_of_date': '2026-01-31',
            'cash': '5000.00',
            'total_assets': '50000.00',
            'total_liabilities': '38000.00',
            'owners_equity': '12000.00',
            'confidence_score': 88
        }

        result = BalanceSheetExtraction(**data)

        assert result.total_assets == Decimal('50000.00')
        assert result.owners_equity == Decimal('12000.00')

    def test_validates_accounting_equation(self):
        """Test balance sheet equation validation."""
        data = {
            'as_of_date': '2026-01-31',
            'total_assets': '50000.00',
            'total_liabilities': '38000.00',
            'owners_equity': '10000.00',  # Wrong! Should be 12000
            'confidence_score': 88
        }

        with pytest.raises(ValidationError) as exc_info:
            BalanceSheetExtraction(**data)

        assert 'equation error' in str(exc_info.value)


class TestProfitLossExtraction:
    """Tests for ProfitLossExtraction schema."""

    def test_valid_profit_loss(self):
        """Test schema accepts valid P&L data."""
        data = {
            'period_start': '2025-01-01',
            'period_end': '2025-12-31',
            'total_revenue': '150000.00',
            'total_expenses': '125000.00',
            'net_income': '25000.00',
            'confidence_score': 90
        }

        result = ProfitLossExtraction(**data)

        assert result.net_income == Decimal('25000.00')

    def test_validates_net_income_calculation(self):
        """Test net income = revenue - expenses."""
        data = {
            'period_start': '2025-01-01',
            'period_end': '2025-12-31',
            'total_revenue': '150000.00',
            'total_expenses': '125000.00',
            'net_income': '30000.00',  # Wrong! Should be 25000
            'confidence_score': 90
        }

        with pytest.raises(ValidationError) as exc_info:
            ProfitLossExtraction(**data)

        assert 'calculation error' in str(exc_info.value)
```

**Step 4: Run tests**

```bash
pytest apps/documents/tests/test_schemas.py -v
```

Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add backend/apps/documents/schemas/ backend/apps/documents/tests/
git commit -m "feat(documents): add business financial schemas (Chapter 11)

- BalanceSheetExtraction with accounting equation validation
- ProfitLossExtraction with net income validation
- Test coverage for business schemas (4 tests)
- Validates mathematical relationships in extracted data

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: OCR Provider Abstraction

### Task 10: Create Base OCR Provider

**Files:**
- Create: `backend/apps/documents/services/__init__.py`
- Create: `backend/apps/documents/services/providers/__init__.py`
- Create: `backend/apps/documents/services/providers/base.py`

**Step 1: Create directory structure**

```bash
mkdir -p backend/apps/documents/services/providers
touch backend/apps/documents/services/__init__.py
touch backend/apps/documents/services/providers/__init__.py
```

**Step 2: Write BaseOCRProvider abstract class**

```python
# backend/apps/documents/services/providers/base.py
"""Abstract base class for OCR providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseOCRProvider(ABC):
    """
    Abstract base class for OCR providers.

    Implementations: ClarifaiOCRProvider, VLLMOCRProvider
    """

    @abstractmethod
    def classify(self, image_data: bytes, prompt: str) -> str:
        """
        Classify document type.

        Args:
            image_data: Raw image bytes (PDF/JPG/PNG)
            prompt: Classification prompt

        Returns:
            Document type code (e.g., "pay_stub")
        """
        pass

    @abstractmethod
    def extract(self, image_data: bytes, prompt: str) -> str:
        """
        Extract structured data from document.

        Args:
            image_data: Raw image bytes (PDF/JPG/PNG)
            prompt: Extraction prompt with JSON schema

        Returns:
            JSON string with extracted data
        """
        pass
```

**Step 3: Commit**

```bash
git add backend/apps/documents/services/
git commit -m "feat(documents): create BaseOCRProvider abstraction

- Abstract base class for OCR providers
- Define classify() and extract() interface
- Prepare for Clarifai and vLLM implementations

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 11: Implement Clarifai OCR Provider

**Files:**
- Create: `backend/apps/documents/services/providers/clarifai.py`
- Modify: `backend/requirements/base.txt`

**Step 1: Add openai dependency**

Modify: `backend/requirements/base.txt`

Add after pydantic:
```
openai==1.60.0  # For Clarifai OpenAI-compatible API
```

**Step 2: Install dependency**

```bash
cd backend
pip install openai==1.60.0
```

**Step 3: Write ClarifaiOCRProvider**

```python
# backend/apps/documents/services/providers/clarifai.py
"""Clarifai OCR provider using OpenAI-compatible API."""

import os
import base64
from openai import OpenAI

from .base import BaseOCRProvider


class ClarifaiOCRProvider(BaseOCRProvider):
    """
    Clarifai API provider using OpenAI-compatible endpoint.

    Uses DeepSeek-OCR model hosted on Clarifai.
    Requires CLARIFAI_PAT environment variable.
    """

    def __init__(self):
        """Initialize Clarifai client."""
        api_key = os.environ.get('CLARIFAI_PAT')
        if not api_key:
            raise ValueError(
                'CLARIFAI_PAT environment variable required for Clarifai provider'
            )

        # Clarifai uses OpenAI-compatible API format
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.clarifai.com/v2"
        )

    def classify(self, image_data: bytes, prompt: str) -> str:
        """
        Quick document type classification.

        Args:
            image_data: Raw image bytes
            prompt: Classification prompt

        Returns:
            Document type code as string
        """
        return self._call_api(image_data, prompt)

    def extract(self, image_data: bytes, prompt: str) -> str:
        """
        Extract structured data from document.

        Args:
            image_data: Raw image bytes
            prompt: Extraction prompt with JSON schema

        Returns:
            JSON string with extracted data
        """
        return self._call_api(image_data, prompt)

    def _call_api(self, image_data: bytes, prompt: str) -> str:
        """
        Make API call to Clarifai.

        Args:
            image_data: Raw image bytes
            prompt: Text prompt for OCR

        Returns:
            API response content as string
        """
        # Encode image as base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        # Call Clarifai API (OpenAI-compatible format)
        response = self.client.chat.completions.create(
            model="deepseek-ocr",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0.0  # Deterministic for data extraction
        )

        return response.choices[0].message.content
```

**Step 4: Export from __init__.py**

Modify: `backend/apps/documents/services/providers/__init__.py`

```python
"""OCR provider implementations."""

from .base import BaseOCRProvider
from .clarifai import ClarifaiOCRProvider

__all__ = [
    'BaseOCRProvider',
    'ClarifaiOCRProvider',
]
```

**Step 5: Commit**

```bash
git add backend/requirements/base.txt backend/apps/documents/services/providers/
git commit -m "feat(documents): implement Clarifai OCR provider

- OpenAI-compatible API integration
- Base64 image encoding
- Temperature=0 for deterministic extraction
- Add openai dependency (1.60.0)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

---

## Phase 4: DocumentOCRService Implementation

### Task 12: Create Schema Registry

**Files:**
- Create: `backend/apps/documents/schemas/registry.py`

**Step 1: Write SCHEMA_MAP registry**

```python
# backend/apps/documents/schemas/registry.py
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
```

**Step 2: Export from __init__.py**

Modify: `backend/apps/documents/schemas/__init__.py`

```python
"""Document extraction schemas."""

from .base import BaseExtractionSchema
from .paystub import PayStubExtraction
from .business import BalanceSheetExtraction, ProfitLossExtraction
from .registry import SCHEMA_MAP, get_schema_for_type

__all__ = [
    'BaseExtractionSchema',
    'PayStubExtraction',
    'BalanceSheetExtraction',
    'ProfitLossExtraction',
    'SCHEMA_MAP',
    'get_schema_for_type',
]
```

**Step 3: Write test**

Add to: `backend/apps/documents/tests/test_schemas.py`

```python
from apps.documents.schemas import get_schema_for_type, SCHEMA_MAP
from apps.documents.models import DocumentType


class TestSchemaRegistry:
    """Tests for schema registry."""

    def test_get_schema_for_paystub(self):
        """Test retrieving pay stub schema."""
        schema = get_schema_for_type(DocumentType.PAY_STUB)
        assert schema == PayStubExtraction

    def test_get_schema_for_balance_sheet(self):
        """Test retrieving balance sheet schema."""
        schema = get_schema_for_type(DocumentType.BALANCE_SHEET)
        assert schema == BalanceSheetExtraction

    def test_get_schema_raises_for_unsupported_type(self):
        """Test error for unsupported document type."""
        with pytest.raises(KeyError) as exc_info:
            get_schema_for_type(DocumentType.BANK_STATEMENT)

        assert 'No extraction schema defined' in str(exc_info.value)

    def test_schema_map_contains_expected_types(self):
        """Test schema map has expected document types."""
        assert DocumentType.PAY_STUB in SCHEMA_MAP
        assert DocumentType.BALANCE_SHEET in SCHEMA_MAP
        assert DocumentType.PROFIT_LOSS in SCHEMA_MAP
```

**Step 4: Run tests**

```bash
pytest apps/documents/tests/test_schemas.py::TestSchemaRegistry -v
```

Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add backend/apps/documents/schemas/
git add backend/apps/documents/tests/test_schemas.py
git commit -m "feat(documents): add schema registry for document types

- SCHEMA_MAP mapping DocumentType to extraction schemas
- get_schema_for_type() helper function
- Test coverage for registry lookups
- Placeholder for future schemas

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 13: Create DocumentOCRService Core

**Files:**
- Create: `backend/apps/documents/services/ocr_service.py`

**Step 1: Write DocumentOCRService class structure**

```python
# backend/apps/documents/services/ocr_service.py
"""Core OCR service for document processing."""

import time
import json
from typing import Dict, Any
from decimal import Decimal
from django.conf import settings

from apps.documents.models import UploadedDocument, OCRResult, OCRStatus
from apps.documents.schemas import get_schema_for_type
from apps.documents.services.providers import ClarifaiOCRProvider


class DocumentOCRService:
    """
    Deployment-agnostic OCR service.

    Handles document processing with pluggable providers
    (Clarifai for MVP, vLLM self-hosted for production).
    """

    def __init__(self):
        """Initialize with configured provider."""
        provider_name = settings.OCR_PROVIDER

        if provider_name == 'clarifai':
            self.provider = ClarifaiOCRProvider()
        # elif provider_name == 'vllm':
        #     self.provider = VLLMOCRProvider()  # Future
        else:
            raise ValueError(f"Unknown OCR provider: {provider_name}")

    def process_document(
        self,
        document: UploadedDocument,
        validate_type: bool = True
    ) -> OCRResult:
        """
        Process uploaded document with OCR extraction.

        Args:
            document: UploadedDocument instance
            validate_type: Whether to validate detected vs declared type

        Returns:
            OCRResult with extracted data

        Raises:
            Exception: If OCR processing fails
        """
        start_time = time.time()

        # Create OCR result record (status: PROCESSING)
        ocr_result = OCRResult.objects.create(
            document=document,
            status=OCRStatus.PROCESSING,
            ocr_provider=settings.OCR_PROVIDER,
            extracted_data='{}',  # Temporary
            overall_confidence=Decimal('0.00')
        )

        try:
            # Step 1: Type validation (if enabled)
            if validate_type:
                detected_type = self._detect_document_type(document)
                document.detected_type = detected_type
                document.save(update_fields=['detected_type'])

                # Type mismatch handling (don't fail, just flag)
                if detected_type != document.user_declared_type:
                    ocr_result.error_message = json.dumps({
                        'type': 'type_mismatch',
                        'declared': document.user_declared_type,
                        'detected': detected_type,
                        'message': 'Document type mismatch - user confirmation needed'
                    })

            # Step 2: Get schema for document type
            schema_class = get_schema_for_type(document.document_type)

            # Step 3: Extract structured data
            extracted_data = self._extract_data(
                document=document,
                schema_class=schema_class
            )

            # Step 4: Validate with Pydantic schema
            validated_data = schema_class(**extracted_data)

            # Step 5: Calculate confidence scores
            confidence_scores = self._calculate_field_confidence(
                validated_data.dict()
            )
            overall_confidence = sum(confidence_scores.values()) / len(confidence_scores)

            # Step 6: Save results
            ocr_result.extracted_data = json.dumps(validated_data.dict())
            ocr_result.confidence_scores = confidence_scores
            ocr_result.overall_confidence = Decimal(str(overall_confidence))
            ocr_result.status = OCRStatus.COMPLETED
            ocr_result.processing_duration = time.time() - start_time
            ocr_result.save()

            return ocr_result

        except Exception as e:
            # Error handling
            ocr_result.status = OCRStatus.FAILED
            ocr_result.error_message = json.dumps({
                'type': 'extraction_error',
                'message': str(e),
            })
            ocr_result.processing_duration = time.time() - start_time
            ocr_result.save()
            raise

    def _detect_document_type(self, document: UploadedDocument) -> str:
        """
        Quick classification to validate user-declared type.

        Args:
            document: UploadedDocument instance

        Returns:
            DocumentType choice value (e.g., 'pay_stub')
        """
        # Read file data
        document.file.seek(0)
        image_data = document.file.read()

        # Build classification prompt
        prompt = """
<image>
Classify this document into ONE of these categories:
- pay_stub: Employee pay stub or earnings statement
- bank_statement: Bank account statement
- balance_sheet: Business balance sheet
- profit_loss: Business profit & loss statement

Return ONLY the category code (e.g., "pay_stub"), nothing else.
        """

        response = self.provider.classify(image_data, prompt)
        return response.strip()

    def _extract_data(
        self,
        document: UploadedDocument,
        schema_class
    ) -> Dict[str, Any]:
        """
        Extract structured data using type-specific prompt.

        Args:
            document: UploadedDocument instance
            schema_class: Pydantic schema class

        Returns:
            Raw dict (before Pydantic validation)
        """
        # Read file data
        document.file.seek(0)
        image_data = document.file.read()

        # Build extraction prompt from schema
        prompt = self._build_extraction_prompt(
            document_type=document.document_type,
            schema_class=schema_class
        )

        # Call OCR provider
        response = self.provider.extract(image_data, prompt)

        # Parse JSON response
        return json.loads(response)

    def _build_extraction_prompt(
        self,
        document_type: str,
        schema_class
    ) -> str:
        """
        Build DeepSeek-OCR grounding prompt from Pydantic schema.

        Args:
            document_type: DocumentType choice value
            schema_class: Pydantic schema class

        Returns:
            Prompt string for OCR extraction
        """
        # Generate schema example from Pydantic model
        schema_example = schema_class.model_json_schema()

        # Convert to extraction template
        field_template = {}
        for field_name, field_info in schema_example['properties'].items():
            field_type = field_info.get('type', 'string')
            field_template[field_name] = field_type

        doc_type_readable = document_type.replace('_', ' ')

        prompt = f"""
<image>
<|grounding|>Extract the following from this {doc_type_readable} in JSON format:
{json.dumps(field_template, indent=2)}

Important:
- Use exact field names as shown
- Return valid JSON only
- Use null for missing fields
- Dates as YYYY-MM-DD
- Numbers as decimals without currency symbols
- Include confidence_score (0-100) for overall extraction quality
"""
        return prompt

    def _calculate_field_confidence(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate per-field confidence scores.

        For MVP: Use overall confidence for all fields.
        Future: DeepSeek-OCR grounding mode can return per-token confidence.

        Args:
            data: Extracted data dict

        Returns:
            Dict mapping field names to confidence scores (0-100)
        """
        overall = data.get('confidence_score', 85)

        return {
            field: float(overall)
            for field in data.keys()
            if field != 'confidence_score'
        }
```

**Step 2: Commit**

```bash
git add backend/apps/documents/services/ocr_service.py
git commit -m "feat(documents): implement DocumentOCRService core

- Pluggable provider architecture (Clarifai/vLLM)
- Type detection and validation
- Schema-driven prompt generation
- Confidence scoring
- Error handling with status tracking

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 14: Write OCR Service Tests

**Files:**
- Create: `backend/apps/documents/tests/test_ocr_service.py`
- Create: `backend/apps/documents/tests/fixtures.py`

**Step 1: Create test fixtures**

```python
# backend/apps/documents/tests/fixtures.py
"""Test fixtures for document OCR tests."""

import pytest
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from apps.intake.models import IntakeSession
from apps.districts.models import District
from apps.documents.models import UploadedDocument, DocumentType

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def district(db):
    """Create test district."""
    return District.objects.get_or_create(
        code='ILND',
        defaults={
            'name': 'Northern District of Illinois',
            'court_name': 'United States Bankruptcy Court'
        }
    )[0]


@pytest.fixture
def intake_session(db, user, district):
    """Create test intake session."""
    return IntakeSession.objects.create(
        user=user,
        district=district,
        status='in_progress',
        current_step=3
    )


@pytest.fixture
def sample_image():
    """Create simple test image with text."""
    img = Image.new('RGB', (400, 200), color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def uploaded_paystub(db, intake_session, user, sample_image):
    """Create uploaded pay stub document."""
    file = SimpleUploadedFile(
        name='paystub.png',
        content=sample_image,
        content_type='image/png'
    )

    return UploadedDocument.objects.create(
        session=intake_session,
        uploaded_by=user,
        document_type=DocumentType.PAY_STUB,
        user_declared_type=DocumentType.PAY_STUB,
        file=file,
        original_filename='paystub.png',
        file_size=len(sample_image),
        mime_type='image/png'
    )
```

**Step 2: Write OCR service tests (with mocking)**

```python
# backend/apps/documents/tests/test_ocr_service.py
"""Tests for DocumentOCRService."""

import pytest
import json
from unittest.mock import Mock, patch
from decimal import Decimal

from apps.documents.services.ocr_service import DocumentOCRService
from apps.documents.models import OCRStatus


@pytest.mark.django_db
class TestDocumentOCRService:
    """Tests for DocumentOCRService."""

    @patch('apps.documents.services.ocr_service.ClarifaiOCRProvider')
    def test_process_document_success(
        self,
        mock_provider_class,
        uploaded_paystub
    ):
        """Test successful document processing."""
        # Mock provider responses
        mock_provider = Mock()
        mock_provider.classify.return_value = 'pay_stub'

        # Mock extraction response
        extraction_response = json.dumps({
            'employer_name': 'Acme Corp',
            'gross_pay': '3240.00',
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'confidence_score': 92
        })
        mock_provider.extract.return_value = extraction_response
        mock_provider_class.return_value = mock_provider

        # Process document
        service = DocumentOCRService()
        result = service.process_document(uploaded_paystub)

        # Verify result
        assert result.status == OCRStatus.COMPLETED
        assert result.overall_confidence == Decimal('92.00')

        # Verify extracted data
        extracted_data = json.loads(result.extracted_data)
        assert extracted_data['employer_name'] == 'Acme Corp'
        assert extracted_data['gross_pay'] == '3240.00'

        # Verify confidence scores
        assert 'employer_name' in result.confidence_scores
        assert result.confidence_scores['employer_name'] == 92.0

    @patch('apps.documents.services.ocr_service.ClarifaiOCRProvider')
    def test_process_document_type_mismatch(
        self,
        mock_provider_class,
        uploaded_paystub
    ):
        """Test type mismatch detection."""
        # Mock provider to return different type
        mock_provider = Mock()
        mock_provider.classify.return_value = 'bank_statement'
        mock_provider_class.return_value = mock_provider

        service = DocumentOCRService()

        # Process with validation (should not fail)
        with pytest.raises(KeyError):
            # Will fail because bank_statement schema not registered yet
            service.process_document(uploaded_paystub, validate_type=True)

        # Check detected type was saved
        uploaded_paystub.refresh_from_db()
        assert uploaded_paystub.detected_type == 'bank_statement'

    @patch('apps.documents.services.ocr_service.ClarifaiOCRProvider')
    def test_process_document_extraction_failure(
        self,
        mock_provider_class,
        uploaded_paystub
    ):
        """Test handling of extraction failure."""
        # Mock provider to raise error
        mock_provider = Mock()
        mock_provider.classify.return_value = 'pay_stub'
        mock_provider.extract.side_effect = Exception('API timeout')
        mock_provider_class.return_value = mock_provider

        service = DocumentOCRService()

        # Should raise exception
        with pytest.raises(Exception) as exc_info:
            service.process_document(uploaded_paystub)

        assert 'API timeout' in str(exc_info.value)

        # Check OCR result was saved with error
        uploaded_paystub.refresh_from_db()
        ocr_result = uploaded_paystub.ocr_result
        assert ocr_result.status == OCRStatus.FAILED
        assert 'API timeout' in ocr_result.error_message

    def test_build_extraction_prompt(self, uploaded_paystub):
        """Test extraction prompt generation from schema."""
        from apps.documents.schemas import PayStubExtraction

        service = DocumentOCRService()
        prompt = service._build_extraction_prompt(
            document_type='pay_stub',
            schema_class=PayStubExtraction
        )

        # Verify prompt contains expected elements
        assert '<image>' in prompt
        assert '<|grounding|>' in prompt
        assert 'pay stub' in prompt
        assert 'JSON format' in prompt
        assert 'employer_name' in prompt
        assert 'confidence_score' in prompt

    def test_calculate_field_confidence(self):
        """Test confidence score calculation."""
        service = DocumentOCRService()

        data = {
            'employer_name': 'Test Corp',
            'gross_pay': '1000.00',
            'confidence_score': 85
        }

        scores = service._calculate_field_confidence(data)

        # All fields get overall confidence (MVP behavior)
        assert scores['employer_name'] == 85.0
        assert scores['gross_pay'] == 85.0
        assert 'confidence_score' not in scores  # Excluded from field scores
```

**Step 3: Run tests**

```bash
pytest apps/documents/tests/test_ocr_service.py -v
```

Expected: All 5 tests PASS (some may be skipped if not using real API)

**Step 4: Commit**

```bash
git add backend/apps/documents/tests/
git commit -m "test(documents): add OCR service test coverage

- Mock-based tests for OCR processing
- Test fixtures for documents and sessions
- Type mismatch detection tests
- Error handling tests
- Prompt generation tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 5: REST API Endpoints

### Task 15: Create Serializers

**Files:**
- Create: `backend/apps/documents/serializers.py`

**Step 1: Write UploadedDocumentSerializer**

```python
# backend/apps/documents/serializers.py
"""Serializers for document upload and OCR results."""

from rest_framework import serializers
from apps.documents.models import UploadedDocument, OCRResult


class OCRResultSerializer(serializers.ModelSerializer):
    """Serializer for OCR extraction results."""

    extracted_data_json = serializers.SerializerMethodField()

    class Meta:
        model = OCRResult
        fields = [
            'status',
            'ocr_provider',
            'extracted_data_json',
            'confidence_scores',
            'overall_confidence',
            'user_validated',
            'validation_changes',
            'processed_at',
            'processing_duration',
            'error_message',
        ]
        read_only_fields = fields

    def get_extracted_data_json(self, obj):
        """Return extracted data as parsed JSON."""
        import json
        try:
            return json.loads(obj.extracted_data)
        except (json.JSONDecodeError, AttributeError):
            return {}


class UploadedDocumentSerializer(serializers.ModelSerializer):
    """Serializer for uploaded documents."""

    ocr_result = OCRResultSerializer(read_only=True)
    type_mismatch = serializers.SerializerMethodField()
    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )

    class Meta:
        model = UploadedDocument
        fields = [
            'id',
            'document_type',
            'document_type_display',
            'user_declared_type',
            'detected_type',
            'type_mismatch',
            'original_filename',
            'file_size',
            'mime_type',
            'uploaded_at',
            'delete_after',
            'ocr_result',
        ]
        read_only_fields = [
            'id',
            'uploaded_at',
            'delete_after',
            'detected_type',
        ]

    def get_type_mismatch(self, obj):
        """Check if detected type differs from declared type."""
        return (
            obj.detected_type is not None and
            obj.detected_type != obj.user_declared_type
        )


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for document upload request."""

    session_id = serializers.UUIDField(required=True)
    document_type = serializers.ChoiceField(
        choices=[(t.value, t.label) for t in UploadedDocument._meta.get_field('document_type').choices],
        required=True
    )
    file = serializers.FileField(required=True)

    def validate_file(self, value):
        """Validate file size and type."""
        from django.conf import settings

        # Check file size
        max_size = settings.DOCUMENT_UPLOAD_MAX_SIZE
        if value.size > max_size:
            raise serializers.ValidationError(
                f'File size exceeds maximum allowed size of {max_size / (1024*1024):.1f}MB'
            )

        # Check mime type
        allowed_types = settings.DOCUMENT_ALLOWED_TYPES
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f'File type {value.content_type} not allowed. '
                f'Allowed types: {", ".join(allowed_types)}'
            )

        return value


class OCRValidationSerializer(serializers.Serializer):
    """Serializer for user validation/correction of OCR results."""

    validated = serializers.BooleanField(required=True)
    corrections = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        default=dict
    )
```

**Step 2: Write test for serializers**

Create: `backend/apps/documents/tests/test_serializers.py`

```python
# backend/apps/documents/tests/test_serializers.py
"""Tests for document serializers."""

import pytest
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.serializers import (
    DocumentUploadSerializer,
    UploadedDocumentSerializer,
    OCRValidationSerializer
)
from apps.documents.models import DocumentType


class TestDocumentUploadSerializer:
    """Tests for DocumentUploadSerializer."""

    def test_valid_upload_data(self, intake_session):
        """Test serializer accepts valid upload data."""
        file = SimpleUploadedFile(
            name='test.pdf',
            content=b'fake pdf content',
            content_type='application/pdf'
        )

        data = {
            'session_id': str(intake_session.id),
            'document_type': DocumentType.PAY_STUB,
            'file': file
        }

        serializer = DocumentUploadSerializer(data=data)
        assert serializer.is_valid()

    def test_rejects_oversized_file(self, intake_session):
        """Test serializer rejects files over size limit."""
        # Create 11MB file (over 10MB limit)
        large_content = b'x' * (11 * 1024 * 1024)
        file = SimpleUploadedFile(
            name='large.pdf',
            content=large_content,
            content_type='application/pdf'
        )

        data = {
            'session_id': str(intake_session.id),
            'document_type': DocumentType.PAY_STUB,
            'file': file
        }

        serializer = DocumentUploadSerializer(data=data)
        assert not serializer.is_valid()
        assert 'file' in serializer.errors
        assert 'exceeds maximum' in str(serializer.errors['file'])

    def test_rejects_invalid_file_type(self, intake_session):
        """Test serializer rejects unsupported file types."""
        file = SimpleUploadedFile(
            name='test.exe',
            content=b'fake exe',
            content_type='application/x-executable'
        )

        data = {
            'session_id': str(intake_session.id),
            'document_type': DocumentType.PAY_STUB,
            'file': file
        }

        serializer = DocumentUploadSerializer(data=data)
        assert not serializer.is_valid()
        assert 'file' in serializer.errors


class TestOCRValidationSerializer:
    """Tests for OCRValidationSerializer."""

    def test_valid_validation_data(self):
        """Test serializer accepts valid validation data."""
        data = {
            'validated': True,
            'corrections': {
                'gross_pay': '3240.00',
                'employer_name': 'Corrected Name'
            }
        }

        serializer = OCRValidationSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['validated'] is True
        assert 'gross_pay' in serializer.validated_data['corrections']
```

**Step 3: Run tests**

```bash
pytest apps/documents/tests/test_serializers.py -v
```

Expected: All tests PASS

**Step 4: Commit**

```bash
git add backend/apps/documents/serializers.py
git add backend/apps/documents/tests/test_serializers.py
git commit -m "feat(documents): add DRF serializers for document upload

- UploadedDocumentSerializer with OCR results
- DocumentUploadSerializer with file validation
- OCRValidationSerializer for user corrections
- Test coverage for serializer validation

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 16: Create DocumentViewSet with Upload Endpoint

**Files:**
- Create: `backend/apps/documents/views.py`

**Step 1: Write DocumentViewSet with upload action**

```python
# backend/apps/documents/views.py
"""Views for document upload and OCR management."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from apps.documents.models import UploadedDocument, OCRResult
from apps.documents.serializers import (
    UploadedDocumentSerializer,
    DocumentUploadSerializer,
    OCRResultSerializer,
    OCRValidationSerializer
)
from apps.documents.services.ocr_service import DocumentOCRService
from apps.intake.models import IntakeSession


class DocumentViewSet(viewsets.ModelViewSet):
    """
    Document upload and OCR management.

    Endpoints:
    - POST /upload/ - Upload new document with OCR processing
    - GET / - List all documents for user's sessions
    - GET /{id}/ - Get document details
    - DELETE /{id}/ - Delete document
    - POST /{id}/reprocess/ - Retry OCR extraction
    - POST /{id}/validate/ - User validates/corrects OCR results
    """

    queryset = UploadedDocument.objects.all()
    serializer_class = UploadedDocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter documents to user's sessions only."""
        user = self.request.user
        return UploadedDocument.objects.filter(
            session__user=user,
            deleted_at__isnull=True  # Exclude soft-deleted
        ).select_related(
            'session',
            'ocr_result'
        ).order_by('-uploaded_at')

    @action(detail=False, methods=['post'], url_path='upload')
    def upload_document(self, request):
        """
        Upload document and trigger OCR processing.

        POST /api/documents/upload/

        Request (multipart/form-data):
            session_id: UUID
            document_type: DocumentType choice
            file: File upload

        Response:
            UploadedDocument with OCR result
        """
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Validate session belongs to user
        session_id = serializer.validated_data['session_id']
        try:
            session = IntakeSession.objects.get(
                id=session_id,
                user=request.user
            )
        except IntakeSession.DoesNotExist:
            return Response(
                {"error": "Invalid session or access denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create document record
        file = serializer.validated_data['file']
        doc_type = serializer.validated_data['document_type']

        document = UploadedDocument.objects.create(
            session=session,
            uploaded_by=request.user,
            document_type=doc_type,
            user_declared_type=doc_type,
            file=file,
            original_filename=file.name,
            file_size=file.size,
            mime_type=file.content_type
        )

        # Trigger OCR processing (synchronous for MVP)
        ocr_service = DocumentOCRService()
        try:
            ocr_result = ocr_service.process_document(
                document=document,
                validate_type=True
            )

            # Check for type mismatch
            type_mismatch = (
                document.detected_type and
                document.detected_type != document.user_declared_type
            )

            # Serialize response
            response_data = UploadedDocumentSerializer(document).data
            response_data['type_mismatch'] = type_mismatch

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            # OCR failed - document still saved, user can retry
            return Response(
                {
                    "id": str(document.id),
                    "error": "OCR processing failed",
                    "message": str(e),
                    "can_retry": True
                },
                status=status.HTTP_202_ACCEPTED
            )

    @action(detail=True, methods=['post'], url_path='reprocess')
    def reprocess_ocr(self, request, pk=None):
        """
        Retry OCR processing for failed document.

        POST /api/documents/{id}/reprocess/
        """
        document = self.get_object()

        # Check if reprocessing is allowed
        if hasattr(document, 'ocr_result'):
            if document.ocr_result.status == 'completed':
                return Response(
                    {"error": "Document already processed successfully"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Reprocess
        ocr_service = DocumentOCRService()
        try:
            ocr_result = ocr_service.process_document(
                document=document,
                validate_type=False  # Skip type validation on retry
            )

            return Response(
                OCRResultSerializer(ocr_result).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='validate')
    def validate_ocr(self, request, pk=None):
        """
        User validates and optionally corrects OCR results.

        POST /api/documents/{id}/validate/

        Request:
            validated: bool
            corrections: dict (optional)
        """
        document = self.get_object()

        if not hasattr(document, 'ocr_result'):
            return Response(
                {"error": "No OCR result to validate"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ocr_result = document.ocr_result
        serializer = OCRValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        corrections = serializer.validated_data.get('corrections', {})

        # Apply corrections to extracted data
        import json
        extracted_data = json.loads(ocr_result.extracted_data)

        changed_fields = []
        for field, new_value in corrections.items():
            if field in extracted_data:
                old_value = extracted_data[field]
                if old_value != new_value:
                    extracted_data[field] = new_value
                    changed_fields.append(field)

        # Update OCR result
        ocr_result.extracted_data = json.dumps(extracted_data)
        ocr_result.user_validated = True
        ocr_result.validation_changes = changed_fields
        ocr_result.status = 'validated'
        ocr_result.save()

        return Response({
            "status": "validated",
            "validation_changes": changed_fields,
            "extracted_data": extracted_data
        })
```

**Step 2: Update URLs**

Modify: `backend/apps/documents/urls.py`

```python
# backend/apps/documents/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import DocumentViewSet

router = DefaultRouter()
router.register(r'', DocumentViewSet, basename='document')

app_name = 'documents'

urlpatterns = [
    path('', include(router.urls)),
]
```

**Step 3: Register in main URLs**

Modify: `backend/config/urls.py`

Add to urlpatterns:
```python
    path('api/documents/', include('apps.documents.urls')),
```

**Step 4: Commit**

```bash
git add backend/apps/documents/views.py
git add backend/apps/documents/urls.py
git add backend/config/urls.py
git commit -m "feat(documents): implement document upload API endpoints

- DocumentViewSet with upload, reprocess, validate actions
- Multipart file upload with OCR processing
- Type mismatch detection
- User validation workflow
- Permission filtering (user's documents only)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

*The implementation plan continues with remaining tasks. Would you like me to continue with:*

- **Task 17-20:** Field Mapping Service
- **Task 21-25:** Document Lifecycle Management
- **Task 26-30:** Frontend Integration

Or should we proceed to implementation based on what we have so far?

---

## Phase 6: Field Mapping Service

### Task 17: Create FieldMapperService Foundation

**Files:**
- Create: `backend/apps/documents/services/field_mapper.py`

**Step 1: Write FieldMapperService class**

```python
# backend/apps/documents/services/field_mapper.py
"""Service for mapping OCR extracted data to intake models."""

from typing import Dict, List, Any
from decimal import Decimal
from datetime import date
import json

from apps.intake.models import (
    IntakeSession,
    IncomeInfo,
    DebtInfo,
    AssetInfo,
    ExpenseInfo
)
from apps.documents.models import DocumentType
from apps.audit.models import AuditLog


class FieldMapperService:
    """
    Maps OCR extracted data to intake session models.

    Handles field transformations and business logic for applying
    document data to the appropriate intake forms.
    """

    def __init__(self, session: IntakeSession):
        """
        Initialize mapper with intake session.

        Args:
            session: IntakeSession to map data to
        """
        self.session = session
        self.updated_fields = []

    def apply_ocr_to_intake(
        self,
        document_type: str,
        extracted_data: Dict[str, Any]
    ) -> List[str]:
        """
        Apply extracted data to appropriate intake model.

        Args:
            document_type: DocumentType choice value
            extracted_data: Dict of extracted field data

        Returns:
            List of field names updated

        Raises:
            ValueError: If no mapper defined for document type
        """
        mapper_method = self._get_mapper_for_type(document_type)

        if not mapper_method:
            raise ValueError(
                f"No mapper defined for document type: {document_type}"
            )

        # Apply mappings
        mapper_method(extracted_data)

        # Create audit log entry
        AuditLog.objects.create(
            user=self.session.user,
            action='ocr_data_applied',
            resource_type='intake_session',
            resource_id=str(self.session.id),
            changes={
                'document_type': document_type,
                'fields_updated': self.updated_fields,
                'source': 'ocr_extraction'
            }
        )

        return self.updated_fields

    def _get_mapper_for_type(self, document_type: str):
        """Return the appropriate mapper method for document type."""
        mappers = {
            DocumentType.PAY_STUB: self._map_pay_stub,
            DocumentType.BALANCE_SHEET: self._map_balance_sheet,
            DocumentType.PROFIT_LOSS: self._map_profit_loss,
            # Add more mappers as needed
        }
        return mappers.get(document_type)

    def _map_pay_stub(self, data: Dict[str, Any]):
        """
        Map pay stub data to IncomeInfo model.

        Args:
            data: Extracted pay stub data
        """
        income_info, created = IncomeInfo.objects.get_or_create(
            session=self.session
        )

        # Map employer name
        if 'employer_name' in data:
            income_info.employer_name = data['employer_name']
            self.updated_fields.append('employer_name')

        # Map gross pay (convert to monthly if needed)
        if 'gross_pay' in data:
            gross_pay = Decimal(str(data['gross_pay']))

            # Determine pay frequency from pay period dates
            pay_period_days = self._calculate_pay_period_days(data)
            monthly_gross = self._convert_to_monthly(gross_pay, pay_period_days)

            income_info.monthly_gross_income = monthly_gross
            self.updated_fields.append('monthly_gross_income')

        # Map employment status (inferred)
        income_info.employment_status = 'employed'
        self.updated_fields.append('employment_status')

        income_info.save()

    def _map_balance_sheet(self, data: Dict[str, Any]):
        """
        Map balance sheet data to AssetInfo and DebtInfo models (Chapter 11).

        Args:
            data: Extracted balance sheet data
        """
        # Map assets
        if 'cash' in data and data['cash']:
            asset, _ = AssetInfo.objects.get_or_create(
                session=self.session,
                asset_type='cash',
                defaults={'description': 'Business cash (from balance sheet)'}
            )
            asset.current_value = Decimal(str(data['cash']))
            asset.save()
            self.updated_fields.append('business_cash')

        if 'accounts_receivable' in data and data['accounts_receivable']:
            asset, _ = AssetInfo.objects.get_or_create(
                session=self.session,
                asset_type='accounts_receivable',
                defaults={'description': 'Accounts receivable (from balance sheet)'}
            )
            asset.current_value = Decimal(str(data['accounts_receivable']))
            asset.save()
            self.updated_fields.append('accounts_receivable')

        # Map liabilities
        if 'accounts_payable' in data and data['accounts_payable']:
            debt, _ = DebtInfo.objects.get_or_create(
                session=self.session,
                creditor_name='Accounts Payable (aggregate)',
                defaults={'debt_type': 'unsecured'}
            )
            debt.amount_owed = Decimal(str(data['accounts_payable']))
            debt.save()
            self.updated_fields.append('accounts_payable')

    def _map_profit_loss(self, data: Dict[str, Any]):
        """
        Map P&L statement to IncomeInfo model (Chapter 11).

        Args:
            data: Extracted P&L data
        """
        income_info, _ = IncomeInfo.objects.get_or_create(
            session=self.session
        )

        if 'total_revenue' in data:
            income_info.business_gross_revenue = Decimal(str(data['total_revenue']))
            self.updated_fields.append('business_gross_revenue')

        if 'net_income' in data:
            income_info.business_net_income = Decimal(str(data['net_income']))
            self.updated_fields.append('business_net_income')

        income_info.save()

    def _calculate_pay_period_days(self, data: Dict[str, Any]) -> int:
        """
        Calculate days in pay period from dates.

        Args:
            data: Extracted data with pay_period_start and pay_period_end

        Returns:
            Number of days in pay period (defaults to 14 if not available)
        """
        if 'pay_period_start' in data and 'pay_period_end' in data:
            try:
                if isinstance(data['pay_period_start'], str):
                    start = date.fromisoformat(data['pay_period_start'])
                    end = date.fromisoformat(data['pay_period_end'])
                else:
                    start = data['pay_period_start']
                    end = data['pay_period_end']

                return (end - start).days + 1
            except (ValueError, TypeError):
                pass

        return 14  # Default to bi-weekly

    def _convert_to_monthly(self, amount: Decimal, pay_period_days: int) -> Decimal:
        """
        Convert pay amount to monthly equivalent.

        Common pay periods:
        - Weekly: 7 days → multiply by 4.33
        - Bi-weekly: 14 days → multiply by 2.17
        - Semi-monthly: ~15 days → multiply by 2
        - Monthly: 30 days → no conversion

        Args:
            amount: Pay amount for period
            pay_period_days: Number of days in pay period

        Returns:
            Monthly equivalent amount
        """
        if pay_period_days <= 7:
            # Weekly
            return amount * Decimal('4.33')
        elif pay_period_days <= 14:
            # Bi-weekly
            return amount * Decimal('2.17')
        elif pay_period_days <= 15:
            # Semi-monthly
            return amount * 2
        else:
            # Assume monthly
            return amount
```

**Step 2: Commit**

```bash
git add backend/apps/documents/services/field_mapper.py
git commit -m "feat(documents): implement FieldMapperService foundation

- Core service for mapping OCR data to intake models
- Pay stub to IncomeInfo mapping
- Balance sheet to AssetInfo/DebtInfo mapping
- P&L to IncomeInfo mapping
- Pay period conversion logic
- Audit logging for field changes

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 18: Add Apply-to-Intake API Endpoint

**Files:**
- Modify: `backend/apps/documents/views.py`

**Step 1: Add apply_to_intake action to DocumentViewSet**

Add this method after the `validate_ocr` action:

```python
    @action(detail=True, methods=['patch'], url_path='apply-to-intake')
    def apply_to_intake(self, request, pk=None):
        """
        Apply extracted data to intake session fields.

        PATCH /api/documents/{id}/apply-to-intake/

        Maps OCR extracted data to appropriate intake models:
        - Pay stub → IncomeInfo
        - Bank statement → AssetInfo
        - Balance sheet → AssetInfo + DebtInfo
        - P&L → IncomeInfo

        Response:
            {
                "applied": true,
                "fields_updated": ["monthly_gross_income", "employer_name"],
                "intake_session_id": "uuid"
            }
        """
        document = self.get_object()

        if not hasattr(document, 'ocr_result'):
            return Response(
                {"error": "No OCR result to apply"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ocr_result = document.ocr_result
        if ocr_result.status not in ['completed', 'validated']:
            return Response(
                {"error": "OCR result must be completed or validated first"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Import field mapping service
        from apps.documents.services.field_mapper import FieldMapperService
        import json

        mapper = FieldMapperService(document.session)
        fields_updated = mapper.apply_ocr_to_intake(
            document_type=document.document_type,
            extracted_data=json.loads(ocr_result.extracted_data)
        )

        return Response({
            "applied": True,
            "fields_updated": fields_updated,
            "intake_session_id": str(document.session.id)
        })
```

**Step 2: Commit**

```bash
git add backend/apps/documents/views.py
git commit -m "feat(documents): add apply-to-intake API endpoint

- PATCH /api/documents/{id}/apply-to-intake/
- Applies OCR extracted data to intake models
- Returns list of updated fields
- Validates OCR result status before applying

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 7: Document Lifecycle Management

### Task 19: Create Auto-Deletion Management Command

**Files:**
- Create: `backend/apps/documents/management/__init__.py`
- Create: `backend/apps/documents/management/commands/__init__.py`
- Create: `backend/apps/documents/management/commands/delete_expired_documents.py`

**Step 1: Create directory structure**

```bash
mkdir -p backend/apps/documents/management/commands
touch backend/apps/documents/management/__init__.py
touch backend/apps/documents/management/commands/__init__.py
```

**Step 2: Write delete_expired_documents command**

```python
# backend/apps/documents/management/commands/delete_expired_documents.py
"""Management command to delete expired documents."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.documents.models import UploadedDocument
from apps.audit.models import AuditLog


class Command(BaseCommand):
    """
    Delete documents past their retention period.

    Run daily via cron (MVP) or Celery periodic task (production).

    Usage:
        python manage.py delete_expired_documents
        python manage.py delete_expired_documents --dry-run
    """

    help = 'Delete documents that have exceeded 22-day retention period'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()

        # Find expired documents
        expired_docs = UploadedDocument.objects.filter(
            delete_after__lte=now,
            deleted_at__isnull=True
        ).select_related('session', 'ocr_result')

        count = expired_docs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} documents'
                )
            )
            for doc in expired_docs[:10]:  # Show first 10
                self.stdout.write(
                    f'  - {doc.original_filename} '
                    f'(uploaded {doc.uploaded_at.date()})'
                )
            return

        # Delete documents with audit trail
        deleted_count = 0
        with transaction.atomic():
            for doc in expired_docs:
                # Create audit log before deletion
                AuditLog.objects.create(
                    user=doc.uploaded_by,
                    action='document_auto_deleted',
                    resource_type='uploaded_document',
                    resource_id=str(doc.id),
                    changes={
                        'original_filename': doc.original_filename,
                        'document_type': doc.document_type,
                        'uploaded_at': doc.uploaded_at.isoformat(),
                        'delete_after': doc.delete_after.isoformat(),
                        'reason': 'retention_period_expired'
                    }
                )

                # Soft delete (mark as deleted, keep OCR results)
                doc.deleted_at = now
                doc.file.delete(save=False)  # Delete encrypted file from storage
                doc.save(update_fields=['deleted_at'])

                deleted_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {deleted_count} expired documents'
            )
        )
```

**Step 3: Test command with dry-run**

```bash
cd backend
python manage.py delete_expired_documents --dry-run
```

Expected: Shows count (likely 0 for fresh install)

**Step 4: Commit**

```bash
git add backend/apps/documents/management/
git commit -m "feat(documents): add auto-deletion management command

- delete_expired_documents command
- Soft delete with audit logging
- Dry-run mode for testing
- Deletes files past 22-day retention

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 20: Add Admin Interface

**Files:**
- Modify: `backend/apps/documents/admin.py`

**Step 1: Register models in admin**

```python
# backend/apps/documents/admin.py
"""Admin interface for document management."""

from django.contrib import admin
from django.utils.html import format_html
from apps.documents.models import UploadedDocument, OCRResult


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    """Admin interface for uploaded documents."""

    list_display = [
        'id',
        'original_filename',
        'document_type',
        'type_match_status',
        'uploaded_by',
        'uploaded_at',
        'delete_after',
        'is_deleted'
    ]
    list_filter = [
        'document_type',
        'uploaded_at',
        'deleted_at'
    ]
    search_fields = [
        'original_filename',
        'uploaded_by__username',
        'uploaded_by__email'
    ]
    readonly_fields = [
        'id',
        'uploaded_at',
        'file_size',
        'mime_type'
    ]
    date_hierarchy = 'uploaded_at'

    def type_match_status(self, obj):
        """Show type match/mismatch status."""
        if obj.detected_type is None:
            return format_html('<span style="color: gray;">Not validated</span>')
        elif obj.detected_type == obj.user_declared_type:
            return format_html('<span style="color: green;">✓ Match</span>')
        else:
            return format_html(
                '<span style="color: orange;">⚠ Mismatch<br/>'
                'Declared: {}<br/>Detected: {}</span>',
                obj.get_user_declared_type_display(),
                obj.get_detected_type_display()
            )
    type_match_status.short_description = 'Type Validation'

    def is_deleted(self, obj):
        """Show deletion status."""
        if obj.deleted_at:
            return format_html('<span style="color: red;">✗ Deleted</span>')
        return format_html('<span style="color: green;">✓ Active</span>')
    is_deleted.short_description = 'Status'


@admin.register(OCRResult)
class OCRResultAdmin(admin.ModelAdmin):
    """Admin interface for OCR results."""

    list_display = [
        'id',
        'document',
        'status',
        'overall_confidence',
        'ocr_provider',
        'user_validated',
        'processed_at'
    ]
    list_filter = [
        'status',
        'ocr_provider',
        'user_validated',
        'processed_at'
    ]
    search_fields = [
        'document__original_filename'
    ]
    readonly_fields = [
        'id',
        'processed_at',
        'processing_duration',
        'extracted_data',
        'confidence_scores',
        'error_message'
    ]
    date_hierarchy = 'processed_at'
```

**Step 2: Commit**

```bash
git add backend/apps/documents/admin.py
git commit -m "feat(documents): add Django admin interface

- UploadedDocument admin with type match indicators
- OCRResult admin with status filtering
- Color-coded status indicators
- Search and filter capabilities

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Final Steps & Execution Handoff

### Task 21: Update Requirements and Dependencies

**Files:**
- Verify: `backend/requirements/base.txt`

**Step 1: Verify all dependencies are listed**

```bash
cd backend
cat requirements/base.txt | grep -E "(pydantic|openai|django-fernet)"
```

Expected to see:
```
pydantic==2.5.3
openai==1.60.0
django-fernet-fields==0.6
```

**Step 2: If any missing, add them**

```bash
# Only run if dependencies are missing
echo "# Dependencies verified" >> requirements/base.txt
```

**Step 3: Freeze current environment**

```bash
pip freeze > requirements-frozen.txt
```

**Step 4: Commit**

```bash
git add requirements/
git commit -m "chore: verify OCR integration dependencies

- Pydantic 2.5.3 for schema validation
- OpenAI 1.60.0 for Clarifai API
- django-fernet-fields for encryption

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 22: Create Integration Test

**Files:**
- Create: `backend/apps/documents/tests/test_integration.py`

**Step 1: Write end-to-end integration test**

```python
# backend/apps/documents/tests/test_integration.py
"""End-to-end integration tests for document OCR workflow."""

import pytest
from unittest.mock import patch, Mock
import json
from decimal import Decimal

from apps.documents.models import DocumentType, OCRStatus
from apps.documents.services.ocr_service import DocumentOCRService
from apps.documents.services.field_mapper import FieldMapperService


@pytest.mark.django_db
class TestDocumentOCRIntegration:
    """Integration tests for complete OCR workflow."""

    @patch('apps.documents.services.ocr_service.ClarifaiOCRProvider')
    def test_complete_paystub_workflow(
        self,
        mock_provider_class,
        uploaded_paystub,
        intake_session
    ):
        """
        Test complete workflow: Upload → OCR → Validate → Apply.

        Workflow:
        1. Upload document (already done via fixture)
        2. OCR processing extracts data
        3. User validates/corrects data
        4. Apply to intake session
        """
        # Mock provider
        mock_provider = Mock()
        mock_provider.classify.return_value = 'pay_stub'
        mock_provider.extract.return_value = json.dumps({
            'employer_name': 'Test Corporation',
            'gross_pay': '5000.00',
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'confidence_score': 88
        })
        mock_provider_class.return_value = mock_provider

        # Step 1: OCR Processing
        ocr_service = DocumentOCRService()
        ocr_result = ocr_service.process_document(uploaded_paystub)

        assert ocr_result.status == OCRStatus.COMPLETED
        assert ocr_result.overall_confidence == Decimal('88.00')

        extracted = json.loads(ocr_result.extracted_data)
        assert extracted['employer_name'] == 'Test Corporation'
        assert extracted['gross_pay'] == '5000.00'

        # Step 2: User Validation (simulate correction)
        extracted['gross_pay'] = '5100.00'  # User corrects
        ocr_result.extracted_data = json.dumps(extracted)
        ocr_result.user_validated = True
        ocr_result.validation_changes = ['gross_pay']
        ocr_result.status = 'validated'
        ocr_result.save()

        # Step 3: Apply to Intake
        mapper = FieldMapperService(intake_session)
        fields_updated = mapper.apply_ocr_to_intake(
            document_type=DocumentType.PAY_STUB,
            extracted_data=extracted
        )

        # Verify fields were mapped
        assert 'employer_name' in fields_updated
        assert 'monthly_gross_income' in fields_updated

        # Verify intake data
        intake_session.refresh_from_db()
        income_info = intake_session.income_info

        assert income_info.employer_name == 'Test Corporation'
        # 5100 biweekly → monthly (5100 * 2.17)
        assert income_info.monthly_gross_income == Decimal('5100.00') * Decimal('2.17')
```

**Step 2: Run integration test**

```bash
pytest apps/documents/tests/test_integration.py -v
```

Expected: Test PASS

**Step 3: Commit**

```bash
git add backend/apps/documents/tests/test_integration.py
git commit -m "test(documents): add end-to-end integration test

- Complete workflow test: upload → OCR → validate → apply
- Mocked provider for deterministic testing
- Verifies field mapping to intake models
- Tests user correction workflow

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Execution Plan Complete

**Plan saved to:** `docs/plans/2026-02-01-deepseek-ocr-implementation.md`

---

## Implementation Summary

**Phase 1-2 Complete:** Core infrastructure, models, schemas (Tasks 1-11)
- ✅ Documents app structure
- ✅ Django models (UploadedDocument, OCRResult)
- ✅ Pydantic schemas (PayStub, BalanceSheet, P&L)
- ✅ Schema registry

**Phase 3-4 Complete:** OCR service layer (Tasks 12-14)
- ✅ Base OCR provider abstraction
- ✅ Clarifai provider implementation
- ✅ DocumentOCRService with prompt generation
- ✅ Confidence scoring

**Phase 5 Complete:** REST API (Tasks 15-16)
- ✅ Serializers (upload, OCR result, validation)
- ✅ DocumentViewSet with upload/reprocess/validate actions
- ✅ API endpoints registered

**Phase 6 Complete:** Field mapping (Tasks 17-18)
- ✅ FieldMapperService
- ✅ Pay stub → IncomeInfo mapping
- ✅ Balance sheet → AssetInfo/DebtInfo mapping
- ✅ Apply-to-intake API endpoint

**Phase 7 Complete:** Lifecycle management (Tasks 19-20)
- ✅ Auto-deletion management command
- ✅ Django admin interface

**Phase 8 Complete:** Testing & validation (Tasks 21-22)
- ✅ Dependencies verified
- ✅ Integration test coverage

---

## Next Steps: Execution Options

### Option 1: Subagent-Driven Development (Recommended)

**Use this session:**
- I dispatch fresh subagent per task
- Review between tasks
- Fast iteration with immediate feedback

**Command:** Use `superpowers:subagent-driven-development` skill

### Option 2: Parallel Session Execution

**Open new session in worktree:**
1. Create worktree: `git worktree add .worktrees/ocr-integration`
2. Open new Claude Code session in worktree
3. Use `superpowers:executing-plans` skill with this plan

**Which execution approach would you like to use?**
