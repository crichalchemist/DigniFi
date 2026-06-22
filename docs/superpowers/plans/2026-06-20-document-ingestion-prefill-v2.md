# Document Ingestion Prefill v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Swap LlamaCppProvider for GeminiProvider, enable opendataloader-pdf hybrid OCR, add credit report multi-tradeline extraction, capture paystub employer name, and wire `is_draft`/`source_document_name` to the frontend debt badge.

**Architecture:** Drop-in provider swap via `BaseOCRProvider` interface — `GeminiProvider` replaces `LlamaCppProvider` with no changes to `DocumentProcessor` internals. The `odl-hybrid` Docker service replaces `llm`. `CreditReportExtraction` + `DraftDebtCreator.create_from_credit_report()` handles N tradelines. The existing `IngestedAggregate`/`AggregateIngestionService`/FillResolver pipeline (already implemented) is extended for `paystub.employer_name`. `DebtInfoSerializer` exposes `is_draft` and `source_document_name` to the already-present frontend badge.

**Tech Stack:** Python 3.11 · Django 5 + DRF · `google-genai>=0.8` SDK · `opendataloader-pdf[hybrid]` · React 19 · TypeScript · vitest + MSW

## Global Constraints

- Provider model: `gemini-2.0-flash` (free tier 1,500 req/day, 15 RPM — upgrade = env var swap, no code change)
- New env var: `GEMINI_API_KEY`. Removed: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`
- Backend tests: `docker compose exec backend python -m pytest` — uses `config.settings.test` (sqlite `:memory:`)
- Frontend tests: `cd frontend && npm test -- --run` (vitest)
- `DebtInfo.is_draft` (BooleanField default=False) and `source_document` FK **already exist** on the model — **no migration needed**
- `IngestedAggregate`, `AggregateIngestionService`, and FillResolver `ingested` source branch are **already implemented** — do NOT re-add them; only extend `_calc_paystubs()` for employer_name
- `is_draft?: boolean` and `source_document?: number | null` **already exist** in `frontend/src/types/api.ts` — only add `source_document_name`
- DebtsStep `is_draft` badge **already exists** at `DebtsStep.tsx:195-199` (`<span className="draft-badge">From scan</span>`) — only tests need adding; badge text stays "From scan" (not "Imported" as spec says)
- UPL: no user-facing copy changes in this spec
- All test files run from repo root via docker compose exec

---

## File Change Map

| File                                                                | Action                                                                                               | Task   |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------ |
| `docker-compose.yml`                                                | Remove `llm` service; add `odl-hybrid`; update `backend.depends_on`                                  | T1     |
| `backend/requirements/base.txt`                                     | Remove `openai`; add `google-genai>=0.8`; change `opendataloader-pdf` → `opendataloader-pdf[hybrid]` | T1     |
| `backend/apps/documents/services/providers/gemini.py`               | **New** — `GeminiProvider(BaseOCRProvider)`                                                          | T2     |
| `backend/apps/documents/services/providers/llama_cpp.py`            | **Delete**                                                                                           | T2     |
| `backend/apps/documents/tests/test_gemini_provider.py`              | **New** — replaces `test_llama_cpp_provider.py`                                                      | T2     |
| `backend/apps/documents/tests/test_llama_cpp_provider.py`           | **Delete**                                                                                           | T2     |
| `backend/apps/documents/views.py`                                   | `_get_processor()` → `GeminiProvider`; CREDIT_REPORT dispatch in `_run_processing`                   | T3, T4 |
| `backend/apps/documents/services/processor.py`                      | Add `hybrid="docling-fast"` to `convert()` call                                                      | T3     |
| `backend/apps/documents/schemas/credit_report.py`                   | **New** — `TradelineItem`, `CreditReportExtraction`                                                  | T4     |
| `backend/apps/documents/schemas/registry.py`                        | Register `CreditReportExtraction` for `CREDIT_REPORT`                                                | T4     |
| `backend/apps/documents/services/draft_debt.py`                     | Add `create_from_credit_report()`; two new static helper methods                                     | T4     |
| `backend/apps/documents/tests/test_draft_debt.py`                   | Extend — add credit report test class                                                                | T4     |
| `backend/apps/documents/services/aggregator.py`                     | Add `paystub.employer_name` capture in `_calc_paystubs()`                                            | T5     |
| `data/forms/schemas/schedule_i.json`                                | `Employers Name Debtor 1`: change to `source: "ingested"` + `ingest_key: "paystub.employer_name"`    | T5     |
| `backend/apps/intake/serializers.py`                                | `DebtInfoSerializer`: add `is_draft` to fields; add `source_document_name` SerializerMethodField     | T5     |
| `backend/apps/documents/tests/test_aggregator.py`                   | Extend — add employer_name test                                                                      | T5     |
| `frontend/src/types/api.ts`                                         | `DebtInfo`: add `source_document_name: string \| null`                                               | T6     |
| `frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx` | **New** — badge render + edit-draft-debt tests                                                       | T6     |

---

### Task 1: Infrastructure Swap + Dependencies

**Files:**

- Modify: `docker-compose.yml`
- Modify: `backend/requirements/base.txt`

**Interfaces:**

- Produces: `odl-hybrid` service at port 5002; `google-genai` importable in backend container; `opendataloader-pdf[hybrid]` importable

- [ ] **Step 1: Swap docker-compose services**

In `docker-compose.yml`, remove the entire `llm:` service block (including the `models:` named volume if it's only used by `llm`). Replace with:

```yaml
odl-hybrid:
  image: ghcr.io/opendataloader-project/opendataloader-pdf:latest
  command: opendataloader-pdf-hybrid --port 5002 --force-ocr
  ports:
    - '5002:5002'
  healthcheck:
    test: ['CMD', 'curl', '-f', 'http://localhost:5002/health']
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 60s
```

In the `backend:` service `depends_on:` block, replace:

```yaml
llm:
  condition: service_healthy
