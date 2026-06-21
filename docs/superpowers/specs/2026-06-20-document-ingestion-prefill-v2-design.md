# Document Ingestion Prefill v2 — Design Spec

**Date:** 2026-06-20  
**Status:** Approved, pending implementation

## Overview

Extends the existing document OCR pipeline to:

1. **(Pipeline A) Creditor prefill** — credit reports and creditor bills → `DebtInfo` records with an "Imported" badge appearing pre-populated in DebtsStep
2. **(Pipeline B) Income aggregation** — paystubs → averaged monthly gross → `IngestedAggregate` → Schedule I prefill

Replaces the local llama.cpp LLM service with Google's free Gemini API (`gemini-2.0-flash`) and upgrades `opendataloader-pdf` to use a persistent hybrid server (eliminating per-document JVM spawns). The JPEG rendering path (pymupdf) is preserved for cell phone screenshot uploads.

---

## Section 1 — Architecture Overview

### Before

```
Upload → background thread → DocumentProcessor
  → opendataloader_pdf.convert() [spawns JVM] → markdown text
  → fallback: pymupdf → JPEG → LlamaCppProvider (local llama.cpp) → JSON
  → OCRResult.extracted_data
  → DraftDebtCreator (CREDITOR_BILL only, 1 record)
```

### After

```
Upload → background thread → DocumentProcessor
  → opendataloader_pdf.convert(hybrid="docling-fast") [calls odl-hybrid:5002, --force-ocr]
  → markdown text (handles scanned docs natively via hybrid OCR)
  → GeminiProvider.extract(text, schema) → validated Pydantic object
  → OCRResult.extracted_data (JSON)
  → DraftDebtCreator
      CREDITOR_BILL → 1 DebtInfo (existing)
      CREDIT_REPORT → N DebtInfo (new, one per tradeline)
  → AggregateIngestionService.recalculate()
      PAY_STUB → IngestedAggregate("paystub.gross", averaged_monthly_value)

Direct image upload (cell phone screenshot, JPEG/PNG/WebP):
  → GeminiProvider (vision mode) directly
  → same OCRResult flow

PDF with poor/no text (text below _MIN_TEXT_LENGTH threshold):
  → pymupdf renders page 0 → JPEG → GeminiProvider (vision mode)
```

### Changes Summary

|                | Removed                                    | Added                                     |
| -------------- | ------------------------------------------ | ----------------------------------------- |
| Docker service | `llm` (llama.cpp)                          | `odl-hybrid` (opendataloader-pdf[hybrid]) |
| Provider       | `LlamaCppProvider`                         | `GeminiProvider`                          |
| Env vars       | `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | `GEMINI_API_KEY`                          |
| Schema         | —                                          | `CreditReportExtraction`                  |
| Model          | —                                          | `IngestedAggregate`                       |
| Service        | —                                          | `AggregateIngestionService`               |
| Frontend       | —                                          | "Imported" badge on `is_draft=True` debts |

---

## Section 2 — Infrastructure

### odl-hybrid Docker Service

Replaces the `llm` service in `docker-compose.yml`:

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

Backend `depends_on` updated: replace `llm` with `odl-hybrid`.

The `--force-ocr` flag causes the hybrid server to OCR all PDFs, including scanned image-only documents (hospital bills, photocopied paystubs, court notices). This eliminates most PDF extraction failures without requiring code-level fallback logic.

### processor.py Change

One line: `opendataloader_pdf.convert(..., hybrid="docling-fast")`. The library auto-discovers the hybrid server at `http://odl-hybrid:5002`. No other change to the text extraction path.

### JPEG Rendering Path (Preserved)

The pymupdf → JPEG path remains for two scenarios:

1. **PDF with poor/no embedded text** (`_MIN_TEXT_LENGTH` threshold) — rendered to JPEG, sent to GeminiProvider vision mode
2. **Direct image uploads** (cell phone screenshots, JPEG/PNG/WebP from hospital bills, statements) — sent directly to GeminiProvider vision mode

The `_pdf_to_image_bytes()` function in `processor.py` is unchanged.

### Dockerfile.heroku

`opendataloader-pdf[hybrid]` added to pip dependencies. Java 11+ (`default-jre-headless`) already present per existing Dockerfile. On Heroku, the hybrid server runs as a separate process dyno, mirroring the previous `llm` service pattern.

---

## Section 3 — GeminiProvider

**Location:** `backend/apps/documents/services/providers/gemini.py`

Drop-in replacement for `LlamaCppProvider` via the existing `BaseOCRProvider` interface. `DocumentProcessor._get_processor()` swaps the provider; no other changes to `DocumentProcessor`.

**Dependencies:**

- `google-genai` Python SDK
- `GEMINI_API_KEY` env var
- Model: `gemini-2.0-flash` (free tier: 1,500 req/day, 15 RPM)

**Interface:**

```python
class GeminiProvider(BaseOCRProvider):
    def classify(self, image_data: bytes, prompt: str) -> str:
        # document type detection
        # if image_data: vision mode; else: text-only mode

    def extract(self, image_data: bytes, prompt: str) -> str:
        # structured extraction
        # if image_data: inline bytes + prompt (vision)
        # else: text prompt only
        # always sets response_mime_type="application/json"
```

