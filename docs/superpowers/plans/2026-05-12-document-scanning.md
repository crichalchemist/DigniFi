# Document Scanning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Clarifai with a fully local pipeline (opendataloader-pdf + pymupdf +
Gemma 3 4B via llama.cpp) that accepts PDF/JPEG/PNG uploads, extracts structured fields,
and auto-creates draft `DebtInfo` entries from creditor bill scans.

**Architecture:** PDF uploads route through opendataloader-pdf for text extraction (falling
back to pymupdf→image for scanned PDFs); images go directly to Gemma vision. A new
`/documents` page sits between registration and the intake wizard. Draft `DebtInfo` rows
appear pre-filled in the Debts wizard step and are confirmed on save.

**Tech Stack:** Python 3.11, Django 5, DRF, opendataloader-pdf, pymupdf, openai SDK
(pointed at llama.cpp), React 19, TypeScript, llama.cpp server Docker image, Gemma 3 4B
Q4_K_M GGUF.

---

## File Map

**New files:**

- `scripts/pull_model.sh` — startup script: download GGUF weights if absent, then exec llama.cpp server
- `backend/apps/documents/schemas/creditor_bill.py` — `CreditorBillExtraction` Pydantic schema
- `backend/apps/documents/services/processor.py` — `DocumentProcessor` routing class
- `backend/apps/documents/services/providers/llama_cpp.py` — `LlamaCppProvider`
- `backend/apps/documents/services/providers/prompts/__init__.py`
- `backend/apps/documents/services/providers/prompts/image_extraction.py`
- `backend/apps/documents/services/providers/prompts/text_extraction.py`
- `backend/apps/documents/services/draft_debt.py` — `DraftDebtCreator`
- `backend/apps/documents/tests/test_processor.py`
- `backend/apps/documents/tests/test_draft_debt.py`
- `backend/apps/documents/tests/test_views.py`
- `frontend/src/pages/DocumentUploadPage.tsx`
- `frontend/src/components/documents/FileDropZone.tsx`
- `frontend/src/components/documents/UploadQueue.tsx`

**Modified files:**

- `docker-compose.yml` — add `llm` service + `models` named volume
- `.env` + `.env.example` — add `LLM_BASE_URL`, remove `CLARIFAI_PAT`/`CLARIFAI_BASE_URL`/`VLLM_*`
- `backend/requirements/base.txt` — add `opendataloader-pdf`, `pymupdf`; remove `openai==1.60.0` pin
- `backend/config/settings/base.py` — replace CLARIFAI/VLLM settings with `LLM_BASE_URL`
- `backend/apps/documents/models.py` — add `CREDITOR_BILL` to `DocumentType`
- `backend/apps/documents/schemas/registry.py` — register `CreditorBillExtraction`
- `backend/apps/documents/views.py` — implement `DocumentViewSet`
- `backend/apps/documents/urls.py` — register `DocumentViewSet`
- `backend/apps/intake/models.py` — add `is_draft`, `source_document` to `DebtInfo`
- `backend/apps/intake/views.py` — bulk-set `is_draft=False` after debts PATCH
- `frontend/src/types/api.ts` — add `UploadedDocument`, `OCRResult`; extend `DebtInfo`
- `frontend/src/api/client.ts` — add `uploadDocument`, `pollDocument`, `listDocuments`, `validateDocument`
- `frontend/src/App.tsx` — add `/documents` route; change post-auth redirect
- `frontend/src/pages/LoginPage.tsx` — redirect to `/documents` after login
- `frontend/src/pages/RegisterPage.tsx` — redirect to `/documents` after register
- `frontend/src/components/wizard/steps/DebtsStep.tsx` — show "From scan" badge on draft entries

---

## Task 1: Docker infrastructure — llm service + model pull script

**Files:**

- Create: `scripts/pull_model.sh`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Create model pull script**

```bash
# scripts/pull_model.sh
#!/bin/sh
set -e

MODEL_DIR="/models"
MODEL_FILE="$MODEL_DIR/gemma-3-4b-it-Q4_K_M.gguf"
MMPROJ_FILE="$MODEL_DIR/mmproj-model-f16.gguf"
HF_BASE="https://huggingface.co/ggml-org/gemma-3-4b-it-GGUF/resolve/main"

mkdir -p "$MODEL_DIR"

if [ ! -f "$MODEL_FILE" ]; then
  echo "[pull_model] Downloading Gemma 3 4B Q4_K_M (~2.5GB)..."
  curl -L --progress-bar -o "$MODEL_FILE" "$HF_BASE/gemma-3-4b-it-Q4_K_M.gguf"
fi

if [ ! -f "$MMPROJ_FILE" ]; then
  echo "[pull_model] Downloading mmproj (~300MB)..."
  curl -L --progress-bar -o "$MMPROJ_FILE" "$HF_BASE/mmproj-model-f16.gguf"
fi

echo "[pull_model] Models ready. Starting llama.cpp server..."
exec /llama-server \
  -m "$MODEL_FILE" \
  --mmproj "$MMPROJ_FILE" \
  --host 0.0.0.0 \
  --port 8080 \
  -c 4096 \
  -np 1
```

Make executable:

```bash
chmod +x scripts/pull_model.sh
```

> **Note:** Verify exact filenames at https://huggingface.co/ggml-org/gemma-3-4b-it-GGUF
> before running. The `mmproj` filename in particular may differ between releases.

- [ ] **Step 2: Add llm service to docker-compose.yml**

In `docker-compose.yml`, add after the `frontend` service block and extend the `volumes` section:

```yaml
  llm:
    image: ghcr.io/ggml-org/llama.cpp:server
    entrypoint: ["/bin/sh", "/scripts/pull_model.sh"]
    volumes:
      - ./scripts:/scripts:ro
      - models:/models
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
      interval: 30s
      timeout: 10s
      start_period: 300s
      retries: 10

volumes:
  postgres_data:
  models:
```

Also add `llm` to the backend's `depends_on`:

```yaml
backend:
  depends_on:
    db:
      condition: service_healthy
    llm:
      condition: service_healthy
```

- [ ] **Step 3: Add LLM_BASE_URL to .env and .env.example**

In `.env`, replace:

```
# Remove these lines:
# CLARIFAI_PAT=...
# (any VLLM_ lines)
```

Add:

```
# LLM (local llama.cpp server)
LLM_BASE_URL=http://llm:8080/v1
```

In `.env.example`, same replacement — remove `CLARIFAI_PAT`/`CLARIFAI_BASE_URL`/`VLLM_*`, add:

```
# LLM (local llama.cpp — auto-started via docker compose up)
LLM_BASE_URL=http://llm:8080/v1
```

- [ ] **Step 4: Verify script is executable and docker-compose parses**

```bash
docker compose config --quiet && echo "compose OK"
```

Expected: `compose OK` (no YAML errors).

- [ ] **Step 5: Commit**

```bash
git add scripts/pull_model.sh docker-compose.yml .env .env.example
git commit -m "feat: add llama.cpp llm service with Gemma 3 4B model pull"
```

---

## Task 2: Python dependencies and settings cleanup

**Files:**

- Modify: `backend/requirements/base.txt`
- Modify: `backend/config/settings/base.py`

- [ ] **Step 1: Update requirements/base.txt**

Remove the pinned `openai==1.60.0` line and add new deps. In `backend/requirements/base.txt`:

```
# Remove:
openai==1.60.0  # For Clarifai OpenAI-compatible API

# Add (unpinned openai + new packages):
openai
opendataloader-pdf
pymupdf
```

- [ ] **Step 2: Update settings/base.py**

