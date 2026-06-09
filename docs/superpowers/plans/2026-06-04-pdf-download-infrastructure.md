# PDF Download Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up a `GET /api/forms/{id}/download/` endpoint that fills official AO court PDF templates with session data and streams them to the browser, plus a frontend Download button that triggers a real file save.

**Architecture:** Each generator exposes a `pdf_field_map() -> dict[str, str]` method (implemented separately in the field-mappings plan). A `PDFFormFiller` service loads the matching court template from `/data/forms/pdfs/`, fills it with `pypdf.PdfWriter.update_page_form_field_values`, and returns bytes. The `download` action on `GeneratedFormViewSet` orchestrates this and streams an `HttpResponse`. The frontend calls raw `fetch` (not the JSON `apiFetch` wrapper) to get the binary, then programmatically clicks an `<a download>` link.

**Tech Stack:** Python 3.11, pypdf 3.17 (already installed), Django 5 + DRF, React 19 + TypeScript

---

## File Map

| Action | Path                                                                 |
| ------ | -------------------------------------------------------------------- |
| CREATE | `backend/apps/forms/services/pdf_filler.py`                          |
| CREATE | `backend/apps/forms/tests/test_pdf_filler.py`                        |
| MODIFY | `backend/apps/forms/views.py` — add `download` action                |
| MODIFY | `Dockerfile.heroku` — COPY official form PDFs into image             |
| MODIFY | `frontend/src/api/client.ts` — add `downloadForm` to `formsAPI`      |
| MODIFY | `frontend/src/components/forms/FormCard.tsx` — add `onDownload` prop |
| MODIFY | `frontend/src/pages/FormDashboard.tsx` — wire `handleDownload`       |

---

## Task 1: PDFFormFiller service

**Files:**

- Create: `backend/apps/forms/services/pdf_filler.py`
- Create: `backend/apps/forms/tests/test_pdf_filler.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/forms/tests/test_pdf_filler.py
from io import BytesIO
import pytest
import pypdf
from apps.forms.services.pdf_filler import PDFFormFiller


def test_fill_returns_valid_pdf_bytes(settings):
    """fill() returns bytes that start with the PDF magic number."""
    filler = PDFFormFiller()
    result = filler.fill("form_121", {
        "Debtor1.First name": "Maria",
        "Debtor1.Last name": "Torres",
    })
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_fill_writes_text_field(settings):
    """fill() writes a text field value into the returned PDF."""
    filler = PDFFormFiller()
    result = filler.fill("form_121", {"Debtor1.First name": "Maria"})
    reader = pypdf.PdfReader(BytesIO(result))
    fields = reader.get_fields() or {}
    field = fields.get("Debtor1.First name")
    assert field is not None
    assert field.get("/V") == "Maria"


def test_fill_unknown_form_type_raises():
    """fill() raises KeyError for an unrecognised form_type."""
    filler = PDFFormFiller()
    with pytest.raises(KeyError):
        filler.fill("form_does_not_exist", {})


def test_fill_ignores_unknown_fields(settings):
    """fill() silently ignores field names not present in the template."""
    filler = PDFFormFiller()
    result = filler.fill("form_121", {"nonexistent_field_xyz": "value"})
    assert result[:4] == b"%PDF"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_filler.py -v
```

Expected: `ImportError: cannot import name 'PDFFormFiller'`

- [ ] **Step 3: Create the service**

```python
# backend/apps/forms/services/pdf_filler.py
from io import BytesIO
from pathlib import Path

import pypdf
from django.conf import settings

# Maps form_type key → filename under PDF_FORMS_DIRECTORY
FORM_TEMPLATES: dict[str, str] = {
    "form_101":    "form_b_101_0624_fillable_clean.pdf",
    "form_103b":   "form_b103b.pdf",
    "form_106dec": "form_b106dec.pdf",
    "form_106sum": "form_b106sum.pdf",
    "form_107":    "b_107_0425-form.pdf",
    "form_121":    "form_b121.pdf",
    "form_122a1":  "b_122a-1.pdf",
    "schedule_a_b": "form_b106ab.pdf",
    "schedule_c":  "b_106c_0425-form.pdf",
    "schedule_d":  "form_b106d.pdf",
    "schedule_e_f": "form_b106ef.pdf",
    "schedule_i":  "form_b106i.pdf",
    "schedule_j":  "form_b106j.pdf",
}


class PDFFormFiller:
    """Fill AO court PDF templates with field values and return bytes."""

    def fill(self, form_type: str, field_map: dict[str, str]) -> bytes:
        """
        Load template for form_type, write field_map into every page, return PDF bytes.

        Args:
            form_type: One of the keys in FORM_TEMPLATES (e.g. "form_101").
            field_map: {pdf_field_name: value_string}. Unknown field names are
                       silently ignored. Checkbox fields expect "/Yes" or "/Off".

        Raises:
            KeyError: form_type not in FORM_TEMPLATES.
            FileNotFoundError: template PDF missing from PDF_FORMS_DIRECTORY.
        """
        filename = FORM_TEMPLATES[form_type]  # KeyError if unknown
        template_path = Path(settings.PDF_FORMS_DIRECTORY) / filename

        reader = pypdf.PdfReader(str(template_path))
        writer = pypdf.PdfWriter()
        writer.append(reader)

        # update_page_form_field_values fills matching fields on one page at a time.
        # auto_regenerate=False keeps visual appearance stable across viewers.
        for page in writer.pages:
            writer.update_page_form_field_values(
                page, field_map, auto_regenerate=False
            )

        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_filler.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/services/pdf_filler.py backend/apps/forms/tests/test_pdf_filler.py
git commit -m "feat(forms): add PDFFormFiller service — fills AO court templates via pypdf"
```