```

with:

```yaml
odl-hybrid:
  condition: service_healthy
```

- [ ] **Step 2: Update Python dependencies**

In `backend/requirements/base.txt`:

Remove this line:

```
openai
```

Change this line:

```
opendataloader-pdf
```

to:

```
opendataloader-pdf[hybrid]
```

Add this line (after the other document-processing deps):

```
google-genai>=0.8
```

- [ ] **Step 3: Verify compose config parses**

```bash
docker compose config --quiet
```

Expected: exit 0, no YAML errors.

- [ ] **Step 4: Add GEMINI_API_KEY to .env (local dev)**

Append to `.env` (not committed — it's gitignored):

```
GEMINI_API_KEY=your-key-here
```

Remove (or comment out) the old LLM vars if present:

```
# LLM_BASE_URL=http://llm:8080/v1
# LLM_API_KEY=not-required
# LLM_MODEL=gemma-3-4b-it
```

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml backend/requirements/base.txt
git commit -m "feat(infra): swap llm service for odl-hybrid, add google-genai dep"
```

---

### Task 2: GeminiProvider

**Files:**

- Create: `backend/apps/documents/services/providers/gemini.py`
- Create: `backend/apps/documents/tests/test_gemini_provider.py`
- Delete: `backend/apps/documents/services/providers/llama_cpp.py`
- Delete: `backend/apps/documents/tests/test_llama_cpp_provider.py`

**Interfaces:**

- Consumes: `BaseOCRProvider` from `apps.documents.services.providers.base`
- Produces: `GeminiProvider(model="gemini-2.0-flash")` with `.classify(image_data, prompt) -> str` and `.extract(image_data, prompt) -> str`

- [ ] **Step 1: Write the failing tests**

Create `backend/apps/documents/tests/test_gemini_provider.py`:

```python
"""Unit tests for GeminiProvider."""
import os
from unittest.mock import MagicMock, patch

import pytest

from apps.documents.services.providers.gemini import GeminiProvider


@pytest.fixture
def mock_genai_client():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.gemini.genai") as mock_genai:
            mock_response = MagicMock()
            mock_response.text = '{"document_type": "pay_stub"}'
            mock_genai.Client.return_value.models.generate_content.return_value = mock_response
            yield mock_genai.Client.return_value


@pytest.fixture
def provider(mock_genai_client):
    return GeminiProvider()


class TestGeminiProviderClassify:
    def test_text_mode_when_no_image(self, provider, mock_genai_client):
        result = provider.classify(b"", "Is this a pay stub?")
        call_args = mock_genai_client.models.generate_content.call_args
        assert call_args.kwargs["contents"] == "Is this a pay stub?"
        assert call_args.kwargs.get("config") is None
        assert result == '{"document_type": "pay_stub"}'

    def test_vision_mode_when_image_provided(self, provider, mock_genai_client):
        provider.classify(b"\xff\xd8\xff", "Classify this document")
        call_args = mock_genai_client.models.generate_content.call_args
        contents = call_args.kwargs["contents"]
        assert isinstance(contents, list)
        assert len(contents) == 2

    def test_no_json_mime_type_on_classify(self, provider, mock_genai_client):
        provider.classify(b"", "Classify")
        call_args = mock_genai_client.models.generate_content.call_args
        assert call_args.kwargs.get("config") is None


class TestGeminiProviderExtract:
    def test_text_mode_sets_json_mime(self, provider, mock_genai_client):
        from google.genai import types

        provider.extract(b"", "Extract fields")
        call_args = mock_genai_client.models.generate_content.call_args
        config = call_args.kwargs.get("config")
        assert config is not None
        assert config.response_mime_type == "application/json"

    def test_vision_mode_sets_json_mime(self, provider, mock_genai_client):
        from google.genai import types

        provider.extract(b"\xff\xd8\xff", "Extract fields from image")
        call_args = mock_genai_client.models.generate_content.call_args
        config = call_args.kwargs.get("config")
        assert config is not None
        assert config.response_mime_type == "application/json"

    def test_returns_empty_string_on_none_response(self, mock_genai_client):
        mock_genai_client.models.generate_content.return_value.text = None
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("apps.documents.services.providers.gemini.genai") as mock_g:
                mock_g.Client.return_value = mock_genai_client
                p = GeminiProvider()
        result = p.extract(b"", "Extract")
        assert result == ""

    def test_vision_mode_passes_image_part_first(self, provider, mock_genai_client):
        provider.extract(b"\xff\xd8\xff", "Extract")
        call_args = mock_genai_client.models.generate_content.call_args
        contents = call_args.kwargs["contents"]
        assert isinstance(contents, list)
        # first element is the image Part, second is the prompt string
        assert isinstance(contents[1], str)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend python -m pytest apps/documents/tests/test_gemini_provider.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.documents.services.providers.gemini'`

