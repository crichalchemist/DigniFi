# SP4: Ask-Modules and Conditional Engine Design

## Context

Phase SP4 focuses on building a dynamic frontend wizard ("Ask-Modules") and a "Conditional Engine" that evaluates schema rules. Since Form 107 and the remaining 12 forms have hundreds of fields, hardcoding React wizard steps for each form is unscalable.

We will use the underlying form schemas (which already map PDF fields) and extend them with UI metadata. The frontend will dynamically render trauma-informed, plain-language questions by interpreting these extended schemas, skipping irrelevant steps instantly using local rule evaluation.

## Architecture & Data Flow

1. **Schema UI Extensions**: We extend the existing form JSON files. Fields with `"source": "asked"` gain a `ui` object describing the step group, plain-language prompt, and widget type.
2. **Hybrid Conditional Engine**: The backend exposes a new `ui-spec` endpoint. The frontend fetches the streamlined specification on load and uses it to render a dynamic wizard. `conditional_on` rules are evaluated entirely in the browser against a React Context state to prevent network latency between skips.
3. **Bulk Upsert Save**: The frontend submits answers in batches via a new generic `FormAnswer` bulk API endpoint whenever the user clicks "Next" on a step.

## Components

### 1. Schema Extensions

The `FieldSpec` (and the raw JSON files) will be extended to optionally support a `ui` block:

```json
{
  "pdf_field": "Part 1, Question 1, Street",
  "source": "asked",
  "binding": "answer:form_107.street",
  "conditional_on": "has_address_history",
  "ui": {
    "step": "Address History",
    "prompt": "What was your previous street address?",
    "widget": "text",
    "help_text": "Do not list a P.O. Box here."
  }
}
```

**Repeat Groups:**
For fields mapping to a collection, the backend will group them logically under a `"widget": "repeat_group"` container in the generated UI Spec, allowing the frontend to loop and render a repeating "Add Another" component.

### 2. Backend UI-Spec Endpoint

**Endpoint:** `GET /api/forms/{form_type}/ui-spec/`
**Responsibility:** Reads the raw JSON schema, strips out PDF-specific formatting details, groups the `asked` fields by their `ui.step` properties, and returns a sequential array of "Step" objects for the frontend to consume.

### 3. Frontend Dynamic Wizard (Ask-Modules)

**Component:** `DynamicFormWizard.tsx`
**Responsibility:**

- Fetches the UI Spec.
- Iterates over the `steps`.
- Evaluates `conditional_on` against the current answers stored in `IntakeContext`. If the predicate is false, it skips rendering the step.
- Maps `widget` string values (`text`, `radio`, `repeat_group`, `date`) to specific React form components.

### 4. Backend Bulk Save Endpoint

**Endpoint:** `POST /api/intake/sessions/{id}/answers/bulk/`
**Responsibility:** Accepts an array of answer objects:

```json
{
  "answers": [{ "form_type": "form_107", "field_key": "street", "value": "123 Main St" }]
}
```

Performs a bulk `update_or_create` on the `FormAnswer` table to save the user's progress for the completed step.

## Error Handling & Edge Cases

- **Missing UI Metadata:** If a field is `"source": "asked"` but lacks a `ui` object, the backend UI-Spec generator will throw a validation error during development to enforce strict curation.
- **Repeat Group Overflows:** The frontend "Add Another" component will enforce a maximum length based on the `repeat_capacity` specified in the schema, preventing the user from adding more items than the sworn PDF document can hold.
- **Orphaned Answers:** If a user answers a section, then changes a previous answer that hides the section via `conditional_on`, the orphaned data remains in `FormAnswer` but is safely ignored by the `FillResolver` during PDF generation.

## Test Strategy

- **Backend:** Unit tests for the new `ui-spec` generator and the bulk upsert endpoint.
- **Frontend:** Vitest component tests verifying that the local conditional engine correctly skips steps based on mock state. Playwright E2E journey for completing a dynamic form section and verifying the API saves.
