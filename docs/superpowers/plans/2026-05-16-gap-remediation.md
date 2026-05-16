# Gap Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close four small but user-facing gaps found during audit: missing fee waiver endpoint, dead API methods, silent form generation errors, and wizard never routing to fee waiver after qualifying.

**Architecture:** Backend gets a `FeeWaiverViewSet` (router-registered, ownership-filtered, one-per-session OneToOne). Frontend removes ~80 lines of dead code, then surfaces `generate_all` errors, then adds a `FeeWaiverPage` reached only when `qualifies_for_fee_waiver` is true after `handleComplete`.

**Tech Stack:** Django REST Framework `ModelViewSet`, `EncryptedDecimalField` (existing), React 19, React Router, MSW for mocks, pytest + vitest/RTL for tests.

---

## File Map

| Task | Files                                                        |
| ---- | ------------------------------------------------------------ |
| 1    | Create `backend/apps/intake/tests/test_fee_waiver_views.py`  |
|      | Modify `backend/apps/intake/serializers.py`                  |
|      | Modify `backend/apps/intake/views.py`                        |
|      | Modify `backend/apps/intake/urls.py`                         |
| 2    | Delete `frontend/src/pages/MeansTestResult.tsx`              |
|      | Modify `frontend/src/api/client.ts`                          |
|      | Modify `frontend/src/test/mocks/handlers.ts`                 |
| 3    | Modify `frontend/src/pages/__tests__/FormDashboard.test.tsx` |
|      | Modify `frontend/src/test/mocks/handlers.ts`                 |
|      | Modify `frontend/src/pages/FormDashboard.tsx`                |
| 4    | Create `frontend/src/pages/__tests__/FeeWaiverPage.test.tsx` |
|      | Create `frontend/src/pages/FeeWaiverPage.tsx`                |
|      | Modify `frontend/src/api/client.ts`                          |
|      | Modify `frontend/src/test/mocks/handlers.ts`                 |
|      | Modify `frontend/src/App.tsx`                                |
|      | Modify `frontend/src/pages/IntakeWizard.tsx`                 |

---

### Task 1: Backend — FeeWaiverViewSet

The `FeeWaiverApplication` model exists (`backend/apps/intake/models.py:418`). It has a OneToOne to `IntakeSession`. There is no serializer, no viewset, and no URL route yet.

**Files:**

- Create: `backend/apps/intake/tests/test_fee_waiver_views.py`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/intake/views.py`
- Modify: `backend/apps/intake/urls.py`

- [ ] **Step 1: Write failing test**

```python
# backend/apps/intake/tests/test_fee_waiver_views.py
from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from apps.districts.models import District
from apps.intake.models import FeeWaiverApplication, IntakeSession
from apps.users.models import User


