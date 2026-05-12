# Document Scanning — Design Spec

**Date:** 2026-05-12
**Status:** Approved

## Overview

Replace the Clarifai/DeepSeek-OCR cloud provider with a fully local document
processing pipeline. Users can upload paystubs, tax returns, creditor bills,
and other supporting documents in PDF, JPEG, or PNG format. Extracted data
pre-fills intake wizard fields. Creditor bill scans auto-create draft `DebtInfo`
entries the user confirms on the Debts wizard step. No document data leaves
the user's machine.

---

## 1. Infrastructure

### New Docker service: `llm`

Image: `ghcr.io/ggml-org/llama.cpp:server`

A shell entrypoint script (`scripts/pull_model.sh`) runs at container startup
and downloads two files from HuggingFace into `./models/` if not already
present:

- `gemma-3-4b-it-q4_k_m.gguf` (~2.5 GB) — quantized Gemma 3 4B instruction-tuned
- `gemma-3-4b-mmproj-f16.gguf` (~300 MB) — multimodal projector for image inputs

After download, starts the llama.cpp server:

```
--host 0.0.0.0 --port 8080 -c 4096
-m /models/gemma-3-4b-it-q4_k_m.gguf
--mmproj /models/gemma-3-4b-mmproj-f16.gguf
```

Volume `./models:/models` persists downloaded weights across restarts.
Backend addresses the service at `http://llm:8080/v1` (OpenAI-compatible API).

### New Python dependencies (`requirements/base.txt`)

- `opendataloader-pdf` — structured text/table extraction from digital PDFs
- `pymupdf` — scanned PDF detection + page-to-image rendering for Gemma vision

### Removed

- `openai==1.60.0` pin replaced with unpinned `openai` (same SDK, different
  `base_url`)
- `CLARIFAI_PAT` environment variable removed from `.env` and `.env.example`

---

## 2. Backend Pipeline

### `documents/services/processor.py` — `DocumentProcessor`

Single entry point for all document types:

```python
processor.process(file_bytes, mime_type, doc_type) -> ExtractionResult
```

`ExtractionResult` fields: `fields: dict`, `confidence: dict[str, float]`,
`detected_type: str`

**Routing logic:**

```
JPEG / PNG
  └─→ Gemma vision (base64 image payload)

PDF
  ├─→ opendataloader-pdf → extract text + tables
  │     ├─→ text substantial (>100 chars)? → Gemma text prompt
  │     └─→ text minimal (scanned PDF)?
  │           └─→ pymupdf render pages (max 3) → Gemma vision
```

### `documents/services/providers/llama_cpp.py` — `LlamaCppProvider`

Replaces `ClarifaiOCRProvider`. Implements the same `BaseOCRProvider`
interface (`classify`, `extract`). Configures the `openai` client with
`base_url=http://llm:8080/v1` and no API key.

### `documents/services/providers/prompts/`

Two Jinja2/f-string prompt templates:

- `image_extraction.py` — used for JPEG/PNG and scanned PDF pages; embeds
  base64 image in the chat message
- `text_extraction.py` — used for digital PDFs; passes structured text from
  opendataloader-pdf

Both templates return a JSON object matching the target schema fields.

### `documents/services/draft_debt.py` — `DraftDebtCreator`

Called by the upload view after `DocumentProcessor` completes, only when
`doc_type == CREDITOR_BILL`. Creates one `DebtInfo` row per extracted creditor
with `is_draft=True` and `source_document` set to the uploaded document.

All other document types (paystubs, tax returns, etc.) write only to
`OCRResult` — no `DebtInfo` side effects.

---

## 3. Data Model Changes

### `intake/models.py` — `DebtInfo`

Two new fields:

```python
is_draft = models.BooleanField(default=False)
source_document = models.ForeignKey(
    'documents.UploadedDocument',
    null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name='draft_debts',
)
```

Saving the Debts wizard step sets `is_draft=False` on all `DebtInfo` rows
for the session (bulk update). No new wizard step required.

### `documents/models.py` — `DocumentType`

New choice added:

```python
CREDITOR_BILL = 'creditor_bill', 'Creditor Bill / Statement'
```

### `documents/schemas/creditor_bill.py` — `CreditorBillSchema`

