# DeepSeek-OCR Integration Design
**Date:** 2026-02-01
**Author:** Claude Code
**Status:** Approved for Implementation

## Executive Summary

This document outlines the complete architecture for integrating DeepSeek-OCR 2 into the DigniFi bankruptcy platform. The integration enables automated extraction of structured data from user-uploaded documents (pay stubs, bank statements, tax returns, business financial statements, etc.) to streamline the intake process while maintaining strict privacy controls and UPL compliance.

**Key Features:**
- Support for 6 document types (Chapter 7) + 8 document types (Chapter 11 Subchapter V)
- Hybrid deployment: Clarifai API (MVP) → self-hosted vLLM (production)
- Confidence-based auto-population with user validation
- 22-day automatic document deletion
- Field mapping to existing intake models

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Data Models & Schema](#2-data-models--schema)
3. [Service Layer Architecture](#3-service-layer-architecture)
4. [REST API Endpoints](#4-rest-api-endpoints)
5. [Field Mapping Service](#5-field-mapping-service)
6. [Document Lifecycle Management](#6-document-lifecycle-management)
7. [Frontend Integration](#7-frontend-integration)
8. [Configuration & Deployment](#8-configuration--deployment)
9. [Implementation Phases](#9-implementation-phases)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  - Document upload UI with type selector                    │
│  - Progress indicators / real-time updates                  │
│  - Confidence-based field highlighting                      │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTPS
┌────────────────▼────────────────────────────────────────────┐
│              Django REST API Layer                          │
│  - Document upload endpoint                                 │
│  - OCR job status/results endpoints                         │
│  - Intake session integration                               │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│         DocumentOCRService (Service Layer)                  │
│  - Type-specific schema definitions                         │
│  - Confidence scoring & validation                          │
│  - Field mapping to intake models                           │
│  - Deployment-agnostic executor pattern                     │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐   ┌─────────────────┐
│ Clarifai API │   │  vLLM (Future)  │
│   (MVP/Dev)  │   │  Self-hosted    │
└──────────────┘   └─────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐   ┌─────────────────┐
│  PostgreSQL  │   │  S3-Compatible  │
│ OCR Results  │   │  Encrypted Docs │
│  (22 days)   │   │   (22 days)     │
└──────────────┘   └─────────────────┘
```

### 1.2 Core Components

**Django App: `documents`** (backend/apps/documents/)
- **Models:** `UploadedDocument`, `OCRResult`, `ExtractionField`
- **Views:** `DocumentUploadViewSet`, `OCRJobViewSet`
- **Services:** `DocumentOCRService`, `DocumentValidationService`, `FieldMapperService`
- **Providers:** `ClarifaiOCRProvider`, `VLLMOCRProvider`

**Storage Layer:**
- Encrypted document storage (Fernet encryption, matching existing PII strategy)
- Auto-deletion jobs (Celery periodic tasks for production, cron for MVP)
- Audit logging (who uploaded, when extracted, field changes)

### 1.3 Document Type Taxonomy

**Chapter 7 (Individual) Documents:**
- Pay Stub
- Bank Statement
- Credit Counseling Certificate
- Credit Report
- Personal Tax Return (1040)
- Special Circumstances Supporting Documents

**Chapter 11 Subchapter V (Business) Documents:**
- Balance Sheet
- Profit & Loss Statement (P&L)
- Cash Flow Statement
- Business Tax Return (1120/1065)
- Accounts Receivable Aging
- Accounts Payable Aging
- Operating Agreement/Bylaws
- Corporate Resolution

**Dual-Use Documents (Both Chapters):**
- Lease Agreement
- Loan Agreement
- Court Judgment
- Lien Notice

---

## 2. Data Models & Schema

### 2.1 Django Models

```python
# backend/apps/documents/models.py

class DocumentType(models.TextChoices):
    """Supported document types for OCR processing."""
    # Chapter 7 (Individual)
    PAY_STUB = 'pay_stub', 'Pay Stub'
    BANK_STATEMENT = 'bank_statement', 'Bank Statement'
    CREDIT_COUNSELING_CERT = 'credit_cert', 'Credit Counseling Certificate'
    CREDIT_REPORT = 'credit_report', 'Credit Report'
    TAX_RETURN_PERSONAL = 'tax_return_personal', 'Personal Tax Return (1040)'
    SPECIAL_CIRCUMSTANCES = 'special_circumstances', 'Supporting Document'

    # Chapter 11 (Business)
    BALANCE_SHEET = 'balance_sheet', 'Balance Sheet'
    PROFIT_LOSS = 'profit_loss', 'Profit & Loss Statement'
    CASH_FLOW = 'cash_flow', 'Cash Flow Statement'
    TAX_RETURN_BUSINESS = 'tax_return_business', 'Business Tax Return'
    ACCOUNTS_RECEIVABLE = 'accounts_receivable', 'Accounts Receivable Aging'
    ACCOUNTS_PAYABLE = 'accounts_payable', 'Accounts Payable Aging'
    OPERATING_AGREEMENT = 'operating_agreement', 'Operating Agreement'
    CORPORATE_RESOLUTION = 'corporate_resolution', 'Corporate Resolution'

    # Dual-use
    LEASE_AGREEMENT = 'lease_agreement', 'Lease Agreement'
    LOAN_AGREEMENT = 'loan_agreement', 'Loan Agreement'
    JUDGMENT = 'judgment', 'Court Judgment'
    LIEN_NOTICE = 'lien_notice', 'Lien Notice'

class OCRStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    VALIDATED = 'validated', 'Validated by User'

class UploadedDocument(models.Model):
    """Encrypted storage for user-uploaded documents."""

    session = models.ForeignKey(IntakeSession, on_delete=models.CASCADE, related_name='uploaded_documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    document_type = models.CharField(max_length=50, choices=DocumentType.choices)
    user_declared_type = models.CharField(max_length=50, choices=DocumentType.choices)
    detected_type = models.CharField(max_length=50, choices=DocumentType.choices, blank=True, null=True)

    file = EncryptedFileField(upload_to='documents/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField()
    mime_type = models.CharField(max_length=100)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    delete_after = models.DateTimeField()
    deleted_at = models.DateTimeField(null=True, blank=True)

class OCRResult(models.Model):
    """Extracted data from OCR processing."""

    document = models.OneToOneField(UploadedDocument, on_delete=models.CASCADE, related_name='ocr_result')

    status = models.CharField(max_length=20, choices=OCRStatus.choices, default=OCRStatus.PENDING)
    ocr_provider = models.CharField(max_length=50, default='clarifai')

    extracted_data = EncryptedTextField()
    confidence_scores = models.JSONField(default=dict)
    overall_confidence = models.DecimalField(max_digits=5, decimal_places=2)

    user_validated = models.BooleanField(default=False)
    validation_changes = models.JSONField(default=list)

    processed_at = models.DateTimeField(auto_now_add=True)
    processing_duration = models.FloatField(null=True)
    error_message = EncryptedTextField(blank=True, null=True)
```

### 2.2 Pydantic Extraction Schemas

**Priority 1: Pay Stub Extraction**
```python
class PayStubExtraction(BaseModel):
    employer_name: str = Field(min_length=1)
    gross_pay: Decimal = Field(gt=0, decimal_places=2)
    pay_period_start: date
    pay_period_end: date
    ytd_gross: Optional[Decimal] = Field(default=None, ge=0)
    net_pay: Optional[Decimal] = Field(default=None, ge=0)
    deductions_total: Optional[Decimal] = Field(default=None, ge=0)
    confidence_score: int = Field(ge=0, le=100)
```

**Priority 2: Balance Sheet Extraction (Chapter 11)**
```python
class BalanceSheetExtraction(BaseModel):
    as_of_date: date
    cash: Optional[Decimal] = Field(ge=0, default=None)
    accounts_receivable: Optional[Decimal] = Field(ge=0, default=None)
    inventory: Optional[Decimal] = Field(ge=0, default=None)
    equipment: Optional[Decimal] = Field(ge=0, default=None)
    total_assets: Decimal = Field(gt=0)
    accounts_payable: Optional[Decimal] = Field(ge=0, default=None)
    loans_payable: Optional[Decimal] = Field(ge=0, default=None)
    total_liabilities: Decimal = Field(ge=0)
    owners_equity: Decimal
    confidence_score: int = Field(ge=0, le=100)

    @validator('owners_equity')
    def validate_accounting_equation(cls, v, values):
        """Assets = Liabilities + Equity"""
        if 'total_assets' in values and 'total_liabilities' in values:
            calculated_equity = values['total_assets'] - values['total_liabilities']
            if abs(calculated_equity - v) / values['total_assets'] > 0.01:
                raise ValueError('Balance sheet equation error')
        return v
```

*Additional schemas defined for: Bank Statements, Credit Counseling Certificates, Credit Reports, P&L Statements, Cash Flow Statements, Tax Returns*

---

## 3. Service Layer Architecture

### 3.1 DocumentOCRService

**Responsibilities:**
- Coordinate OCR processing workflow
- Manage provider abstraction (Clarifai vs vLLM)
- Type validation and mismatch detection
- Confidence scoring
- Error handling and retries

**Key Methods:**
```python
class DocumentOCRService:
    def __init__(self):
        # Initialize configured provider (clarifai or vllm)

    def process_document(self, document: UploadedDocument, validate_type: bool = True) -> OCRResult:
        # 1. Type validation (if enabled)
        # 2. Extract structured data
        # 3. Validate with Pydantic schema
        # 4. Calculate confidence scores
        # 5. Save results

    def _detect_document_type(self, document: UploadedDocument) -> str:
        # Quick classification for type validation

    def _extract_data(self, document: UploadedDocument, schema_class) -> Dict[str, Any]:
        # Type-specific extraction using grounding prompts

    def _build_extraction_prompt(self, document_type: str, schema_class) -> str:
        # Generate DeepSeek-OCR grounding prompt from Pydantic schema
```

### 3.2 OCR Provider Abstraction

**Base Interface:**
```python
class BaseOCRProvider(ABC):
    @abstractmethod
    def classify(self, image_data: bytes, prompt: str) -> str:
        """Classify document type."""

    @abstractmethod
    def extract(self, image_data: bytes, prompt: str) -> str:
        """Extract structured data. Returns JSON string."""
```

**Clarifai Provider (MVP):**
- OpenAI-compatible endpoint
- Uses Personal Access Token (PAT)
- Base64 image encoding
- Temperature=0.0 for deterministic extraction

**vLLM Provider (Production):**
- Self-hosted DeepSeek-OCR 2 model
- HTTP requests to local GPU server
- Batched processing support
- No third-party data sharing

---

## 4. REST API Endpoints

### 4.1 Document Management

```
POST   /api/documents/upload/              # Upload & process document
GET    /api/documents/                     # List user's documents
GET    /api/documents/{id}/                # Get document details
DELETE /api/documents/{id}/                # Delete document
POST   /api/documents/{id}/reprocess/      # Retry OCR if failed
GET    /api/documents/{id}/ocr-result/     # Get OCR extraction
POST   /api/documents/{id}/validate/       # User validates/corrects OCR
PATCH  /api/documents/{id}/apply-to-intake/ # Apply to intake session
```

### 4.2 Upload Workflow

**Request (POST /api/documents/upload/):**
```json
{
  "session_id": "uuid",
  "document_type": "pay_stub",
  "file": "<multipart file upload>"
}
```

**Response (Success):**
```json
{
  "id": "uuid",
  "document_type": "pay_stub",
  "user_declared_type": "pay_stub",
  "detected_type": "pay_stub",
  "type_mismatch": false,
  "original_filename": "paystub_jan2026.pdf",
  "file_size": 245678,
  "uploaded_at": "2026-02-01T10:30:00Z",
  "delete_after": "2026-02-23T10:30:00Z",
  "ocr_result": {
    "status": "completed",
    "overall_confidence": 92.5,
    "extracted_data": {
      "employer_name": "Acme Corp",
      "gross_pay": "3240.00",
      "pay_period_start": "2026-01-01",
      "pay_period_end": "2026-01-15"
    },
    "confidence_scores": {
      "employer_name": 95,
      "gross_pay": 88,
      "pay_period_start": 92,
      "pay_period_end": 94
    }
  }
}
```

**Response (Type Mismatch):**
```json
{
  "id": "uuid",
  "document_type": "bank_statement",
  "user_declared_type": "pay_stub",
  "detected_type": "bank_statement",
  "type_mismatch": true,
  "original_filename": "statement.pdf",
  "ocr_result": {
    "status": "completed",
    "...": "..."
  }
}
```

### 4.3 Validation Workflow

**Request (POST /api/documents/{id}/validate/):**
```json
{
  "validated": true,
  "corrections": {
    "gross_pay": "3240.00",
    "pay_period_end": "2026-01-31"
  }
}
```

**Response:**
```json
{
  "status": "validated",
  "validation_changes": ["gross_pay", "pay_period_end"],
  "extracted_data": {
    "employer_name": "Acme Corp",
    "gross_pay": "3240.00",
    "pay_period_start": "2026-01-01",
    "pay_period_end": "2026-01-31"
  }
}
```

---

## 5. Field Mapping Service

### 5.1 FieldMapperService

Maps OCR extracted data to existing intake models (`IncomeInfo`, `DebtInfo`, `AssetInfo`, `ExpenseInfo`).

**Key Mappings:**

**Pay Stub → IncomeInfo:**
- `employer_name` → `IncomeInfo.employer_name`
- `gross_pay` → `IncomeInfo.monthly_gross_income` (converted based on pay frequency)
- `ytd_gross` → (validation/verification)

**Bank Statement → AssetInfo:**
- `ending_balance` → `AssetInfo.current_value` (type: bank_account)
- `bank_name` + `account_number_last4` → `AssetInfo.description`

**Balance Sheet → AssetInfo + DebtInfo (Chapter 11):**
- `cash` → `AssetInfo` (type: cash)
- `accounts_receivable` → `AssetInfo` (type: accounts_receivable)
- `equipment` → `AssetInfo` (type: business_equipment)
- `accounts_payable` → `DebtInfo` (creditor: "Accounts Payable (aggregate)")
- `loans_payable` → `DebtInfo` (creditor: "Business loans (aggregate)")

**Profit & Loss → IncomeInfo + ExpenseInfo (Chapter 11):**
- `total_revenue` → `IncomeInfo.business_gross_revenue`
- `net_income` → `IncomeInfo.business_net_income`
- `expense_breakdown` → Multiple `ExpenseInfo` records

### 5.2 Pay Period Conversion Logic

```python
def _convert_to_monthly(amount: Decimal, pay_period_days: int) -> Decimal:
    """
    Convert pay amount to monthly equivalent.

    - Weekly (7 days): multiply by 4.33
    - Bi-weekly (14 days): multiply by 2.17
    - Semi-monthly (15 days): multiply by 2
    - Monthly (30 days): no conversion
    """
```

### 5.3 Audit Logging

All field mapping operations create audit log entries:
```python
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
```

---

## 6. Document Lifecycle Management

### 6.1 Retention Policy

**Documents are automatically deleted after:**
- 22 days from upload date, OR
- When bankruptcy form is filed (whichever comes first)

**User notifications:**
- 7 days before deletion: Email reminder to download documents
- Deletion notice in user dashboard

### 6.2 Auto-Deletion Mechanisms

**Management Commands:**

```bash
# Delete expired documents (run daily at 2 AM)
python manage.py delete_expired_documents

# Delete documents for filed forms (run hourly)
python manage.py delete_on_form_filed

# Notify users 7 days before deletion (run daily at 9 AM)
python manage.py notify_pending_deletion
```

**Celery Periodic Tasks (Production):**
```python
app.conf.beat_schedule = {
    'delete-expired-documents-daily': {
        'task': 'apps.documents.tasks.delete_expired_documents',
        'schedule': crontab(hour=2, minute=0),
    },
    'delete-filed-form-documents-hourly': {
        'task': 'apps.documents.tasks.delete_documents_for_filed_forms',
        'schedule': crontab(minute=0),
    },
}
```

**Cron Setup (MVP):**
```cron
0 2 * * * cd /path/to/dignifi && python manage.py delete_expired_documents
0 * * * * cd /path/to/dignifi && python manage.py delete_on_form_filed
0 9 * * * cd /path/to/dignifi && python manage.py notify_pending_deletion
```

### 6.3 Soft Delete Strategy

Documents are **soft deleted** (not hard deleted):
- `UploadedDocument.deleted_at` timestamp set
- Encrypted file removed from storage
- OCR results retained (encrypted JSON)
- Audit log entry created

This allows:
- Retention of extracted data for form generation
- Audit trail of what was deleted and when
- Compliance with data minimization principles

---

## 7. Frontend Integration

### 7.1 Document Upload Component

**Features:**
- Document type selector (filtered by chapter)
- Drag-and-drop file upload
- Document-specific tips ("Upload your most recent pay stub...")
- Progress indicator (upload → OCR processing)
- Type mismatch modal

**User Flow:**
1. User selects document type from dropdown
2. Uploads file (PDF, JPG, PNG)
3. Progress bar shows: "Uploading... → Processing with OCR..."
4. If type mismatch: Modal asks "Continue as [declared] or [detected]?"
5. OCR results displayed for review

### 7.2 OCR Results Review Component

**Confidence-Based Highlighting:**

```
✓ Employer Name: "Acme Corp"        [High confidence - green]
⚠ Gross Pay: "$3,240.00"            [Medium confidence - yellow, verify carefully]
✗ Pay Period End: [Empty]           [Low confidence - red, enter manually]
```

**Confidence Thresholds:**
- **High (≥90%):** Green checkmark, auto-filled
- **Medium (70-90%):** Yellow warning, "Please verify carefully"
- **Low (<70%):** Red X, leave empty with message "We couldn't read this clearly"

**User Actions:**
- Edit any field (click "Edit" button)
- Corrections tracked in `validation_changes` array
- "Confirm All Fields" button marks as validated
- "Apply to My Intake Form" button triggers field mapping

### 7.3 Type Mismatch Modal

```
⚠️ Document Type Check

You selected Pay Stub, but this looks like a Bank Statement.

No problem! This happens sometimes. Which type should we use?

[Keep as Pay Stub]  [Change to Bank Statement]
```

---

## 8. Configuration & Deployment

### 8.1 Environment Variables

```bash
# OCR Provider
OCR_PROVIDER=clarifai  # 'clarifai' or 'vllm'

# Clarifai API (MVP/Development)
CLARIFAI_PAT=your-personal-access-token

# vLLM Self-Hosted (Production)
VLLM_BASE_URL=http://gpu-server:8000
VLLM_API_KEY=optional-api-key

# Document Storage
DOCUMENT_STORAGE_BACKEND=filesystem  # 's3' for production
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=dignifi-documents

# Feature Flags
ENABLE_CHAPTER_11=False  # Set True for personal use
ENABLE_CHAPTER_13=False

# Celery (Production)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 8.2 Docker Compose Updates

**Add Redis for Celery:**
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

**Add Celery Worker (production profile):**
```yaml
celery_worker:
  build: ./backend
  command: celery -A config worker -l info
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
  profiles:
    - production
```

### 8.3 vLLM Self-Hosted Deployment (Future)

```yaml
# docker-compose.vllm.yml
vllm_server:
  image: vllm/vllm-openai:latest
  runtime: nvidia
  ports:
    - "8000:8000"
  command: >
    --model deepseek-ai/DeepSeek-OCR-2
    --served-model-name deepseek-ocr
    --host 0.0.0.0
    --port 8000
    --max-model-len 4096
    --trust-remote-code
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### 8.4 Migration Path: Clarifai → vLLM

**Testing Provider:**
```bash
python manage.py switch_ocr_provider --test vllm
```

**Switching Provider:**
```bash
python manage.py switch_ocr_provider --switch vllm
# Restart Django to apply changes
```

---

## 9. Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)

**Backend:**
- [ ] Create `documents` Django app
- [ ] Implement data models (UploadedDocument, OCRResult)
- [ ] Create database migrations
- [ ] Implement EncryptedFileField storage
- [ ] Set up document retention (delete_after calculation)

**Testing:**
- [ ] Model creation tests
- [ ] Encryption/decryption tests
- [ ] Soft delete tests

### Phase 2: OCR Service Layer (Week 2-3)

**Backend:**
- [ ] Implement Pydantic schemas (PayStub, BankStatement, BalanceSheet, P&L)
- [ ] Create BaseOCRProvider abstract class
- [ ] Implement ClarifaiOCRProvider
- [ ] Implement DocumentOCRService
- [ ] Build prompt generation from schemas
- [ ] Add confidence scoring logic

**Configuration:**
- [ ] Add OCR settings to base.py
- [ ] Create .env.example with CLARIFAI_PAT
- [ ] Update docker-compose.yml with environment variables

**Testing:**
- [ ] Provider connectivity tests
- [ ] Schema validation tests
- [ ] Prompt generation tests
- [ ] OCR extraction integration tests (with sample documents)

### Phase 3: API Endpoints (Week 3-4)

**Backend:**
- [ ] Implement DocumentUploadViewSet
- [ ] Create upload endpoint with multipart parsing
- [ ] Implement type validation and mismatch detection
- [ ] Create reprocess endpoint
- [ ] Create validate endpoint (user corrections)
- [ ] Implement serializers (UploadedDocument, OCRResult)

**Testing:**
- [ ] Upload workflow tests
- [ ] Type mismatch tests
- [ ] Validation workflow tests
- [ ] Permission/authorization tests (user can only access their documents)

### Phase 4: Field Mapping (Week 4)

**Backend:**
- [ ] Implement FieldMapperService
- [ ] Create mappers for all document types:
  - [ ] Pay stub → IncomeInfo
  - [ ] Bank statement → AssetInfo
  - [ ] Balance sheet → AssetInfo + DebtInfo
  - [ ] P&L → IncomeInfo + ExpenseInfo
  - [ ] Cash flow → ExpenseInfo
  - [ ] Tax returns → IncomeInfo
- [ ] Add pay period conversion logic
- [ ] Implement apply-to-intake endpoint
- [ ] Add audit logging for field mapping

**Testing:**
- [ ] Field mapping tests for each document type
- [ ] Pay period conversion tests
- [ ] Audit log verification tests

### Phase 5: Document Lifecycle (Week 5)

**Backend:**
- [ ] Implement delete_expired_documents management command
- [ ] Implement delete_on_form_filed management command
- [ ] Implement notify_pending_deletion management command
- [ ] Add soft delete logic to UploadedDocument model
- [ ] Create audit logs for deletions

**Infrastructure:**
- [ ] Set up cron jobs for MVP
- [ ] Create Celery tasks for production
- [ ] Add Celery beat schedule

**Testing:**
- [ ] Deletion logic tests
- [ ] Notification tests
- [ ] Audit trail verification

### Phase 6: Frontend Integration (Week 5-6)

**Frontend:**
- [ ] Create TypeScript types (DocumentType, OCRResult, etc.)
- [ ] Implement DocumentUpload component
- [ ] Create file upload with progress indicator
- [ ] Implement TypeMismatchModal
- [ ] Create OCRResultsReview component
- [ ] Build confidence-based field highlighting
- [ ] Implement field editing/correction UI
- [ ] Add "Apply to Intake Form" button

**API Integration:**
- [ ] Create API client functions (uploadDocument, validateOCR, applyToIntake)
- [ ] Add error handling and retry logic
- [ ] Implement loading states

**Testing:**
- [ ] Component unit tests
- [ ] Integration tests with mock API
- [ ] E2E tests with real document uploads

### Phase 7: Chapter 11 Support (Week 6)

**Backend:**
- [ ] Add Chapter 11 document types to models
- [ ] Create business-specific Pydantic schemas
- [ ] Implement business document field mappings
- [ ] Add chapter-based document type filtering

**Frontend:**
- [ ] Filter document types by chapter
- [ ] Add business document upload UI
- [ ] Create business-specific field display

**Configuration:**
- [ ] Add ENABLE_CHAPTER_11 feature flag
- [ ] Document Chapter 11 activation process

### Phase 8: Production Readiness (Week 7-8)

**Backend:**
- [ ] Implement VLLMOCRProvider (stub for future)
- [ ] Add provider switching management command
- [ ] Performance optimization (async processing path)
- [ ] Add comprehensive error handling
- [ ] Implement rate limiting

**Infrastructure:**
- [ ] Redis setup for Celery
- [ ] Celery worker configuration
- [ ] S3-compatible storage integration (optional)
- [ ] Monitoring and alerting setup

**Documentation:**
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Deployment guide
- [ ] User documentation for document upload

**Testing:**
- [ ] Load testing (concurrent uploads)
- [ ] Security testing (file upload vulnerabilities)
- [ ] Privacy compliance review
- [ ] UPL compliance review (extracted data never provides advice)

---

## Appendix A: Decision Log

**1. Hybrid Deployment Strategy**
- **Decision:** Start with Clarifai API, migrate to self-hosted vLLM
- **Rationale:** Fast development with managed API, privacy with self-hosting when GPU available
- **Trade-offs:** Initial per-request costs vs. long-term infrastructure investment

**2. Auto-Populate with User Review**
- **Decision:** Auto-fill form fields with confidence highlighting
- **Rationale:** Trauma-informed UX (reduce cognitive load), UPL-safe (user confirms all data)
- **Trade-offs:** Risk of users not reviewing vs. slower manual entry alternative

**3. Confidence-Based Fallback**
- **Decision:** Three-tier confidence (High/Medium/Low) with different UI treatment
- **Rationale:** Transparent about reliability, prevents errors from low-confidence extractions
- **Trade-offs:** More complex UI vs. simpler all-or-nothing approach

**4. 22-Day Retention with Auto-Delete**
- **Decision:** Documents deleted after 22 days or form filing
- **Rationale:** Privacy by design, data minimization, GDPR/state law compliance
- **Trade-offs:** User convenience (can't review originals later) vs. privacy protection

**5. User Declares Type Upfront + Smart Validation**
- **Decision:** User selects type, system validates and prompts if mismatch
- **Rationale:** Clarity (user knows what we expect), safety net (catch mistakes), educational
- **Trade-offs:** Extra click for user vs. silent auto-detection errors

**6. Chapter 11 Feature Flag**
- **Decision:** Build Chapter 11 support with feature flag (disabled by default)
- **Rationale:** Enables founder's personal filing, validates business support, keeps MVP focused
- **Trade-offs:** Additional complexity vs. limiting to Chapter 7 only

---

## Appendix B: Success Metrics

**Technical Metrics:**
- OCR success rate: >90%
- Average processing time: <10 seconds per document
- Field mapping accuracy: >95% (validated data matches manual entry)
- System uptime: 99.5%

**User Experience Metrics:**
- Document upload completion rate: >85%
- User correction rate per document: <20% of fields
- Time saved vs. manual entry: >60%
- User satisfaction with auto-population: >4/5 rating

**Privacy Metrics:**
- Document deletion compliance: 100% (all documents deleted on schedule)
- Encryption verification: 100% (all PII encrypted at rest)
- Audit log completeness: 100% (all uploads/extractions/deletions logged)

**Business Metrics:**
- Reduction in intake abandonment: >30%
- Increase in form completion speed: >40%
- Support ticket reduction for data entry errors: >50%

---

## Appendix C: Risk Mitigation

**Risk 1: OCR Extraction Errors**
- **Mitigation:** Confidence scoring, user validation required, audit trails
- **Fallback:** Manual entry always available, reprocess option if OCR fails

**Risk 2: Privacy Breach (Document Exposure)**
- **Mitigation:** Fernet encryption, soft delete, audit logs, 22-day auto-deletion
- **Fallback:** Immediate deletion on breach detection, user notification protocol

**Risk 3: Third-Party API Dependency (Clarifai)**
- **Mitigation:** Provider abstraction, vLLM migration path, graceful degradation
- **Fallback:** Disable OCR feature, allow manual entry only

**Risk 4: UPL Violation (OCR data interpreted as advice)**
- **Mitigation:** All extracted data labeled "please verify", user confirms all fields, audit logs
- **Fallback:** Disable auto-population, show as suggestions only

**Risk 5: Type Misclassification**
- **Mitigation:** User declares type upfront, validation prompts for mismatches, edit option
- **Fallback:** User can reprocess with correct type, manual override always available

---

**Document Status:** ✅ Approved for Implementation
**Next Steps:** Create implementation plan with git worktree and task breakdown