- [ ] **Step 3: Create `gemini.py`**

Create `backend/apps/documents/services/providers/gemini.py`:

```python
"""Google Gemini provider for document OCR via google-genai SDK."""
import os

from google import genai
from google.genai import types

from .base import BaseOCRProvider


class GeminiProvider(BaseOCRProvider):
    """
    Gemini vision/text provider.

    Uses text mode (opendataloader-pdf extracted markdown → prompt) when image_data is empty.
    Uses vision mode (pymupdf JPEG or direct image upload) when image_data is non-empty.
    extract() sets response_mime_type="application/json" for reliable structured output.
    """

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def classify(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision(image_data, prompt)
        return self._text(prompt)

    def extract(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision(image_data, prompt, json_mode=True)
        return self._text(prompt, json_mode=True)

    def _text(self, prompt: str, *, json_mode: bool = False) -> str:
        config = (
            types.GenerateContentConfig(response_mime_type="application/json")
            if json_mode
            else None
        )
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    def _vision(self, image_data: bytes, prompt: str, *, json_mode: bool = False) -> str:
        config = (
            types.GenerateContentConfig(response_mime_type="application/json")
            if json_mode
            else None
        )
        image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
        response = self._client.models.generate_content(
            model=self.model,
            contents=[image_part, prompt],
            config=config,
        )
        return response.text or ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend python -m pytest apps/documents/tests/test_gemini_provider.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Delete llama_cpp files**

```bash
rm backend/apps/documents/services/providers/llama_cpp.py
rm backend/apps/documents/tests/test_llama_cpp_provider.py
```

- [ ] **Step 6: Run full document tests to catch any stale import**

```bash
docker compose exec backend python -m pytest apps/documents/ -v
```

Expected: all tests PASS; `test_llama_cpp_provider.py` no longer collected.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/documents/services/providers/gemini.py \
        backend/apps/documents/tests/test_gemini_provider.py
git rm backend/apps/documents/services/providers/llama_cpp.py \
       backend/apps/documents/tests/test_llama_cpp_provider.py
git commit -m "feat(documents): add GeminiProvider, remove LlamaCppProvider"
```

---

### Task 3: Wire GeminiProvider + Hybrid Param

**Files:**

- Modify: `backend/apps/documents/views.py` (lines 16, 25–29)
- Modify: `backend/apps/documents/services/processor.py` (line 82)

**Interfaces:**

- Consumes: `GeminiProvider` from Task 2
- Produces: `_get_processor()` returns `DocumentProcessor(provider=GeminiProvider())`; `processor.py` passes `hybrid="docling-fast"` to `opendataloader_pdf.convert()`

- [ ] **Step 1: Identify exact lines to change in views.py**

```bash
grep -n 'LlamaCppProvider\|from apps.documents.services.providers' backend/apps/documents/views.py
```

Expected output (verify line numbers match before editing):

```
16:from apps.documents.services.providers.llama_cpp import LlamaCppProvider
```

- [ ] **Step 2: Replace the import and `_get_processor` body in views.py**

In `backend/apps/documents/views.py`:

Change line 16 from:

```python
from apps.documents.services.providers.llama_cpp import LlamaCppProvider
```

to:

```python
from apps.documents.services.providers.gemini import GeminiProvider
```

Change the `_get_processor` function body (lines 24–30). Before:

```python
def _get_processor() -> DocumentProcessor:
    provider = LlamaCppProvider(
        base_url=settings.LLM_BASE_URL,
        api_key=getattr(settings, "LLM_API_KEY", "not-required"),
        model=getattr(settings, "LLM_MODEL", "gemma-3-4b-it"),
    )
    return DocumentProcessor(provider=provider)
```

After (remove all LLM\_\* settings references):

```python
def _get_processor() -> DocumentProcessor:
    return DocumentProcessor(provider=GeminiProvider())
```

(The exact lines 25–29 may differ slightly — read the current file before editing. The goal: create `GeminiProvider()` with no arguments; it reads `GEMINI_API_KEY` from env.)

- [ ] **Step 3: Add `hybrid` parameter to processor.py**

In `backend/apps/documents/services/processor.py`, find the `opendataloader_pdf.convert(` call (around line 82). It looks like:

```python
opendataloader_pdf.convert(
    input_path=str(input_path),
    output_dir=str(output_dir),
    format="markdown",
)
```

Add `hybrid="docling-fast"`:

