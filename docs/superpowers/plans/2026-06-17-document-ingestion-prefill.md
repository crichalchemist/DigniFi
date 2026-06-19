# Document Ingestion Prefill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the "ingested" source branch in FillResolver and an aggregation layer to precalculate totals from OCR documents.

**Architecture:** A new `IngestedAggregate` model caches mathematically-combined totals (like `paystub.gross`) calculated by an `AggregateIngestionService` when OCR finishes or user validates. `FillResolver` reads directly from this model for O(1) resolution.

**Tech Stack:** Django ORM, Pydantic (schema parsing).

## Global Constraints

No new document-specific tables. O(1) lookups in FillResolver. Do not crash recalculation if a single document fails parsing.

---

### Task 1: IngestedAggregate Model

**Files:**

- Modify: `backend/apps/documents/models.py`

**Interfaces:**

- Produces: `IngestedAggregate` (Django Model)

- [ ] **Step 1: Write the failing test**

Create `backend/apps/documents/tests/test_models.py` if it doesn't exist, or append:

```python
from django.test import TestCase
from apps.documents.models import IngestedAggregate
from apps.intake.models import IntakeSession
from django.contrib.auth import get_user_model
from django.db import IntegrityError

class TestIngestedAggregate(TestCase):
    def test_unique_constraint(self):
        user = get_user_model().objects.create_user("testuser", "test@test.com", "pass")
        session = IntakeSession.objects.create(user=user)
        IngestedAggregate.objects.create(session=session, ingest_key="paystub.gross", value="100")
        with self.assertRaises(IntegrityError):
            IngestedAggregate.objects.create(session=session, ingest_key="paystub.gross", value="200")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/documents/tests/test_models.py -v`
Expected: FAIL (ImportError: cannot import name 'IngestedAggregate')

- [ ] **Step 3: Write minimal implementation**

Append to `backend/apps/documents/models.py`:

```python
class IngestedAggregate(models.Model):
    """Stores aggregated values from OCR documents for FillResolver."""

    session = models.ForeignKey(
        "intake.IntakeSession", on_delete=models.CASCADE, related_name="ingested_aggregates"
    )
    ingest_key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)

    class Meta:
        db_table = "ingested_aggregates"
        unique_together = [["session", "ingest_key"]]

    def __str__(self):
        return f"{self.ingest_key}: {self.value}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py makemigrations documents`
Run: `pytest backend/apps/documents/tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/documents/models.py backend/apps/documents/migrations/ backend/apps/documents/tests/
git commit -m "feat(documents): add IngestedAggregate model"
```

---

### Task 2: AggregateIngestionService

**Files:**

- Create: `backend/apps/documents/services/aggregator.py`
- Create: `backend/apps/documents/tests/test_aggregator.py`

**Interfaces:**

- Consumes: `IngestedAggregate`, `OCRResult`
- Produces: `AggregateIngestionService.recalculate(session_id: int)`

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/documents/tests/test_aggregator.py
import json
from decimal import Decimal
from django.test import TestCase
from apps.documents.models import DocumentType, IngestedAggregate, OCRResult, OCRStatus, UploadedDocument
from apps.intake.models import IntakeSession
from django.contrib.auth import get_user_model
from apps.documents.services.aggregator import AggregateIngestionService

class TestAggregateIngestionService(TestCase):
    def test_recalculate_paystub_gross(self):
        user = get_user_model().objects.create_user("testuser", "test@test.com", "pass")
        session = IntakeSession.objects.create(user=user)

        doc = UploadedDocument.objects.create(
            session=session, uploaded_by=user, document_type=DocumentType.PAY_STUB,
            file="test.pdf", original_filename="test.pdf", file_size=100, mime_type="application/pdf"
        )

        ocr = OCRResult.objects.create(
            document=doc, status=OCRStatus.COMPLETED,
            extracted_data=json.dumps({
                "employer_name": "Acme",
                "gross_pay": "1000.00",
                "pay_period_start": "2026-01-01",
                "pay_period_end": "2026-01-14", # 14 days
                "confidence_score": 100
            })
        )

        AggregateIngestionService.recalculate(session.id)

        agg = IngestedAggregate.objects.get(session=session, ingest_key="paystub.gross")
        # 1000 / 14 * 30.416666 = 2172.619 -> 2172.62
        self.assertEqual(agg.value, "2172.62")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/documents/tests/test_aggregator.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/apps/documents/services/aggregator.py
