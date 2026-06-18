# Means Test Expense Deductions — Design Spec

> **Status:** Ready for Implementation
> **Depends on:** MeansTest model + calculator (existing), Form 122A-1/122A-2 schemas (existing)

---

## Context

The means test has two pathways:

- **Below median:** CMI < state median for household size → passes (already implemented)
- **Above median:** CMI ≥ state median → must calculate allowable expenses to determine if disposable income is below threshold

Currently the calculator only handles the below-median path. Above-median filers get a generic "additional calculations may be needed" message. This spec implements the full above-median expense deduction calculation using IRS standards.

## Legal Framework

Per **11 U.S.C. § 707(b)(2)(A)**, above-median filers must pass a second test:

```
Disposable income = CMI - (allowable expenses + priority debt payments)
If disposable income < $9,075 (2024) over 60 months → passes
```

**Allowable expenses** are the lesser of:

1. **Actual expenses** (what the debtor actually pays)
2. **IRS Standards** (National Standards for food/clothing/health + Local Standards for housing/transport)

---

## Components

### 1. IRS Standards Data Store

**Location:** `backend/apps/eligibility/services/irs_standards.py`

Static data tables for 2024/2025 IRS standards. No model needed — these are constants that change annually.

**National Standards (monthly, per household size):**

| Category               | Size 1 | Size 2 | Size 3 | Size 4 | Size 5+ |
| ---------------------- | ------ | ------ | ------ | ------ | ------- |
| Food, Clothing, Misc   | $713   | $904   | $1,088 | $1,289 | $1,453  |
| Health Care (under 65) | $73    | $146   | $146   | $146   | $146    |
| Health Care (65+)      | $164   | $164   | $164   | $164   | $164    |

**Local Standards (monthly, by IRS metro area):**

| Category                        | ILND (Chicago) |
| ------------------------------- | -------------- |
| Housing + Utilities (1 person)  | $1,730         |
| Housing + Utilities (2 person)  | $1,997         |
| Housing + Utilities (3 person)  | $2,049         |
| Housing + Utilities (4 person)  | $2,281         |
| Housing + Utilities (5+ person) | $2,302         |
| Transportation (owned, 1 car)   | $318           |
| Transportation (owned, 2 cars)  | $636           |
| Transportation (operating)      | $283           |

### 2. Expense Deduction Calculator

**Location:** `backend/apps/eligibility/services/expense_deduction_calculator.py`

Computes total allowable monthly expenses from:

- IRS National Standards (food/clothing, health care)
- IRS Local Standards (housing, transportation)
- Actual expenses from ExpenseInfo (the lesser of actual vs standard)
- Priority debts (child support, taxes, etc.)
- Special circumstances adjustments (from SpecialCircumstances model, future)

**Key formula:**

```
allowable_expenses = min(actual_expenses, national_standards + local_standards)
disposable_income = monthly_cmi - allowable_expenses - monthly_priority_debts
passes_above_median = disposable_income < $756.25/month ($9,075/60 months)
```

### 3. Enhanced MeansTest Model

**Extend:** `backend/apps/eligibility/models.py`

Add fields to MeansTest:

```python
# Above-median calculation
total_allowable_expenses = DecimalField(...)  # Monthly
total_actual_expenses = DecimalField(...)     # Monthly
disposable_income = DecimalField(...)         # Monthly
priority_debts_monthly = DecimalField(...)    # Monthly
passes_above_median = BooleanField(...)       # For above-median filers
above_median_calculated = BooleanField(...)   # Whether above-median calc ran
```

### 4. Enhanced MeansTestCalculator

**Extend:** `backend/apps/eligibility/services/means_test_calculator.py`

After the existing below-median check, if above median:

1. Calculate allowable expenses using ExpenseDeductionCalculator
2. Compute disposable income
3. Determine if above-median pathway passes
4. Store detailed breakdown in calculation_details

### 5. Form 122A-2 Full Curation

**Extend:** `data/forms/schemas/form_122a2.json`

Wire remaining 94 constant fields to derivations:

- Quest3A/3A1 → income source adjustments
- Quest5 → deduction count
- Quest6 → food/clothing standard
- Quest7A-E → health care standards
- Quest8 → housing deduction
- Quest9 → housing actual
- Quest10 → corrected housing
- Quest12 → vehicle operating
- Quest13A-D → vehicle ownership/leasing
- Quest14-15 → public transportation

### 6. Form 122B Consideration

Form 122B (Alternative Means Test) has a non-fillable PDF (0 form fields). Options:

- **Skip for now** — 122A-2 covers the primary calculation
- **Find updated template** — AO may have a newer fillable version
- **Build custom PDF** — generate 122B from scratch (not recommended for MVP)

**Recommendation:** Skip 122B for MVP. The 122A-2 handles the primary means test calculation. 122B is only needed when 122A-2 doesn't apply (rare edge cases).

---

## Data Flow

```
IntakeSession
    ↓
MeansTestCalculator.calculate()
    ↓
    ├── CMI < median → passes (existing)
    └── CMI ≥ median →
            ↓
        ExpenseDeductionCalculator.calculate()
            ↓
            ├── National Standards (food, health)
            ├── Local Standards (housing, transport)
            ├── Actual expenses (from ExpenseInfo)
            ├── Priority debts (from DebtInfo)
            └── Compute: disposable_income
            ↓
        disposable_income < $756.25/mo → passes above median
            ↓
        Store in MeansTest.above_median_calculated
            ↓
        Form 122A-2 reads deductions → PDF
```

---

## Testing Strategy

- **Unit tests:** ExpenseDeductionCalculator with mock data
- **Integration test:** Full above-median flow — session with high income → calculate → verify deductions
- **Edge cases:** No expenses, all expenses above standard, special circumstances adjustment
- **IRS standards validation:** Verify National/Local standards match published IRS data

---

## Deferred (Post-MVP)

- 122B alternative means test
- Special circumstances adjustment to deductions
- Continuation pages for long 122A-2 narratives
- Historical IRS standards (multi-year support)
