# Means Test Expense Deductions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full above-median means test expense deduction calculation using IRS National and Local Standards, wiring deductions to Form 122A-2.

**Architecture:** IRS standards stored as static data. ExpenseDeductionCalculator computes allowable deductions from standards + actual expenses + priority debts. MeansTest model extended with above-median fields. Form 122A-2 schema fully curated with derivation rules.

**Tech Stack:** Python, Django, Decimal arithmetic, pytest

## Global Constraints

- All monetary values use `Decimal` (never float) for court-form precision
- UPL boundary: calculation is factual (income vs thresholds), never advisory
- IRS standards are 2024 values (updated annually, not in scope)
- `on_states` must be `["/Yes"]` (list, not dict) for checkboxes

---

### Task 1: IRS Standards Data

**Files:**

- Create: `backend/apps/eligibility/services/irs_standards.py`
- Create: `backend/apps/eligibility/tests/test_irs_standards.py`

**Interfaces:**

- Produces: `IRS_STANDARDS` dict with National and Local standard lookup functions

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/eligibility/tests/test_irs_standards.py
from apps.eligibility.services.irs_standards import get_national_standard, get_local_standard, get_housing_standard

def test_national_standard_food_size_1():
    assert get_national_standard("food", 1) == Decimal("713.00")

def test_national_standard_food_size_4():
    assert get_national_standard("food", 4) == Decimal("1289.00")

def test_national_standard_health_under_65():
    assert get_national_standard("health_care", 2, age_under_65=True) == Decimal("146.00")

def test_national_standard_health_over_65():
    assert get_national_standard("health_care", 2, age_under_65=False) == Decimal("164.00")

def test_local_standard_housing_ilnd():
    assert get_local_standard("ILND", "housing", 2) == Decimal("1997.00")

def test_local_standard_transport_owned_one_car():
    assert get_local_standard("ILND", "transport_owned", 1) == Decimal("318.00")

def test_local_standard_transport_operating():
    assert get_local_standard("ILND", "transport_operating") == Decimal("283.00")

def test_housing_standard_returns_none_for_unknown_district():
    assert get_housing_standard("ZZZZ", 1) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/eligibility/tests/test_irs_standards.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

```python
# backend/apps/eligibility/services/irs_standards.py
"""IRS National and Local Standards for means test expense deductions (2024)."""

from decimal import Decimal

NATIONAL_STANDARDS = {
    "food": {
        1: Decimal("713"), 2: Decimal("904"), 3: Decimal("1088"),
        4: Decimal("1289"), 5: Decimal("1453"),
    },
    "health_care_under_65": {
        1: Decimal("73"), 2: Decimal("146"), 3: Decimal("146"),
        4: Decimal("146"), 5: Decimal("146"),
    },
    "health_care_65_plus": {
        1: Decimal("164"), 2: Decimal("164"), 3: Decimal("164"),
        4: Decimal("164"), 5: Decimal("164"),
    },
}

LOCAL_STANDARDS = {
    "ILND": {
        "housing": {
            1: Decimal("1730"), 2: Decimal("1997"), 3: Decimal("2049"),
            4: Decimal("2281"), 5: Decimal("2302"),
        },
        "transport_owned": {1: Decimal("318"), 2: Decimal("636")},
        "transport_operating": Decimal("283"),
    },
}


def get_national_standard(category: str, family_size: int, age_under_65: bool = True) -> Decimal:
    key = category
    if category == "health_care":
        key = "health_care_under_65" if age_under_65 else "health_care_65_plus"
    family_size = min(family_size, 5)
    return NATIONAL_STANDARDS[key][family_size]


def get_local_standard(district_code: str, category: str, family_size: int = 1) -> Decimal | None:
    district = LOCAL_STANDARDS.get(district_code.upper())
    if not district:
        return None
    val = district.get(category)
    if isinstance(val, dict):
        family_size = min(family_size, 5)
        return val.get(family_size)
    return val


def get_housing_standard(district_code: str, family_size: int) -> Decimal | None:
    return get_local_standard(district_code, "housing", family_size)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/eligibility/tests/test_irs_standards.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/eligibility/services/irs_standards.py backend/apps/eligibility/tests/test_irs_standards.py
git commit -m "feat(eligibility): add IRS National and Local Standards data (2024)"
```

---

### Task 2: Expense Deduction Calculator

**Files:**

- Create: `backend/apps/eligibility/services/expense_deduction_calculator.py`
- Create: `backend/apps/eligibility/tests/test_expense_deduction_calculator.py`

**Interfaces:**