import json
import logging
from decimal import Decimal

from apps.documents.models import DocumentType, IngestedAggregate, OCRResult, OCRStatus

logger = logging.getLogger(__name__)

class AggregateIngestionService:
    @classmethod
    def recalculate(cls, session_id: int) -> None:
        try:
            results = list(
                OCRResult.objects.filter(
                    document__session_id=session_id, status=OCRStatus.COMPLETED
                ).select_related("document")
            )

            # Group by document type
            by_type = {}
            for res in results:
                by_type.setdefault(res.document.document_type, []).append(res)

            # Recalculate each type
            if DocumentType.PAY_STUB in by_type:
                cls._calc_paystubs(session_id, by_type[DocumentType.PAY_STUB])
            else:
                IngestedAggregate.objects.filter(session_id=session_id, ingest_key__startswith="paystub.").delete()

        except Exception as exc:
            logger.exception("Failed to recalculate ingestion aggregates for session %s: %s", session_id, exc)

    @classmethod
    def _calc_paystubs(cls, session_id: int, results: list[OCRResult]) -> None:
        from apps.documents.schemas.paystub import PayStubExtraction

        total_monthly_gross = Decimal("0")
        valid_stubs = 0

        for ocr in results:
            try:
                data = json.loads(ocr.extracted_data or "{}")
                parsed = PayStubExtraction(**data)

                days = (parsed.pay_period_end - parsed.pay_period_start).days + 1
                if days <= 0:
                    continue

                daily_gross = parsed.gross_pay / Decimal(str(days))
                monthly_gross = daily_gross * Decimal("30.416666")

                total_monthly_gross += monthly_gross
                valid_stubs += 1
            except Exception as e:
                logger.warning("Skipping invalid paystub OCRResult %s: %s", ocr.id, e)

        if valid_stubs > 0:
            avg_monthly_gross = (total_monthly_gross / Decimal(str(valid_stubs))).quantize(Decimal("0.01"))
            IngestedAggregate.objects.update_or_create(
                session_id=session_id, ingest_key="paystub.gross",
                defaults={"value": str(avg_monthly_gross)}
            )
        else:
            IngestedAggregate.objects.filter(session_id=session_id, ingest_key__startswith="paystub.").delete()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/documents/tests/test_aggregator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/documents/services/aggregator.py backend/apps/documents/tests/test_aggregator.py
git commit -m "feat(documents): implement AggregateIngestionService"
```

---

### Task 3: Hook Aggregation in Document Views

**Files:**

- Modify: `backend/apps/documents/views.py`

**Interfaces:**

- Consumes: `AggregateIngestionService.recalculate`

- [ ] **Step 1: Write the failing test**

```python
# Create backend/apps/documents/tests/test_aggregator_hooks.py
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.intake.models import IntakeSession
from django.contrib.auth import get_user_model
from apps.documents.models import DocumentType, OCRResult, OCRStatus, UploadedDocument
from apps.documents.views import _run_processing