```python
opendataloader_pdf.convert(
    input_path=str(input_path),
    output_dir=str(output_dir),
    format="markdown",
    hybrid="docling-fast",
)
```

- [ ] **Step 4: Run the existing processor + views tests**

```bash
docker compose exec backend python -m pytest apps/documents/tests/test_processor.py apps/documents/tests/test_views.py -v
```

Expected: all existing tests PASS. (Tests mock `DocumentProcessor` and `opendataloader_pdf`, so the new `hybrid` kwarg is transparent to them.)

- [ ] **Step 5: Commit**

```bash
git add backend/apps/documents/views.py backend/apps/documents/services/processor.py
git commit -m "feat(documents): wire GeminiProvider into DocumentProcessor, enable odl hybrid"
```

---

### Task 4: CreditReportExtraction + DraftDebtCreator

**Files:**

- Create: `backend/apps/documents/schemas/credit_report.py`
- Modify: `backend/apps/documents/schemas/registry.py`
- Modify: `backend/apps/documents/services/draft_debt.py`
- Modify: `backend/apps/documents/views.py`
- Modify: `backend/apps/documents/tests/test_draft_debt.py`

**Interfaces:**

- Consumes: `BaseExtractionSchema` from `apps.documents.schemas.base`; `DocumentType.CREDIT_REPORT`; `DebtInfo` model
- Produces: `CreditReportExtraction` registered in SCHEMA_REGISTRY; `DraftDebtCreator.create_from_credit_report(result, session, source_document) -> list[DebtInfo]`; views.py dispatches CREDIT_REPORT type

- [ ] **Step 1: Write the failing tests**

Extend `backend/apps/documents/tests/test_draft_debt.py`. Append after the existing test classes:

```python
# Add imports at top of file (after existing imports):
# from decimal import Decimal
# from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem


class TestDraftDebtCreatorCreditReport:
    """Tests for multi-tradeline credit report extraction."""

    def test_creates_one_debt_per_nonzero_tradeline(self, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem
        from apps.documents.services.draft_debt import DraftDebtCreator

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Chase Bank",
                    account_number="****1234",
                    amount_owed=Decimal("5000.00"),
                    account_type="credit_card",
                    account_status="open",
                ),
                TradelineItem(
                    creditor_name="Paid Off LLC",
                    account_number=None,
                    amount_owed=Decimal("0"),
                    account_type="other",
                    account_status="closed",
                ),
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)

        assert len(debts) == 1
        assert debts[0].creditor_name == "Chase Bank"
        assert debts[0].is_draft is True
        assert debts[0].source_document == uploaded_doc
        assert debts[0].session == session

    def test_skips_zero_balance_tradelines(self, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem
        from apps.documents.services.draft_debt import DraftDebtCreator

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Zero Balance",
                    account_number=None,
                    amount_owed=Decimal("0"),
                    account_type="credit_card",
                    account_status="closed",
                )
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts == []

    def test_empty_tradelines_returns_empty_list(self, session, uploaded_doc):
        from apps.documents.schemas.credit_report import CreditReportExtraction
        from apps.documents.services.draft_debt import DraftDebtCreator

        result = CreditReportExtraction(tradelines=[])
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts == []

    def test_maps_account_type_to_debt_type(self, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem
        from apps.documents.services.draft_debt import DraftDebtCreator

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Auto Dealer",
                    account_number=None,
                    amount_owed=Decimal("12000.00"),
                    account_type="auto_loan",
                    account_status="open",
                )
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts[0].debt_type == "auto_loan"
        assert debts[0].is_secured is True

    def test_accepts_masked_account_numbers(self, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem
        from apps.documents.services.draft_debt import DraftDebtCreator

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Citi",
                    account_number="****9999",
                    amount_owed=Decimal("3500.00"),
                    account_type="credit_card",
                    account_status="open",
                )
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts[0].account_number == "****9999"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend python -m pytest apps/documents/tests/test_draft_debt.py::TestDraftDebtCreatorCreditReport -v
```

Expected: `ImportError: cannot import name 'CreditReportExtraction'`

- [ ] **Step 3: Create `credit_report.py` schema**

Create `backend/apps/documents/schemas/credit_report.py`:

```python
"""Credit report extraction schema — one tradeline per account."""
from decimal import Decimal

from pydantic import BaseModel

from .base import BaseExtractionSchema


class TradelineItem(BaseModel):
    creditor_name: str
    account_number: str | None = None
    amount_owed: Decimal
    account_type: str  # credit_card | auto_loan | student_loan | mortgage | medical | personal_loan | other
    account_status: str  # open | closed | charged_off | in_collections | delinquent
    credit_limit: Decimal | None = None


class CreditReportExtraction(BaseExtractionSchema):
    tradelines: list[TradelineItem]
```

- [ ] **Step 4: Register schema in registry.py**

In `backend/apps/documents/schemas/registry.py`, add the import and registry entry for `CREDIT_REPORT`. Find the `SCHEMA_REGISTRY` dict and add:

```python
from apps.documents.schemas.credit_report import CreditReportExtraction

# In SCHEMA_REGISTRY:
DocumentType.CREDIT_REPORT: CreditReportExtraction,
```

(Read the file first to see the exact dict structure; follow the pattern of the existing entries.)

- [ ] **Step 5: Extend DraftDebtCreator**

In `backend/apps/documents/services/draft_debt.py`, add the following method and two static helpers to the `DraftDebtCreator` class:

```python
def create_from_credit_report(
    self, result: "CreditReportExtraction", session, source_document
) -> list:
    """Create draft DebtInfo records from each non-zero tradeline."""
    from apps.intake.models import DebtInfo

    created = []
    for tradeline in result.tradelines:
        if tradeline.amount_owed == 0:
            continue
        debt = DebtInfo.objects.create(
            session=session,
            source_document=source_document,
            is_draft=True,
            creditor_name=tradeline.creditor_name,
            account_number=tradeline.account_number or "",
            amount_owed=tradeline.amount_owed,
            debt_type=self._map_account_type(tradeline.account_type),
            is_secured=tradeline.account_type in ("auto_loan", "mortgage"),
            priority_classification=self._priority_for_type(tradeline.account_type),
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
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
docker compose exec backend python -m pytest apps/documents/tests/test_draft_debt.py -v
```

Expected: all tests PASS including new `TestDraftDebtCreatorCreditReport` class.

- [ ] **Step 7: Add CREDIT_REPORT dispatch in views.py**

In `backend/apps/documents/views.py`, find the section in `_run_processing` around line 57 that currently reads:

```python
                    DraftDebtCreator().create_from_result(result, doc.session, doc)
```

This is inside an `if result.detected_type == DocumentType.CREDITOR_BILL:` block (or similar). Add the `CREDIT_REPORT` branch immediately after:

```python
                if result.detected_type == DocumentType.CREDITOR_BILL:
                    try:
                        DraftDebtCreator().create_from_result(result, doc.session, doc)
                    except Exception as exc:
                        logger.warning("DraftDebtCreator failed for doc %s: %s", doc_id, exc)
                elif result.detected_type == DocumentType.CREDIT_REPORT:
                    try:
                        from apps.documents.schemas.credit_report import CreditReportExtraction

                        schema_obj = CreditReportExtraction.model_validate_json(
                            result.extracted_data
                        )
                        DraftDebtCreator().create_from_credit_report(schema_obj, doc.session, doc)
                    except Exception as exc:
                        logger.warning(
                            "DraftDebtCreator (credit report) failed for doc %s: %s", doc_id, exc
                        )
```

(Read `views.py` around line 55–65 to see the exact existing structure before editing.)

- [ ] **Step 8: Run full document test suite**

```bash
docker compose exec backend python -m pytest apps/documents/ -v
```

Expected: all tests PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/apps/documents/schemas/credit_report.py \
        backend/apps/documents/schemas/registry.py \
        backend/apps/documents/services/draft_debt.py \
        backend/apps/documents/views.py \
        backend/apps/documents/tests/test_draft_debt.py
git commit -m "feat(documents): add CreditReportExtraction schema and multi-tradeline DraftDebtCreator"
```

---

### Task 5: Aggregator employer_name + Schedule I Wiring + DebtInfoSerializer

**Files:**

- Modify: `backend/apps/documents/services/aggregator.py`
- Modify: `data/forms/schemas/schedule_i.json`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/documents/tests/test_aggregator.py`

**Interfaces:**

- Consumes: `PayStubExtraction.employer_name` (already on the schema); `IngestedAggregate` (already exists); `DebtInfo.source_document` FK (already exists)
- Produces: `IngestedAggregate(ingest_key="paystub.employer_name")` written after each recalculate; `DebtInfoSerializer` exposes `is_draft: bool` and `source_document_name: str | null`

- [ ] **Step 1: Write the failing aggregator test**

In `backend/apps/documents/tests/test_aggregator.py`, add a new test method to the existing `TestAggregateIngestionService` class:

```python
def test_captures_employer_name_from_most_recent_stub(self):
    """Employer name comes from the paystub with the latest pay_period_end."""
    import json
    from apps.documents.models import (
        DocumentType, IngestedAggregate, OCRResult, OCRStatus, UploadedDocument,
    )
    from apps.documents.services.aggregator import AggregateIngestionService
    from apps.intake.models import IntakeSession
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user("emptest", "emp@test.com", "pass")
    session = IntakeSession.objects.create(user=user)

    for i, (employer, start, end) in enumerate([
        ("Old Job", "2026-01-01", "2026-01-15"),
        ("New Job", "2026-02-01", "2026-02-15"),
    ]):
        doc = UploadedDocument.objects.create(
            session=session,
            uploaded_by=user,
            document_type=DocumentType.PAY_STUB,
            file=f"stub{i}.pdf",
            original_filename=f"stub{i}.pdf",
            file_size=100,
            mime_type="application/pdf",
        )
        OCRResult.objects.create(
            document=doc,
            status=OCRStatus.COMPLETED,
            extracted_data=json.dumps({
                "employer_name": employer,
                "gross_pay": "1000.00",
                "pay_period_start": start,
                "pay_period_end": end,
            }),
            overall_confidence=0.9,
            confidence_scores={},
        )

    AggregateIngestionService.recalculate(session.id)

    agg = IngestedAggregate.objects.get(session=session, ingest_key="paystub.employer_name")
    assert agg.value == "New Job"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec backend python -m pytest apps/documents/tests/test_aggregator.py::TestAggregateIngestionService::test_captures_employer_name_from_most_recent_stub -v
```