---

## Task 2: Copy official form PDFs into the Docker image

**Files:**

- Modify: `Dockerfile.heroku`
- Check: `.dockerignore` (must NOT exclude the forms directory)

The official forms live at `Official Bankruptcy Rules+Forms/Forms/` in the repo root.  
The Django setting `PDF_FORMS_DIRECTORY = BASE_DIR.parent / "data" / "forms" / "pdfs"` resolves to `/data/forms/pdfs` inside the container.

- [ ] **Step 1: Check .dockerignore does not exclude the forms directory**

```bash
grep -i "official\|bankruptcy\|forms" /Volumes/Containers/DigniFi/.dockerignore
```

If it lists the directory, remove that line. If the file doesn't exist, nothing to do.

- [ ] **Step 2: Add COPY instruction to Dockerfile.heroku**

In `Dockerfile.heroku`, find the line `RUN mkdir -p /data/forms/pdfs` and replace it with:

```dockerfile
# Bake official AO court PDF templates into the image for PDF filling at runtime.
COPY "Official Bankruptcy Rules+Forms/Forms/" /data/forms/pdfs/
```

The `mkdir -p` is no longer needed because `COPY` creates the destination directory.

- [ ] **Step 3: Verify the build includes the forms**

```bash
# Build locally and check the directory exists in the image
docker build -f Dockerfile.heroku -t dignifi-test . && \
  docker run --rm dignifi-test ls /data/forms/pdfs | head -5
```

Expected: file listing showing `form_b_101_0624_fillable_clean.pdf` and others.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile.heroku .dockerignore
git commit -m "feat(docker): bake official court PDF templates into image for PDF filling"
```

---

## Task 3: Download action on GeneratedFormViewSet

**Files:**

- Modify: `backend/apps/forms/views.py`
- Create test: `backend/apps/forms/tests/test_download_action.py`

**Context:** `GeneratedFormViewSet` lives in `backend/apps/forms/views.py`. The registry function `get_generator(form_type, session)` is already imported there. `PDFFormFiller` needs to be imported. The view must:

1. Ownership-check the form (already handled by `get_object()` which filters by `session__user`).
2. Call `generator.pdf_field_map()` — this method is added by the field-mappings plan. Until all 13 are done, a `NotImplementedError` fallback returns a 501.
3. Fill the template and stream as `application/pdf`.
4. Mark the record `downloaded` if currently `generated`.

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/forms/tests/test_download_action.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
from apps.forms.models import GeneratedForm


@pytest.mark.django_db
def test_download_returns_pdf(api_client_authed, generated_form_factory):
    """GET /api/forms/{id}/download/ streams application/pdf."""
    form = generated_form_factory(status="generated")
    fake_pdf = b"%PDF-1.4 fake content"

    with patch("apps.forms.views.get_generator") as mock_gen_cls, \
         patch("apps.forms.views.PDFFormFiller") as mock_filler_cls:
        mock_gen = MagicMock()
        mock_gen.pdf_field_map.return_value = {"Debtor1.First name": "Maria"}
        mock_gen_cls.return_value = mock_gen

        mock_filler = MagicMock()
        mock_filler.fill.return_value = fake_pdf
        mock_filler_cls.return_value = mock_filler

        url = reverse("generatedform-download", kwargs={"pk": form.pk})
        response = api_client_authed.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert b"%PDF" in response.content


@pytest.mark.django_db
def test_download_marks_form_downloaded(api_client_authed, generated_form_factory):
    """download action transitions status generated → downloaded."""
    form = generated_form_factory(status="generated")
    fake_pdf = b"%PDF-1.4 fake"

    with patch("apps.forms.views.get_generator") as mock_gen_cls, \
         patch("apps.forms.views.PDFFormFiller") as mock_filler_cls:
        mock_gen_cls.return_value.pdf_field_map.return_value = {}
        mock_filler_cls.return_value.fill.return_value = fake_pdf
        url = reverse("generatedform-download", kwargs={"pk": form.pk})
        api_client_authed.get(url)

    form.refresh_from_db()
    assert form.status == "downloaded"


@pytest.mark.django_db
def test_download_returns_501_when_mapping_not_implemented(
    api_client_authed, generated_form_factory
):
    """download returns 501 when generator lacks pdf_field_map()."""
    form = generated_form_factory(status="generated")

    with patch("apps.forms.views.get_generator") as mock_gen_cls:
        mock_gen_cls.return_value.pdf_field_map.side_effect = NotImplementedError
        url = reverse("generatedform-download", kwargs={"pk": form.pk})
        response = api_client_authed.get(url)

    assert response.status_code == 501
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_download_action.py -v
```