Find the CLARIFAI/VLLM block (around line 250) and replace it:

```python
# Remove these lines:
# CLARIFAI_PAT = env('CLARIFAI_PAT', default='')
# CLARIFAI_BASE_URL = env('CLARIFAI_BASE_URL', default='https://api.clarifai.com/v2')
# VLLM_BASE_URL = env('VLLM_BASE_URL', default='http://localhost:8000')
# VLLM_API_KEY = env('VLLM_API_KEY', default='')

# Add:
LLM_BASE_URL = env('LLM_BASE_URL', default='http://llm:8080/v1')
```

- [ ] **Step 3: Verify Django starts cleanly**

```bash
cd backend && pip install opendataloader-pdf pymupdf openai --quiet
python manage.py check
```

Expected: `System check identified no issues (0 silenced).` (the staticfiles warning is fine).

- [ ] **Step 4: Commit**

```bash
git add backend/requirements/base.txt backend/config/settings/base.py
git commit -m "chore: replace Clarifai/vLLM deps with opendataloader-pdf, pymupdf, llama.cpp settings"
```

---

## Task 3: Data model changes — DebtInfo draft fields + DocumentType

**Files:**

- Modify: `backend/apps/intake/models.py`
- Modify: `backend/apps/documents/models.py`
- Auto-generate: two migration files

- [ ] **Step 1: Write failing tests for new DebtInfo fields**

Create `backend/apps/intake/tests/test_draft_debtinfo.py`:

```python
import pytest
from apps.intake.models import DebtInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def session(db):
    user = User.objects.create_user(username='testuser', password='pass')
    return IntakeSession.objects.create(user=user)


def test_debtinfo_has_is_draft_field(db, session):
    debt = DebtInfo.objects.create(
        session=session,
        creditor_name='Test Bank',
        debt_type='credit_card',
        amount_owed='1000.00',
        is_draft=True,
    )
    assert debt.is_draft is True


def test_debtinfo_is_draft_defaults_false(db, session):
    debt = DebtInfo.objects.create(
        session=session,
        creditor_name='Test Bank',
        debt_type='credit_card',
        amount_owed='500.00',
    )
    assert debt.is_draft is False


def test_debtinfo_source_document_nullable(db, session):
    debt = DebtInfo.objects.create(
        session=session,
        creditor_name='Test Bank',
        debt_type='medical',
        amount_owed='200.00',
    )
    assert debt.source_document is None
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend && python -m pytest apps/intake/tests/test_draft_debtinfo.py -v
```

Expected: `FAILED` — `DebtInfo has no field 'is_draft'`.

- [ ] **Step 3: Add fields to DebtInfo**

In `backend/apps/intake/models.py`, locate the `DebtInfo` class and add after the `data_source` field (around line 316):

```python
    # Draft state (set by document scanner, cleared on wizard save)
    is_draft = models.BooleanField(
        default=False,
        help_text="True for entries auto-created from scanned documents, pending user confirmation",
    )
    source_document = models.ForeignKey(
        'documents.UploadedDocument',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='draft_debts',
        help_text="Document scan that generated this entry",
    )
```

- [ ] **Step 4: Add CREDITOR_BILL to DocumentType**

In `backend/apps/documents/models.py`, inside `DocumentType(models.TextChoices)`, add after `SPECIAL_CIRCUMSTANCES`:

```python
    # Creditor bills (both chapters)
    CREDITOR_BILL = 'creditor_bill', 'Creditor Bill / Statement'
```

- [ ] **Step 5: Generate and apply migrations**

```bash
cd backend
python manage.py makemigrations intake --name="debtinfo_draft_fields"
python manage.py makemigrations documents --name="documenttype_creditor_bill"
python manage.py migrate
```

Expected: both migrations created and applied with `OK`.

- [ ] **Step 6: Run tests — verify they pass**

```bash
python -m pytest apps/intake/tests/test_draft_debtinfo.py -v
```

Expected: 3 tests `PASSED`.

- [ ] **Step 7: Commit**

```bash
git add apps/intake/models.py apps/documents/models.py \
        apps/intake/migrations/ apps/documents/migrations/ \
        apps/intake/tests/test_draft_debtinfo.py
git commit -m "feat: add is_draft + source_document to DebtInfo, add CREDITOR_BILL DocumentType"
```

---

## Task 4: CreditorBillExtraction schema + registry

**Files:**

- Create: `backend/apps/documents/schemas/creditor_bill.py`
- Modify: `backend/apps/documents/schemas/registry.py`

- [ ] **Step 1: Write failing test**

In `backend/apps/documents/tests/test_schemas.py`, append:

```python
from apps.documents.schemas.creditor_bill import CreditorBillExtraction
from apps.documents.schemas.registry import get_schema_for_type
from apps.documents.models import DocumentType


def test_creditor_bill_schema_valid():
    bill = CreditorBillExtraction(
        creditor_name='Capital One',
        account_number='4111',
        amount_owed='2450.00',
        minimum_payment='35.00',
        creditor_type='credit_card',
        confidence_score=88,
    )
    assert bill.creditor_name == 'Capital One'
    assert str(bill.amount_owed) == '2450.00'


def test_creditor_bill_schema_optional_fields():
    bill = CreditorBillExtraction(
        creditor_name='City Hospital',
        amount_owed='850.00',
        creditor_type='medical',
        confidence_score=72,
    )
    assert bill.account_number is None
    assert bill.minimum_payment is None
    assert bill.due_date is None


def test_creditor_bill_in_registry():
    schema = get_schema_for_type(DocumentType.CREDITOR_BILL)
    assert schema is CreditorBillExtraction
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend && python -m pytest apps/documents/tests/test_schemas.py -k "creditor" -v
```

Expected: `ERROR` — `cannot import name 'CreditorBillExtraction'`.

- [ ] **Step 3: Create CreditorBillExtraction schema**

Create `backend/apps/documents/schemas/creditor_bill.py`:

```python
"""Creditor bill extraction schema for amounts owed population."""

from decimal import Decimal
from datetime import date
from typing import Optional
from pydantic import Field

from .base import BaseExtractionSchema

CREDITOR_TYPE_TO_DEBT_TYPE = {
    'credit_card': 'credit_card',
    'medical': 'medical',
    'personal_loan': 'personal_loan',
    'student_loan': 'student_loan',
    'auto_loan': 'auto_loan',
    'mortgage': 'mortgage',
    'utility': 'utility',
    'other': 'other',
}


class CreditorBillExtraction(BaseExtractionSchema):
    """
    Schema for creditor bill / statement OCR extraction.

    Used to auto-populate DebtInfo entries on the Debts wizard step.
    """

    creditor_name: str = Field(
        min_length=1,
        description="Name of the creditor or collection agency",
    )
    account_number: Optional[str] = Field(
        default=None,
        description="Account or reference number (last 4 digits acceptable)",
    )
    amount_owed: Decimal = Field(
        gt=0,
        description="Current balance or total amount owed",
    )
    minimum_payment: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Minimum payment due (if shown)",
    )
    due_date: Optional[date] = Field(
        default=None,
        description="Payment due date (YYYY-MM-DD)",
    )
    creditor_type: str = Field(
        description=(
            "Creditor category. One of: credit_card, medical, personal_loan, "
            "student_loan, auto_loan, mortgage, utility, other"
        ),
    )

    def to_debt_type(self) -> str:
        """Map extracted creditor_type to DebtInfo.debt_type choice."""
        return CREDITOR_TYPE_TO_DEBT_TYPE.get(self.creditor_type, 'other')
```

- [ ] **Step 4: Register in schema registry**