**Reliability improvement:** `response_mime_type="application/json"` constrains Gemini to return valid JSON, eliminating the freeform JSON parsing brittleness present in the current `_parse_result()`. The safety-net `_parse_result()` remains but should rarely trigger.

**Rate limit handling:** At clinic scale (one filer uploading a handful of documents), the free tier is not a concern. Upgrading to a paid key requires only an env var change — no code changes.

**Removed env vars:** `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.

---

## Section 4 — Credit Report Schema + Multi-Tradeline DraftDebtCreator

### New Schema: `backend/apps/documents/schemas/credit_report.py`

```python
class TradelineItem(BaseModel):
    creditor_name: str
    account_number: str | None          # masked like ****1234 accepted
    amount_owed: Decimal
    account_type: str                   # credit_card | auto_loan | student_loan |
                                        # mortgage | medical | personal_loan | other
    account_status: str                 # open | closed | charged_off |
                                        # in_collections | delinquent
    credit_limit: Decimal | None        # revolving accounts

class CreditReportExtraction(BaseExtractionSchema):
    tradelines: list[TradelineItem]
```

Registered in `schemas/registry.py` for `DocumentType.CREDIT_REPORT`.

Gemini handles Equifax/Experian/TransUnion/Credit Karma layout variance well — LLM extraction outperforms rule-based parsers for this document type.

### DraftDebtCreator Extension

`backend/apps/documents/services/draft_debt.py` gains:

```python
def create_from_credit_report(
    self, result: CreditReportExtraction, session, source_document
) -> list[DebtInfo]:
    # skip tradelines where amount_owed == 0 (paid-off accounts)
    # map account_status in_collections/charged_off → is_in_collections=True
    # create one DebtInfo per remaining tradeline, is_draft=True
```

`create_from_result()` dispatches to this method for `CREDIT_REPORT` type and returns a list. Callers in `views.py` are updated to handle both the single-record and list return shapes.

**Known limitation:** uploading Equifax, Experian, and TransUnion reports separately may produce duplicate entries for the same debt (up to 3×). No auto-dedup in this spec — filers review and delete duplicates in DebtsStep. Acceptable for clinic context.

---

## Section 5 — IngestedAggregate + AggregateIngestionService

### New Model: `IngestedAggregate`

Added to `backend/apps/documents/models.py`:

```python
class IngestedAggregate(models.Model):
    session = models.ForeignKey(IntakeSession, on_delete=models.CASCADE)
    ingest_key = models.CharField(max_length=100)   # e.g., "paystub.gross"
    value = models.CharField(max_length=100)         # Decimal stored as string

    class Meta:
        unique_together = ("session", "ingest_key")
```

Storing Decimal as string avoids float precision loss and matches how the FillResolver passes values to PDF field mappers.

### New Service: `AggregateIngestionService`

`backend/apps/documents/services/aggregator.py`:

```python
class AggregateIngestionService:
    @classmethod
    def recalculate(cls, session_id: int) -> None:
        # 1. Query all OCRResult (status=COMPLETED, document.type=PAY_STUB) for session
        # 2. Parse each PayStubExtraction from extracted_data
        # 3. daily_gross = gross_pay / (end_date - start_date + timedelta(days=1)).days
        # 4. monthly = daily_gross × 30.41667
        # 5. Average all monthly values → paystub.gross
        # 6. employer_name from most recently dated stub → paystub.employer_name
        # 7. update_or_create both keys
```

Recomputes from scratch on every call — handles document deletions and field corrections naturally. Paystubs with invalid dates (end before start) are skipped; the remaining stubs are still averaged.

**Trigger points:**

- End of `_run_processing()` in `views.py` (OCR completes)
- In the `validate` action in `views.py` (user corrects extracted fields)

Both are one-line additions.

### FillResolver Wiring

`backend/apps/forms/services/fill_resolver.py` gains an `"ingested"` source branch in `_scalar_value()`:

```python
if field.source == "ingested":
    agg = IngestedAggregate.objects.filter(
        session=session, ingest_key=field.ingest_key
    ).first()
    return agg.value if agg else ""