Expected: errors about missing fixtures and missing `download` URL name.

- [ ] **Step 3: Add the download action to GeneratedFormViewSet**

In `backend/apps/forms/views.py`, add these imports near the top with the existing imports:

```python
from django.http import HttpResponse
from apps.forms.services.pdf_filler import PDFFormFiller
```

Then add this method inside `GeneratedFormViewSet`, after the existing `mark_filed` action:

```python
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """
        GET /api/forms/{id}/download/
        Fill the matching AO court PDF template and stream it to the client.
        Marks the form as downloaded on success.
        Returns 501 if the generator does not yet implement pdf_field_map().
        """
        generated_form = self.get_object()
        session = generated_form.session

        generator = get_generator(generated_form.form_type, session)
        try:
            field_map = generator.pdf_field_map()
        except NotImplementedError:
            return Response(
                {"error": "PDF field mapping not yet implemented for this form type."},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        pdf_bytes = PDFFormFiller().fill(generated_form.form_type, field_map)

        if generated_form.status == "generated":
            generated_form.status = "downloaded"
            generated_form.save(update_fields=["status", "updated_at"])

        filename = f"{generated_form.form_type}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
```

- [ ] **Step 4: Add the test fixtures** (if not already in conftest)

In `backend/apps/forms/tests/conftest.py` (create if absent), add:

```python
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.forms.models import GeneratedForm
from apps.intake.models import IntakeSession
from apps.districts.models import District

User = get_user_model()


@pytest.fixture
def api_client_authed(db):
    user = User.objects.create_user(username="testuser", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def generated_form_factory(db, api_client_authed):
    def _make(status="generated"):
        user = User.objects.filter(username="testuser").first()
        district = District.objects.filter(code="ilnd").first()
        if not district:
            district = District.objects.create(
                code="ilnd", name="Northern District of Illinois",
                court_name="U.S. Bankruptcy Court, N.D. Ill.",
                state="IL",
            )
        session = IntakeSession.objects.create(
            user=user, district=district, status="completed", current_step=6
        )
        return GeneratedForm.objects.create(
            session=session,
            form_type="form_121",
            status=status,
            form_data={"debtor_name": "Maria Torres"},
            generated_by=user,
        )
    return _make
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_download_action.py -v
```

Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/apps/forms/views.py backend/apps/forms/tests/test_download_action.py \
        backend/apps/forms/tests/conftest.py