In `backend/apps/documents/schemas/registry.py`, add the import and map entry:

```python
from apps.documents.models import DocumentType
from .paystub import PayStubExtraction
from .business import BalanceSheetExtraction, ProfitLossExtraction
from .creditor_bill import CreditorBillExtraction   # add this

SCHEMA_MAP = {
    DocumentType.PAY_STUB: PayStubExtraction,
    DocumentType.BALANCE_SHEET: BalanceSheetExtraction,
    DocumentType.PROFIT_LOSS: ProfitLossExtraction,
    DocumentType.CREDITOR_BILL: CreditorBillExtraction,   # add this
}
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
python -m pytest apps/documents/tests/test_schemas.py -v
```

Expected: all schema tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add apps/documents/schemas/creditor_bill.py apps/documents/schemas/registry.py \
        apps/documents/tests/test_schemas.py
git commit -m "feat: add CreditorBillExtraction schema and register in schema registry"
```

---

## Task 5: LlamaCppProvider (replaces ClarifaiOCRProvider)

**Files:**

- Create: `backend/apps/documents/services/providers/llama_cpp.py`
- Modify: `backend/apps/documents/services/providers/__init__.py` (if it exports providers)

- [ ] **Step 1: Write failing test**

Create `backend/apps/documents/tests/test_llama_cpp_provider.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from apps.documents.services.providers.llama_cpp import LlamaCppProvider


@pytest.fixture
def provider():
    with patch('apps.documents.services.providers.llama_cpp.OpenAI'):
        return LlamaCppProvider(base_url='http://llm:8080/v1')


def test_provider_implements_base_interface(provider):
    from apps.documents.services.providers.base import BaseOCRProvider
    assert isinstance(provider, BaseOCRProvider)


def test_extract_text_calls_chat_completion(provider):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"creditor_name": "Bank", "amount_owed": "500"}'
    provider.client.chat.completions.create.return_value = mock_response

    result = provider.extract(b'', 'Extract fields from: Bank owes $500')

    provider.client.chat.completions.create.assert_called_once()
    assert 'Bank' in result


def test_extract_image_encodes_base64(provider):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"type": "pay_stub"}'
    provider.client.chat.completions.create.return_value = mock_response

    image_bytes = b'\x89PNG\r\n'
    provider.classify(image_bytes, 'What document type is this?')

    call_kwargs = provider.client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get('messages') or call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs['messages']
    # Verify image content was included in messages
    message_str = str(messages)
    assert 'image_url' in message_str or 'base64' in message_str
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend && python -m pytest apps/documents/tests/test_llama_cpp_provider.py -v
```

Expected: `ERROR` — `cannot import name 'LlamaCppProvider'`.

- [ ] **Step 3: Implement LlamaCppProvider**

Create `backend/apps/documents/services/providers/llama_cpp.py`:

```python
"""llama.cpp OCR provider using OpenAI-compatible API."""

import base64
from openai import OpenAI

from .base import BaseOCRProvider