Expected: FAIL — `IngestedAggregate matching query does not exist`

- [ ] **Step 3: Read the current `_calc_paystubs` method**

```bash
grep -n '_calc_paystubs\|employer_name\|ingest_key\|update_or_create' backend/apps/documents/services/aggregator.py
```

Read the full `_calc_paystubs` method body to understand the current loop structure before editing.

- [ ] **Step 4: Add employer_name tracking to `_calc_paystubs`**

In `backend/apps/documents/services/aggregator.py`, inside `_calc_paystubs`, you'll find a loop over `results` that accumulates `total_monthly_gross`. Add employer_name tracking alongside it.

Find the variable that tracks daily gross per stub and the loop body. Add:

```python
# After initializing total_monthly_gross and valid_stubs, add:
most_recent_end: str | None = None
most_recent_employer: str = ""

# Inside the loop, after parsing each PayStubExtraction (call it `stub`):
# Add after the existing daily_gross / monthly_gross calculation:
if most_recent_end is None or stub.pay_period_end > most_recent_end:
    most_recent_end = stub.pay_period_end
    most_recent_employer = stub.employer_name or ""
```

Then after the `update_or_create` call for `paystub.gross`, add:

```python
IngestedAggregate.objects.update_or_create(
    session_id=session_id,
    ingest_key="paystub.employer_name",
    defaults={"value": most_recent_employer},
)
```

Also add the `paystub.employer_name` deletion in the else branch (when no PAY_STUB results exist):

```python
else:
    IngestedAggregate.objects.filter(
        session_id=session_id, ingest_key__startswith="paystub."
    ).delete()
```

(This likely already deletes `paystub.gross` — verify it uses `ingest_key__startswith="paystub."` which will cover employer_name too. If it uses `ingest_key="paystub.gross"` exactly, change to `ingest_key__startswith="paystub."`)

- [ ] **Step 5: Run the aggregator tests**

```bash
docker compose exec backend python -m pytest apps/documents/tests/test_aggregator.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Wire schedule_i.json employer name field to ingested source**

First, confirm the exact JSON structure of the employer name field:

```bash
python3 -c "
import json
data = json.load(open('data/forms/schemas/schedule_i.json'))
for f in data['fields']:
    if f.get('pdf_field') == 'Employers Name Debtor 1':
        import pprint; pprint.pprint(f)