```

Schedule I schema fields (`data/forms/schemas/schedule_i.json`) for monthly gross income and employer name get `source: "ingested"` with the appropriate `ingest_key`.

---

## Section 6 — Frontend: DebtsStep Draft Badge

### Backend Serializer

`DebtInfoSerializer` in `backend/apps/intake/serializers.py` adds two read-only fields:

- `is_draft: bool` (already on the model)
- `source_document_name: str | None` (from `source_document.original_filename`)

### Frontend Types

`src/types/api.ts` `DebtInfo` interface gains:

```typescript
is_draft: boolean;
source_document_name: string | null;
```

### Badge UI

A small muted pill reading **"Imported"** appears on each debt card where `is_draft === true`. The badge marks data origin, not review status — it remains even after the filer edits the record. Editing and deleting work identically to manually entered debts.

Scale consideration: a credit report may add 15–25 draft debts at once. The existing list handles arbitrary length; no special handling needed.

**Out of scope for this spec:** bulk "clear all imported" action, a separate review/confirmation step, or `is_draft` → `false` transitions when the user edits a record.

---

## Section 7 — Error Handling

| Failure                                          | Behavior                                                                                                                                         |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `odl-hybrid` server unavailable                  | `convert()` raises → caught by processor → falls back to pymupdf JPEG → Gemini vision. Logged as warning. Processing continues.                  |
| Gemini rate limit / network error                | `OCRResult.status = FAILED`, `extracted_data = "{}"`. No auto-retry. User re-triggers by deleting and re-uploading.                              |
| Gemini returns unparseable JSON                  | `_parse_result()` returns `ExtractionResult(fields={}, error=...)`, status FAILED.                                                               |
| Credit report with 0 tradelines                  | Not an error. `DraftDebtCreator` creates no records, status COMPLETED. Likely a non-credit-report document or Gemini couldn't extract structure. |
| `AggregateIngestionService.recalculate()` raises | Logged as warning. Does not affect OCR status or `extracted_data`. Paystub aggregation is best-effort.                                           |
| Paystub with invalid dates (end before start)    | Validator in `PayStubExtraction` rejects; that stub is skipped; remaining stubs proceed normally.                                                |

---

## Section 8 — Testing Strategy

### Backend Unit Tests

| Target                                         | Coverage                                                                                                                              |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `GeminiProvider`                               | Mock `google.genai.Client`. Verify text mode vs vision mode code paths. Verify `response_mime_type="application/json"` header is set. |
| `CreditReportExtraction`                       | Schema validation: tradelines parse correctly, `amount_owed=0` filter works, masked account numbers (`****1234`) accepted.            |
| `DraftDebtCreator.create_from_credit_report()` | Creates N records, skips zero-balance tradelines, maps `in_collections`/`charged_off` status → `is_in_collections=True` correctly.    |
| `AggregateIngestionService.recalculate()`      | Multi-stub averaging with mixed pay periods. Upsert behavior (second call overwrites, doesn't duplicate). Skips failed OCR results.   |
| `FillResolver` ingested source                 | Resolves `paystub.gross` when aggregate exists; returns `""` when absent.                                                             |

### Backend Integration Test

Upload a creditor bill fixture → OCR completes → `DebtInfo` appears with `is_draft=True` in the debts list endpoint response.

### Frontend Tests (vitest + MSW)

- MSW handler returns debts including records with `is_draft: true`
- Verify "Imported" badge renders on the correct cards
- Verify editing a draft debt still works (form opens, save succeeds)
- Verify `source_document_name` renders on the badge tooltip or detail view (if designed)

---

## File Change Map

| File                                                               | Change                                                                                                             |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ----- |
| `docker-compose.yml`                                               | Remove `llm` service; add `odl-hybrid`; update `backend.depends_on`                                                |
| `Dockerfile.heroku`                                                | Add `opendataloader-pdf[hybrid]` to pip deps                                                                       |
| `backend/apps/documents/services/processor.py`                     | `hybrid="docling-fast"` on `convert()`; `GeminiProvider` in `_get_processor()`                                     |
| `backend/apps/documents/services/providers/gemini.py`              | **New file** — `GeminiProvider(BaseOCRProvider)`                                                                   |
| `backend/apps/documents/services/providers/llama_cpp.py`           | **Delete**                                                                                                         |
| `backend/apps/documents/schemas/credit_report.py`                  | **New file** — `TradelineItem`, `CreditReportExtraction`                                                           |
| `backend/apps/documents/schemas/registry.py`                       | Register `CreditReportExtraction` for `CREDIT_REPORT` type                                                         |
| `backend/apps/documents/services/draft_debt.py`                    | Add `create_from_credit_report()`; update dispatch in `create_from_result()`                                       |
| `backend/apps/documents/models.py`                                 | Add `IngestedAggregate` model                                                                                      |
| `backend/apps/documents/services/aggregator.py`                    | **New file** — `AggregateIngestionService`                                                                         |
| `backend/apps/documents/views.py`                                  | Wire `GeminiProvider`; call `recalculate()` post-OCR and post-validate; handle list return from `DraftDebtCreator` |
| `backend/apps/forms/services/fill_resolver.py`                     | Add `"ingested"` source branch                                                                                     |
| `data/forms/schemas/schedule_i.json`                               | Monthly gross and employer name fields → `source: "ingested"`                                                      |
| `backend/apps/intake/serializers.py`                               | `DebtInfoSerializer` exposes `is_draft`, `source_document_name`                                                    |
| `frontend/src/types/api.ts`                                        | `DebtInfo` gains `is_draft: boolean`, `source_document_name: string                                                | null` |
| `frontend/src/pages/DebtsStep.tsx` (or wherever debt cards render) | "Imported" badge on `is_draft === true`                                                                            |
| `backend/apps/documents/tests/`                                    | Unit tests per Section 8                                                                                           |
| `frontend/src/…/__tests__/`                                        | Vitest + MSW tests per Section 8                                                                                   |