class LlamaCppProvider(BaseOCRProvider):
    """
    llama.cpp server provider (Gemma 3 4B multimodal).

    Uses the OpenAI-compatible API exposed by the llama.cpp server
    at LLM_BASE_URL. No API key required for local deployment.
    """

    def __init__(self, base_url: str = 'http://llm:8080/v1'):
        self.client = OpenAI(api_key='not-required', base_url=base_url)

    def classify(self, image_data: bytes, prompt: str) -> str:
        """Classify document type from image bytes."""
        return self._call_vision(image_data, prompt)

    def extract(self, image_data: bytes, prompt: str) -> str:
        """
        Extract structured data.

        Pass non-empty image_data for visual input (JPEG/PNG/scanned PDF page).
        Pass empty bytes for text-based input — prompt must contain the text.
        """
        if image_data:
            return self._call_vision(image_data, prompt)
        return self._call_text(prompt)

    def _call_vision(self, image_data: bytes, prompt: str) -> str:
        b64 = base64.b64encode(image_data).decode('utf-8')
        response = self.client.chat.completions.create(
            model='gemma-3-4b-it',
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {
                            'type': 'image_url',
                            'image_url': {'url': f'data:image/jpeg;base64,{b64}'},
                        },
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        return response.choices[0].message.content

    def _call_text(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model='gemma-3-4b-it',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.1,
            max_tokens=1024,
        )
        return response.choices[0].message.content
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest apps/documents/tests/test_llama_cpp_provider.py -v
```

Expected: 4 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add apps/documents/services/providers/llama_cpp.py \
        apps/documents/tests/test_llama_cpp_provider.py
git commit -m "feat: add LlamaCppProvider replacing ClarifaiOCRProvider"
```

---

## Task 6: Prompt templates

**Files:**

- Create: `backend/apps/documents/services/providers/prompts/__init__.py`
- Create: `backend/apps/documents/services/providers/prompts/image_extraction.py`
- Create: `backend/apps/documents/services/providers/prompts/text_extraction.py`

- [ ] **Step 1: Write failing test**

Create `backend/apps/documents/tests/test_prompts.py`:

```python
from apps.documents.services.providers.prompts.image_extraction import build_image_extraction_prompt
from apps.documents.services.providers.prompts.text_extraction import build_text_extraction_prompt
from apps.documents.models import DocumentType


def test_image_prompt_contains_doc_type():
    prompt = build_image_extraction_prompt(DocumentType.CREDITOR_BILL)
    assert 'creditor' in prompt.lower()
    assert 'JSON' in prompt


def test_image_prompt_contains_schema_fields():
    prompt = build_image_extraction_prompt(DocumentType.CREDITOR_BILL)
    assert 'creditor_name' in prompt
    assert 'amount_owed' in prompt


def test_text_prompt_embeds_content():
    prompt = build_text_extraction_prompt(DocumentType.PAY_STUB, 'Employer: Acme\nGross: $3200')
    assert 'Acme' in prompt
    assert 'gross_pay' in prompt


def test_text_prompt_requests_json():
    prompt = build_text_extraction_prompt(DocumentType.CREDITOR_BILL, 'Capital One $450')
    assert 'JSON' in prompt
    assert 'confidence_score' in prompt
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend && python -m pytest apps/documents/tests/test_prompts.py -v
```

Expected: `ERROR` — import errors.

- [ ] **Step 3: Create prompt modules**

Create `backend/apps/documents/services/providers/prompts/__init__.py` (empty).

Create `backend/apps/documents/services/providers/prompts/image_extraction.py`:

```python
"""Prompt builder for image-based document extraction (JPEG/PNG/scanned PDF)."""

from apps.documents.models import DocumentType

_FIELD_HINTS = {
    DocumentType.CREDITOR_BILL: (
        'creditor_name (string), account_number (string or null), '
        'amount_owed (decimal string), minimum_payment (decimal string or null), '
        'due_date (YYYY-MM-DD or null), creditor_type (one of: credit_card, '
        'medical, personal_loan, student_loan, auto_loan, mortgage, utility, other)'
    ),
    DocumentType.PAY_STUB: (
        'employer_name (string), gross_pay (decimal string), '
        'pay_period_start (YYYY-MM-DD), pay_period_end (YYYY-MM-DD), '
        'ytd_gross (decimal string or null), net_pay (decimal string or null), '
        'deductions_total (decimal string or null)'
    ),
}

_DEFAULT_FIELDS = 'all visible fields as key-value pairs'


def build_image_extraction_prompt(document_type: str) -> str:
    fields = _FIELD_HINTS.get(document_type, _DEFAULT_FIELDS)
    return (
        f'You are a document data extraction assistant for a legal filing platform. '
        f'Extract the following fields from this {document_type.replace("_", " ")} image. '
        f'Return ONLY a valid JSON object with these fields: {fields}, '
        f'confidence_score (integer 0-100 reflecting your extraction confidence). '
        f'If a field is not visible or not applicable, set it to null. '
        f'Do not include any text outside the JSON object.'
    )
```

Create `backend/apps/documents/services/providers/prompts/text_extraction.py`:

```python
"""Prompt builder for text-based document extraction (digital PDF via opendataloader-pdf)."""

from apps.documents.models import DocumentType
from .image_extraction import _FIELD_HINTS, _DEFAULT_FIELDS


def build_text_extraction_prompt(document_type: str, extracted_text: str) -> str:
    fields = _FIELD_HINTS.get(document_type, _DEFAULT_FIELDS)
    return (
        f'You are a document data extraction assistant for a legal filing platform. '
        f'The following text was extracted from a {document_type.replace("_", " ")} document:\n\n'
        f'---\n{extracted_text[:4000]}\n---\n\n'
        f'Extract these fields: {fields}, '
        f'confidence_score (integer 0-100). '
        f'Return ONLY a valid JSON object. Set missing fields to null.'
    )
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest apps/documents/tests/test_prompts.py -v
```

Expected: 4 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add apps/documents/services/providers/prompts/ \
        apps/documents/tests/test_prompts.py
git commit -m "feat: add image and text extraction prompt builders"
```

---

## Task 7: DocumentProcessor

**Files:**

- Create: `backend/apps/documents/services/processor.py`
- Create: `backend/apps/documents/tests/test_processor.py`

- [ ] **Step 1: Write failing tests**

Create `backend/apps/documents/tests/test_processor.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from apps.documents.services.processor import DocumentProcessor, ExtractionResult
from apps.documents.models import DocumentType


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.extract.return_value = (
        '{"creditor_name": "Chase", "amount_owed": "1200.00", '
        '"creditor_type": "credit_card", "confidence_score": 85}'
    )
    return provider


@pytest.fixture
def processor(mock_provider):
    return DocumentProcessor(provider=mock_provider)


def test_jpeg_routes_to_vision(processor, mock_provider):
    image_bytes = b'\xff\xd8\xff'  # JPEG magic bytes
    result = processor.process(image_bytes, 'image/jpeg', DocumentType.CREDITOR_BILL)

    assert isinstance(result, ExtractionResult)
    # Vision path: image_data is passed to provider
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == image_bytes  # image bytes passed through


def test_png_routes_to_vision(processor, mock_provider):
    png_bytes = b'\x89PNG\r\n'
    processor.process(png_bytes, 'image/png', DocumentType.CREDITOR_BILL)
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == png_bytes


def test_extraction_result_parses_fields(processor):
    result = processor.process(b'\xff\xd8', 'image/jpeg', DocumentType.CREDITOR_BILL)
    assert result.fields['creditor_name'] == 'Chase'
    assert result.confidence['overall'] == 85
    assert result.detected_type == DocumentType.CREDITOR_BILL


def test_invalid_json_returns_failed_result(processor, mock_provider):
    mock_provider.extract.return_value = 'Not JSON at all'
    result = processor.process(b'\xff\xd8', 'image/jpeg', DocumentType.CREDITOR_BILL)
    assert result.fields == {}
    assert result.confidence['overall'] == 0


def test_pdf_with_text_routes_to_text_path(processor, mock_provider):
    """Digital PDFs with extractable text use text prompt, not vision."""
    mock_provider.extract.return_value = (
        '{"employer_name": "Acme", "gross_pay": "3200.00", '
        '"pay_period_start": "2026-01-01", "pay_period_end": "2026-01-15", '
        '"confidence_score": 90}'
    )
    # We'll use a mock for opendataloader_pdf
    with patch('apps.documents.services.processor.opendataloader_pdf') as mock_odl:
        mock_odl.convert.return_value = None
        with patch('apps.documents.services.processor._read_odl_output') as mock_read:
            mock_read.return_value = 'Employer: Acme Corp\nGross Pay: $3,200.00'
            result = processor.process(b'%PDF-1.4', 'application/pdf', DocumentType.PAY_STUB)

    # Text path: empty bytes passed to provider (text embedded in prompt)
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == b''
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend && python -m pytest apps/documents/tests/test_processor.py -v
```

Expected: `ERROR` — `cannot import name 'DocumentProcessor'`.

- [ ] **Step 3: Implement DocumentProcessor**

Create `backend/apps/documents/services/processor.py`:

````python
"""Document processing pipeline — routes inputs to appropriate extraction path."""

import json
import tempfile
import os
from dataclasses import dataclass, field
from typing import Any

import opendataloader_pdf

from apps.documents.models import DocumentType
from apps.documents.services.providers.base import BaseOCRProvider
from apps.documents.services.providers.prompts.image_extraction import build_image_extraction_prompt
from apps.documents.services.providers.prompts.text_extraction import build_text_extraction_prompt

# Minimum extracted text length to consider a PDF "digital" (not scanned)
_MIN_TEXT_LENGTH = 100
# Maximum PDF pages to render for scanned PDF fallback
_MAX_SCANNED_PAGES = 3


@dataclass
class ExtractionResult:
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, Any] = field(default_factory=dict)
    detected_type: str = ''
    error: str = ''


def _read_odl_output(output_dir: str) -> str:
    """Read text content from opendataloader-pdf output directory."""
    for fname in os.listdir(output_dir):
        if fname.endswith('.md') or fname.endswith('.txt'):
            with open(os.path.join(output_dir, fname)) as f:
                return f.read()
    return ''


def _pdf_to_image_bytes(pdf_bytes: bytes, page_index: int = 0) -> bytes:
    """Render a single PDF page to JPEG bytes using pymupdf."""
    import fitz  # pymupdf
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    if page_index >= len(doc):
        page_index = 0
    page = doc[page_index]
    pix = page.get_pixmap(dpi=150)
    return pix.tobytes('jpeg')


class DocumentProcessor:
    def __init__(self, provider: BaseOCRProvider):
        self._provider = provider

    def process(self, file_bytes: bytes, mime_type: str, doc_type: str) -> ExtractionResult:
        """Route file to correct extraction path and return structured result."""
        try:
            if mime_type in ('image/jpeg', 'image/png', 'image/webp'):
                return self._process_image(file_bytes, doc_type)
            elif mime_type == 'application/pdf':
                return self._process_pdf(file_bytes, doc_type)
            else:
                return ExtractionResult(error=f'Unsupported MIME type: {mime_type}')
        except Exception as exc:
            return ExtractionResult(error=str(exc))

    def _process_image(self, image_bytes: bytes, doc_type: str) -> ExtractionResult:
        prompt = build_image_extraction_prompt(doc_type)
        raw = self._provider.extract(image_bytes, prompt)
        return self._parse_result(raw, doc_type)

    def _process_pdf(self, pdf_bytes: bytes, doc_type: str) -> ExtractionResult:
        with tempfile.TemporaryDirectory() as tmp_in, \
             tempfile.TemporaryDirectory() as tmp_out:
            pdf_path = os.path.join(tmp_in, 'document.pdf')
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)

            opendataloader_pdf.convert(
                input_path=[pdf_path],
                output_dir=tmp_out,
                format='markdown',
            )
            text = _read_odl_output(tmp_out)

        if len(text.strip()) >= _MIN_TEXT_LENGTH:
            # Digital PDF — use text extraction path
            prompt = build_text_extraction_prompt(doc_type, text)
            raw = self._provider.extract(b'', prompt)
        else:
            # Scanned PDF — render first page and use vision path
            image_bytes = _pdf_to_image_bytes(pdf_bytes, page_index=0)
            prompt = build_image_extraction_prompt(doc_type)
            raw = self._provider.extract(image_bytes, prompt)

        return self._parse_result(raw, doc_type)

    def _parse_result(self, raw: str, doc_type: str) -> ExtractionResult:
        try:
            # Strip markdown code fences if model wrapped output
            clean = raw.strip()
            if clean.startswith('```'):
                clean = clean.split('```')[1]
                if clean.startswith('json'):
                    clean = clean[4:]
            data = json.loads(clean)
            confidence_score = int(data.pop('confidence_score', 0))
            return ExtractionResult(
                fields=data,
                confidence={'overall': confidence_score},
                detected_type=doc_type,
            )
        except (json.JSONDecodeError, ValueError):
            return ExtractionResult(
                fields={},
                confidence={'overall': 0},
                detected_type=doc_type,
                error=f'Failed to parse LLM response: {raw[:200]}',
            )
````

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest apps/documents/tests/test_processor.py -v
```

Expected: 5 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add apps/documents/services/processor.py \
        apps/documents/tests/test_processor.py
git commit -m "feat: add DocumentProcessor with PDF/image routing"
```

---

## Task 8: DraftDebtCreator

**Files:**

- Create: `backend/apps/documents/services/draft_debt.py`
- Create: `backend/apps/documents/tests/test_draft_debt.py`

- [ ] **Step 1: Write failing tests**

Create `backend/apps/documents/tests/test_draft_debt.py`:

```python
import pytest
from decimal import Decimal
from apps.documents.services.draft_debt import DraftDebtCreator
from apps.documents.services.processor import ExtractionResult
from apps.documents.models import DocumentType, UploadedDocument
from apps.intake.models import IntakeSession, DebtInfo
from apps.users.models import User


@pytest.fixture
def session(db):
    user = User.objects.create_user(username='drafttest', password='pass')
    return IntakeSession.objects.create(user=user)


@pytest.fixture
def uploaded_doc(db, session):
    user = session.user
    return UploadedDocument.objects.create(
        session=session,
        uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename='bill.pdf',
        file_size=1024,
        mime_type='application/pdf',
        file='documents/2026/05/bill.pdf',
    )


def test_creates_draft_debtinfo(db, session, uploaded_doc):
    result = ExtractionResult(
        fields={
            'creditor_name': 'Capital One',
            'account_number': '4111',
            'amount_owed': '1500.00',
            'creditor_type': 'credit_card',
        },
        confidence={'overall': 88},
        detected_type=DocumentType.CREDITOR_BILL,
    )
    creator = DraftDebtCreator()
    debt = creator.create_from_result(result, session, uploaded_doc)

    assert debt.is_draft is True
    assert debt.creditor_name == 'Capital One'
    assert debt.debt_type == 'credit_card'
    assert debt.source_document == uploaded_doc
    assert debt.data_source == 'uploaded_document'
    assert DebtInfo.objects.filter(session=session, is_draft=True).count() == 1


def test_unknown_creditor_type_maps_to_other(db, session, uploaded_doc):
    result = ExtractionResult(
        fields={
            'creditor_name': 'Unknown Co',
            'amount_owed': '300.00',
            'creditor_type': 'payday_loan',
        },
        confidence={'overall': 60},
        detected_type=DocumentType.CREDITOR_BILL,
    )
    creator = DraftDebtCreator()
    debt = creator.create_from_result(result, session, uploaded_doc)
    assert debt.debt_type == 'other'


def test_non_creditor_bill_raises(db, session, uploaded_doc):
    result = ExtractionResult(
        fields={'employer_name': 'Acme'},
        confidence={'overall': 90},
        detected_type=DocumentType.PAY_STUB,
    )
    creator = DraftDebtCreator()
    with pytest.raises(ValueError, match='CREDITOR_BILL'):
        creator.create_from_result(result, session, uploaded_doc)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend && python -m pytest apps/documents/tests/test_draft_debt.py -v
```

Expected: `ERROR` — import error.

- [ ] **Step 3: Implement DraftDebtCreator**

Create `backend/apps/documents/services/draft_debt.py`:

```python
"""Creates draft DebtInfo entries from creditor bill OCR extraction results."""

from decimal import Decimal, InvalidOperation

from apps.documents.models import DocumentType, UploadedDocument
from apps.documents.services.processor import ExtractionResult
from apps.intake.models import DebtInfo, IntakeSession

_VALID_DEBT_TYPES = {c[0] for c in DebtInfo.DEBT_TYPE_CHOICES}


class DraftDebtCreator:
    """Converts a CREDITOR_BILL ExtractionResult into a draft DebtInfo row."""

    def create_from_result(
        self,
        result: ExtractionResult,
        session: IntakeSession,
        source_document: UploadedDocument,
    ) -> DebtInfo:
        if result.detected_type != DocumentType.CREDITOR_BILL:
            raise ValueError(
                f'DraftDebtCreator only handles CREDITOR_BILL, got {result.detected_type}'
            )

        fields = result.fields
        debt_type = fields.get('creditor_type', 'other')
        if debt_type not in _VALID_DEBT_TYPES:
            debt_type = 'other'

        try:
            amount_owed = Decimal(str(fields.get('amount_owed', '0')))
        except InvalidOperation:
            amount_owed = Decimal('0')

        return DebtInfo.objects.create(
            session=session,
            creditor_name=fields.get('creditor_name', 'Unknown Creditor')[:255],
            debt_type=debt_type,
            account_number=fields.get('account_number') or '',
            amount_owed=amount_owed,
            data_source='uploaded_document',
            is_draft=True,
            source_document=source_document,
        )
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest apps/documents/tests/test_draft_debt.py -v
```

Expected: 3 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add apps/documents/services/draft_debt.py \
        apps/documents/tests/test_draft_debt.py
git commit -m "feat: add DraftDebtCreator service for creditor bill scan to DebtInfo"
```

---

## Task 9: DocumentViewSet API

**Files:**

- Modify: `backend/apps/documents/views.py`
- Modify: `backend/apps/documents/urls.py`
- Create: `backend/apps/documents/tests/test_views.py`

- [ ] **Step 1: Write failing tests**

Create `backend/apps/documents/tests/test_views.py`:

```python
import pytest
import json
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from apps.users.models import User
from apps.intake.models import IntakeSession
from apps.documents.models import UploadedDocument, OCRResult, OCRStatus, DocumentType


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='doctest', password='pass')
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def session(db, auth_client):
    _, user = auth_client
    return IntakeSession.objects.create(user=user)