class TestAggregatorHooks(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("testuser", "test@test.com", "pass")
        self.session = IntakeSession.objects.create(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.doc = UploadedDocument.objects.create(
            session=self.session, uploaded_by=self.user, document_type=DocumentType.PAY_STUB,
            file="test.pdf", original_filename="test.pdf", file_size=100, mime_type="application/pdf"
        )
        self.ocr = OCRResult.objects.create(
            document=self.doc, status=OCRStatus.PENDING, extracted_data="{}"
        )

    @patch('apps.documents.views.DocumentProcessor')
    @patch('apps.documents.views.AggregateIngestionService.recalculate')
    def test_run_processing_hook(self, mock_recalc, mock_processor):
        mock_processor.return_value.process.return_value.error = None
        mock_processor.return_value.process.return_value.fields = {}
        mock_processor.return_value.process.return_value.confidence = {}

        _run_processing(self.doc.id)
        mock_recalc.assert_called_once_with(self.session.id)

    @patch('apps.documents.views.AggregateIngestionService.recalculate')
    def test_validate_hook(self, mock_recalc):
        url = reverse('document-validate', args=[self.doc.id])
        resp = self.client.post(url, {"fields": {"gross_pay": "2000.00"}}, format='json')
        self.assertEqual(resp.status_code, 200)
        mock_recalc.assert_called_once_with(self.session.id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/documents/tests/test_aggregator_hooks.py -v`
Expected: FAIL (AssertionError: Expected 'recalculate' to be called once)

- [ ] **Step 3: Write minimal implementation**

In `backend/apps/documents/views.py`:

Add import at the top:

```python
from apps.documents.services.aggregator import AggregateIngestionService
```

In `_run_processing`, at the end of the `else` block (around line 60), before `ocr.save()` or right after, add:

```python
        ocr.save()
        try:
            AggregateIngestionService.recalculate(doc.session_id)
        except Exception as exc:
            logger.warning("Recalculate failed for doc %s: %s", doc_id, exc)
        return  # end of try
```

Wait, in `views.py`, `_run_processing` has `ocr.save()`. Modify it to:

```python
            if doc.document_type == DocumentType.CREDITOR_BILL:
                try:
                    DraftDebtCreator().create_from_result(result, doc.session, doc)
                except Exception as exc:
                    logger.warning("DraftDebtCreator failed for doc %s: %s", doc_id, exc)

        ocr.save()

        # Add aggregation hook here:
        if ocr.status == OCRStatus.COMPLETED:
            AggregateIngestionService.recalculate(doc.session_id)

    except Exception as exc:
```

In `validate`, around line 163, before `return Response(...)`:

```python
        if doc.document_type == DocumentType.CREDITOR_BILL:
            doc.draft_debts.filter(is_draft=True).update(
                **{k: v for k, v in fields.items() if k in ("creditor_name", "amount_owed")}
            )

        # Add aggregation hook here:
        AggregateIngestionService.recalculate(doc.session_id)

        return Response(_serialize_ocr(ocr))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/documents/tests/test_aggregator_hooks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/documents/views.py backend/apps/documents/tests/test_aggregator_hooks.py
git commit -m "feat(documents): hook aggregator into processing and validation"
```

---

### Task 4: FillResolver Ingested Source

**Files:**

- Modify: `backend/apps/forms/services/fill_resolver.py`

**Interfaces:**

- Consumes: `IngestedAggregate`

- [ ] **Step 1: Write the failing test**

```python
# Append to backend/apps/forms/tests/test_fill_resolver.py
from apps.documents.models import IngestedAggregate

def test_resolve_ingested_source(session):
    schema = FormSchema(
        form_type="107",
        fields=[
            FieldSpec(
                pdf_field="Income.Gross",
                source="ingested",
                ingest_key="paystub.gross"
            )
        ]
    )

    # Missing aggregate -> empty
    out1 = resolve(schema, session)
    assert out1 == {"Income.Gross": ""}

    # Existing aggregate -> resolved
    IngestedAggregate.objects.create(session=session, ingest_key="paystub.gross", value="5000.00")
    out2 = resolve(schema, session)
    assert out2 == {"Income.Gross": "5000.00"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/forms/tests/test_fill_resolver.py::test_resolve_ingested_source -v`
Expected: FAIL (returns `{"Income.Gross": None}` or doesn't resolve)

- [ ] **Step 3: Write minimal implementation**

In `backend/apps/forms/services/fill_resolver.py`, update `_scalar_value`:

```python
def _scalar_value(field: FieldSpec, session: IntakeSession) -> str | None:
    if field.source == "constant":
        return field.value
    if field.source == "derived":
        fn = DERIVATIONS.get(field.rule)
        if fn is None:
            raise ValueError(f"Unknown derivation rule {field.rule!r} on field {field.pdf_field!r}")
        return fn(session)
    if field.source == "asked":
        if not field.binding:
            raise RuntimeError(f"Field {field.pdf_field} has source='asked' but no binding")
        val = resolve_binding(field.binding, session)
        return val if isinstance(val, str) else None
    if field.source == "ingested":
        if not field.ingest_key:
            raise RuntimeError(f"Field {field.pdf_field} has source='ingested' but no ingest_key")
        from apps.documents.models import IngestedAggregate
        agg = IngestedAggregate.objects.filter(session=session, ingest_key=field.ingest_key).first()
        return agg.value if agg else ""
    # signature → nothing
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/forms/tests/test_fill_resolver.py::test_resolve_ingested_source -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/services/fill_resolver.py backend/apps/forms/tests/test_fill_resolver.py
git commit -m "feat(forms): resolve ingested source via IngestedAggregate"
```
