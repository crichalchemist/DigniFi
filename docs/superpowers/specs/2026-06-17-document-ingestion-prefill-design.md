# SP3 Document-Ingestion Prefill Design

## Context

This design addresses Phase SP3 of the schema-driven form-fill engine (see `synthetic-mapping-bengio.md`). The goal is to allow the `FillResolver` to natively populate PDF fields marked with `"source": "ingested"` by reading values extracted by the Document OCR scanner (e.g., extracting `paystub.gross` from a paystub scan).

## Architecture & Data Flow

We are using a **Validation-Triggered Aggregator** pattern:

1. **No new document-specific tables:** OCR extractions remain as JSON in `OCRResult`.
2. **Dedicated Storage Model:** A new simple `IngestedAggregate(session, ingest_key, value)` model stores the computed totals.
3. **Triggered Execution:** The calculation service runs when a document finishes OCR processing or when a user explicitly validates OCR results.
4. **Resolution:** `FillResolver` directly queries `IngestedAggregate` via `O(1)` lookups for `"ingested"` sources, keeping form generation fast.

## Components

### 1. IngestedAggregate Model

**Path:** `backend/apps/documents/models.py` (or `intake/models.py`, but preferably `documents` since it's document-derived).

```python
class IngestedAggregate(models.Model):
    session = models.ForeignKey('intake.IntakeSession', on_delete=models.CASCADE, related_name='ingested_aggregates')
    ingest_key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = [['session', 'ingest_key']]
```

### 2. AggregateIngestionService

**Path:** `backend/apps/documents/services/aggregator.py`
**Responsibilities:**

- Fetch all `OCRResult` objects for the session with `status=COMPLETED`.
- Parse the JSON using Pydantic schemas (e.g., `PayStubExtraction`).
- Compute aggregates (e.g., scaling bi-weekly gross pay to a strict monthly average).
- Perform `update_or_create` upserts on `IngestedAggregate` mapping calculated values to keys like `paystub.gross` or `paystub.deductions`.
- Remove `IngestedAggregate` rows if no valid documents remain for an ingest key.

### 3. Execution Hooks

**Path:** `backend/apps/documents/views.py`

- Hook `AggregateIngestionService.recalculate(session_id)` to run after `_run_processing` successfully completes.
- Hook the service to run at the end of the `validate` endpoint.

### 4. FillResolver Integration

**Path:** `backend/apps/forms/services/fill_resolver.py`

- Implement the `"source": "ingested"` branch.
- Query `IngestedAggregate.objects.filter(session=session, ingest_key=field.ingest_key).first()`.
- Return the value if found, or an empty string if missing.

## Error Handling

- **Parsing/Date Errors:** If an `OCRResult` JSON is malformed or missing critical dates required for aggregation, the `AggregateIngestionService` logs a warning and skips that specific document, rather than failing the entire session calculation.
- **Missing Data:** If no `IngestedAggregate` exists for a key, `FillResolver` safely leaves the PDF field blank.

## Testing Strategy

- **Math & Aggregation Logic:** Unit tests for `AggregateIngestionService` ensuring proper scaling of different pay frequencies (weekly, bi-weekly, semi-monthly, monthly) to accurate monthly averages.
- **Hook Verification:** Tests in `test_views.py` ensuring validation correctly updates the `IngestedAggregate`.
- **Resolver Validation:** Unit tests proving `FillResolver` extracts the value from `IngestedAggregate` when source is `ingested`.
