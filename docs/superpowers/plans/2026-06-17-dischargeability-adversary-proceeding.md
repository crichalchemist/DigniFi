# Dischargeability & Adversary Proceeding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flag non-dischargeable debts, create adversary proceedings for student loans, and show users UPL-compliant explanations of their discharge options.

**Architecture:** DischargeabilityClassifier evaluates debts when saved. AdversaryProceeding model tracks student loan discharge process. DebtExplanationsPanel shows summary to user. All messaging is informational, never advisory.

**Tech Stack:** Python, Django, DRF, React 19, TypeScript, pytest, vitest

## Global Constraints

- UPL boundary: all text is informational, never advisory
- Never use: "you should", "you qualify for", "you will be discharged"
- Use: "generally non-dischargeable", "may require", "you can request"
- Adversary proceedings are informational tracking only — DigniFi does not file them

---

### Task 1: Dischargeability Classifier

**Files:**

- Create: `backend/apps/eligibility/services/dischargeability_classifier.py`
- Create: `backend/apps/eligibility/tests/test_dischargeability_classifier.py`

**Interfaces:**

- Consumes: `DebtInfo` instances from a session
- Produces: Classification dict with dischargeable flag, reason, proceeding_needed

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/eligibility/tests/test_dischargeability_classifier.py
import pytest
from decimal import Decimal
from apps.eligibility.services.dischargeability_classifier import (
    DischargeabilityClassifier, classify_debt,
)
from apps.districts.models import District
from apps.intake.models import DebtInfo, IntakeSession
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def session_with_debts(db):
    user = User.objects.create_user(username="discharge", password="pass")
    district = District.objects.create(
        code="ILND", name="Northern District of Illinois", state="IL",
        court_name="U.S. Bankruptcy Court", filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtInfo.objects.create(
        session=session, creditor_name="Navient", amount_owed=Decimal("28000"),
        is_secured=False, is_priority=False, debt_type="student_loan",
    )
    DebtInfo.objects.create(
        session=session, creditor_name="Chase", amount_owed=Decimal("5000"),
        is_secured=False, is_priority=False, debt_type="credit_card",
    )
    DebtInfo.objects.create(
        session=session, creditor_name="IRS", amount_owed=Decimal("3000"),
        is_secured=False, is_priority=True, debt_type="taxes",
    )
    return session

@pytest.mark.django_db
class TestClassifyDebt:
    def test_student_loan_non_dischargeable(self):
        debt = type("D", (), {"debt_type": "student_loan"})()
        result = classify_debt(debt)
        assert result["dischargeable"] is False
        assert "523" in result["reason"]

    def test_credit_card_dischargeable(self):
        debt = type("D", (), {"debt_type": "credit_card"})()
        result = classify_debt(debt)
        assert result["dischargeable"] is True

    def test_child_support_non_dischargeable(self):
        debt = type("D", (), {"debt_type": "child_support"})()
        result = classify_debt(debt)
        assert result["dischargeable"] is False

    def test_unknown_type_dischargeable(self):
        debt = type("D", (), {"debt_type": "medical"})()
        result = classify_debt(debt)
        assert result["dischargeable"] is True

@pytest.mark.django_db
class TestDischargeabilityClassifier:
    def test_evaluate_flags_student_loan(self, session_with_debts):
        classifier = DischargeabilityClassifier(session_with_debts)
        results = classifier.evaluate()
        student = [r for r in results if r["debt_type"] == "student_loan"][0]
        assert student["dischargeable"] is False
        assert student["proceeding_needed"] is True

    def test_evaluate_counts_dischargeable(self, session_with_debts):
        classifier = DischargeabilityClassifier(session_with_debts)
        results = classifier.evaluate()
        dischargeable = sum(1 for r in results if r["dischargeable"])
        assert dischargeable == 1  # Only credit card
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/eligibility/tests/test_dischargeability_classifier.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

```python
# backend/apps/eligibility/services/dischargeability_classifier.py
"""Classify debts as dischargeable or non-dischargeable in Chapter 7."""

from apps.intake.models import IntakeSession

NON_DISCHARGEABLE_TYPES = {
    "student_loan": "11 U.S.C. § 523(a)(8) — requires adversary proceeding",
    "child_support": "11 U.S.C. § 523(a)(5) — domestic support obligation",
    "alimony": "11 U.S.C. § 523(a)(5) — domestic support obligation",
    "taxes": "11 U.S.C. § 523(a)(1) — certain tax debts",
    "restitution": "11 U.S.C. § 523(a)(6) — willful and malicious injury",
}


def classify_debt(debt) -> dict:
    reason = NON_DISCHARGEABLE_TYPES.get(debt.debt_type)
    proceeding_needed = (debt.debt_type == "student_loan")
    return {
        "dischargeable": reason is None,
        "reason": reason or "",
        "proceeding_needed": proceeding_needed,
    }


class DischargeabilityClassifier:
    def __init__(self, session: IntakeSession):
        self.session = session

    def evaluate(self) -> list[dict]:
        results = []
        for debt in self.session.debts.all():
            classification = classify_debt(debt)
            results.append({
                "debt_id": debt.id,
                "creditor": debt.creditor_name,
                "debt_type": debt.debt_type,
                **classification,
            })
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/eligibility/tests/test_dischargeability_classifier.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/eligibility/services/dischargeability_classifier.py backend/apps/eligibility/tests/test_dischargeability_classifier.py
git commit -m "feat(eligibility): add dischargeability classifier for Chapter 7 debts"
```

---

### Task 2: AdversaryProceeding Model + DebtInfo Extension

**Files:**

- Modify: `backend/apps/intake/models.py`
- Create: `backend/apps/intake/migrations/0010_add_adversary_proceedings.py`
- Create: `backend/apps/intake/tests/test_adversary_proceedings.py`

**Interfaces:**

- Produces: AdversaryProceeding model, extended DebtInfo fields

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/intake/tests/test_adversary_proceedings.py
import pytest
from decimal import Decimal
from apps.intake.models import AdversaryProceeding, DebtInfo, IntakeSession
from apps.districts.models import District
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def session_with_student_loan(db):
    user = User.objects.create_user(username="adversary", password="pass")
    district = District.objects.create(
        code="ILND", name="Northern District of Illinois", state="IL",
        court_name="U.S. Bankruptcy Court", filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    debt = DebtInfo.objects.create(
        session=session, creditor_name="Navient", amount_owed=Decimal("28000"),
        is_secured=False, is_priority=False, debt_type="student_loan",
    )
    return session, debt

@pytest.mark.django_db
class TestAdversaryProceeding:
    def test_create_proceeding(self, session_with_student_loan):
        session, debt = session_with_student_loan
        ap = AdversaryProceeding.objects.create(
            session=session, debt=debt, proceeding_type="student_loan",
            lender_name="Navient", loan_amount=Decimal("28000"),
        )
        assert ap.status == "identified"
        assert ap.proceeding_type == "student_loan"

    def test_debt_flagged_non_dischargeable(self, session_with_student_loan):
        session, debt = session_with_student_loan
        debt.is_dischargeable = False
        debt.adversary_proceeding_needed = True
        debt.save()
        debt.refresh_from_db()
        assert debt.is_dischargeable is False
        assert debt.adversary_proceeding_needed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/intake/tests/test_adversary_proceedings.py -v`
Expected: FAIL (model doesn't exist yet)

- [ ] **Step 3: Add model + DebtInfo fields**

Add to `backend/apps/intake/models.py`:

```python
class AdversaryProceeding(models.Model):
    PROCEEDING_TYPES = [
        ("student_loan", "Student Loan Discharge (§ 523(a)(8))"),
        ("other", "Other Non-Dischargeable Debt"),
    ]
    STATUS_CHOICES = [
        ("identified", "Identified"),
        ("filed", "Filed"),
        ("pending", "Pending"),
        ("granted", "Granted"),
        ("denied", "Denied"),
        ("settled", "Settled"),
    ]
    session = models.ForeignKey(IntakeSession, on_delete=models.CASCADE, related_name="adversary_proceedings")
    debt = models.ForeignKey("DebtInfo", on_delete=models.CASCADE, null=True, blank=True)
    proceeding_type = models.CharField(max_length=20, choices=PROCEEDING_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="identified")
    lender_name = models.CharField(max_length=255, blank=True)
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    loan_type = models.CharField(max_length=50, blank=True)
    hardship_narrative = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "adversary_proceedings"
```

Add to DebtInfo:

```python
    is_dischargeable = models.BooleanField(default=True)
    adversary_proceeding_needed = models.BooleanField(default=False)
```

Run: `python manage.py makemigrations intake --name add_adversary_proceedings`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/intake/tests/test_adversary_proceedings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/intake/models.py backend/apps/intake/migrations/ backend/apps/intake/tests/test_adversary_proceedings.py
git commit -m "feat(intake): add AdversaryProceeding model and DebtInfo dischargeability fields"
```

---

### Task 3: DischargeabilityService

**Files:**

- Create: `backend/apps/eligibility/services/dischargeability_service.py`
- Create: `backend/apps/eligibility/tests/test_dischargeability_service.py`

**Interfaces:**

- Consumes: IntakeSession, DebtInfo, AdversaryProceeding
- Produces: Creates AdversaryProceeding records for non-dischargeable debts

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/eligibility/tests/test_dischargeability_service.py
import pytest
from decimal import Decimal
from apps.eligibility.services.dischargeability_service import DischargeabilityService
from apps.intake.models import AdversaryProceeding, DebtInfo, IntakeSession
from apps.districts.models import District
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def session_with_student_loan(db):
    user = User.objects.create_user(username="dsvctest", password="pass")
    district = District.objects.create(
        code="ILND", name="Northern District of Illinois", state="IL",
        court_name="U.S. Bankruptcy Court", filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtInfo.objects.create(
        session=session, creditor_name="Navient", amount_owed=Decimal("28000"),
        is_secured=False, is_priority=False, debt_type="student_loan",
    )
    DebtInfo.objects.create(
        session=session, creditor_name="Chase", amount_owed=Decimal("5000"),
        is_secured=False, is_priority=False, debt_type="credit_card",
    )
    return session

@pytest.mark.django_db
class TestDischargeabilityService:
    def test_flags_student_loan(self, session_with_student_loan):
        svc = DischargeabilityService(session_with_student_loan)
        results = svc.evaluate()
        navient = [r for r in results if r["creditor"] == "Navient"][0]
        debt = DebtInfo.objects.get(creditor_name="Navient")
        assert debt.is_dischargeable is False
        assert debt.adversary_proceeding_needed is True

    def test_creates_adversary_proceeding(self, session_with_student_loan):
        svc = DischargeabilityService(session_with_student_loan)
        svc.evaluate()
        aps = AdversaryProceeding.objects.filter(session=session_with_student_loan)
        assert aps.count() == 1
        assert aps.first().proceeding_type == "student_loan"

    def test_does_not_duplicate_proceedings(self, session_with_student_loan):
        svc = DischargeabilityService(session_with_student_loan)
        svc.evaluate()
        svc.evaluate()
        assert AdversaryProceeding.objects.filter(session=session_with_student_loan).count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/eligibility/tests/test_dischargeability_service.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

```python
# backend/apps/eligibility/services/dischargeability_service.py
"""Evaluate dischargeability and create adversary proceedings."""
from apps.eligibility.services.dischargeability_classifier import classify_debt
from apps.intake.models import AdversaryProceeding, IntakeSession


class DischargeabilityService:
    def __init__(self, session: IntakeSession):
        self.session = session

    def evaluate(self) -> list[dict]:
        results = []
        debts_to_update = []
        for debt in self.session.debts.all():
            classification = classify_debt(debt)

            if debt.is_dischargeable != classification["dischargeable"] or debt.adversary_proceeding_needed != classification["proceeding_needed"]:
                debt.is_dischargeable = classification["dischargeable"]
                debt.adversary_proceeding_needed = classification["proceeding_needed"]
                debts_to_update.append(debt)

            if classification["proceeding_needed"]:
                self._ensure_proceeding(debt, classification)

            results.append({
                "debt_id": debt.id,
                "creditor": debt.creditor_name,
                "debt_type": debt.debt_type,
                **classification,
            })

        if debts_to_update:
            from apps.intake.models import DebtInfo
            DebtInfo.objects.bulk_update(debts_to_update, ["is_dischargeable", "adversary_proceeding_needed"])

        return results

    def _ensure_proceeding(self, debt, classification):
        AdversaryProceeding.objects.get_or_create(
            session=self.session,
            debt=debt,
            defaults={
                "proceeding_type": "student_loan",
                "lender_name": debt.creditor_name,
                "loan_amount": debt.amount_owed,
            },
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/eligibility/tests/test_dischargeability_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/eligibility/services/dischargeability_service.py backend/apps/eligibility/tests/test_dischargeability_service.py
git commit -m "feat(eligibility): add dischargeability service with adversary proceeding creation"
```

---

### Task 4: Dischargeability API Endpoint

**Files:**

- Modify: `backend/apps/eligibility/views.py`
- Modify: `backend/apps/eligibility/urls.py`
- Create: `backend/apps/eligibility/tests/test_dischargeability_views.py`

**Interfaces:**

- Produces: POST /api/intake/sessions/{id}/dischargeability/

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/eligibility/tests/test_dischargeability_views.py
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from apps.intake.models import DebtInfo, IntakeSession
from apps.districts.models import District
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def auth_client_with_student_loan(db):
    user = User.objects.create_user(username="discview", password="pass")
    district = District.objects.create(
        code="ILND", name="Northern District of Illinois", state="IL",
        court_name="U.S. Bankruptcy Court", filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtInfo.objects.create(
        session=session, creditor_name="Navient", amount_owed=Decimal("28000"),
        is_secured=False, is_priority=False, debt_type="student_loan",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session

@pytest.mark.django_db
class TestDischargeabilityView:
    def test_returns_classification(self, auth_client_with_student_loan):
        client, session = auth_client_with_student_loan
        url = reverse("intakesession-dischargeability", kwargs={"pk": session.pk})
        response = client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["debt_type"] == "student_loan"
        assert data[0]["dischargeable"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/eligibility/tests/test_dischargeability_views.py -v`
Expected: FAIL (no URL or view)

- [ ] **Step 3: Write view + URL**

Add to IntakeSessionViewSet in `backend/apps/intake/views.py`:

```python
    @action(detail=True, methods=["post"], url_path="dischargeability", url_name="dischargeability")
    def dischargeability(self, request, pk=None):
        session = self.get_object()
        from apps.eligibility.services.dischargeability_service import DischargeabilityService
        svc = DischargeabilityService(session)
        results = svc.evaluate()
        return Response(results)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/eligibility/tests/test_dischargeability_views.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/eligibility/tests/test_dischargeability_views.py backend/apps/intake/views.py
git commit -m "feat(intake): add dischargeability evaluation endpoint"
```

---

### Task 5: Frontend — DebtExplanationsPanel

**Files:**

- Create: `frontend/src/components/forms/DebtExplanationsPanel.tsx`
- Create: `frontend/src/components/forms/__tests__/DebtExplanationsPanel.test.tsx`
- Modify: `frontend/src/pages/FormDashboard.tsx`

**Interfaces:**

- Consumes: dischargeability API response
- Produces: Summary panel showing dischargeable/non-dischargeable debts

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/components/forms/__tests__/DebtExplanationsPanel.test.tsx
import { render, screen } from '@testing-library/react';
import { DebtExplanationsPanel } from '../DebtExplanationsPanel';

const mockData = [
  { debt_id: 1, creditor: "Navient", debt_type: "student_loan", dischargeable: false, reason: "11 U.S.C. § 523(a)(8)", proceeding_needed: true },
  { debt_id: 2, creditor: "Chase", debt_type: "credit_card", dischargeable: true, reason: "", proceeding_needed: false },
];

describe('DebtExplanationsPanel', () => {
  it('renders dischargeable count', () => {
    render(<DebtExplanationsPanel debts={mockData} />);
    expect(screen.getByText(/1.*dischargeable/i)).toBeInTheDocument();
  });

  it('renders non-dischargeable count', () => {
    render(<DebtExplanationsPanel debts={mockData} />);
    expect(screen.getByText(/1.*non-dischargeable/i)).toBeInTheDocument();
  });

  it('shows student loan proceeding needed', () => {
    render(<DebtExplanationsPanel debts={mockData} />);
    expect(screen.getByText(/Navient/i)).toBeInTheDocument();
    expect(screen.getByText(/adversary proceeding/i)).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<DebtExplanationsPanel debts={[]} />);
    expect(screen.getByText(/no debts/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/forms/__tests__/DebtExplanationsPanel.test.tsx`
Expected: FAIL (component doesn't exist)

- [ ] **Step 3: Write implementation**

```tsx
// frontend/src/components/forms/DebtExplanationsPanel.tsx
interface DebtClassification {
  debt_id: number;
  creditor: string;
  debt_type: string;
  dischargeable: boolean;
  reason: string;
  proceeding_needed: boolean;
}

export function DebtExplanationsPanel({ debts }: { debts: DebtClassification[] }) {
  if (debts.length === 0) {
    return <div className="p-4 text-gray-500">No debts to evaluate.</div>;
  }

  const dischargeable = debts.filter((d) => d.dischargeable);
  const nonDischargeable = debts.filter((d) => !d.dischargeable);

  return (
    <div className="debt-explanations p-4 border rounded">
      <h3 className="text-lg font-semibold mb-3">Debt Discharge Summary</h3>
      <p className="text-sm text-gray-600 mb-4">
        In Chapter 7 bankruptcy, most unsecured debts are discharged (eliminated). Some debts are
        non-dischargeable under federal law.
      </p>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-green-50 p-3 rounded">
          <div className="text-2xl font-bold text-green-700">{dischargeable.length}</div>
          <div className="text-sm text-green-600">Dischargeable debts</div>
        </div>
        <div className="bg-amber-50 p-3 rounded">
          <div className="text-2xl font-bold text-amber-700">{nonDischargeable.length}</div>
          <div className="text-sm text-amber-600">Non-dischargeable debts</div>
        </div>
      </div>

      {nonDischargeable.length > 0 && (
        <div className="mt-4">
          <h4 className="font-medium mb-2">Non-Dischargeable Debts</h4>
          {nonDischargeable.map((debt) => (
            <div key={debt.debt_id} className="border-l-4 border-amber-400 pl-3 mb-3">
              <div className="font-medium">{debt.creditor}</div>
              <div className="text-sm text-gray-600">{debt.reason}</div>
              {debt.proceeding_needed && (
                <div className="text-sm text-amber-600 mt-1">
                  This debt may require a separate adversary proceeding to request discharge.
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/forms/__tests__/DebtExplanationsPanel.test.tsx`
Expected: PASS

- [ ] **Step 5: Integrate into FormDashboard**

Add to `frontend/src/pages/FormDashboard.tsx` — after the Generate All button, fetch dischargeability data and render the panel:

```tsx
// Add state and fetch
const [dischargeData, setDischargeData] = useState<unknown[]>([]);

useEffect(() => {
  if (session) {
    api.intake
      .getDischargeability(session.id)
      .then(setDischargeData)
      .catch(() => {});
  }
}, [session, forms]);

// Add to JSX after the forms grid
{
  dischargeData.length > 0 && <DebtExplanationsPanel debts={dischargeData} />;
}
```

Add to API client `frontend/src/api/client.ts`:

```typescript
  getDischargeability: async (sessionId: number): Promise<unknown[]> => {
    return apiFetch<unknown[]>(`/intake/sessions/${sessionId}/dischargeability/`);
  },
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/forms/DebtExplanationsPanel.tsx frontend/src/components/forms/__tests__/DebtExplanationsPanel.test.tsx frontend/src/pages/FormDashboard.tsx frontend/src/api/client.ts
git commit -m "feat(frontend): add DebtExplanationsPanel for dischargeability summary"
```

---

### Task 6: Integration Test — Full Flow

**Files:**

- Modify: `backend/apps/eligibility/tests/test_dischargeability_service.py`

**Interfaces:**

- End-to-end: add student loan → evaluate → verify proceeding → verify API

- [ ] **Step 1: Write integration test**

```python
@pytest.mark.django_db
class TestDischargeabilityEndToEnd:
    def test_student_loan_full_flow(self):
        """Student loan → classify → flag → adversary proceeding → API returns."""
        from django.contrib.auth import get_user_model
        from apps.districts.models import District
        from apps.intake.models import DebtInfo, IntakeSession
        from apps.eligibility.services.dischargeability_service import DischargeabilityService
        from rest_framework.test import APIClient

        User = get_user_model()
        user = User.objects.create_user(username="e2e_disc", password="pass")
        district = District.objects.create(
            code="ILND", name="Northern District of Illinois", state="IL",
            court_name="U.S. Bankruptcy Court", filing_fee_chapter_7=Decimal("338"),
        )
        session = IntakeSession.objects.create(user=user, district=district)
        DebtInfo.objects.create(
            session=session, creditor_name="Sallie Mae", amount_owed=Decimal("35000"),
            is_secured=False, is_priority=False, debt_type="student_loan",
        )

        svc = DischargeabilityService(session)
        results = svc.evaluate()
        assert len(results) == 1
        assert results[0]["dischargeable"] is False

        debt = DebtInfo.objects.get(creditor_name="Sallie Mae")
        assert debt.is_dischargeable is False
        assert debt.adversary_proceeding_needed is True

        from apps.intake.models import AdversaryProceeding
        ap = AdversaryProceeding.objects.get(session=session)
        assert ap.proceeding_type == "student_loan"
        assert ap.status == "identified"
```

- [ ] **Step 2: Run test**

Run: `pytest backend/apps/eligibility/tests/test_dischargeability_service.py::TestDischargeabilityEndToEnd -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/apps/eligibility/tests/test_dischargeability_service.py
git commit -m "test(eligibility): dischargeability end-to-end integration test"
```

---

## Task Ordering

Tasks 1-2 are independent. Task 3 depends on 1-2. Tasks 4-5 depend on 3. Task 6 depends on all.

Recommended: 1 → 2 → 3 → 4 → 5 → 6
