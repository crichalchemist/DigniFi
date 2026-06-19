# Student Loan Dischargeability & Adversary Proceeding — Design Spec

> **Status:** Ready for Implementation
> **Priority:** P1 — important for user trust, not blocking MVP filing

---

## Context

Student loans are **non-dischargeable** in Chapter 7 under 11 U.S.C. § 523(a)(8) unless the debtor proves "undue hardship" via a separate adversary proceeding. The current codebase lists `student_loan` as a debt type but provides no guidance about dischargeability, the adversary proceeding requirement, or the undue hardship standard.

This feature informs users that student loans require separate legal action, without advising whether they qualify (UPL boundary).

---

## Legal Framework

**11 U.S.C. § 523(a)(8):** Student loans are non-dischargeable unless:

1. The loan is from a government unit or nonprofit educational institution, OR
2. The debtor proves "undue hardship" in an adversary proceeding

**Adversary Proceeding:** A separate lawsuit filed within the bankruptcy case. The debtor must file a complaint, serve the loan holder, and appear at a hearing. The court applies the **Brunner test** (most circuits) or **totality of circumstances** test:

- **Brunner Test (3 prongs):**
  1. Based on current income and expenses, the debtor cannot maintain a minimal standard of living for themselves and dependents
  2. Additional circumstances exist indicating this state of affairs is likely to persist for a significant portion of the repayment period
  3. The debtor has made good faith efforts to repay

**Timeline:** Adversary proceedings typically take 6-12 months after the main case is filed.

---

## Architecture

```
User enters student loan debt in DebtsStep
    ↓
DebtInfo.debt_type = "student_loan"
    ↓
DischargeabilityClassifier evaluates each debt
    ↓
Non-dischargeable debts flagged with reason
    ↓
AdversaryProceeding model created for student loans
    ↓
User sees explanation + guidance (UPL-compliant)
    ↓
Optional: adversary proceeding questionnaire captures
  loan details, income, hardship factors
    ↓
Document generation: Adversary Complaint template
  (future — requires court-specific template)
```

---

## Components

### 1. DischargeabilityClassifier

**Location:** `backend/apps/eligibility/services/dischargeability_classifier.py`

Classifies each debt as dischargeable, non-dischargeable, or conditionally dischargeable.

```python
NON_DISCHARGEABLE_TYPES = {
    "student_loan": "11 U.S.C. § 523(a)(8) — requires adversary proceeding",
    "child_support": "11 U.S.C. § 523(a)(5) — domestic support obligations",
    "alimony": "11 U.S.C. § 523(a)(5) — domestic support obligations",
    "taxes": "11 U.S.C. § 523(a)(1) — recent tax debts (within 3 years)",
    "restitution": "11 U.S.C. § 523(a)(6) — willful and malicious injury",
}
```

### 2. AdversaryProceeding Model

**Location:** `backend/apps/intake/models.py`

```python
class AdversaryProceeding(models.Model):
    """Tracks adversary proceedings for non-dischargeable debts."""

    PROCEEDING_TYPES = [
        ("student_loan", "Student Loan Discharge (§ 523(a)(8))"),
        ("other", "Other Non-Dischargeable Debt"),
    ]

    STATUS_CHOICES = [
        ("identified", "Identified — Not Yet Filed"),
        ("filed", "Complaint Filed"),
        ("pending", "Pending Hearing"),
        ("granted", "Discharge Granted"),
        ("denied", "Discharge Denied"),
        ("settled", "Settled"),
    ]

    session = ForeignKey(IntakeSession, related_name="adversary_proceedings")
    debt = ForeignKey(DebtInfo, on_delete=CASCADE, null=True, blank=True)
    proceeding_type = CharField(max_length=20, choices=PROCEEDING_TYPES)
    status = CharField(max_length=20, choices=STATUS_CHOICES, default="identified")

    # Student loan specifics
    lender_name = CharField(max_length=255, blank=True)
    loan_amount = DecimalField(max_digits=12, decimal_places=2, null=True)
    loan_type = CharField(max_length=50, blank=True)  # federal, private, etc.

    # Hardship factors (for user questionnaire)
    income_insufficient = BooleanField(default=False)
    persistence_likely = BooleanField(default=False)
    good_faith_efforts = BooleanField(default=False)
    hardship_narrative = EncryptedTextField(blank=True)

    # Metadata
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 3. DebtInfo Extension

**Extend:** `backend/apps/intake/models.py` — add fields to DebtInfo:

```python
    is_dischargeable = BooleanField(
        default=True, help_text="Whether debt is dischargeable in Chapter 7"
    )
    dischargeability_notes = CharField(
        max_length=255, blank=True,
        help_text="Why debt is non-dischargeable (if applicable)"
    )
    adversary_proceeding_needed = BooleanField(
        default=False, help_text="Whether an adversary proceeding is required"
    )