- Consumes: `IntakeSession`, IRS standards from Task 1
- Produces: `ExpenseDeductionResult` with allowable_expenses, disposable_income, etc.

- [ ] **Step 1: Write the failing test**

```python
# backend/apps/eligibility/tests/test_expense_deduction_calculator.py
import pytest
from decimal import Decimal
from apps.eligibility.services.expense_deduction_calculator import ExpenseDeductionCalculator

@pytest.fixture
def session_with_expenses(db):
    from apps.intake.models import IntakeSession, ExpenseInfo, DebtInfo
    from apps.districts.models import District
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(username="deductcalc", password="pass")
    district = District.objects.create(
        code="ILND", name="Northern District of Illinois", state="IL",
        court_name="U.S. Bankruptcy Court", filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    ExpenseInfo.objects.create(
        session=session,
        rent_or_mortgage=Decimal("1200"),
        utilities=Decimal("200"),
        food_and_groceries=Decimal("500"),
        vehicle_payment=Decimal("400"),
    )
    DebtInfo.objects.create(
        session=session, creditor_name="IRS", amount_owed=Decimal("5000"),
        is_secured=False, is_priority=True, debt_type="taxes",
    )
    return session

def test_calculator_returns_allowable_expenses(session_with_expenses):
    calc = ExpenseDeductionCalculator(session_with_expenses)
    result = calc.calculate()
    assert result.allowable_expenses > Decimal("0")
    assert result.disposable_income is not None

def test_calculator_uses_lesser_of_actual_vs_standard(session_with_expenses):
    calc = ExpenseDeductionCalculator(session_with_expenses)
    result = calc.calculate()
    # Food actual ($500) vs national standard for size 1 ($713)
    # Allowable = min(500, 713) = 500
    assert result.national_food_allowance == Decimal("500.00")

def test_calculator_includes_priority_debts(session_with_expenses):
    calc = ExpenseDeductionCalculator(session_with_expenses)
    result = calc.calculate()
    assert result.priority_debts_monthly > Decimal("0")

def test_calculator_empty_session(db):
    from apps.intake.models import IntakeSession
    from apps.districts.models import District
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(username="emptycalc", password="pass")
    district = District.objects.create(
        code="ILND", name="Northern District of Illinois", state="IL",
        court_name="U.S. Bankruptcy Court", filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    calc = ExpenseDeductionCalculator(session)
    result = calc.calculate()
    assert result.allowable_expenses >= Decimal("0")
    assert result.disposable_income >= Decimal("0")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/eligibility/tests/test_expense_deduction_calculator.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

```python
# backend/apps/eligibility/services/expense_deduction_calculator.py
"""Calculate allowable expense deductions for above-median means test."""

from dataclasses import dataclass
from decimal import Decimal

from apps.eligibility.services.irs_standards import get_national_standard, get_local_standard
from apps.intake.models import IntakeSession


@dataclass
class ExpenseDeductionResult:
    national_food_allowance: Decimal
    national_health_allowance: Decimal
    local_housing_allowance: Decimal
    local_transport_allowance: Decimal
    actual_total_expenses: Decimal
    allowable_expenses: Decimal
    priority_debts_monthly: Decimal
    disposable_income: Decimal
    family_size: int


