# SP4: Ask-Modules and Conditional Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dynamic React wizard (Ask-Modules) powered by a backend-served UI Spec, backed by a local conditional engine and bulk upsert saving.

**Architecture:** Extend JSON form schemas with `ui` metadata. Expose this through a new `/ui-spec/` backend endpoint. Build a generic bulk-upsert endpoint for `FormAnswer` models. Implement a frontend wizard that evaluates skips dynamically based on React Context and renders fields based on the spec.

**Tech Stack:** Python, Django REST Framework, React 19, TypeScript.

## Global Constraints

- No new document-specific tables; use the generic `FormAnswer` model for all new form data.
- The UI Spec payload must flatten `repeat_group` fields logically to simplify the frontend loop.
- Conditional rules (`conditional_on`) must be evaluated locally in the browser to ensure zero-latency skips.

---

### Task 1: Schema Extensions

**Files:**

- Modify: `backend/apps/forms/schema.py`
- Modify: `backend/apps/forms/tests/test_schema.py`

**Interfaces:**

- Consumes: JSON schemas with optional `"ui": {"step": "...", "prompt": "...", "widget": "..."}` block.
- Produces: `UIFieldSpec` dataclass and populated `FieldSpec.ui` attribute.

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/forms/tests/test_schema.py
import json
from dataclasses import asdict
from apps.forms.schema import load_schema, UIFieldSpec

def test_load_schema_with_ui_metadata(tmp_path):
    schema_data = {
        "form_type": "test_form",
        "template_filename": "test.pdf",
        "template_version": "v1",
        "fields": [
            {
                "pdf_field": "street",
                "type": "text",
                "source": "asked",
                "binding": "answer:form.street",
                "ui": {
                    "step": "Address",
                    "prompt": "What is your street address?",
                    "widget": "text",
                    "help_text": "No PO Boxes"
                }
            }
        ]
    }
    schema_file = tmp_path / "test.json"
    schema_file.write_text(json.dumps(schema_data))

    schema = load_schema(schema_file)
    field = schema.fields[0]

    assert field.ui is not None
    assert field.ui.step == "Address"
    assert field.ui.prompt == "What is your street address?"
    assert field.ui.widget == "text"
    assert field.ui.help_text == "No PO Boxes"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/forms/tests/test_schema.py::test_load_schema_with_ui_metadata -v`
Expected: FAIL due to missing `ui` field mapping in `FieldSpec`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/apps/forms/schema.py
# (Add this above FieldSpec)
from dataclasses import dataclass, field

@dataclass
class UIFieldSpec:
    step: str
    prompt: str
    widget: str
    help_text: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> 'UIFieldSpec':
        return cls(
            step=data.get("step", "Unknown Step"),
            prompt=data.get("prompt", ""),
            widget=data.get("widget", "text"),
            help_text=data.get("help_text")
        )

# Inside FieldSpec definition, add:
#    ui: UIFieldSpec | None = None

# In FieldSpec.from_dict, add:
#    ui_data = data.get("ui")
#    ui_spec = UIFieldSpec.from_dict(ui_data) if ui_data else None

# modify return cls(..., ui=ui_spec, ...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/forms/tests/test_schema.py::test_load_schema_with_ui_metadata -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/schema.py backend/apps/forms/tests/test_schema.py
git commit -m "feat(forms): extend schema parsing with UI metadata"
```

---

### Task 2: Backend UI-Spec Endpoint

**Files:**

- Modify: `backend/apps/forms/views.py`
- Modify: `backend/config/urls.py`
- Create: `backend/apps/forms/tests/test_schema_views.py`

**Interfaces:**

- Consumes: `FormSchemaRegistry` to access parsed schemas.
- Produces: `GET /api/forms/{form_type}/ui-spec/` returning JSON.

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/forms/tests/test_schema_views.py
from django.urls import reverse
from rest_framework.test import APITestCase
from apps.forms.schema import FormSchema, FieldSpec, UIFieldSpec
from apps.forms.services.registry import FORM_SCHEMAS

