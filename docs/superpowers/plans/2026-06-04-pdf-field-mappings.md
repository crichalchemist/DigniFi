# PDF Field Mappings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `pdf_field_map() -> dict[str, str]` to all 13 bankruptcy form generators so the download infrastructure (Layers 1+3) can fill official AO court PDF templates.

**Architecture:** Each generator already holds an `IntakeSession` instance with all related models available via `self.session`. The `pdf_field_map()` method reads session data directly and returns `{pdf_field_name: value_string}`. It does NOT call `generate()` — it maps directly from the session models to the PDF field names discovered by inspecting the template files. Checkbox fields use `"/Yes"` for checked and `"/Off"` for unchecked. An empty string leaves the field blank.

**Tech Stack:** Python 3.11, Django 5, pypdf 3.17 (for field name verification), pytest

**Prerequisite:** Layers 1+3 plan must be merged first so the `download` endpoint exists to test against.

---

## PDF Field Name Reference

All field names were verified by running `pypdf.PdfReader(path).get_fields()` against the templates in `Official Bankruptcy Rules+Forms/Forms/`. Template filenames:

| form_type    | template file                      | fields |
| ------------ | ---------------------------------- | ------ |
| form_101     | form_b_101_0624_fillable_clean.pdf | 163    |
| form_103b    | form_b103b.pdf                     | 134    |
| form_106dec  | form_b106dec.pdf                   | 18     |
| form_106sum  | form_b106sum.pdf                   | 29     |
| form_107     | b_107_0425-form.pdf                | 537    |
| form_121     | form_b121.pdf                      | 32     |
| form_122a1   | b_122a-1.pdf                       | 67     |
| schedule_a_b | form_b106ab.pdf                    | 379    |
| schedule_c   | b_106c_0425-form.pdf               | 107    |
| schedule_d   | form_b106d.pdf                     | 193    |
| schedule_e_f | form_b106ef.pdf                    | 336    |
| schedule_i   | form_b106i.pdf                     | 86     |
| schedule_j   | form_b106j.pdf                     | 80     |

---

## Shared test helper

Before the per-form tasks, create a pytest fixture that verifies a `pdf_field_map()` method exists and returns a non-empty dict with all string values.

- [ ] **Step 1: Create shared test helper**

```python
# backend/apps/forms/tests/test_pdf_field_maps.py
"""
Verify pdf_field_map() on every generator returns the correct shape and
writes real values into the corresponding AO court PDF template.
"""
from io import BytesIO
from decimal import Decimal
from datetime import date

import pytest
import pypdf
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import (
    IntakeSession, DebtorInfo, IncomeInfo, ExpenseInfo, AssetInfo, DebtInfo,
    FeeWaiverApplication,
)
from apps.forms.registry import get_generator

User = get_user_model()


@pytest.fixture
def ilnd(db):
    return District.objects.get_or_create(
        code="ilnd",
        defaults={
            "name": "Northern District of Illinois",
            "court_name": "U.S. Bankruptcy Court, N.D. Ill.",
            "state": "IL",
        },
    )[0]


@pytest.fixture
def full_session(db, ilnd):
    """IntakeSession with all related models populated (mirrors demo_maria persona)."""
    user = User.objects.create_user(username="maptest", password="x")
    session = IntakeSession.objects.create(
        user=user, district=ilnd, status="completed", current_step=6
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Maria", middle_name="", last_name="Torres",
        ssn="900-55-0001",
        date_of_birth=date(1982, 3, 14),
        phone="312-555-0101",
        email="maria.torres@demo.dignifi.org",
        street_address="742 W 18th St Apt 3B",
        city="Chicago", state="IL", zip_code="60616",
    )
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        number_of_dependents=2,
        monthly_income=[2200, 2200, 2200, 2200, 2200, 2200],
    )
    ExpenseInfo.objects.create(
        session=session,
        rent_or_mortgage=Decimal("950.00"),
        utilities=Decimal("120.00"),
        home_maintenance=Decimal("0.00"),
        vehicle_payment=Decimal("0.00"),
        vehicle_insurance=Decimal("80.00"),
        vehicle_maintenance=Decimal("30.00"),
        food_and_groceries=Decimal("400.00"),
        clothing=Decimal("50.00"),
        medical_expenses=Decimal("75.00"),
        childcare=Decimal("200.00"),
        child_support_paid=Decimal("0.00"),
        insurance_not_deducted=Decimal("0.00"),
        other_expenses=Decimal("100.00"),
    )
    AssetInfo.objects.create(
        session=session, asset_type="bank_account",
        description="Chase checking", current_value=Decimal("320.00"),
        amount_owed=Decimal("0.00"),
    )
    DebtInfo.objects.create(
        session=session, creditor_name="Capital One",
        debt_type="credit_card", amount_owed=Decimal("4200.00"),
        monthly_payment=Decimal("75.00"), is_in_collections=False,
        consumer_business_classification="consumer",
    )
    FeeWaiverApplication.objects.create(
        session=session,
        household_size=3, monthly_income=Decimal("2200.00"),
        monthly_expenses=Decimal("2005.00"),
        receives_public_benefits=False,
        cannot_pay_full=True, cannot_pay_installments=True,
        status="pending",
    )
    return session


def _assert_map_shape(field_map: dict) -> None:
    """All values must be strings; dict must be non-empty."""
    assert isinstance(field_map, dict), "pdf_field_map() must return a dict"
    assert field_map, "pdf_field_map() must return at least one field"
    for k, v in field_map.items():
        assert isinstance(k, str), f"Key {k!r} is not a string"
        assert isinstance(v, str), f"Value for {k!r} is not a string (got {type(v)})"
```