class ExpenseDeductionCalculator:
    def __init__(self, session: IntakeSession):
        self.session = session
        self.district = session.district

    def calculate(self) -> ExpenseDeductionResult:
        family_size = self._get_family_size()
        age_under_65 = self._is_under_65()

        # National standards
        food_std = get_national_standard("food", family_size)
        health_std = get_national_standard("health_care", family_size, age_under_65)

        # Local standards
        housing_std = get_local_standard(self.district.code, "housing", family_size) or Decimal("0")
        transport_std = get_local_standard(self.district.code, "transport_operating") or Decimal("0")

        # Actual expenses (from ExpenseInfo)
        actual = self._get_actual_expenses()

        # Allowable = lesser of actual vs standard for each category
        food_allowance = min(actual["food"], food_std)
        health_allowance = min(actual["health"], health_std)
        housing_allowance = min(actual["housing"], housing_std)
        transport_allowance = min(actual["transport"], transport_std)

        total_allowable = food_allowance + health_allowance + housing_allowance + transport_allowance

        # Priority debts (child support, taxes, etc.)
        priority = self._get_priority_debts_monthly()

        # Disposable income
        cmi = self._get_cmi()
        disposable = cmi - total_allowable - priority

        return ExpenseDeductionResult(
            national_food_allowance=food_allowance,
            national_health_allowance=health_allowance,
            local_housing_allowance=housing_allowance,
            local_transport_allowance=transport_allowance,
            actual_total_expenses=actual["total"],
            allowable_expenses=total_allowable,
            priority_debts_monthly=priority,
            disposable_income=disposable,
            family_size=family_size,
        )

    def _get_family_size(self) -> int:
        di = getattr(self.session, "debtor_info", None)
        if di and (di.household_size or 0) >= 1:
            return di.household_size
        try:
            ii = self.session.income_info
            size = ii.number_of_dependents + 1
            if ii.marital_status in ("married_joint", "married_separate"):
                size += 1
            return size
        except Exception:
            return 1

    def _is_under_65(self) -> bool:
        di = getattr(self.session, "debtor_info", None)
        if di and di.date_of_birth:
            from datetime import date
            age = (date.today() - di.date_of_birth).days // 365
            return age < 65
        return True

    def _get_actual_expenses(self) -> dict[str, Decimal]:
        zero = Decimal("0")
        try:
            ei = self.session.expense_info
            return {
                "food": Decimal(str(ei.food_and_groceries or zero)),
                "health": Decimal(str(ei.medical_expenses or zero)),
                "housing": Decimal(str(ei.rent_or_mortgage or zero)),
                "transport": Decimal(str(ei.vehicle_payment or zero)),
                "total": Decimal(str(ei.calculate_total_monthly_expenses())),
            }
        except Exception:
            return {"food": zero, "health": zero, "housing": zero, "transport": zero, "total": zero}

    def _get_priority_debts_monthly(self) -> Decimal:
        from apps.intake.models import DebtInfo
        zero = Decimal("0")
        priority = DebtInfo.objects.filter(session=self.session, is_priority=True)
        return sum((d.monthly_payment or zero for d in priority), zero)

    def _get_cmi(self) -> Decimal:
        try:
            ii = self.session.income_info
            total = sum(Decimal(str(v)) for v in (ii.monthly_income or []))
            return total / Decimal("6") if total else Decimal("0")
        except Exception:
            return Decimal("0")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/apps/eligibility/tests/test_expense_deduction_calculator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/eligibility/services/expense_deduction_calculator.py backend/apps/eligibility/tests/test_expense_deduction_calculator.py
git commit -m "feat(eligibility): add expense deduction calculator for above-median means test"
```

---

### Task 3: Extend MeansTest Model

**Files:**

- Modify: `backend/apps/eligibility/models.py`
- Create: `backend/apps/eligibility/migrations/0002_add_above_median_fields.py`
- Modify: `backend/apps/eligibility/tests/test_means_test_calculator.py`

**Interfaces:**

- Consumes: ExpenseDeductionResult from Task 2
- Produces: Extended MeansTest model with above-median fields

- [ ] **Step 1: Write the failing test**

```python
# Add to backend/apps/eligibility/tests/test_means_test_calculator.py

class TestAboveMedianCalculation:
    def test_above_median_calculates_disposable_income(self, session_with_above_median_income):
        calculator = MeansTestCalculator(session_with_above_median_income)
        result = calculator.calculate()
        means_test = session_with_above_median_income.means_test
        assert means_test.above_median_calculated is True
        assert means_test.disposable_income is not None

    def test_above_median_passes_when_disposable_low(self, session_with_high_expenses):
        calculator = MeansTestCalculator(session_with_high_expenses)
        result = calculator.calculate()
        assert result["passes_means_test"] is True

    def test_above_median_fails_when_disposable_high(self, session_with_low_expenses):
        calculator = MeansTestCalculator(session_with_low_expenses)
        result = calculator.calculate()
        assert result["passes_means_test"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/apps/eligibility/tests/test_means_test_calculator.py::TestAboveMedianCalculation -v`
Expected: FAIL with AttributeError (missing fields)

- [ ] **Step 3: Add model fields + migration**

```python
# Add to MeansTest in backend/apps/eligibility/models.py (after existing fields)

    # Above-median calculation fields
    total_allowable_expenses = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text="Monthly allowable expenses (IRS standards + actual)"
    )
    disposable_income = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text="Monthly disposable income after deductions"
    )
    priority_debts_monthly = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text="Monthly priority debt payments"
    )
    passes_above_median = models.BooleanField(
        default=False, help_text="True if disposable income < $756.25/mo"
    )
    above_median_calculated = models.BooleanField(
        default=False, help_text="Whether above-median calculation was performed"
    )