```

### 4. DischargeabilityService

**Location:** `backend/apps/eligibility/services/dischargeability_service.py`

Runs when debts are saved. Flags non-dischargeable debts and creates AdversaryProceeding records.

```python
class DischargeabilityService:
    def evaluate(self, session: IntakeSession) -> list[dict]:
        """Evaluate all debts, flag non-dischargeable, return summary."""
        results = []
        debts_to_update = []
        for debt in session.debts.all():
            classification = self._classify(debt)

            if debt.is_dischargeable != classification["dischargeable"] or debt.adversary_proceeding_needed != classification["proceeding_needed"]:
                debt.is_dischargeable = classification["dischargeable"]
                debt.adversary_proceeding_needed = classification["proceeding_needed"]
                debts_to_update.append(debt)

            if classification["proceeding_needed"]:
                self._ensure_proceeding(session, debt, classification)
            results.append({
                "debt_id": debt.id,
                "creditor": debt.creditor_name,
                "type": debt.debt_type,
                **classification,
            })

        if debts_to_update:
            DebtInfo.objects.bulk_update(debts_to_update, ["is_dischargeable", "adversary_proceeding_needed"])

        return results

    def _classify(self, debt) -> dict:
        reason = NON_DISCHARGEABLE_TYPES.get(debt.debt_type)
        proceeding_needed = (debt.debt_type == "student_loan")
        return {
            "dischargeable": reason is None,
            "reason": reason or "",
            "proceeding_needed": proceeding_needed,
        }
```

### 5. API Endpoints

| Endpoint                                                | Method | Purpose                            |
| ------------------------------------------------------- | ------ | ---------------------------------- |
| `/api/intake/sessions/{id}/dischargeability/`           | POST   | Evaluate all debts, return summary |
| `/api/intake/sessions/{id}/adversary-proceedings/`      | GET    | List adversary proceedings         |
| `/api/intake/sessions/{id}/adversary-proceedings/`      | POST   | Create/update proceeding           |
| `/api/intake/sessions/{id}/adversary-proceedings/{id}/` | PATCH  | Update status/narrative            |

### 6. Frontend — DebtExplanationsPanel

**Location:** `frontend/src/components/forms/DebtExplanationsPanel.tsx`

After user completes the Debts step, shows a summary panel explaining:

- Which debts are dischargeable
- Which debts are non-dischargeable and why
- What adversary proceedings are needed
- Next steps for student loans

**UPL compliance:**

- "This debt type is generally non-dischargeable under 11 U.S.C. § 523(a)(8)" — informational
- "You may be able to discharge this debt by filing an adversary proceeding" — informational
- Never: "You qualify for discharge" or "You should file an adversary proceeding"

---

## Data Flow

```
DebtsStep → save debts → POST /api/intake/sessions/{id}/debts/
    ↓
DischargeabilityService.evaluate(session)
    ↓
For each student_loan debt:
    1. Set debt.is_dischargeable = False
    2. Set debt.adversary_proceeding_needed = True
    3. Create AdversaryProceeding(status="identified")
    ↓
POST /api/intake/sessions/{id}/dischargeability/
    ↓
DebtExplanationsPanel shows:
    "2 of 5 debts are non-dischargeable:
     - Navient Student Loan: requires adversary proceeding
     - IRS Tax Debt: may be partially dischargeable"
    ↓
User can view adversary proceeding details
```

---

## Testing Strategy

- **Unit tests:** DischargeabilityClassifier with mock debts
- **Integration test:** Full flow — add student loan debt → evaluate → verify adversary proceeding created
- **UPL test:** Verify all user-facing text is informational, never advisory

---

## Deferred (Post-MVP)

- Adversary complaint PDF generation (requires court-specific template)
- Due date tracking for adversary proceedings
- Integration with document scanning (auto-detect student loan statements)
- Undue hardship questionnaire (Brunner test factors)