| Extracted field   | Type      | Maps to `DebtInfo` field                 |
| ----------------- | --------- | ---------------------------------------- |
| `creditor_name`   | `str`     | `creditor_name`                          |
| `account_number`  | `str`     | `account_number` (Fernet-encrypted)      |
| `amount_owed`     | `Decimal` | `amount_owed`                            |
| `minimum_payment` | `Decimal` | informational only                       |
| `due_date`        | `date`    | informational only                       |
| `creditor_type`   | `str`     | `debt_type` (mapped to existing choices) |

---

## 4. API Endpoints

`documents/views.py` — `DocumentViewSet`:

| Method | URL                             | Behaviour                                                                                                                                                           |
| ------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST` | `/api/documents/upload/`        | Accept multipart file + `document_type` + `session_id`. Start background processing thread. Return `202` with `{id, status: 'processing'}`.                         |
| `GET`  | `/api/documents/`               | List documents for `?session_id=`. Auth-scoped.                                                                                                                     |
| `GET`  | `/api/documents/{id}/`          | Return document + OCR result. Frontend polls every 3 s until `status` is `completed` or `failed`.                                                                   |
| `POST` | `/api/documents/{id}/validate/` | Accept partial `fields` dict. Update `OCRResult.extracted_data`, set `user_validated=True`. For `CREDITOR_BILL`: propagate changed fields to linked `DebtInfo` row. |

**Processing** runs in a `ThreadPoolExecutor` thread — no Celery or Redis
required. All endpoints require JWT auth. Documents are session-scoped:
a document uploaded in one session is never returned in another session's
listing.

---

## 5. Frontend

### New route: `/documents`

Registered under `IntakeLayout` (shares `IntakeProvider`). Auth-guarded.

**Registration and login success redirects** change from `/intake/1` to
`/documents`.

Three UI states:

1. **Empty** — drop zone (PDF, JPEG, PNG) + "Skip for now" link → `/intake/1`
2. **Uploading / processing** — per-file status rows; frontend polls
   `GET /api/documents/{id}/` every 3 s; spinner until `completed` or `failed`
3. **Complete** — extraction summary ("2 creditor bills found, 1 paystub
   processed") + "Continue to intake" button → `/intake/1`

Multiple files can be queued. Document type is auto-detected from OCR result;
user can override via per-file dropdown before upload.

The page is also reachable from `/forms` (FormDashboard) so users who skipped
during intake can return later.

### Debts step (`components/wizard/steps/Debts.tsx`)

On mount, loads `DebtInfo` rows where `is_draft=true` for the session. These
render as pre-filled entries with a subtle "From scan" badge. Existing
add/edit/delete behaviour unchanged. Saving the step confirms all entries:
the existing `updateSession()` PATCH sends the full debts array; the
`IntakeSessionViewSet` handler is updated to bulk-set `is_draft=False` on all
`DebtInfo` rows for the session as a post-save side effect.

### `api/client.ts` — four new typed functions

```typescript
uploadDocument(sessionId, file, documentType): Promise<Document>
pollDocument(id): Promise<Document>          // single fetch, caller loops
listDocuments(sessionId): Promise<Document[]>
validateDocument(id, fields): Promise<OCRResult>
```

---

## 6. Error Handling

- **llm service not ready**: `DocumentProcessor` checks `http://llm:8080/health`
  before processing. If unavailable, `OCRResult.status` is set to `failed`
  with `error_message: 'LLM service unavailable'`. Upload still succeeds; user
  is shown a "Processing failed — please enter details manually" message.
- **Unsupported file type**: rejected at upload with `400` before processing.
- **Extraction low confidence** (`overall_confidence < 60`): `OCRResult.status`
  set to `completed` but frontend shows a warning prompting user to review all
  fields.
- **Draft debt mapping failure** (e.g. unrecognised `creditor_type`): maps to
  `debt_type='other'` rather than failing.

---

## 7. Out of Scope

- Hybrid opendataloader-pdf sidecar (complex tables in scanned PDFs deferred)
- Async task queue (Celery/Redis) — `ThreadPoolExecutor` sufficient for MVP
- Multi-page creditor bill extraction (first page only for MVP)
- S3/cloud storage for uploaded files (local filesystem, same as current)
- Auto-populating Income step from paystub extraction (deferred; OCR result
  stored, mapping not wired)