```

Run: `python manage.py makemigrations eligibility --name add_above_median_fields`

- [ ] **Step 4: Update MeansTest.calculate() for above-median path**

```python
# In MeansTest.calculate(), after the existing below-median check:

        if not passes_test:
            # Above-median pathway: calculate allowable expenses
            from apps.eligibility.services.expense_deduction_calculator import (
                ExpenseDeductionCalculator,
            )
            ded_calc = ExpenseDeductionCalculator(self.session)
            ded_result = ded_calc.calculate()

            self.total_allowable_expenses = ded_result.allowable_expenses
            self.disposable_income = ded_result.disposable_income
            self.priority_debts_monthly = ded_result.priority_debts_monthly
            self.above_median_calculated = True

            # $756.25/mo = $9,075 over 60 months (2024 threshold)
            threshold = Decimal("756.25")
            self.passes_above_median = ded_result.disposable_income < threshold
            passes_test = self.passes_above_median

            details["above_median"] = {
                "allowable_expenses": float(ded_result.allowable_expenses),
                "disposable_income": float(ded_result.disposable_income),
                "priority_debts": float(ded_result.priority_debts_monthly),
                "passes_above_median": self.passes_above_median,
            }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/apps/eligibility/tests/test_means_test_calculator.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/eligibility/models.py backend/apps/eligibility/migrations/ backend/apps/eligibility/tests/test_means_test_calculator.py
git commit -m "feat(eligibility): extend MeansTest with above-median expense deduction fields"
```

---

### Task 4: Curate Form 122A-2 Schema

**Files:**

- Modify: `data/forms/schemas/form_122a2.json`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/test_generate_all_schema_driven.py`

**Interfaces:**

- Consumes: MeansTest.above_median_calculated, ExpenseDeductionResult
- Produces: Fully curated Form 122A-2 schema with derivation rules

- [ ] **Step 1: Add new derivation rules**

```python
# Add to derivations.py DERIVATIONS dict:

    "means_test_disposable_income": _means_test_disposable_income,
    "means_test_total_deductions": _means_test_total_deductions,
    "means_test_priority_debts": _means_test_priority_debts,
```

Add functions:

```python
def _means_test_disposable_income(session: IntakeSession) -> str:
    try:
        mt = session.means_test
        return _fmt(mt.disposable_income)
    except Exception:
        return "0.00"

def _means_test_total_deductions(session: IntakeSession) -> str:
    try:
        mt = session.means_test
        return _fmt(mt.total_allowable_expenses)
    except Exception:
        return "0.00"

def _means_test_priority_debts(session: IntakeSession) -> str:
    try:
        mt = session.means_test
        return _fmt(mt.priority_debts_monthly)
    except Exception:
        return "0.00"
```

- [ ] **Step 2: Curate remaining form_122a2 fields**

```python
# In form_122a2.json, map remaining TBD fields to derivations:

Quest1 → means_test_total_deductions (total deductions line)
Quest5 → means_test_priority_debts (priority debts)
Quest8 → schedule_j_rent_or_mortgage (housing actual)
Quest9 → schedule_j_utilities (utilities)
Quest10 → means_test_total_deductions (corrected housing)
Quest12 → schedule_j_vehicle_maintenance (vehicle operating)
Quest13D → schedule_j_vehicle_payment (ownership/leasing)
Quest14 → schedule_j_vehicle_payment (transportation)
Quest15 → schedule_j_vehicle_payment (additional transport)
sig → full_name
Date signed → today_iso
```

- [ ] **Step 3: Run tests**

Run: `pytest apps/forms/tests/ -v --tb=short -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add data/forms/schemas/form_122a2.json backend/apps/forms/services/derivations.py
git commit -m "feat(forms): curate Form 122A-2 with means test deduction derivations"
```

---

### Task 5: Integration Test — Above-Median Pathway

**Files:**

- Modify: `backend/apps/eligibility/tests/test_means_test_calculator.py`

**Interfaces:**

- End-to-end: session with above-median income → calculate → verify deductions → verify 122A-2

- [ ] **Step 1: Write integration test**