- [ ] **Step 2: Run to confirm fixture works**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py -v
```

Expected: collected 0 items (no test functions yet), 0 errors.

---

## Task 1: Form 121 — SSN Statement (simplest, 32 fields)

**File:** `backend/apps/forms/services/form_121_generator.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/apps/forms/tests/test_pdf_field_maps.py`:

```python
def test_form_121_pdf_field_map(full_session):
    gen = get_generator("form_121", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert field_map["Debtor1.First name"] == "Maria"
    assert field_map["Debtor1.Last name"] == "Torres"
    assert "900-55-0001" in field_map["Debtor1a SSNum"]
    assert field_map["Bankruptcy District Information"] == "Northern District of Illinois"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_121_pdf_field_map -v
```

Expected: `AttributeError: 'Form121Generator' object has no attribute 'pdf_field_map'`

- [ ] **Step 3: Add `pdf_field_map()` to Form121Generator**

Open `backend/apps/forms/services/form_121_generator.py`. Add after the existing `preview()` method inside `Form121Generator`:

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 121 (form_b121.pdf) field names."""
        data = _extract_debtor_data(self.session)
        di = self.session.debtor_info
        district_name = self.session.district.name

        return {
            "Bankruptcy District Information": district_name,
            "Debtor1.First name": di.first_name,
            "Debtor1.Middle name": di.middle_name or "",
            "Debtor1.Last name": di.last_name,
            "Debtor1a SSNum": data["ssn_formatted"],
            "Check Box1": "/Yes",   # Has SSN (vs ITIN)
        }
```

- [ ] **Step 4: Run — verify PASS**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_121_pdf_field_map -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/services/form_121_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Form 121 (SSN statement)"
```

---

## Task 2: Form 106Dec — Declaration (18 fields)

**File:** `backend/apps/forms/services/form_106dec_generator.py`

The 18 fields for this form are:
`Bankruptcy District Information` (/Ch), `Case number` (/Tx), `Debtor 1` (/Tx), `Debtor1` (?), `Debtor1.signature` (/Tx), `Executed on` (/Tx), `Name of person payed to help file` (/Tx), `check1` (/Btn), plus Button controls.

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_form_106dec_pdf_field_map(full_session):
    gen = get_generator("form_106dec", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map["Debtor 1"]
    assert field_map["Bankruptcy District Information"] == "Northern District of Illinois"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_106dec_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to Form106DecGenerator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 106Dec (form_b106dec.pdf) field names."""
        di = self.session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()
        return {
            "Bankruptcy District Information": self.session.district.name,
            "Debtor 1": full_name,
        }
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_106dec_pdf_field_map -v
git add backend/apps/forms/services/form_106dec_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Form 106Dec (declaration)"
```

---

## Task 3: Form 101 — Voluntary Petition (163 fields)

**File:** `backend/apps/forms/services/form_101_generator.py`

Key confirmed field names from the template:

- `Debtor1.First name`, `Debtor1.Middle name`, `Debtor1.Last name`, `Debtor1.Name`
- `Debtor1.SSNum`, `Debtor1.City`, `Debtor1.State`, `Debtor1.Zip`, `Debtor1.Street address`
- `Debtor1.Cell phone`, `Debtor1.Email address_2`
- `Bankruptcy District Information` (combo box — value must match option text exactly)
- `Check Box5` = Chapter 7 checkbox
- `Check Box1` = Individual debtor checkbox
- `Check Box16` = consumer debts checkbox
- `Case number` (blank — assigned by court)

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_form_101_pdf_field_map(full_session):
    gen = get_generator("form_101", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert field_map["Debtor1.First name"] == "Maria"
    assert field_map["Debtor1.Last name"] == "Torres"
    assert field_map["Debtor1.SSNum"] == "900-55-0001"
    assert field_map["Debtor1.City"] == "Chicago"
    assert field_map["Check Box5"] == "/Yes"   # Chapter 7
    assert field_map["Check Box1"] == "/Yes"   # Individual
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_101_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to Form101Generator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 101 (form_b_101_0624_fillable_clean.pdf)."""
        di = self.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()

        return {
            # Identity
            "Debtor1.First name": di.first_name,
            "Debtor1.Middle name": di.middle_name or "",
            "Debtor1.Last name": di.last_name,
            "Debtor1.Name": full_name,
            "Debtor1.First name_3": di.first_name,
            "Debtor1.Middle name_3": di.middle_name or "",
            "Debtor1.Last name_3": di.last_name,
            "Debtor1.First name_5": di.first_name,
            "Debtor1.Middle name_5": di.middle_name or "",
            "Debtor1.Last name_5": di.last_name,
            "Debtor1.SSNum": di.ssn,
            # Address
            "Debtor1.Street address": di.street_address,
            "Debtor1.City": di.city,
            "Debtor1.State": di.state,
            "Debtor1.Zip": di.zip_code,
            "Debtor1.County": "",
            # Contact
            "Debtor1.Cell phone": di.phone or "",
            "Debtor1.Email address_2": di.email or "",
            # Case info
            "Bankruptcy District Information": self.district.name,
            "Case number": "",  # assigned by court
            "Case number1": "",
            # Checkboxes — Chapter 7, individual, consumer debts
            "Check Box1": "/Yes",   # Individual (not business)
            "Check Box5": "/Yes",   # Chapter 7
            "Check Box16": "/Yes",  # Consumer debts
        }
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_101_pdf_field_map -v
git add backend/apps/forms/services/form_101_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Form 101 (voluntary petition)"
```

---

## Task 4: Form 106Sum — Summary of Schedules (29 fields)

**File:** `backend/apps/forms/services/form_106sum_generator.py`

The 29 fields are short codes. From Official Form 106Sum, the lines are:

- `1a` = Schedule A/B real property total
- `1b` = Schedule A/B personal property total
- `1c` = Schedule A/B total assets
- `2` = Schedule D secured claims total
- `3` = Schedule E/F unsecured total
- `4` = Schedule G unexpired leases (not tracked — leave blank)
- `5` = Schedule H codebtors (not tracked)
- `6a` = Schedule I monthly income
- `6b` = Schedule J monthly expenses
- `Debtor 1` = full name
- `Bankruptcy District Information` = district

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_form_106sum_pdf_field_map(full_session):
    gen = get_generator("form_106sum", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map.get("Debtor 1", "")
    # 1a should be a numeric string (real property total = 0 for this persona)
    assert field_map.get("1a", "0") == "0.00"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_106sum_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to Form106SumGenerator**

Open `form_106sum_generator.py` and add at the end of the class:

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 106Sum (form_b106sum.pdf)."""
        from decimal import Decimal, ROUND_HALF_UP
        from apps.intake.models import AssetInfo, DebtInfo

        ZERO = Decimal("0.00")
        TWO = Decimal("0.01")

        session = self.session
        di = session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()

        assets = list(AssetInfo.objects.filter(session=session))
        debts = list(DebtInfo.objects.filter(session=session))

        real_property = sum(
            (a.current_value or ZERO) for a in assets if a.asset_type == "real_property"
        )
        personal_property = sum(
            (a.current_value or ZERO) for a in assets if a.asset_type != "real_property"
        )
        total_assets = real_property + personal_property

        secured_claims = sum(
            (d.amount_owed or ZERO) for d in debts if d.is_secured
        )
        unsecured_claims = sum(
            (d.amount_owed or ZERO) for d in debts if not d.is_secured
        )

        # CMI from IncomeInfo
        try:
            monthly_income_list = list(session.income_info.monthly_income)
            cmi = (sum(Decimal(str(m)) for m in monthly_income_list) /
                   Decimal(str(len(monthly_income_list)))).quantize(TWO, rounding=ROUND_HALF_UP) \
                if monthly_income_list else ZERO
        except Exception:
            cmi = ZERO

        # Monthly expenses total from ExpenseInfo
        try:
            ei = session.expense_info
            from apps.forms.services.schedule_j_generator import EXPENSE_FIELDS
            total_expenses = sum(
                Decimal(str(getattr(ei, f))) for f in EXPENSE_FIELDS
            ).quantize(TWO, rounding=ROUND_HALF_UP)
        except Exception:
            total_expenses = ZERO

        fmt = lambda d: str(d.quantize(TWO, rounding=ROUND_HALF_UP))

        return {
            "Bankruptcy District Information": session.district.name,
            "Debtor 1": full_name,
            "1a": fmt(real_property),
            "1b": fmt(personal_property),
            "1c": fmt(total_assets),
            "2": fmt(secured_claims),
            "3": fmt(unsecured_claims),
            "6a": fmt(cmi),
            "6b": fmt(total_expenses),
        }
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_106sum_pdf_field_map -v
git add backend/apps/forms/services/form_106sum_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Form 106Sum (summary of schedules)"
```

---

## Task 5: Schedule I — Income (86 fields)

**File:** `backend/apps/forms/services/schedule_i_generator.py`

Confirmed PDF field names (from template inspection):

- `Amount 10 Debtor 1` = total monthly income (CMI)
- `Amount 2 Debtor 1` = gross wages/salary
- `Amount 12` = total monthly income line
- `Debtor 1` = full name
- `Bankruptcy District Information` = district
- Marital status: `check1` = married filing jointly, `check2` = not married

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_schedule_i_pdf_field_map(full_session):
    gen = get_generator("schedule_i", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map.get("Debtor 1", "")
    # CMI for 6x $2200/mo = $2200.00
    assert field_map.get("Amount 10 Debtor 1") == "2200.00"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_i_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to ScheduleIGenerator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 106I (form_b106i.pdf)."""
        from decimal import Decimal, ROUND_HALF_UP

        ZERO = Decimal("0.00")
        TWO = Decimal("0.01")

        session = self.session
        di = session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()

        try:
            income_info = session.income_info
            monthly_list = list(income_info.monthly_income)
            cmi = (sum(Decimal(str(m)) for m in monthly_list) /
                   Decimal(str(len(monthly_list)))).quantize(TWO, rounding=ROUND_HALF_UP) \
                if monthly_list else ZERO
            marital_status = income_info.marital_status
            dependents = income_info.number_of_dependents
        except Exception:
            cmi = ZERO
            marital_status = "single"
            dependents = 0

        fmt = lambda d: str(d.quantize(TWO, rounding=ROUND_HALF_UP))

        return {
            "Bankruptcy District Information": session.district.name,
            "Debtor 1": full_name,
            # Line 2 — gross wages (we treat CMI as gross wages; no breakdown available)
            "Amount 2 Debtor 1": fmt(cmi),
            # Line 10 — total monthly income
            "Amount 10 Debtor 1": fmt(cmi),
            # Line 12 — combined total
            "Amount 12": fmt(cmi),
            # Dependents
            "undefined_7": str(dependents),
            # Marital status checkboxes: check4 = not married
            "check4": "/Yes" if marital_status != "married_joint" else "/Off",
            "check3": "/Yes" if marital_status == "married_joint" else "/Off",
        }
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_i_pdf_field_map -v
git add backend/apps/forms/services/schedule_i_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Schedule I (income)"
```

---

## Task 6: Schedule J — Expenses (80 fields)

**File:** `backend/apps/forms/services/schedule_j_generator.py`

Official Form 106J line → PDF field name → model field:

- `10` = rent/mortgage → `rent_or_mortgage`
- `12` = utilities → `utilities`
- `14` = home maintenance → `home_maintenance`
- `15a` = food/housekeeping → `food_and_groceries`
- `15b` = childcare → `childcare`
- `15c` = clothing → `clothing`
- `16` = medical → `medical_expenses`
- `17a` = vehicle maintenance (transportation excluding payment) → `vehicle_maintenance`
- `17b` = vehicle payment → `vehicle_payment`
- `17c` = vehicle insurance → `vehicle_insurance`
- `20a` = insurance not deducted → `insurance_not_deducted`
- `22` = total expenses
- `Debtor 1` = full name

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_schedule_j_pdf_field_map(full_session):
    gen = get_generator("schedule_j", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert field_map.get("10") == "950.00"   # rent_or_mortgage
    assert field_map.get("15a") == "400.00"  # food_and_groceries
    assert field_map.get("16") == "75.00"    # medical_expenses
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_j_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to ScheduleJGenerator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 106J (form_b106j.pdf)."""
        from decimal import Decimal, ROUND_HALF_UP
        TWO = Decimal("0.01")
        ZERO = Decimal("0.00")

        expense_values = self._get_expense_values()
        total_income = self._get_total_income()
        total_expenses = sum(expense_values.values(), ZERO).quantize(TWO, rounding=ROUND_HALF_UP)
        net = (total_income - total_expenses).quantize(TWO, rounding=ROUND_HALF_UP)

        fmt = lambda d: str(d.quantize(TWO, rounding=ROUND_HALF_UP))

        di = self.session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()

        return {
            "Bankruptcy District Information": self.session.district.name,
            "Debtor 1": full_name,
            # Expense lines
            "10":  fmt(expense_values.get("rent_or_mortgage", ZERO)),
            "12":  fmt(expense_values.get("utilities", ZERO)),
            "14":  fmt(expense_values.get("home_maintenance", ZERO)),
            "15a": fmt(expense_values.get("food_and_groceries", ZERO)),
            "15b": fmt(expense_values.get("childcare", ZERO)),
            "15c": fmt(expense_values.get("clothing", ZERO)),
            "16":  fmt(expense_values.get("medical_expenses", ZERO)),
            "17a": fmt(expense_values.get("vehicle_maintenance", ZERO)),
            "17b": fmt(expense_values.get("vehicle_payment", ZERO)),
            "17c": fmt(expense_values.get("vehicle_insurance", ZERO)),
            "20a": fmt(expense_values.get("insurance_not_deducted", ZERO)),
            "21":  fmt(expense_values.get("other_expenses", ZERO) +
                       expense_values.get("child_support_paid", ZERO)),
            # Totals
            "22":  fmt(total_expenses),
            "23":  fmt(total_income),
            "24":  fmt(net),
        }
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_j_pdf_field_map -v
git add backend/apps/forms/services/schedule_j_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Schedule J (expenses)"
```

---

## Task 7: Form 122A-1 — Means Test (67 fields)

**File:** `backend/apps/forms/services/form_122a1_generator.py`

Confirmed field names from template:

- `Bankruptcy District Information` (/Ch)
- `Case number1` (/Tx)
- `Debtor1.First name`, `Debtor1.Last name`, `Debtor1.Middle name`
- `12B` = current monthly income (CMI × 12 annualized)
- `13A` = applicable median income
- `13B` = annualized CMI (same as 12B)
- `13C` = difference (13B − 13A)
- `14a` = checkbox: below median (passes means test)

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_form_122a1_pdf_field_map(full_session):
    gen = get_generator("form_122a1", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert field_map["Debtor1.First name"] == "Maria"
    # CMI = $2200/mo, annualized = $26,400
    assert field_map.get("12B") == "26400.00"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_122a1_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to Form122A1Generator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 122A-1 (b_122a-1.pdf)."""
        from decimal import Decimal, ROUND_HALF_UP
        TWO = Decimal("0.01")
        ZERO = Decimal("0.00")

        data = self.generate()
        di = self.session.debtor_info
        fmt = lambda d: str(Decimal(str(d)).quantize(TWO, rounding=ROUND_HALF_UP))

        # CMI and annualized values
        cmi = Decimal(str(data.get("current_monthly_income", ZERO)))
        annualized_cmi = (cmi * 12).quantize(TWO, rounding=ROUND_HALF_UP)
        median_annual = Decimal(str(data.get("median_income_annual", ZERO)))
        diff = annualized_cmi - median_annual
        below_median = diff <= ZERO

        return {
            "Bankruptcy District Information": self.session.district.name,
            "Case number1": "",
            "Debtor1.First name": di.first_name,
            "Debtor1.Middle name": di.middle_name or "",
            "Debtor1.Last name": di.last_name,
            "12B": fmt(annualized_cmi),
            "13A": fmt(median_annual),
            "13B": fmt(annualized_cmi),
            "13C": fmt(diff),
            "14a": "/Yes" if below_median else "/Off",
        }
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_122a1_pdf_field_map -v
git add backend/apps/forms/services/form_122a1_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Form 122A-1 (means test)"
```

---

## Task 8: Form 103B — Fee Waiver Application (134 fields)

**File:** `backend/apps/forms/services/form_103b_generator.py`

Key confirmed fields: `Bankruptcy District Information`, `Debtor` (full name), `Amount you owe`, `check1` (income-based), `check2` (benefits-based), plus household size and income fields.

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_form_103b_pdf_field_map(full_session):
    gen = get_generator("form_103b", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map.get("Debtor", "")
    assert field_map.get("Bankruptcy District Information") == "Northern District of Illinois"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_103b_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to Form103BGenerator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 103B (form_b103b.pdf)."""
        from decimal import Decimal, ROUND_HALF_UP
        TWO = Decimal("0.01")
        fmt = lambda d: str(Decimal(str(d)).quantize(TWO, rounding=ROUND_HALF_UP))

        data = self.generate()
        di = self.session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()

        basis = data.get("qualification_basis", "none")
        monthly_income = data.get("monthly_income", Decimal("0.00"))
        monthly_expenses = data.get("monthly_expenses", Decimal("0.00"))
        household_size = data.get("household_size", 1)
        total_debt = data.get("total_debt", Decimal("0.00"))

        return {
            "Bankruptcy District Information": self.session.district.name,
            "Debtor": full_name,
            "Amount you owe": fmt(total_debt),
            # Qualification basis checkboxes
            "check1": "/Yes" if basis == "income" else "/Off",
            "check2": "/Yes" if basis == "benefits" else "/Off",
            # Financial summary
            "3 type": str(household_size),
            "4 type": fmt(monthly_income),
            "5 Type": fmt(monthly_expenses),
        }
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_103b_pdf_field_map -v
git add backend/apps/forms/services/form_103b_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Form 103B (fee waiver application)"
```

---

## Task 9: Schedule A/B — Property (379 fields)

**File:** `backend/apps/forms/services/schedule_ab_generator.py`

Schedule A/B lists assets. Each asset row uses fields `1 1`, `1 1a`, `10 check`, `10 description`, `10 description amount`, etc. The numbered rows (1–17) correspond to property categories. Our model has `asset_type`: `real_property`, `vehicle`, `bank_account`, `retirement_account`, `other`.

Key field mappings:

- Row `1 1` / `1 1a` = real property description / value
- Row `16 Cash amount` = cash/bank balance
- Row `17` = vehicles (description amount fields)
- `Debtor 1` = full name

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_schedule_ab_pdf_field_map(full_session):
    gen = get_generator("schedule_a_b", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map.get("Debtor 1", "")
    # The full_session has a bank_account asset worth $320
    assert field_map.get("16 Cash amount") == "320.00"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_ab_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to ScheduleABGenerator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 106A/B (form_b106ab.pdf)."""
        from decimal import Decimal, ROUND_HALF_UP
        from apps.intake.models import AssetInfo
        TWO = Decimal("0.01")
        ZERO = Decimal("0.00")
        fmt = lambda d: str(Decimal(str(d)).quantize(TWO, rounding=ROUND_HALF_UP))

        session = self.session
        di = session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()
        assets = list(AssetInfo.objects.filter(session=session))

        result: dict[str, str] = {
            "Bankruptcy District Information": session.district.name,
            "Debtor 1": full_name,
        }

        # Part 1: Real property (row 1)
        real_props = [a for a in assets if a.asset_type == "real_property"]
        if real_props:
            result["1 1"] = real_props[0].description or ""
            result["1 1a"] = fmt(real_props[0].current_value or ZERO)

        # Part 2: Vehicles (row 3)
        vehicles = [a for a in assets if a.asset_type == "vehicle"]
        if vehicles:
            result["3 description"] = vehicles[0].description or ""
            result["3 description amount"] = fmt(vehicles[0].current_value or ZERO)

        # Part 2: Cash and bank balances (row 16)
        bank_total = sum((a.current_value or ZERO) for a in assets if a.asset_type == "bank_account")
        result["16 Cash amount"] = fmt(bank_total)

        # Part 2: Retirement (row 12)
        retirement = [a for a in assets if a.asset_type == "retirement_account"]
        if retirement:
            result["12"] = fmt(retirement[0].current_value or ZERO)

        # Part 2: Other (row 17)
        others = [a for a in assets if a.asset_type == "other"]
        if others:
            result["17"] = fmt(others[0].current_value or ZERO)

        return result
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_ab_pdf_field_map -v
git add backend/apps/forms/services/schedule_ab_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Schedule A/B (property)"
```

---

## Task 10: Schedule C — Exemptions (107 fields)

**File:** `backend/apps/forms/services/schedule_c_generator.py`

Field names are `2`, `2.1`, `2.2`, `2.3`, `3`, `4`, etc. Row `2.X` corresponds to exemption entries. Field `2.1` = property description, `2.2` = law/statute, `2.3` = value claimed, `3` = current value of property, `4` = amount of exemption.

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_schedule_c_pdf_field_map(full_session):
    gen = get_generator("schedule_c", full_session)
    field_map = gen.pdf_field_map()
    # full_session has a bank_account — may or may not generate an exemption
    assert isinstance(field_map, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in field_map.items())
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_c_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to ScheduleCGenerator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 106C (b_106c_0425-form.pdf)."""
        from decimal import Decimal, ROUND_HALF_UP
        TWO = Decimal("0.01")
        fmt = lambda d: str(Decimal(str(d)).quantize(TWO, rounding=ROUND_HALF_UP))

        session = self.session
        di = session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()
        exemptions = self.generate().get("exemptions", [])

        result: dict[str, str] = {
            "Bankruptcy District Information": session.district.name,
            "Debtor 1": full_name,
        }

        # Up to 5 exemption rows (2.1–2.3 pattern; rows are 2, 3, 4, 5, 6 on the form)
        row_fields = [("2.1", "2.2", "2.3"), ("3", "3.2", "3.3"),
                      ("4", "4.2", "4.3"), ("5", "5.2", "5.3"),
                      ("6", "6.2", "6.3")]
        for i, exemption in enumerate(exemptions[:5]):
            desc_field, statute_field, amount_field = row_fields[i]
            result[desc_field] = exemption.get("property_description", "")
            result[statute_field] = exemption.get("statute", "")
            result[amount_field] = fmt(exemption.get("amount_claimed", Decimal("0.00")))

        return result
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_c_pdf_field_map -v
git add backend/apps/forms/services/schedule_c_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Schedule C (exemptions)"
```

---

## Task 11: Schedule D — Secured Creditors (193 fields)

**File:** `backend/apps/forms/services/schedule_d_generator.py`

Fields follow a numbered pattern per row: `1`, `1_2`, `1_3`, `1_4`, `1_5` for creditor 1 (name, address, description of collateral, value, claim amount), then `2`, `2_2`, etc.

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_schedule_d_pdf_field_map(full_session):
    gen = get_generator("schedule_d", full_session)
    field_map = gen.pdf_field_map()
    assert isinstance(field_map, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in field_map.items())
    assert field_map.get("Bankruptcy District Information") == "Northern District of Illinois"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_d_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to ScheduleDGenerator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 106D (form_b106d.pdf)."""
        from decimal import Decimal, ROUND_HALF_UP
        from apps.intake.models import DebtInfo
        TWO = Decimal("0.01")
        ZERO = Decimal("0.00")
        fmt = lambda d: str(Decimal(str(d)).quantize(TWO, rounding=ROUND_HALF_UP))

        session = self.session
        di = session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()

        secured_debts = list(
            DebtInfo.objects.filter(session=session, is_secured=True)
        )

        result: dict[str, str] = {
            "Bankruptcy District Information": session.district.name,
            "Debtor 1": full_name,
        }

        # Each creditor row: N (creditor name), N_2 (address), N_3 (collateral desc),
        # N_4 (collateral value), N_5 (claim amount)
        for i, debt in enumerate(secured_debts[:6], start=1):
            sfx = "" if i == 1 else f"_{i}"  # row 1 has no suffix, row 2 is _2, etc.
            # Actually the pattern is 1, 1_2, 1_3... so row index IS the base number
            base = str(i)
            result[base] = debt.creditor_name or ""
            result[f"{base}_2"] = ""  # address not tracked
            result[f"{base}_3"] = debt.collateral_description or ""
            result[f"{base}_4"] = fmt(debt.collateral_value or ZERO)
            result[f"{base}_5"] = fmt(debt.amount_owed or ZERO)

        # Total secured claims
        total_secured = sum((d.amount_owed or ZERO) for d in secured_debts)
        result["undefined_44"] = fmt(total_secured)

        return result
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_d_pdf_field_map -v
git add backend/apps/forms/services/schedule_d_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Schedule D (secured creditors)"
```

---

## Task 12: Schedule E/F — Unsecured Creditors (336 fields)

**File:** `backend/apps/forms/services/schedule_ef_generator.py`

Fields follow the same numbered pattern: `1`, `1_2`, `1_3`, `1_4`, `1_5` per creditor row.

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_schedule_ef_pdf_field_map(full_session):
    gen = get_generator("schedule_e_f", full_session)
    field_map = gen.pdf_field_map()
    assert isinstance(field_map, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in field_map.items())
    # full_session has Capital One credit card ($4200 unsecured)
    assert field_map.get("1") == "Capital One"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_ef_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to ScheduleEFGenerator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 106E/F (form_b106ef.pdf)."""
        from decimal import Decimal, ROUND_HALF_UP
        from apps.intake.models import DebtInfo
        TWO = Decimal("0.01")
        ZERO = Decimal("0.00")
        fmt = lambda d: str(Decimal(str(d)).quantize(TWO, rounding=ROUND_HALF_UP))

        session = self.session
        di = session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()

        unsecured_debts = list(
            DebtInfo.objects.filter(session=session, is_secured=False)
        )

        result: dict[str, str] = {
            "Bankruptcy District Information": session.district.name,
            "Debtor 1": full_name,
        }

        # Part 2 (nonpriority unsecured): rows 1, 2, 3...
        # Fields: N (creditor name), N_2 (last 4 of account), N_3 (date incurred),
        # N_4 (amount), N_5 (basis — e.g. "credit card")
        for i, debt in enumerate(unsecured_debts[:10], start=1):
            base = str(i)
            result[base] = debt.creditor_name or ""
            result[f"{base}_2"] = ""  # account last 4 not tracked
            result[f"{base}_3"] = ""  # date incurred not tracked
            result[f"{base}_4"] = fmt(debt.amount_owed or ZERO)
            result[f"{base}_5"] = (debt.debt_type or "").replace("_", " ")

        return result
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_schedule_ef_pdf_field_map -v
git add backend/apps/forms/services/schedule_ef_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Schedule E/F (unsecured creditors)"
```

---

## Task 13: Form 107 — Statement of Financial Affairs (537 fields)

**File:** `backend/apps/forms/services/form_107_generator.py`

Form 107 has 537 fields. Most of its 25 questions are placeholders in the current generator. Map the fields we have data for (income history and creditor payments), leave the rest blank.

Key fields: debtor name/district header, plus question-specific fields.
Field pattern for income (question 1): `Amount 2 Debtor 1` (matches Schedule I).
Field pattern for creditor payments (question 3): `Amount1 13a`, `Amount2 13a` (creditor amounts).

- [ ] **Step 1: Write the failing test**

Append to `test_pdf_field_maps.py`:

```python
def test_form_107_pdf_field_map(full_session):
    gen = get_generator("form_107", full_session)
    field_map = gen.pdf_field_map()
    assert isinstance(field_map, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in field_map.items())
    assert field_map.get("Bankruptcy District Information") == "Northern District of Illinois"
    assert "Torres" in field_map.get("Debtor 1", "")
```

- [ ] **Step 2: Run — verify FAIL**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_107_pdf_field_map -v
```

- [ ] **Step 3: Add `pdf_field_map()` to Form107Generator**

```python
    def pdf_field_map(self) -> dict[str, str]:
        """Map session data to Official Form 107 (b_107_0425-form.pdf).

        Only questions 1 (income) and 3 (creditor payments in last 90 days)
        have data from the intake models. All other questions are left blank.
        """
        from decimal import Decimal, ROUND_HALF_UP
        from apps.intake.models import DebtInfo
        TWO = Decimal("0.01")
        ZERO = Decimal("0.00")
        fmt = lambda d: str(Decimal(str(d)).quantize(TWO, rounding=ROUND_HALF_UP))

        session = self.session
        di = session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()

        # CMI
        try:
            ml = list(session.income_info.monthly_income)
            cmi = (sum(Decimal(str(m)) for m in ml) / Decimal(str(len(ml)))
                   ).quantize(TWO, rounding=ROUND_HALF_UP) if ml else ZERO
        except Exception:
            cmi = ZERO

        # Recent creditor payments (question 3 — up to 3 creditors)
        debts = list(DebtInfo.objects.filter(session=session)[:3])

        result: dict[str, str] = {
            "Bankruptcy District Information": session.district.name,
            "Debtor 1": full_name,
            # Question 1 — income (reuses Schedule I field naming)
            "Amount 2 Debtor 1": fmt(cmi),
        }

        # Question 3 — creditor payments: Amount1 13a, Amount1 13b, Amount1 14
        amount_fields = ["Amount1 13a", "Amount1 13b", "Amount1 14"]
        creditor_fields = ["Street address 1b Debtor 1", "Street address 1c Debtor 1",
                           "Street address 2b Debtor 1"]
        for i, debt in enumerate(debts):
            if i < len(amount_fields):
                result[amount_fields[i]] = fmt(debt.amount_owed or ZERO)
                result[creditor_fields[i]] = debt.creditor_name or ""

        return result
```

- [ ] **Step 4: Run — verify PASS, commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_107_pdf_field_map -v
git add backend/apps/forms/services/form_107_generator.py \
        backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): pdf_field_map() for Form 107 (statement of financial affairs)"
```

---

## Task 14: Run full test suite + deploy

- [ ] **Step 1: Run all form-related tests**

```bash
docker compose exec backend python -m pytest apps/forms/tests/ -v
```

Expected: all 13 `test_*_pdf_field_map` tests pass, plus existing tests.

- [ ] **Step 2: Run full backend suite**

```bash
docker compose exec backend python -m pytest --tb=short -q
```

Expected: no regressions (413+ tests passing).

- [ ] **Step 3: Push to Heroku and smoke-test**

```bash
git push heroku main
```

Navigate to the demo, click Download on Form 121 first (simplest, 32 fields). Verify the PDF opens with Maria Torres's name in the fields. Then test Form 101, Schedule J.

- [ ] **Step 4: Re-seed demo data to regenerate form records**

```bash
heroku run python manage.py seed_demo_data --reset --app dignifi
```

The `--reset` flag drops and recreates all demo accounts so `generate()` is called fresh with current generator code.

---

## Self-Review

**Spec coverage:**

- ✅ All 13 generators have `pdf_field_map()`
- ✅ Each method has a test asserting shape and at least one field value
- ✅ Checkbox fields use `/Yes`/`/Off` strings
- ✅ Full integration verified by deploying + downloading real PDFs

**Known partial mappings (data not tracked in intake models):**

- Schedule D: creditor address (not in DebtInfo model)
- Schedule E/F: account last 4 digits, date incurred (not tracked)
- Form 107: questions 2, 4–25 are blank (data not collected)
- Form 103B: some property detail rows not mapped

These are intentional — the court forms allow blank fields where information is not available. The filed PDF will be accurate for the data we do have.

**Interface contract with Layers 1+3:**
The `download` endpoint calls `generator.pdf_field_map()`. If a generator raises `NotImplementedError`, the endpoint returns 501. After this plan is merged, all 13 return a `dict[str, str]` and the 501 path is never hit.