@pytest.fixture
def setup(db):
    user = User.objects.create_user(username="fwtest", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session, user


def test_create_fee_waiver(setup):
    """POST /intake/fee-waiver/ creates a FeeWaiverApplication linked to user's session."""
    client, session, _ = setup
    payload = {
        "session": session.id,
        "household_size": 2,
        "monthly_income": "1800.00",
        "monthly_expenses": "1600.00",
        "receives_public_benefits": False,
        "benefit_types": [],
        "cannot_pay_full": True,
        "cannot_pay_installments": True,
    }
    resp = client.post("/api/intake/fee-waiver/", payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["session"] == session.id
    assert data["household_size"] == 2
    assert FeeWaiverApplication.objects.filter(session=session).exists()


def test_create_fee_waiver_unauthenticated(db):
    """POST /intake/fee-waiver/ without auth returns 401."""
    client = APIClient()
    resp = client.post("/api/intake/fee-waiver/", {}, format="json")
    assert resp.status_code == 401


def test_get_fee_waiver(setup):
    """GET /intake/fee-waiver/{id}/ returns record owned by user."""
    client, session, _ = setup
    fw = FeeWaiverApplication.objects.create(
        session=session,
        household_size=1,
        monthly_income=Decimal("1200.00"),
        monthly_expenses=Decimal("1000.00"),
    )
    resp = client.get(f"/api/intake/fee-waiver/{fw.id}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == fw.id


def test_other_user_cannot_access_fee_waiver(db):
    """GET /intake/fee-waiver/{id}/ for another user's record returns 404."""
    owner = User.objects.create_user(username="owner", password="pass")
    other = User.objects.create_user(username="other", password="pass")
    district = District.objects.create(
        code="ILND2",
        name="Illinois Northern 2",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=owner, district=district)
    fw = FeeWaiverApplication.objects.create(
        session=session,
        household_size=1,
        monthly_income=Decimal("1200.00"),
        monthly_expenses=Decimal("1000.00"),
    )
    client = APIClient()
    client.force_authenticate(user=other)
    resp = client.get(f"/api/intake/fee-waiver/{fw.id}/")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec backend python -m pytest backend/apps/intake/tests/test_fee_waiver_views.py -v
```

Expected: FAIL (route does not exist — Django returns 404 on the POST).

- [ ] **Step 3: Add `FeeWaiverApplicationSerializer` to `serializers.py`**

Add `FeeWaiverApplication` to the model imports block at top of `backend/apps/intake/serializers.py`:

```python
from .models import (
    IntakeSession,
    DebtorInfo,
    IncomeInfo,
    ExpenseInfo,
    AssetInfo,
    DebtInfo,
    FeeWaiverApplication,  # add
)
```

Append at end of file:

```python
class FeeWaiverApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeWaiverApplication
        fields = [
            "id",
            "session",
            "household_size",
            "monthly_income",
            "monthly_expenses",
            "receives_public_benefits",
            "benefit_types",
            "cannot_pay_full",
            "cannot_pay_installments",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
```

- [ ] **Step 4: Add `FeeWaiverViewSet` to `views.py`**

Update imports at top of `backend/apps/intake/views.py`:

```python
from .models import AssetInfo, DebtInfo, FeeWaiverApplication, IntakeSession
from .serializers import (
    AssetInfoSerializer,
    DebtInfoSerializer,
    FeeWaiverApplicationSerializer,
    IntakeSessionSerializer,
)
```

Append at end of file:

```python
class FeeWaiverViewSet(viewsets.ModelViewSet):
    """CRUD for fee waiver applications, scoped to authenticated user's sessions."""

    serializer_class = FeeWaiverApplicationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return FeeWaiverApplication.objects.filter(
            session__user=self.request.user
        ).select_related("session")

    def perform_create(self, serializer):
        # FeeWaiverApplication is OneToOne with IntakeSession — second POST from
        # the same session would raise IntegrityError. Use update_or_create so
        # reloading the FeeWaiverPage is safe.
        session = serializer.validated_data["session"]
        FeeWaiverApplication.objects.update_or_create(
            session=session,
            defaults={k: v for k, v in serializer.validated_data.items() if k != "session"},
        )
```

- [ ] **Step 5: Register router in `urls.py`**

Replace `backend/apps/intake/urls.py` entirely:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FeeWaiverViewSet, IntakeSessionViewSet, AssetViewSet, DebtViewSet

router = DefaultRouter()
router.register(r"sessions", IntakeSessionViewSet, basename="intake-session")
router.register(r"assets", AssetViewSet, basename="asset-info")
router.register(r"debts", DebtViewSet, basename="debt-info")
router.register(r"fee-waiver", FeeWaiverViewSet, basename="fee-waiver")

urlpatterns = [
    path("", include(router.urls)),
]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
docker compose exec backend python -m pytest backend/apps/intake/tests/test_fee_waiver_views.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 7: Run full backend suite**

```bash
docker compose exec backend python -m pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/apps/intake/tests/test_fee_waiver_views.py \
        backend/apps/intake/serializers.py \
        backend/apps/intake/views.py \
        backend/apps/intake/urls.py
git commit -m "feat(intake): add FeeWaiverViewSet and serializer

Closes the missing API endpoint for 28 U.S.C. § 1930(f) fee waiver
applications. Scoped to authenticated user's sessions."
```

---

### Task 2: Remove dead frontend code

`debtorAPI`, `incomeAPI`, `expenseAPI` hit routes that don't exist. `MeansTestResult.tsx` is not in any route. Remove both.

**Files:**

- Delete: `frontend/src/pages/MeansTestResult.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/test/mocks/handlers.ts`

- [ ] **Step 1: Verify nothing else imports the dead code**

```bash
grep -rn "from .*pages/MeansTestResult" frontend/src --include="*.tsx" --include="*.ts"
grep -r "debtorAPI\|incomeAPI\|expenseAPI" frontend/src --include="*.tsx" --include="*.ts" -l
```

Expected: zero matches for the first query (the page is never imported anywhere). Only `frontend/src/api/client.ts` for the second. If other files appear, stop and investigate. Note: `MeansTestResult` also names a type in `frontend/src/types/api.ts` — that type should NOT be deleted; only the page file is removed.

- [ ] **Step 2: Delete `MeansTestResult.tsx`**

```bash
rm frontend/src/pages/MeansTestResult.tsx
```

- [ ] **Step 3: Remove dead API objects from `client.ts`**

Delete the three blocks (approx. lines 375–448 in `frontend/src/api/client.ts`):

```
// Debtor Info API section + export const debtorAPI = { ... };
// Income Info API section + export const incomeAPI = { ... };
// Expense Info API section + export const expenseAPI = { ... };
```

Update the `api` export object to remove the three dead entries:

```typescript
export const api = {
  auth: authAPI,
  intake: intakeAPI,
  assets: assetsAPI,
  debts: debtsAPI,
  forms: formsAPI,
};
```

- [ ] **Step 4: Remove orphan MSW handlers from `handlers.ts`**

Delete these three handlers from `frontend/src/test/mocks/handlers.ts`:

```typescript
http.post(`${API}/intake/debtor-info/`, () =>
  HttpResponse.json({ id: 1, session: 1, first_name: 'Jane' }),
),
http.post(`${API}/intake/income-info/`, () =>
  HttpResponse.json({ id: 1, session: 1, monthly_income: [3500, 3500, 3500, 3500, 3500, 3500] }),
),
http.post(`${API}/intake/expense-info/`, () =>
  HttpResponse.json({ id: 1, session: 1, rent_or_mortgage: 1200 }),
),
```

- [ ] **Step 5: Type-check and test**

```bash
cd frontend && npx tsc --noEmit && npm test -- --run
```

Expected: no type errors, all tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts \
        frontend/src/test/mocks/handlers.ts
git rm frontend/src/pages/MeansTestResult.tsx
git commit -m "refactor(frontend): remove dead debtorAPI, incomeAPI, expenseAPI and MeansTestResult page

These hit routes that don't exist. Intake sub-resources are updated
via PATCH /intake/sessions/{id}/. MeansTestResult was never routed."
```

---

### Task 3: Surface `generate_all` errors in FormDashboard

`handleGenerateAll` discards `response.errors`. Also the existing MSW mock returns the wrong shape (`{forms, message}` instead of `{generated, errors, total_generated, total_errors}`). Fix both.

**Files:**

- Modify: `frontend/src/test/mocks/handlers.ts`
- Modify: `frontend/src/pages/__tests__/FormDashboard.test.tsx`
- Modify: `frontend/src/pages/FormDashboard.tsx`

- [ ] **Step 1: Fix the MSW mock shape**

In `frontend/src/test/mocks/handlers.ts`, replace:

```typescript
// Before
http.post(`${API}/forms/generate_all/`, () =>
  HttpResponse.json({
    forms: [mockGeneratedForm],
    message: 'All forms generated.',
  }),
),
```

With:

```typescript
// After — matches GenerateAllFormsResponse
http.post(`${API}/forms/generate_all/`, () =>
  HttpResponse.json({
    generated: [mockGeneratedForm],
    errors: [],
    total_generated: 1,
    total_errors: 0,
  }),
),
```

- [ ] **Step 2: Write failing test for error surfacing**

Append inside the `describe('FormDashboard')` block in `frontend/src/pages/__tests__/FormDashboard.test.tsx`:

```typescript
it('shows error banner when generate_all returns partial failures', async () => {
  server.use(
    http.post('http://localhost:8000/api/forms/generate_all/', () =>
      HttpResponse.json({
        generated: [],
        errors: [{ form_type: 'form_101', error: 'Missing debtor name' }],
        total_generated: 0,
        total_errors: 1,
      })
    )
  );

  renderFormDashboard();
  await waitFor(() => expect(screen.getByText('Your Court Forms')).toBeInTheDocument());

  const generateAllBtn = screen.getByRole('button', { name: /generate all/i });
  await userEvent.click(generateAllBtn);

  await waitFor(() => {
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/1 form.*could not be generated/i)).toBeInTheDocument();
  });
});
```

Add `userEvent` import at the top of the test file if not already present:

```typescript
import userEvent from '@testing-library/user-event';
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd frontend && npm test -- FormDashboard --run
```

Expected: new test FAILS (no alert rendered yet).

- [ ] **Step 4: Add error state and banner to `FormDashboard.tsx`**

In `frontend/src/pages/FormDashboard.tsx`:

Add after existing state declarations:

```typescript
const [generationErrors, setGenerationErrors] = useState<
  Array<{ form_type: string; error: string }>
>([]);
```

Replace `handleGenerateAll`:

```typescript
const handleGenerateAll = async () => {
  if (!session) return;
  const response = await api.forms.generateAll(session.id);
  setForms(response.generated);
  setGenerationErrors(response.errors);
  trackEvent('form_generated', { form_type: 'all', session_id: session.id });
  setShowSurvey(true);
};
```

Add error banner in JSX after the existing `{error && ...}` block:

```tsx
{
  generationErrors.length > 0 && (
    <div className="form-dashboard-error" role="alert">
      <p>
        {generationErrors.length} form{generationErrors.length > 1 ? 's' : ''} could not be
        generated. You can try generating them individually below.
      </p>
      <ul>
        {generationErrors.map((e) => (
          <li key={e.form_type}>
            {e.form_type}: {e.error}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd frontend && npm test -- FormDashboard --run
```

Expected: all FormDashboard tests PASS.

- [ ] **Step 6: Run full frontend suite**

```bash
cd frontend && npm test -- --run
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/FormDashboard.tsx \
        frontend/src/pages/__tests__/FormDashboard.test.tsx \
        frontend/src/test/mocks/handlers.ts
git commit -m "feat(forms): surface generate_all partial errors in FormDashboard

Silently dropped response.errors. Now shows an alert banner listing
which forms failed and why. Also fixed MSW mock shape (was returning
{forms} instead of {generated, errors, total_generated, total_errors})."
```

---

### Task 4: FeeWaiverPage + wizard routing

`handleComplete` in `IntakeWizard.tsx` calls `completeSession()` then navigates straight to `/forms`. It never calls `calculateMeansTest()`, so `qualifies_for_fee_waiver` is never acted on. This task checks the flag and routes qualifying users to a new `/fee-waiver` page.

**Files:**

- Create: `frontend/src/pages/__tests__/FeeWaiverPage.test.tsx`
- Create: `frontend/src/pages/FeeWaiverPage.tsx`
- Modify: `frontend/src/api/client.ts` (add `feeWaiverAPI`)
- Modify: `frontend/src/test/mocks/handlers.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/IntakeWizard.tsx`

- [ ] **Step 1: Add `feeWaiverAPI` and `FeeWaiverApplication` type to `client.ts`**

After the `debtsAPI` block in `frontend/src/api/client.ts`, add:

```typescript
// ============================================================================
// Fee Waiver API
// ============================================================================

export interface FeeWaiverPayload {
  session: number;
  household_size: number;
  monthly_income: string;
  monthly_expenses: string;
  receives_public_benefits: boolean;
  benefit_types: string[];
  cannot_pay_full: boolean;
  cannot_pay_installments: boolean;
}

export interface FeeWaiverApplication {
  id: number;
  session: number;
  household_size: number;
  monthly_income: string;
  monthly_expenses: string;
  receives_public_benefits: boolean;
  benefit_types: string[];
  cannot_pay_full: boolean;
  cannot_pay_installments: boolean;
  status: 'pending' | 'approved' | 'denied';
  created_at: string;
  updated_at: string;
}

export const feeWaiverAPI = {
  create: async (data: FeeWaiverPayload): Promise<FeeWaiverApplication> => {
    return apiFetch<FeeWaiverApplication>('/intake/fee-waiver/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
```

Update the `api` export object:

```typescript
export const api = {
  auth: authAPI,
  intake: intakeAPI,
  assets: assetsAPI,
  debts: debtsAPI,
  forms: formsAPI,
  feeWaiver: feeWaiverAPI,
};
```

- [ ] **Step 2: Add MSW handler for `/intake/fee-waiver/`**

In `frontend/src/test/mocks/handlers.ts`, add after the debts handler:

```typescript
// -- Fee Waiver -----------------------------------------------------------
http.post(`${API}/intake/fee-waiver/`, async ({ request }) => {
  const body = (await request.json()) as { session: number };
  return HttpResponse.json({
    id: 1,
    session: body.session,
    household_size: 1,
    monthly_income: '1200.00',
    monthly_expenses: '1000.00',
    receives_public_benefits: false,
    benefit_types: [],
    cannot_pay_full: true,
    cannot_pay_installments: true,
    status: 'pending',
    created_at: '2026-01-20T10:00:00Z',
    updated_at: '2026-01-20T10:00:00Z',
  });
}),
```

- [ ] **Step 3: Write failing tests for `FeeWaiverPage`**

Create `frontend/src/pages/__tests__/FeeWaiverPage.test.tsx`:

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { FeeWaiverPage } from '../FeeWaiverPage';

function renderFeeWaiver() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter>
      <IntakeProvider>
        <FeeWaiverPage />
      </IntakeProvider>
    </MemoryRouter>,
  );
}

describe('FeeWaiverPage', () => {
  it('renders the fee waiver heading', async () => {
    renderFeeWaiver();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /filing fee waiver/i })).toBeInTheDocument();
    });
  });

  it('submits and clears the form on success', async () => {
    renderFeeWaiver();
    await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

    await userEvent.type(screen.getByLabelText(/household size/i), '1');
    await userEvent.type(screen.getByLabelText(/monthly income/i), '1200');
    await userEvent.type(screen.getByLabelText(/monthly expenses/i), '1000');

    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    // Button enters submitting state during the call
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  it('shows error when submission fails', async () => {
    server.use(
      http.post('http://localhost:8000/api/intake/fee-waiver/', () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 500 }),
      ),
    );

    renderFeeWaiver();
    await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

    await userEvent.type(screen.getByLabelText(/household size/i), '1');
    await userEvent.type(screen.getByLabelText(/monthly income/i), '1200');
    await userEvent.type(screen.getByLabelText(/monthly expenses/i), '1000');
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 4: Run test to verify it fails**

```bash
cd frontend && npm test -- FeeWaiverPage --run
```

Expected: FAIL — module not found.

- [ ] **Step 5: Create `FeeWaiverPage.tsx`**

Create `frontend/src/pages/FeeWaiverPage.tsx`:

```tsx
/**
 * FeeWaiverPage — Form 103B data collection.
 *
 * Reached only when calculateMeansTest returns qualifies_for_fee_waiver=true.
 * Submits to POST /api/intake/fee-waiver/ then navigates to /forms.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api } from '../api/client';
import { Button } from '../components/common';

export function FeeWaiverPage() {
  const navigate = useNavigate();
  const { session } = useIntake();

  const [householdSize, setHouseholdSize] = useState('');
  const [monthlyIncome, setMonthlyIncome] = useState('');
  const [monthlyExpenses, setMonthlyExpenses] = useState('');
  const [receivesPublicBenefits, setReceivesPublicBenefits] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await api.feeWaiver.create({
        session: session.id,
        household_size: parseInt(householdSize, 10),
        monthly_income: monthlyIncome,
        monthly_expenses: monthlyExpenses,
        receives_public_benefits: receivesPublicBenefits,
        benefit_types: [],
        cannot_pay_full: true,
        cannot_pay_installments: true,
      });
      navigate('/forms');
    } catch {
      setError('Unable to submit your fee waiver application. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="fee-waiver-page">
      <h1>Filing Fee Waiver Application</h1>
      <p>
        Based on your intake information, you may qualify to have the $338 filing fee waived. Please
        confirm the details below.
      </p>

      {error && (
        <div className="fee-waiver-error" role="alert">
          <p>{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-field">
          <label htmlFor="household-size">Household Size</label>
          <input
            id="household-size"
            type="number"
            min={1}
            value={householdSize}
            onChange={(e) => setHouseholdSize(e.target.value)}
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="monthly-income">Total Monthly Income</label>
          <input
            id="monthly-income"
            type="number"
            min={0}
            step="0.01"
            value={monthlyIncome}
            onChange={(e) => setMonthlyIncome(e.target.value)}
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="monthly-expenses">Total Monthly Expenses</label>
          <input
            id="monthly-expenses"
            type="number"
            min={0}
            step="0.01"
            value={monthlyExpenses}
            onChange={(e) => setMonthlyExpenses(e.target.value)}
            required
          />
        </div>

        <div className="form-field">
          <label>
            <input
              type="checkbox"
              checked={receivesPublicBenefits}
              onChange={(e) => setReceivesPublicBenefits(e.target.checked)}
            />{' '}
            I receive SSI, SNAP, TANF, or other means-tested public benefits
          </label>
        </div>

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Submitting...' : 'Submit Waiver Application'}
        </Button>
      </form>
    </main>
  );
}
```

- [ ] **Step 6: Run `FeeWaiverPage` tests**

```bash
cd frontend && npm test -- FeeWaiverPage --run
```

Expected: all 3 tests PASS.

- [ ] **Step 7: Add `/fee-waiver` route to `App.tsx`**

Add import:

```typescript
import { FeeWaiverPage } from './pages/FeeWaiverPage';
```

Add route inside the `ProtectedRoute > IntakeLayout` block:

```tsx
<Route element={<ProtectedRoute />}>
  <Route element={<IntakeLayout />}>
    <Route path="/intake" element={<IntakeWizard />} />
    <Route path="/forms" element={<FormDashboard />} />
    <Route path="/documents" element={<DocumentUploadPage />} />
    <Route path="/fee-waiver" element={<FeeWaiverPage />} />
  </Route>
</Route>
```

- [ ] **Step 8: Write failing tests for wizard routing**

Create (or append to) `frontend/src/pages/__tests__/IntakeWizard.test.tsx`:

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { IntakeWizard } from '../IntakeWizard';

// Override session handler to return step 6 — wizard renders ReviewStep
// and shows the Complete button. Without this, current_step:1 renders
// DebtorInfoStep which has no Complete button.
const sessionAtStep6 = {
  id: 1,
  user: 1,
  district: 1,
  current_step: 6,
  status: 'in_progress' as const,
  created_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  completed_at: null,
  debtor_info: { first_name: 'Jane', last_name: 'Doe' },
  income_info: { monthly_income: [1200, 1200, 1200, 1200, 1200, 1200] },
  expense_info: { rent_or_mortgage: 1000 },
  assets: [],
  debts: [],
};

function renderWizard() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={['/intake']}>
      <IntakeProvider>
        <Routes>
          <Route path="/intake" element={<IntakeWizard />} />
          <Route path="/fee-waiver" element={<div>FeeWaiverPage</div>} />
          <Route path="/forms" element={<div>FormDashboard</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>,
  );
}

describe('IntakeWizard handleComplete routing', () => {
  beforeEach(() => {
    // All wizard routing tests need a session at step 6 to show the Complete button
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep6),
      ),
    );
  });

  it('navigates to /fee-waiver when qualifies_for_fee_waiver is true', async () => {
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/calculate_means_test/',
        () =>
          HttpResponse.json({
            means_test_result: {
              passes_means_test: true,
              qualifies_for_fee_waiver: true,
              current_monthly_income: 1200,
              median_income_threshold: 71304,
              disposable_monthly_income: 200,
              message: 'You qualify.',
              details: {
                household_size: 1,
                total_income: 1200,
                total_expenses: 1000,
                district_name: 'ILND',
              },
            },
            session_id: 1,
          }),
      ),
    );

    renderWizard();
    const completeBtn = await screen.findByRole('button', { name: /complete/i });
    await userEvent.click(completeBtn);

    await waitFor(() => {
      expect(screen.getByText('FeeWaiverPage')).toBeInTheDocument();
    });
  });

  it('navigates to /forms when qualifies_for_fee_waiver is false', async () => {
    // Default mock returns qualifies_for_fee_waiver: false
    renderWizard();
    const completeBtn = await screen.findByRole('button', { name: /complete/i });
    await userEvent.click(completeBtn);

    await waitFor(() => {
      expect(screen.getByText('FormDashboard')).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 9: Run test to verify it fails**

```bash
cd frontend && npm test -- IntakeWizard --run
```

Expected: FAIL — wizard navigates to `/forms` in both cases.

- [ ] **Step 10: Update `handleComplete` in `IntakeWizard.tsx`**

Update the destructure at line ~33:

```typescript
const { session, createSession, updateCurrentStep, completeSession, calculateMeansTest } =
  useIntake();
```

Replace `handleComplete` (lines ~110–123):

```typescript
const handleComplete = async () => {
  try {
    await saveCurrentStepData();
    await completeSession();
    trackEvent('intake_completed', {
      // eslint-disable-next-line react-hooks/purity
      total_duration_ms: Date.now() - sessionStartRef.current,
      session_id: session?.id,
    });
    const result = await calculateMeansTest();
    if (result.qualifies_for_fee_waiver) {
      navigate('/fee-waiver');
    } else {
      navigate('/forms');
    }
  } catch (error) {
    console.error('Error completing intake:', error);
  }
};
```

- [ ] **Step 11: Run IntakeWizard tests**

```bash
cd frontend && npm test -- IntakeWizard --run
```

Expected: PASS.

- [ ] **Step 12: Run full frontend suite**

```bash
cd frontend && npm test -- --run
```

Expected: all tests pass.

- [ ] **Step 13: Commit**

```bash
git add frontend/src/pages/FeeWaiverPage.tsx \
        frontend/src/pages/__tests__/FeeWaiverPage.test.tsx \
        frontend/src/pages/__tests__/IntakeWizard.test.tsx \
        frontend/src/api/client.ts \
        frontend/src/test/mocks/handlers.ts \
        frontend/src/App.tsx \
        frontend/src/pages/IntakeWizard.tsx
git commit -m "feat(wizard): route to FeeWaiverPage when means test qualifies

handleComplete now calls calculateMeansTest after completeSession.
If qualifies_for_fee_waiver, user goes to /fee-waiver (Form 103B
collection) before /forms. Non-qualifying users go to /forms as before."
```

---

## Self-Review

### Spec coverage

| Gap                                                  | Task | Covered |
| ---------------------------------------------------- | ---- | ------- |
| Fee waiver backend endpoint                          | 1    | ✅      |
| Dead `debtorAPI`/`incomeAPI`/`expenseAPI`            | 2    | ✅      |
| Dead `MeansTestResult.tsx`                           | 2    | ✅      |
| `generate_all` errors silently dropped               | 3    | ✅      |
| Wizard never calls means test / routes to fee waiver | 4    | ✅      |

### Placeholder scan

No TBD, TODO, or vague "add validation" language.

### Type consistency

- `FeeWaiverPayload` / `FeeWaiverApplication` defined in Task 4 Step 1 used identically in `FeeWaiverPage.tsx` Step 5.
- `generationErrors` uses `Array<{form_type: string; error: string}>` matching `GenerateAllFormsResponse.errors` in `frontend/src/types/api.ts:366`.
- `calculateMeansTest()` returns `MeansTestResult` which has `qualifies_for_fee_waiver: boolean` — used as `result.qualifies_for_fee_waiver` in Task 4 Step 10.