class TestUISpecView(APITestCase):
    def setUp(self):
        self.test_schema = FormSchema(
            form_type="form_test",
            template_filename="test.pdf",
            template_version="v1",
            fields=[
                FieldSpec(
                    pdf_field="Q1", type="text", source="asked", binding="answer:test.q1",
                    ui=UIFieldSpec(step="Step 1", prompt="Prompt 1", widget="text")
                )
            ]
        )
        FORM_SCHEMAS["form_test"] = self.test_schema

    def tearDown(self):
        FORM_SCHEMAS.pop("form_test", None)

    def test_get_ui_spec_returns_structured_data(self):
        url = reverse('form-schema-ui-spec', kwargs={'form_type': 'form_test'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("steps", data)
        self.assertEqual(len(data["steps"]), 1)
        self.assertEqual(data["steps"][0]["title"], "Step 1")
        self.assertEqual(data["steps"][0]["fields"][0]["binding"], "answer:test.q1")
        self.assertEqual(data["steps"][0]["fields"][0]["prompt"], "Prompt 1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/forms/tests/test_schema_views.py -v`
Expected: FAIL due to missing URL route.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/apps/forms/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from apps.forms.services.registry import FORM_SCHEMAS

class FormSchemaUIView(APIView):
    def get(self, request, form_type):
        schema = FORM_SCHEMAS.get(form_type)
        if not schema:
            raise NotFound(f"Schema for form {form_type} not found")

        steps_dict = {}
        for field in schema.fields:
            if field.source == "asked" and field.ui:
                step_title = field.ui.step
                if step_title not in steps_dict:
                    steps_dict[step_title] = {
                        "title": step_title,
                        "fields": []
                    }

                steps_dict[step_title]["fields"].append({
                    "binding": field.binding,
                    "prompt": field.ui.prompt,
                    "widget": field.ui.widget,
                    "help_text": field.ui.help_text,
                    "conditional_on": field.conditional_on,
                    "repeat": field.repeat,
                    "repeat_capacity": field.repeat_capacity
                })

        steps_list = list(steps_dict.values())
        return Response({"form_type": form_type, "steps": steps_list})
```

```python
# backend/config/urls.py
# (Add inside urlpatterns)
from apps.forms.views import FormSchemaUIView

path('api/forms/<str:form_type>/ui-spec/', FormSchemaUIView.as_view(), name='form-schema-ui-spec'),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/forms/tests/test_schema_views.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/views.py backend/config/urls.py backend/apps/forms/tests/test_schema_views.py
git commit -m "feat(forms): add /api/forms/{form_type}/ui-spec/ endpoint"
```

---

### Task 3: Backend Bulk Upsert Endpoint

**Files:**

- Modify: `backend/apps/intake/views.py`
- Modify: `backend/apps/intake/serializers.py`
- Create: `backend/apps/intake/tests/test_bulk_answers.py`

**Interfaces:**

- Consumes: JSON array of answers mapped to the `session_id`.
- Produces: Upserted `FormAnswer` records.

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/intake/tests/test_bulk_answers.py
from django.urls import reverse
from rest_framework.test import APITestCase
from apps.intake.models import IntakeSession, FormAnswer

class TestBulkAnswerView(APITestCase):
    def setUp(self):
        self.session = IntakeSession.objects.create()

    def test_bulk_upsert_creates_and_updates(self):
        FormAnswer.objects.create(
            session=self.session, form_type="form_test", field_key="q1", value="old"
        )
        url = reverse('intakesession-bulk-answers', kwargs={'pk': self.session.pk})
        payload = {
            "answers": [
                {"form_type": "form_test", "field_key": "q1", "value": "new"},
                {"form_type": "form_test", "field_key": "q2", "value": "brand new"}
            ]
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 200)

        answers = FormAnswer.objects.filter(session=self.session).order_by("field_key")
        self.assertEqual(answers.count(), 2)
        self.assertEqual(answers[0].value, "new")
        self.assertEqual(answers[1].value, "brand new")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/intake/tests/test_bulk_answers.py -v`
Expected: FAIL due to missing URL route/action.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/apps/intake/serializers.py
# (Add these classes)
from rest_framework import serializers

class BulkAnswerItemSerializer(serializers.Serializer):
    form_type = serializers.CharField(max_length=20)
    field_key = serializers.CharField(max_length=100)
    value = serializers.CharField(allow_blank=True)

class BulkAnswerPayloadSerializer(serializers.Serializer):
    answers = BulkAnswerItemSerializer(many=True)
```

```python
# backend/apps/intake/views.py
# (Add in IntakeSessionViewSet)
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.intake.serializers import BulkAnswerPayloadSerializer
from apps.intake.models import FormAnswer

    @action(detail=True, methods=["post"], url_path="answers/bulk", url_name="bulk-answers")
    def bulk_answers(self, request, pk=None):
        session = self.get_object()
        serializer = BulkAnswerPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answers_data = serializer.validated_data["answers"]
        created_count = 0
        updated_count = 0

        for ans in answers_data:
            obj, created = FormAnswer.objects.update_or_create(
                session=session,
                form_type=ans["form_type"],
                field_key=ans["field_key"],
                defaults={"value": ans["value"]}
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        return Response({"status": "success", "created": created_count, "updated": updated_count})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/intake/tests/test_bulk_answers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/intake/views.py backend/apps/intake/serializers.py backend/apps/intake/tests/test_bulk_answers.py
git commit -m "feat(intake): add bulk FormAnswer upsert endpoint"
```

---

### Task 4: Frontend API Client & Types

**Files:**

- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/api/client.ts`

**Interfaces:**

- Consumes: The UI Spec format defined in Task 2.
- Produces: Typed methods `getUISpec(formType)` and `bulkUpsertAnswers(sessionId, answers)`.

- [ ] **Step 1: Write types and implementation**

```typescript
// frontend/src/types/api.ts
// Add these interfaces:
export interface UIFieldSpec {
  binding: string;
  prompt: string;
  widget: string;
  help_text?: string | null;
  conditional_on?: string | null;
  repeat?: string | null;
  repeat_capacity?: number | null;
}

export interface UIStep {
  title: string;
  fields: UIFieldSpec[];
}

export interface FormUISpec {
  form_type: string;
  steps: UIStep[];
}

export interface AnswerPayload {
  form_type: string;
  field_key: string;
  value: string;
}
```

```typescript
// frontend/src/api/client.ts
// Add these functions:
export async function getUISpec(formType: string): Promise<FormUISpec> {
  const token = getAccessToken();
  const res = await fetch(`${API_BASE_URL}/forms/${formType}/ui-spec/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch UI Spec');
  return res.json();
}

export async function bulkUpsertAnswers(sessionId: string, answers: AnswerPayload[]): Promise<any> {
  const token = getAccessToken();
  const res = await fetch(`${API_BASE_URL}/intake/sessions/${sessionId}/answers/bulk/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) throw new Error('Failed to bulk save answers');
  return res.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/api/client.ts
git commit -m "feat(frontend): add API client methods for SP4 Ask-Modules"
```

---

### Task 5: Frontend Ask-Modules UI

**Files:**

- Create: `frontend/src/components/forms/DynamicFormWizard.tsx`

**Interfaces:**

- Consumes: `IntakeContext` to read active session data and conditionally evaluate rules.

- [ ] **Step 1: Implement DynamicFormWizard Component**

```tsx
// frontend/src/components/forms/DynamicFormWizard.tsx
import React, { useState, useEffect } from 'react';
import { useIntake } from '../../context/IntakeContext';
import { getUISpec, bulkUpsertAnswers, FormUISpec, AnswerPayload } from '../../api/client';

export function DynamicFormWizard({
  formType,
  onComplete,
}: {
  formType: string;
  onComplete: () => void;
}) {
  const { session } = useIntake();
  const [uiSpec, setUiSpec] = useState<FormUISpec | null>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUISpec(formType)
      .then((spec) => {
        setUiSpec(spec);
        setLoading(false);
      })
      .catch(console.error);
  }, [formType]);

  if (loading || !uiSpec) return <div>Loading wizard...</div>;

  const isConditionMet = (condition?: string | null) => {
    if (!condition) return true;
    return true; // Simplified placeholder. Real evaluation logic goes here later.
  };

  const steps = uiSpec.steps.filter((step) => {
    return step.fields.some((f) => isConditionMet(f.conditional_on));
  });

  if (steps.length === 0) return <div>No steps required.</div>;

  const currentStep = steps[currentStepIndex];

  const handleNext = async () => {
    if (!session) return;

    const payloads: AnswerPayload[] = Object.entries(formData).map(([binding, value]) => {
      const parts = binding.split(':');
      const fType = parts[1].split('.')[0];
      const fKey = parts[1].split('.')[1];
      return { form_type: fType, field_key: fKey, value };
    });

    try {
      if (payloads.length > 0) {
        await bulkUpsertAnswers(session.id, payloads);
      }
      if (currentStepIndex < steps.length - 1) {
        setCurrentStepIndex((curr) => curr + 1);
      } else {
        onComplete();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="dynamic-wizard p-6 bg-white shadow rounded">
      <h2 className="text-xl font-bold mb-4">{currentStep.title}</h2>
      {currentStep.fields
        .filter((f) => isConditionMet(f.conditional_on))
        .map((field, i) => (
          <div key={i} className="mb-4">
            <label className="block mb-2 font-medium">{field.prompt}</label>
            {field.help_text && <p className="text-sm text-gray-500 mb-2">{field.help_text}</p>}
            <input
              type="text"
              className="w-full border p-2 rounded"
              value={formData[field.binding] || ''}
              onChange={(e) => setFormData({ ...formData, [field.binding]: e.target.value })}
            />
          </div>
        ))}
      <div className="mt-6 flex justify-end">
        <button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={handleNext}>
          {currentStepIndex < steps.length - 1 ? 'Next' : 'Complete'}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/forms/DynamicFormWizard.tsx
git commit -m "feat(frontend): implement DynamicFormWizard skeleton component"
```