def test_upload_returns_202(db, auth_client, session):
    client, _ = auth_client
    pdf = SimpleUploadedFile('bill.pdf', b'%PDF-1.4 fake', content_type='application/pdf')

    with patch('apps.documents.views.ThreadPoolExecutor') as mock_pool:
        mock_pool.return_value.__enter__.return_value.submit = MagicMock()
        response = client.post(
            '/api/documents/upload/',
            {
                'file': pdf,
                'document_type': DocumentType.CREDITOR_BILL,
                'session_id': session.id,
            },
            format='multipart',
        )

    assert response.status_code == 202
    data = response.json()
    assert 'id' in data
    assert data['status'] == 'processing'


def test_list_scoped_to_session(db, auth_client, session):
    client, user = auth_client
    UploadedDocument.objects.create(
        session=session, uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename='bill.pdf', file_size=100,
        mime_type='application/pdf', file='documents/x.pdf',
    )
    response = client.get(f'/api/documents/?session_id={session.id}')
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_document_returns_ocr_result(db, auth_client, session):
    client, user = auth_client
    doc = UploadedDocument.objects.create(
        session=session, uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename='bill.pdf', file_size=100,
        mime_type='application/pdf', file='documents/x.pdf',
    )
    OCRResult.objects.create(
        document=doc, status=OCRStatus.COMPLETED,
        extracted_data='{"creditor_name": "Chase"}',
        confidence_scores={'overall': 85},
        overall_confidence=85,
    )
    response = client.get(f'/api/documents/{doc.id}/')
    assert response.status_code == 200
    data = response.json()
    assert data['ocr_result']['status'] == 'completed'