```python
@pytest.mark.django_db
class TestAboveMedianEndToEnd:
    def test_above_median_full_flow(self):
        """Above-median filer: CMI → deductions → disposable → 122A-2 generates."""
        from apps.districts.models import District, MedianIncome
        from apps.forms.registry import get_generator
        from apps.intake.models import IntakeSession, DebtorInfo, IncomeInfo, ExpenseInfo
        from django.contrib.auth import get_user_model
        from datetime import date

        User = get_user_model()
        user = User.objects.create_user(username="e2e_above", password="pass")
        district = District.objects.create(
            code="ILND", name="Northern District of Illinois", state="IL",
            court_name="U.S. Bankruptcy Court", filing_fee_chapter_7=Decimal("338"),
        )
        MedianIncome.objects.create(
            district=district, effective_date=date(2025, 1, 1),
            family_size_1=Decimal("55000"), family_size_2=Decimal("65000"),
            family_size_3=Decimal("75000"), family_size_4=Decimal("85000"),
            family_size_5=Decimal("95000"), family_size_6=Decimal("105000"),
            family_size_7=Decimal("115000"), family_size_8=Decimal("125000"),
        )
        session = IntakeSession.objects.create(user=user, district=district)
        DebtorInfo.objects.create(
            session=session, first_name="Above", middle_name="", last_name="Median",
            ssn="987-65-4321", date_of_birth=date(1985, 1, 1),
            phone="312-555-0100", email="above@test.com",
            street_address="456 Oak Ave", city="Chicago", state="IL", zip_code="60601",
            household_size=1,
        )
        IncomeInfo.objects.create(
            session=session, monthly_income=[6000]*6, marital_status="single", number_of_dependents=0,
        )
        ExpenseInfo.objects.create(
            session=session, rent_or_mortgage=Decimal("1500"), utilities=Decimal("200"),
            food_and_groceries=Decimal("400"), vehicle_payment=Decimal("500"),
        )

        from apps.eligibility.services.means_test_calculator import MeansTestCalculator
        result = MeansTestCalculator(session).calculate()
        assert result["passes_means_test"] is False  # Above median
        assert session.means_test.above_median_calculated is True
        assert session.means_test.disposable_income is not None

        gen = get_generator("form_122a2", session)
        field_map = gen.pdf_field_map()
        assert "Name" in field_map or "Bankruptcy District Information" in field_map
```

- [ ] **Step 2: Run test**

Run: `pytest backend/apps/eligibility/tests/test_means_test_calculator.py::TestAboveMedianEndToEnd -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/apps/eligibility/tests/test_means_test_calculator.py
git commit -m "test(eligibility): above-median end-to-end integration test"
```

---

### Task 6: Update MeansTestCalculator Response

**Files:**

- Modify: `backend/apps/eligibility/services/means_test_calculator.py`

**Interfaces:**

- Consumes: Extended MeansTest from Task 3
- Produces: Updated result dict with above-median details

- [ ] **Step 1: Update calculate() return value**

```python
# In MeansTestCalculator.calculate(), add to the result dict:

        result = {
            "passes_means_test": means_test.passes_means_test,
            "qualifies_for_fee_waiver": means_test.qualifies_for_fee_waiver,
            "cmi": means_test.calculated_cmi,
            "median_income_threshold": means_test.median_income_threshold,
            "family_size": means_test.get_calculation_details().get("family_size", 0),
            "message": self._generate_upl_compliant_message(means_test),
            "details": means_test.get_calculation_details(),
            "means_test_id": means_test.id,
            # Above-median fields
            "above_median_calculated": means_test.above_median_calculated,
            "disposable_income": means_test.disposable_income,
            "total_allowable_expenses": means_test.total_allowable_expenses,
            "passes_above_median": means_test.passes_above_median,
        }
```

- [ ] **Step 2: Update UPL message for above-median**

```python
# In _generate_upl_compliant_message(), add:

        if means_test.above_median_calculated and means_test.passes_above_median:
            message = (
                f"Based on the information provided, your income is above the median "
                f"income for a household of this size in {self.district.state}. "
                f"After accounting for allowable expenses and priority debts, your "
                f"disposable income is below the statutory threshold. This means you "
                f"may still be eligible for Chapter 7 bankruptcy."
            )
        elif means_test.above_median_calculated and not means_test.passes_above_median:
            message = (
                f"Based on the information provided, your income is above the median "
                f"income for a household of this size in {self.district.state}. "
                f"After accounting for allowable expenses and priority debts, your "
                f"disposable income exceeds the statutory threshold. You may want to "
                f"consult with a legal aid organization about Chapter 13 options."
            )
```

- [ ] **Step 3: Run full test suite**

Run: `pytest backend/apps/eligibility/tests/ -v --tb=short -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/apps/eligibility/services/means_test_calculator.py
git commit -m "feat(eligibility): update MeansTestCalculator with above-median response"
```

---

## Task Ordering

Tasks 1-2 are independent. Tasks 3-6 depend on 1-2. Recommended order:

1. Task 1 (IRS Standards) — foundation
2. Task 2 (Calculator) — depends on 1
3. Task 3 (Model extension) — depends on 2
4. Task 4 (Schema curation) — depends on 3
5. Task 5 (Integration test) — depends on 4
6. Task 6 (Calculator response) — depends on 3, can run parallel with 4-5