git commit -m "feat(forms): add GET /api/forms/{id}/download/ — fills PDF template and streams it"
```

---

## Task 4: Frontend — downloadForm API function

**Files:**

- Modify: `frontend/src/api/client.ts`

The `apiFetch` helper parses JSON. PDF binary requires raw `fetch`. The `API_BASE_URL` and `getAccessToken` are already defined and exported from this file — use them directly.

- [ ] **Step 1: Add `downloadForm` to `formsAPI` in `frontend/src/api/client.ts`**

Find the `formsAPI` object (around line 479). After the `markFiled` method, add:

```typescript
  /**
   * Download a generated form as a filled PDF.
   * GET /api/forms/{id}/download/
   * Triggers a browser file save dialog.
   */
  downloadForm: async (formId: number, filename: string): Promise<void> => {
    const token = getAccessToken();
    const response = await fetch(`${API_BASE_URL}/forms/${formId}/download/`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      throw new APIClientError(
        `Download failed (${response.status})`,
        response.status,
      );
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(frontend): add api.forms.downloadForm — fetches binary PDF and triggers save"
```

---

## Task 5: FormCard — add onDownload prop and wire the button

**Files:**

- Modify: `frontend/src/components/forms/FormCard.tsx`

**Current state:** `FormCard` accepts `onMarkDownloaded: (formId: number) => Promise<void>`. The "Download" button calls `onMarkDownloaded(generatedForm.id)`.

**Change:** Rename the prop to `onDownload` (the parent will handle both downloading the file and refreshing status). This is a rename + parent update, not a new prop.

- [ ] **Step 1: Update `FormCard.tsx`**

Replace the `FormCardProps` interface and the component signature:

```typescript
interface FormCardProps {
  formType: FormType;
  generatedForm?: GeneratedForm;
  onGenerate: (formType: FormType) => Promise<void>;
  onDownload: (formId: number) => Promise<void>;   // was: onMarkDownloaded
  onMarkFiled: (formId: number) => Promise<void>;
}

export function FormCard({
  formType,
  generatedForm,
  onGenerate,
  onDownload,                                       // was: onMarkDownloaded
  onMarkFiled,
}: FormCardProps) {
```

Replace the Download button's `onClick`:

```tsx
<Button
  size="sm"
  variant="primary"
  onClick={() => handleAction(() => onDownload(generatedForm.id))}
  isLoading={isLoading}
  loadingText="Preparing..."
>
  Download
</Button>
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: error about `onMarkDownloaded` still used in `FormDashboard.tsx` (fixed in Task 6).

- [ ] **Step 3: Commit after Task 6 fixes the caller (bundle these commits)**

---

## Task 6: FormDashboard — wire handleDownload

**Files:**

- Modify: `frontend/src/pages/FormDashboard.tsx`

- [ ] **Step 1: Replace `handleMarkDownloaded` with `handleDownload`**

Find `handleMarkDownloaded`:

```typescript
const handleMarkDownloaded = async (formId: number) => {
  await api.forms.markDownloaded(formId);
  await loadForms();
};
```

Replace with:

```typescript
const handleDownload = async (formId: number) => {
  const form = forms.find((f) => f.id === formId);
  const filename = form ? `${form.form_type}.pdf` : `form_${formId}.pdf`;
  await api.forms.downloadForm(formId, filename);
  await loadForms();
};
```

- [ ] **Step 2: Update the `FormCard` usage in the render**

Find:

```tsx
onMarkDownloaded = { handleMarkDownloaded };
```

Replace with:

```tsx
onDownload = { handleDownload };
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend && npm test -- --run
```

Expected: existing tests pass. If any test references `onMarkDownloaded`, update it to `onDownload`.

- [ ] **Step 5: Commit Tasks 5 + 6 together**

```bash
git add frontend/src/components/forms/FormCard.tsx frontend/src/pages/FormDashboard.tsx
git commit -m "feat(frontend): wire Download button to real PDF download endpoint"
```

---

## Task 7: Deploy and smoke-test

- [ ] **Step 1: Push to Heroku**

```bash
git push heroku main
```

- [ ] **Step 2: Smoke-test with demo user**

Navigate to `https://dignifi.crichalchemist.com/`, click **Try Demo**, then click **Download** on any form that shows status "generated".

Expected:

- Browser save dialog opens with filename `form_XXX.pdf`
- Opening the PDF shows the filled AO court form
- Form status changes to "downloaded" after the download

If the form shows status "downloaded" but no dialog appeared, the download fired but the browser blocked it (pop-up blocker). Try directly on the `/forms` page rather than after an auto-redirect.

- [ ] **Step 3: Check Heroku logs if anything fails**

```bash
heroku logs --tail --app dignifi
```

Look for `501` (field mapping not yet implemented — normal until Layer 2 is merged), `404` (template PDF not found in image — re-check Dockerfile COPY), or `500` (unexpected).

---

## Self-Review

**Spec coverage:**

- ✅ PDFFormFiller service with tests
- ✅ Official PDFs baked into Docker image
- ✅ `download` action streams PDF, marks status
- ✅ 501 graceful fallback when `pdf_field_map()` not yet on a generator
- ✅ Frontend `downloadForm` with binary fetch + programmatic `<a>` click
- ✅ FormCard prop rename + FormDashboard wired
- ✅ Deploy + smoke test

**Interface contract with Layer 2 (field-mappings plan):**
Every generator must implement:

```python
def pdf_field_map(self) -> dict[str, str]:
    """Return {pdf_field_name: value_string} for all fillable fields."""
    ...
```

Checkbox fields use `"/Yes"` (checked) or `"/Off"` (unchecked).
Fields not returned are left blank in the output PDF.
Raise `NotImplementedError` (or leave unimplemented) for forms not yet mapped — the endpoint returns 501.