"
```

Then update that field. The change: remove the `rule` key, change `source` to `"ingested"`, add `ingest_key: "paystub.employer_name"`.

Edit `data/forms/schemas/schedule_i.json` — find the `"Employers Name Debtor 1"` field object and update it from:

```json
{
  "pdf_field": "Employers Name Debtor 1",
  "source": "derived",
  "rule": "schedule_i_employer_debtor1",
  "ingest_key": null
}
```

to:

```json
{
  "pdf_field": "Employers Name Debtor 1",
  "source": "ingested",
  "ingest_key": "paystub.employer_name"
}
```

Note: leave the employer address fields (`Employers Street1 Debtor 1`, `Employers City Debtor 1`, etc.) as-is — these are not wired to ingested in this spec. Monthly gross income wiring was out of scope: no PDF field matching "gross" or "income" exists in schedule_i.json under those search terms. Defer to follow-up investigation.

- [ ] **Step 7: Write the failing serializer test**

Add to `backend/apps/intake/tests/` (find the existing serializer test file or `test_views.py`). Search first:

```bash
grep -rn 'DebtInfoSerializer\|source_document_name' backend/apps/intake/tests/
```

Add to an appropriate existing test file:

```python
class TestDebtInfoSerializerDraftFields(TestCase):
    """Verify is_draft and source_document_name appear in serialized output."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.documents.models import DocumentType, UploadedDocument
        from apps.intake.models import DebtInfo, IntakeSession

        User = get_user_model()
        user = User.objects.create_user("stest", "s@test.com", "pass")
        self.session = IntakeSession.objects.create(user=user)
        self.doc = UploadedDocument.objects.create(
            session=self.session,
            uploaded_by=user,
            document_type=DocumentType.CREDITOR_BILL,
            file="bill.pdf",
            original_filename="Chase_bill.pdf",
            file_size=100,
            mime_type="application/pdf",
        )
        self.debt = DebtInfo.objects.create(
            session=self.session,
            source_document=self.doc,
            is_draft=True,
            creditor_name="Chase",
            account_number="",
            amount_owed="5000.00",
            debt_type="credit_card",
            is_secured=False,
        )

    def test_is_draft_included_and_true(self):
        from apps.intake.serializers import DebtInfoSerializer
        data = DebtInfoSerializer(self.debt).data
        assert data["is_draft"] is True

    def test_source_document_name_included(self):
        from apps.intake.serializers import DebtInfoSerializer
        data = DebtInfoSerializer(self.debt).data
        assert data["source_document_name"] == "Chase_bill.pdf"

    def test_source_document_name_none_when_no_document(self):
        from apps.intake.models import DebtInfo
        from apps.intake.serializers import DebtInfoSerializer
        debt = DebtInfo.objects.create(
            session=self.session,
            creditor_name="Manual",
            account_number="",
            amount_owed="1000.00",
            debt_type="other",
            is_secured=False,
        )
        data = DebtInfoSerializer(debt).data
        assert data["source_document_name"] is None
```

- [ ] **Step 8: Run serializer tests to verify they fail**

```bash
docker compose exec backend python -m pytest -k "TestDebtInfoSerializerDraftFields" -v
```

Expected: FAIL — `KeyError: 'is_draft'` or `KeyError: 'source_document_name'`

- [ ] **Step 9: Update DebtInfoSerializer**

In `backend/apps/intake/serializers.py`, find `DebtInfoSerializer`. Add `source_document_name` as a `SerializerMethodField` and add both fields to `Meta.fields`:

```python
class DebtInfoSerializer(serializers.ModelSerializer):
    source_document_name = serializers.SerializerMethodField()

    class Meta:
        model = DebtInfo
        fields = [
            # ... existing fields ...
            "is_draft",
            "source_document_name",
        ]
        read_only_fields = [
            # ... existing read_only_fields ...
            "is_draft",
            "source_document_name",
        ]

    def get_source_document_name(self, obj) -> str | None:
        if obj.source_document:
            return obj.source_document.original_filename
        return None
```

(Read the existing serializer before editing to see the current `fields` list and add the two new entries at the end.)

- [ ] **Step 10: Run serializer + full intake tests**

```bash
docker compose exec backend python -m pytest apps/intake/ apps/documents/tests/test_aggregator.py -v
```

Expected: all tests PASS.

- [ ] **Step 11: Commit**

```bash
git add backend/apps/documents/services/aggregator.py \
        data/forms/schemas/schedule_i.json \
        backend/apps/intake/serializers.py \
        backend/apps/documents/tests/test_aggregator.py \
        backend/apps/intake/tests/
git commit -m "feat(documents): capture paystub employer_name, expose is_draft in DebtInfoSerializer"
```

---

### Task 6: Frontend DebtsStep Tests

**Files:**

- Modify: `frontend/src/types/api.ts`
- Create: `frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx`

**Interfaces:**

- Consumes: `DebtsStep` component (badge at line 195 already implemented); `DebtInfo` interface
- Produces: `source_document_name: string | null` on the `DebtInfo` interface; test coverage for the badge

- [ ] **Step 1: Add `source_document_name` to `DebtInfo` interface**

In `frontend/src/types/api.ts`, find the `DebtInfo` interface (line 146). The `// Document scanning` comment block currently has:

```typescript
  // Document scanning
  is_draft?: boolean;
  source_document?: number | null;
```

Add `source_document_name` after:

```typescript
  // Document scanning
  is_draft?: boolean;
  source_document?: number | null;
  source_document_name?: string | null;
```

- [ ] **Step 2: Write the failing tests**

Create `frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { DebtsStep } from '../DebtsStep';
import type { DebtInfo } from '../../../../types/api';

const baseDebt: Partial<DebtInfo> = {
  id: 1,
  session: 1,
  debt_type: 'credit_card',
  creditor_name: 'Chase Bank',
  account_number: '****1234',
  amount_owed: 5000,
  monthly_payment: 0,
  is_secured: false,
  collateral_description: '',
};

describe('DebtsStep', () => {
  it('renders draft badge on debts with is_draft=true', () => {
    const draftDebt: Partial<DebtInfo> = {
      ...baseDebt,
      is_draft: true,
      source_document_name: 'Chase_bill.pdf',
    };

    render(
      <DebtsStep
        initialData={[draftDebt]}
        onDataChange={vi.fn()}
        onValidationChange={vi.fn()}
      />
    );

    expect(screen.getByText('From scan')).toBeInTheDocument();
  });

  it('does not render draft badge on manually entered debts', () => {
    render(
      <DebtsStep
        initialData={[baseDebt]}
        onDataChange={vi.fn()}
        onValidationChange={vi.fn()}
      />
    );

    expect(screen.queryByText('From scan')).not.toBeInTheDocument();
  });

  it('renders badge with aria-label for screen readers', () => {
    const draftDebt: Partial<DebtInfo> = { ...baseDebt, is_draft: true };

    render(
      <DebtsStep
        initialData={[draftDebt]}
        onDataChange={vi.fn()}
        onValidationChange={vi.fn()}
      />
    );

    expect(
      screen.getByRole('generic', { name: /pre-filled from document scan/i })
    ).toBeInTheDocument();
  });

  it('still renders edit controls on draft debts', () => {
    const draftDebt: Partial<DebtInfo> = { ...baseDebt, is_draft: true };

    render(
      <DebtsStep
        initialData={[draftDebt]}
        onDataChange={vi.fn()}
        onValidationChange={vi.fn()}
      />
    );

    // The creditor_name field should be editable
    expect(
      screen.getByDisplayValue('Chase Bank')
    ).toBeInTheDocument();
  });

  it('renders badge on each draft debt in a mixed list', () => {
    const manualDebt: Partial<DebtInfo> = { ...baseDebt, id: 2, creditor_name: 'Manual Citi' };
    const draftDebt: Partial<DebtInfo> = {
      ...baseDebt,
      id: 3,
      creditor_name: 'Scanned Wells Fargo',
      is_draft: true,
    };

    render(
      <DebtsStep
        initialData={[manualDebt, draftDebt]}
        onDataChange={vi.fn()}
        onValidationChange={vi.fn()}
      />
    );

    // Only one badge
    expect(screen.getAllByText('From scan')).toHaveLength(1);
  });
});
```

- [ ] **Step 3: Run tests to verify they fail (or catch type errors)**

```bash
cd frontend && npm test -- --run DebtsStep
```

Expected: Some tests FAIL or type errors if `source_document_name` isn't on `DebtInfo` yet. After Step 1 is done, expected failures would be component rendering failures only.

- [ ] **Step 4: Run tests to verify they pass**

The badge implementation already exists at `DebtsStep.tsx:195-199`. After adding `source_document_name` to the type, all tests should pass without any component changes.

```bash
cd frontend && npm test -- --run DebtsStep
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run full frontend test suite to check for regressions**

```bash
cd frontend && npm test -- --run
```

Expected: all 171+ tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/api.ts \
        frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx
git commit -m "test(frontend): add DebtsStep badge tests, add source_document_name to DebtInfo type"
```

---

## Self-Review Checklist

Spec coverage check against `docs/superpowers/specs/2026-06-20-document-ingestion-prefill-v2-design.md`:

| Spec Section                                                              | Covered by Task                                      |
| ------------------------------------------------------------------------- | ---------------------------------------------------- |
| S1 Architecture: odl-hybrid replaces llm                                  | T1, T3                                               |
| S1 Architecture: GeminiProvider replaces LlamaCppProvider                 | T2, T3                                               |
| S1 Architecture: CREDIT_REPORT → N DebtInfo                               | T4                                                   |
| S1 Architecture: PAY_STUB → IngestedAggregate (gross already implemented) | T5 (employer_name)                                   |
| S2 Infrastructure: docker-compose swap                                    | T1                                                   |
| S2 Infrastructure: hybrid="docling-fast" in processor                     | T3                                                   |
| S2 Infrastructure: JPEG rendering path preserved                          | No change needed (already preserved)                 |
| S2 Infrastructure: opendataloader-pdf[hybrid] in requirements             | T1                                                   |
| S3 GeminiProvider: text mode / vision mode / json_mode                    | T2                                                   |
| S3 GeminiProvider: response_mime_type="application/json" on extract       | T2                                                   |
| S4 CreditReportExtraction schema                                          | T4                                                   |
| S4 DraftDebtCreator.create_from_credit_report                             | T4                                                   |
| S4 Registry: CREDIT_REPORT → CreditReportExtraction                       | T4                                                   |
| S5 IngestedAggregate model                                                | Already exists — no task needed                      |
| S5 AggregateIngestionService.recalculate                                  | Already exists — no task needed                      |
| S5 employer_name from most-recent stub                                    | T5                                                   |
| S5 FillResolver ingested source                                           | Already exists — no task needed                      |
| S5 Schedule I employer name wiring                                        | T5                                                   |
| S5 Schedule I monthly gross wiring                                        | Deferred — field not found in schema                 |
| S6 DebtInfoSerializer is_draft                                            | T5                                                   |
| S6 DebtInfoSerializer source_document_name                                | T5                                                   |
| S6 Frontend DebtInfo type additions                                       | T6                                                   |
| S6 DebtsStep badge                                                        | Already exists — T6 adds tests                       |
| S7 Error handling: graceful failure paths                                 | Covered by existing try/except in views + aggregator |
| S8 Testing: GeminiProvider mocked tests                                   | T2                                                   |
| S8 Testing: CreditReport schema tests                                     | T4 (via DraftDebtCreator tests)                      |
| S8 Testing: DraftDebtCreator credit report                                | T4                                                   |
| S8 Testing: aggregator employer_name                                      | T5                                                   |
| S8 Testing: Frontend badge                                                | T6                                                   |

**Known deviations from spec:**

1. Badge text is "From scan" not "Imported" (already in codebase; changing is out of scope)
2. Monthly gross income Schedule I wiring deferred — the PDF field name wasn't discoverable via "gross"/"income" keyword search; requires manual inspection of the JSON to find the correct field
3. `is_in_collections` not mapped from `account_status` — field doesn't exist on `DebtInfo` model