def test_validate_updates_ocr_result(db, auth_client, session):
    client, user = auth_client
    doc = UploadedDocument.objects.create(
        session=session, uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename='bill.pdf', file_size=100,
        mime_type='application/pdf', file='documents/x.pdf',
    )
    ocr = OCRResult.objects.create(
        document=doc, status=OCRStatus.COMPLETED,
        extracted_data='{"creditor_name": "Chase"}',
        confidence_scores={}, overall_confidence=80,
    )
    response = client.post(
        f'/api/documents/{doc.id}/validate/',
        {'fields': {'creditor_name': 'Chase Bank NA'}},
        format='json',
    )
    assert response.status_code == 200
    ocr.refresh_from_db()
    assert ocr.user_validated is True
    assert json.loads(ocr.extracted_data)['creditor_name'] == 'Chase Bank NA'
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend && python -m pytest apps/documents/tests/test_views.py -v
```

Expected: `FAILED` — 404s (no routes registered).

- [ ] **Step 3: Implement DocumentViewSet**

Replace the contents of `backend/apps/documents/views.py`:

```python
"""Document upload and OCR result views."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.documents.models import (
    DocumentType, OCRResult, OCRStatus, UploadedDocument,
)
from apps.documents.services.draft_debt import DraftDebtCreator
from apps.documents.services.processor import DocumentProcessor
from apps.documents.services.providers.llama_cpp import LlamaCppProvider
from apps.intake.models import IntakeSession

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {'application/pdf', 'image/jpeg', 'image/png', 'image/webp'}


def _get_processor() -> DocumentProcessor:
    provider = LlamaCppProvider(base_url=getattr(settings, 'LLM_BASE_URL', 'http://llm:8080/v1'))
    return DocumentProcessor(provider=provider)


def _run_processing(doc_id: int) -> None:
    """Background thread: run OCR and optionally create draft DebtInfo."""
    from apps.documents.models import UploadedDocument  # avoid circular import at module level

    try:
        doc = UploadedDocument.objects.select_related('session').get(pk=doc_id)
        ocr = OCRResult.objects.get(document=doc)
        ocr.status = OCRStatus.PROCESSING
        ocr.save(update_fields=['status'])

        file_bytes = doc.file.read()
        processor = _get_processor()
        result = processor.process(file_bytes, doc.mime_type, doc.document_type)

        if result.error:
            ocr.status = OCRStatus.FAILED
            ocr.error_message = result.error
            ocr.extracted_data = '{}'
            ocr.overall_confidence = 0
        else:
            ocr.status = OCRStatus.COMPLETED
            ocr.extracted_data = json.dumps(result.fields)
            ocr.confidence_scores = result.confidence
            ocr.overall_confidence = result.confidence.get('overall', 0)

            if doc.document_type == DocumentType.CREDITOR_BILL and not result.error:
                try:
                    DraftDebtCreator().create_from_result(result, doc.session, doc)
                except Exception as exc:
                    logger.warning('DraftDebtCreator failed for doc %s: %s', doc_id, exc)

        ocr.save()
    except Exception as exc:
        logger.exception('Processing failed for document %s: %s', doc_id, exc)
        try:
            OCRResult.objects.filter(document_id=doc_id).update(
                status=OCRStatus.FAILED, error_message=str(exc)
            )
        except Exception:
            pass


class DocumentViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        file = request.FILES.get('file')
        document_type = request.data.get('document_type')
        session_id = request.data.get('session_id')

        if not file or not document_type or not session_id:
            return Response(
                {'error': 'file, document_type, and session_id are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.content_type not in ALLOWED_MIME_TYPES:
            return Response(
                {'error': f'Unsupported file type: {file.content_type}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            intake_session = IntakeSession.objects.get(pk=session_id, user=request.user)
        except IntakeSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        doc = UploadedDocument.objects.create(
            session=intake_session,
            uploaded_by=request.user,
            document_type=document_type,
            user_declared_type=document_type,
            original_filename=file.name,
            file_size=file.size,
            mime_type=file.content_type,
            file=file,
        )
        OCRResult.objects.create(
            document=doc,
            status=OCRStatus.PENDING,
            extracted_data='{}',
            confidence_scores={},
            overall_confidence=0,
        )

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_run_processing, doc.id)

        return Response({'id': doc.id, 'status': 'processing'}, status=status.HTTP_202_ACCEPTED)

    def list(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': 'session_id required'}, status=status.HTTP_400_BAD_REQUEST)
        docs = UploadedDocument.objects.filter(
            session_id=session_id, session__user=request.user
        ).select_related('ocr_result').order_by('-uploaded_at')
        return Response([_serialize_doc(d) for d in docs])

    def retrieve(self, request, pk=None):
        try:
            doc = UploadedDocument.objects.select_related('ocr_result').get(
                pk=pk, session__user=request.user
            )
        except UploadedDocument.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_doc(doc))

    @action(detail=True, methods=['post'], url_path='validate')
    def validate(self, request, pk=None):
        try:
            doc = UploadedDocument.objects.select_related('ocr_result', 'session').get(
                pk=pk, session__user=request.user
            )
        except UploadedDocument.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        fields = request.data.get('fields', {})
        ocr = doc.ocr_result
        existing = json.loads(ocr.extracted_data or '{}')
        existing.update(fields)
        ocr.extracted_data = json.dumps(existing)
        ocr.user_validated = True
        ocr.validation_changes = list(fields.keys())
        ocr.save()

        # Propagate changes to linked draft DebtInfo if present
        if doc.document_type == DocumentType.CREDITOR_BILL:
            doc.draft_debts.filter(is_draft=True).update(
                **{k: v for k, v in fields.items() if k in ('creditor_name', 'amount_owed')}
            )

        return Response(_serialize_ocr(ocr))


def _serialize_doc(doc: UploadedDocument) -> dict:
    result = {
        'id': doc.id,
        'document_type': doc.document_type,
        'original_filename': doc.original_filename,
        'uploaded_at': doc.uploaded_at.isoformat(),
        'ocr_result': None,
    }
    if hasattr(doc, 'ocr_result'):
        result['ocr_result'] = _serialize_ocr(doc.ocr_result)
    return result


def _serialize_ocr(ocr: OCRResult) -> dict:
    return {
        'status': ocr.status,
        'extracted_data': json.loads(ocr.extracted_data or '{}'),
        'confidence_scores': ocr.confidence_scores,
        'overall_confidence': float(ocr.overall_confidence),
        'user_validated': ocr.user_validated,
        'error_message': ocr.error_message,
    }
```

- [ ] **Step 4: Register routes in urls.py**

Replace `backend/apps/documents/urls.py`:

```python
from django.urls import path
from .views import DocumentViewSet

doc_list = DocumentViewSet.as_view({'get': 'list'})
doc_detail = DocumentViewSet.as_view({'get': 'retrieve'})
doc_upload = DocumentViewSet.as_view({'post': 'upload'})
doc_validate = DocumentViewSet.as_view({'post': 'validate'})

app_name = 'documents'
urlpatterns = [
    path('', doc_list, name='list'),
    path('upload/', doc_upload, name='upload'),
    path('<int:pk>/', doc_detail, name='detail'),
    path('<int:pk>/validate/', doc_validate, name='validate'),
]
```

Verify `/api/documents/` is included in `backend/config/urls.py`. If not, add:

```python
path('api/documents/', include('apps.documents.urls', namespace='documents')),
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
python -m pytest apps/documents/tests/test_views.py -v
```

Expected: 4 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add apps/documents/views.py apps/documents/urls.py \
        apps/documents/tests/test_views.py
git commit -m "feat: implement DocumentViewSet with upload, list, retrieve, validate endpoints"
```

---

## Task 10: Bulk clear is_draft on debts save

**Files:**

- Modify: `backend/apps/intake/views.py`

- [ ] **Step 1: Write failing test**

In `backend/apps/intake/tests/` (add to an appropriate existing test file, e.g. `test_views.py`), append:

```python
def test_debts_patch_clears_is_draft(auth_client_with_session):
    """Saving the Debts step sets is_draft=False on all session debts."""
    client, session = auth_client_with_session
    user = session.user
    from apps.documents.models import UploadedDocument, DocumentType
    # Create a draft debt
    DebtInfo.objects.create(
        session=session,
        creditor_name='Draft Bank',
        debt_type='credit_card',
        amount_owed='500.00',
        is_draft=True,
    )
    response = client.patch(
        f'/api/intake/sessions/{session.id}/',
        {'debts': [{'creditor_name': 'Draft Bank', 'debt_type': 'credit_card', 'amount_owed': '500.00'}]},
        format='json',
    )
    assert response.status_code in (200, 201)
    assert not DebtInfo.objects.filter(session=session, is_draft=True).exists()
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd backend && python -m pytest apps/intake/tests/test_views.py::test_debts_patch_clears_is_draft -v
```

Expected: `FAILED` — draft debt still has `is_draft=True`.

- [ ] **Step 3: Update IntakeSessionViewSet**

In `backend/apps/intake/views.py`, find the `partial_update` method (or `update`, depending on how the PATCH is handled). After the session is saved/updated, add:

```python
# Clear draft flag on all debts for this session after any PATCH
if 'debts' in request.data:
    from apps.intake.models import DebtInfo
    DebtInfo.objects.filter(session=instance, is_draft=True).update(is_draft=False)
```

Place this immediately after `serializer.save()` within the update handler.

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest apps/intake/tests/test_views.py::test_debts_patch_clears_is_draft -v
```

Expected: `PASSED`.

- [ ] **Step 5: Run full backend test suite**

```bash
python -m pytest --tb=short -q
```

Expected: all existing tests still pass, new test passes.

- [ ] **Step 6: Commit**

```bash
git add apps/intake/views.py apps/intake/tests/
git commit -m "feat: bulk-clear is_draft on DebtInfo when debts step is saved"
```

---

## Task 11: Frontend TypeScript types

**Files:**

- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: Add new types and extend DebtInfo**

In `frontend/src/types/api.ts`, add after the existing `GeneratedForm` block:

```typescript
// Document scanning
export type OCRStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'validated';

export interface OCRResult {
  status: OCRStatus;
  extracted_data: Record<string, unknown>;
  confidence_scores: Record<string, number>;
  overall_confidence: number;
  user_validated: boolean;
  error_message: string | null;
}

export interface UploadedDocument {
  id: number;
  document_type: string;
  original_filename: string;
  uploaded_at: string;
  ocr_result: OCRResult | null;
}

export interface DocumentUploadResponse {
  id: number;
  status: 'processing';
}
```

In the existing `DebtInfo` interface (around line 138), add two fields:

```typescript
  is_draft?: boolean;
  source_document?: number | null;
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat: add UploadedDocument, OCRResult TypeScript types; extend DebtInfo"
```

---

## Task 12: Frontend API client functions

**Files:**

- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add four document API functions**

In `frontend/src/api/client.ts`, append after the existing exports:

```typescript
import type { UploadedDocument, DocumentUploadResponse, OCRResult } from '../types/api';

export async function uploadDocument(
  sessionId: number,
  file: File,
  documentType: string
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', documentType);
  formData.append('session_id', String(sessionId));

  const token = await getAccessToken();
  const res = await fetch(`${API_BASE}/documents/upload/`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function pollDocument(id: number): Promise<UploadedDocument> {
  return apiFetch<UploadedDocument>(`/documents/${id}/`);
}

export async function listDocuments(sessionId: number): Promise<UploadedDocument[]> {
  return apiFetch<UploadedDocument[]>(`/documents/?session_id=${sessionId}`);
}

export async function validateDocument(
  id: number,
  fields: Record<string, unknown>
): Promise<OCRResult> {
  return apiFetch<OCRResult>(`/documents/${id}/validate/`, {
    method: 'POST',
    body: JSON.stringify({ fields }),
  });
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add uploadDocument, pollDocument, listDocuments, validateDocument API functions"
```

---

## Task 13: DocumentUploadPage and components

**Files:**

- Create: `frontend/src/components/documents/FileDropZone.tsx`
- Create: `frontend/src/components/documents/UploadQueue.tsx`
- Create: `frontend/src/pages/DocumentUploadPage.tsx`

- [ ] **Step 1: Create FileDropZone**

Create `frontend/src/components/documents/FileDropZone.tsx`:

```tsx
import { useRef } from 'react';

interface FileDropZoneProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
const ACCEPTED_EXTS = '.pdf,.jpg,.jpeg,.png';

export function FileDropZone({ onFiles, disabled }: FileDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter((f) => ACCEPTED_TYPES.includes(f.type));
    if (files.length) onFiles(files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onFiles(files);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Drop files here or click to upload"
      aria-disabled={disabled}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => e.key === 'Enter' && !disabled && inputRef.current?.click()}
      style={{
        border: '2px dashed #6b7280',
        borderRadius: 8,
        padding: '2rem',
        textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <p>Drop PDF, JPEG, or PNG files here</p>
      <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>or click to browse</p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTS}
        multiple
        hidden
        onChange={handleChange}
      />
    </div>
  );
}
```

- [ ] **Step 2: Create UploadQueue**

Create `frontend/src/components/documents/UploadQueue.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { pollDocument } from '../../api/client';
import type { UploadedDocument } from '../../types/api';

interface QueueItem {
  docId: number;
  filename: string;
  doc: UploadedDocument | null;
}

interface UploadQueueProps {
  items: QueueItem[];
  onAllComplete: (docs: UploadedDocument[]) => void;
}

export function UploadQueue({ items, onAllComplete }: UploadQueueProps) {
  const [states, setStates] = useState<Record<number, UploadedDocument | null>>({});

  useEffect(() => {
    if (!items.length) return;

    const intervals: ReturnType<typeof setInterval>[] = [];

    items.forEach((item) => {
      const interval = setInterval(async () => {
        try {
          const doc = await pollDocument(item.docId);
          if (doc.ocr_result?.status === 'completed' || doc.ocr_result?.status === 'failed') {
            clearInterval(interval);
            setStates((prev) => ({ ...prev, [item.docId]: doc }));
          }
        } catch {
          clearInterval(interval);
        }
      }, 3000);
      intervals.push(interval);
    });

    return () => intervals.forEach(clearInterval);
  }, [items]);

  useEffect(() => {
    if (!items.length) return;
    const completed = items.filter((i) => states[i.docId] !== undefined);
    if (completed.length === items.length) {
      onAllComplete(Object.values(states).filter(Boolean) as UploadedDocument[]);
    }
  }, [states, items, onAllComplete]);

  const statusLabel = (docId: number) => {
    const doc = states[docId];
    if (!doc) return 'Processing…';
    const s = doc.ocr_result?.status;
    if (s === 'completed') return '✓ Done';
    if (s === 'failed') return '✗ Failed';
    return 'Processing…';
  };

  return (
    <ul aria-label="Upload queue" style={{ listStyle: 'none', padding: 0 }}>
      {items.map((item) => (
        <li key={item.docId} style={{ padding: '0.5rem 0', display: 'flex', gap: '1rem' }}>
          <span>{item.filename}</span>
          <span aria-live="polite">{statusLabel(item.docId)}</span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 3: Create DocumentUploadPage**

Create `frontend/src/pages/DocumentUploadPage.tsx`:

```tsx
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropZone } from '../components/documents/FileDropZone';
import { UploadQueue } from '../components/documents/UploadQueue';
import { uploadDocument } from '../api/client';
import { useIntake } from '../context/IntakeContext';
import type { UploadedDocument } from '../types/api';

interface QueuedUpload {
  docId: number;
  filename: string;
  doc: UploadedDocument | null;
}

const DOC_TYPE_OPTIONS = [
  { value: 'creditor_bill', label: 'Creditor bill or statement' },
  { value: 'pay_stub', label: 'Pay stub' },
  { value: 'tax_return_personal', label: 'Personal tax return' },
  { value: 'bank_statement', label: 'Bank statement' },
  { value: 'credit_report', label: 'Credit report' },
];

export function DocumentUploadPage() {
  const navigate = useNavigate();
  const { session } = useIntake();
  const [queue, setQueue] = useState<QueuedUpload[]>([]);
  const [uploading, setUploading] = useState(false);
  const [allComplete, setAllComplete] = useState(false);
  const [summary, setSummary] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleFiles = useCallback(
    async (files: File[]) => {
      if (!session?.id) {
        setError('No active session. Please start from the beginning.');
        return;
      }
      setUploading(true);
      setError('');

      const newItems: QueuedUpload[] = [];
      for (const file of files) {
        // Default to creditor_bill — user can refine later
        const docType = 'creditor_bill';
        try {
          const res = await uploadDocument(session.id, file, docType);
          newItems.push({ docId: res.id, filename: file.name, doc: null });
        } catch {
          setError(`Failed to upload ${file.name}.`);
        }
      }
      setQueue((prev) => [...prev, ...newItems]);
      setUploading(false);
    },
    [session]
  );

  const handleAllComplete = useCallback((docs: UploadedDocument[]) => {
    setAllComplete(true);
    const bills = docs.filter((d) => d.document_type === 'creditor_bill').length;
    const stubs = docs.filter((d) => d.document_type === 'pay_stub').length;
    const parts: string[] = [];
    if (bills) parts.push(`${bills} creditor bill${bills > 1 ? 's' : ''}`);
    if (stubs) parts.push(`${stubs} pay stub${stubs > 1 ? 's' : ''}`);
    setSummary(parts.length ? `Found: ${parts.join(', ')}.` : 'Processing complete.');
  }, []);

  const isEmpty = queue.length === 0 && !uploading;

  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: '2rem' }}>
      <h1>Upload your documents</h1>
      <p>
        Upload paystubs, creditor bills, and other supporting documents. We'll extract the
        information and pre-fill your intake forms — you can review and correct anything before
        submitting.
      </p>
      <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
        Your documents are processed locally and never sent to any external service.
      </p>

      {error && (
        <p role="alert" style={{ color: '#dc2626' }}>
          {error}
        </p>
      )}

      {isEmpty && <FileDropZone onFiles={handleFiles} disabled={uploading} />}

      {queue.length > 0 && (
        <>
          <UploadQueue items={queue} onAllComplete={handleAllComplete} />
          {!allComplete && <FileDropZone onFiles={handleFiles} disabled={uploading} />}
        </>
      )}

      {allComplete && summary && (
        <p role="status" style={{ color: '#16a34a', fontWeight: 600 }}>
          {summary}
        </p>
      )}

      <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
        <button
          onClick={() => navigate('/intake')}
          disabled={uploading}
          style={{ padding: '0.75rem 1.5rem', cursor: 'pointer' }}
        >
          {allComplete ? 'Continue to intake' : 'Skip for now'}
        </button>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/documents/ frontend/src/pages/DocumentUploadPage.tsx
git commit -m "feat: add FileDropZone, UploadQueue, DocumentUploadPage components"
```

---

## Task 14: App routing and auth redirects

**Files:**

- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/LoginPage.tsx`
- Modify: `frontend/src/pages/RegisterPage.tsx`

- [ ] **Step 1: Add /documents route to App.tsx**

In `frontend/src/App.tsx`, add the import and route:

```tsx
import { DocumentUploadPage } from './pages/DocumentUploadPage';
```

Inside the `IntakeLayout` route block (alongside `/intake` and `/forms`), add:

```tsx
<Route path="/documents" element={<DocumentUploadPage />} />
```

- [ ] **Step 2: Update post-auth redirects**

In `frontend/src/pages/LoginPage.tsx`, change all occurrences of:

```tsx
navigate('/intake', { replace: true });
```

to:

```tsx
navigate('/documents', { replace: true });
```

In `frontend/src/pages/RegisterPage.tsx`, change all occurrences of:

```tsx
navigate('/intake', { replace: true });
```

to:

```tsx
navigate('/documents', { replace: true });
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend && npm test
```

Expected: all existing tests pass. (No new tests needed for routing — covered by E2E.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/LoginPage.tsx \
        frontend/src/pages/RegisterPage.tsx
git commit -m "feat: add /documents route; redirect post-auth to upload page"
```

---

## Task 15: DebtsStep — show "From scan" badge on draft entries

**Files:**

- Modify: `frontend/src/components/wizard/steps/DebtsStep.tsx`

- [ ] **Step 1: Locate where debt rows are rendered**

In `DebtsStep.tsx`, find the JSX that renders individual debt entries (the
component maps over `debts` state and renders a form row per entry). Look for
the `creditor_name` input — the badge goes near the row label.

- [ ] **Step 2: Add badge to draft entries**

In the debt row render, add a conditional badge next to the creditor name
label. Locate the element rendering each debt's header/label and add:

```tsx
{
  debt.is_draft && (
    <span
      aria-label="Pre-filled from document scan"
      style={{
        fontSize: '0.75rem',
        background: '#dbeafe',
        color: '#1d4ed8',
        borderRadius: 4,
        padding: '0 6px',
        marginLeft: 8,
        verticalAlign: 'middle',
      }}
    >
      From scan
    </span>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors (since `is_draft` was added to `DebtInfo` in Task 11).

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend && npm test
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/wizard/steps/DebtsStep.tsx
git commit -m "feat: show 'From scan' badge on draft DebtInfo entries in Debts step"
```

---

## Final verification

- [ ] **Run full backend test suite**

```bash
cd backend && python -m pytest -q
```

Expected: all tests pass.

- [ ] **Run full frontend test suite**

```bash
cd frontend && npm test
```

Expected: all tests pass.

- [ ] **Remove ClarifaiOCRProvider**

```bash
git rm backend/apps/documents/services/providers/clarifai.py
git commit -m "chore: remove ClarifaiOCRProvider (replaced by LlamaCppProvider)"
```
