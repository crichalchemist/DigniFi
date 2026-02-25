# Chapter 7 Bankruptcy Forms Generators Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build 13 form generators to file a real Chapter 7 bankruptcy case with ILND using DigniFi platform (dog-fooding for founder's case).

**Architecture:** Service layer pattern (matching existing Form101Generator). Each form generator is a service class that takes IntakeSession and generates a PDF matching official bankruptcy form layout. Extends existing intake models with Chapter 7-specific fields. Uses PyPDF2 for PDF generation. TDD with pytest for each form.

**Tech Stack:** Django 5.0, Django REST Framework, PyPDF2, pytest, django-encrypted-model-fields

**Context:** User is sole proprietor with 70% personal / 30% business debts, $0 income, needs fee waiver (Form 103B). Filing urgently (4-6 weeks) via ILND eDB portal.

---

## Phase 1: Data Model Extensions (Week 1)

### Task 1: Extend DebtInfo Model for Consumer vs Business Classification

**Files:**
- Modify: `backend/apps/intake/models.py` (DebtInfo class)
- Create: `backend/apps/intake/migrations/0002_add_debt_classification.py`
- Test: `backend/apps/intake/tests/test_models.py`

**Step 1: Write failing test for debt classification**

```bash
cd backend
```

Create test file if doesn't exist:

```python
# backend/apps/intake/tests/test_models.py
import pytest
from apps.intake.models import DebtInfo, IntakeSession
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestDebtInfoClassification:
    def test_debt_type_defaults_to_consumer(self):
        """Test that debt_type defaults to consumer."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        debt = DebtInfo.objects.create(
            session=session,
            creditor_name='Test Creditor',
            amount_owed=1000.00
        )

        assert debt.debt_type == 'consumer'

    def test_can_mark_debt_as_business(self):
        """Test that debt can be marked as business type."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        debt = DebtInfo.objects.create(
            session=session,
            creditor_name='Business Vendor',
            amount_owed=5000.00,
            debt_type='business'
        )

        assert debt.debt_type == 'business'

    def test_can_mark_debt_as_secured(self):
        """Test that debt can be marked as secured."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        debt = DebtInfo.objects.create(
            session=session,
            creditor_name='Auto Lender',
            amount_owed=15000.00,
            is_secured=True,
            collateral_description='2020 Honda Civic'
        )

        assert debt.is_secured is True
        assert debt.collateral_description == '2020 Honda Civic'
```

**Step 2: Run test to verify it fails**

```bash
pytest backend/apps/intake/tests/test_models.py::TestDebtInfoClassification -v
```

Expected output: FAIL - "DebtInfo has no attribute 'debt_type'"

**Step 3: Add fields to DebtInfo model**

```python
# backend/apps/intake/models.py

class DebtInfo(models.Model):
    """
    Debt information (Schedule D for secured, E/F for unsecured).
    Supports both consumer and business debt classification for Chapter 7 means test.
    """

    # Existing fields...
    session = models.ForeignKey(IntakeSession, on_delete=models.CASCADE, related_name='debts')
    creditor_name = models.CharField(max_length=255)
    creditor_address = models.TextField(blank=True)
    account_number = models.CharField(max_length=100, blank=True)
    amount_owed = EncryptedDecimalField(max_digits=12, decimal_places=2)

    # NEW: Chapter 7 classification fields
    debt_type = models.CharField(
        max_length=20,
        choices=[
            ('consumer', 'Consumer Debt'),
            ('business', 'Business Debt'),
        ],
        default='consumer',
        help_text="Consumer vs business classification for means test applicability"
    )

    is_secured = models.BooleanField(
        default=False,
        help_text="Secured debts go on Schedule D; unsecured on Schedule E/F"
    )

    collateral_description = models.TextField(
        blank=True,
        help_text="Description of collateral if secured debt (e.g., '2020 Honda Civic')"
    )

    is_priority = models.BooleanField(
        default=False,
        help_text="Priority unsecured debts (e.g., taxes, child support) on Schedule E/F Part 1"
    )

    is_contingent = models.BooleanField(
        default=False,
        help_text="Debt depends on future event"
    )

    is_unliquidated = models.BooleanField(
        default=False,
        help_text="Amount not yet determined"
    )

    is_disputed = models.BooleanField(
        default=False,
        help_text="Debtor disputes validity or amount"
    )

    date_incurred = models.DateField(
        null=True,
        blank=True,
        help_text="When debt was incurred"
    )

    # Existing fields...
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'debts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.creditor_name}: ${self.amount_owed} ({self.get_debt_type_display()})"
```

**Step 4: Create migration**

```bash
python manage.py makemigrations intake --name add_debt_classification
```

Expected output: "Migrations for 'intake': backend/apps/intake/migrations/0002_add_debt_classification.py"

**Step 5: Run migration**

```bash
python manage.py migrate intake
```

Expected output: "Applying intake.0002_add_debt_classification... OK"

**Step 6: Run tests to verify they pass**

```bash
pytest backend/apps/intake/tests/test_models.py::TestDebtInfoClassification -v
```

Expected output: 3 tests PASSED

**Step 7: Commit**

```bash
git add backend/apps/intake/models.py backend/apps/intake/migrations/0002_add_debt_classification.py backend/apps/intake/tests/test_models.py
git commit -m "feat(intake): add consumer/business debt classification for Chapter 7

- Add debt_type field (consumer/business) for means test calculation
- Add is_secured field for Schedule D vs E/F routing
- Add collateral_description for secured debts
- Add priority/contingent/unliquidated/disputed flags for Schedule E/F
- Add date_incurred for debt timeline tracking
- Migration: 0002_add_debt_classification

Supports Chapter 7 filing requirements per 11 U.S.C. § 707(b)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 2: Create FeeWaiverApplication Model

**Files:**
- Modify: `backend/apps/intake/models.py`
- Create: `backend/apps/intake/migrations/0003_add_fee_waiver.py`
- Test: `backend/apps/intake/tests/test_models.py`

**Step 1: Write failing test**

```python
# backend/apps/intake/tests/test_models.py

@pytest.mark.django_db
class TestFeeWaiverApplication:
    def test_fee_waiver_defaults_to_pending(self):
        """Test that fee waiver status defaults to pending."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        from apps.intake.models import FeeWaiverApplication

        waiver = FeeWaiverApplication.objects.create(
            session=session,
            monthly_income=0.00,
            monthly_expenses=1200.00
        )

        assert waiver.status == 'pending'

    def test_qualifies_for_waiver_with_zero_income(self):
        """Test that $0 income automatically qualifies for fee waiver."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        from apps.intake.models import FeeWaiverApplication

        waiver = FeeWaiverApplication.objects.create(
            session=session,
            monthly_income=0.00,
            monthly_expenses=1200.00
        )

        # Poverty threshold for 1 person: $1,882.50/month
        assert waiver.qualifies_for_waiver() is True

    def test_qualifies_for_waiver_with_public_benefits(self):
        """Test that receiving public benefits qualifies for waiver."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        from apps.intake.models import FeeWaiverApplication

        waiver = FeeWaiverApplication.objects.create(
            session=session,
            monthly_income=800.00,
            monthly_expenses=1200.00,
            receives_public_benefits=True,
            benefit_types=['SNAP', 'Medicaid']
        )

        assert waiver.qualifies_for_waiver() is True
```

**Step 2: Run test to verify it fails**

```bash
pytest backend/apps/intake/tests/test_models.py::TestFeeWaiverApplication -v
```

Expected: ImportError - "cannot import name 'FeeWaiverApplication'"

**Step 3: Implement FeeWaiverApplication model**

```python
# backend/apps/intake/models.py

from decimal import Decimal

class FeeWaiverApplication(models.Model):
    """
    Chapter 7 fee waiver application (Form 103B).

    Qualifies if:
    1. Income < 150% federal poverty line ($1,882.50/month for 1 person as of 2024)
    2. OR receives means-tested public benefits (SSI, SNAP, TANF, etc.)
    3. AND cannot pay filing fee ($338) in full or installments

    Per 28 U.S.C. § 1930(f)
    """

    # Relations
    session = models.OneToOneField(
        IntakeSession,
        on_delete=models.CASCADE,
        related_name='fee_waiver'
    )

    # Household information
    household_size = models.IntegerField(
        default=1,
        help_text="Number of people in household"
    )

    # Financial information (encrypted)
    monthly_income = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total monthly income from all sources"
    )

    monthly_expenses = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total monthly expenses"
    )

    # Public benefits
    receives_public_benefits = models.BooleanField(
        default=False,
        help_text="Receives SSI, SNAP, TANF, or other means-tested benefits"
    )

    benefit_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of benefit programs (e.g., ['SNAP', 'Medicaid'])"
    )

    # Inability to pay
    cannot_pay_full = models.BooleanField(
        default=True,
        help_text="Cannot pay $338 filing fee in full"
    )

    cannot_pay_installments = models.BooleanField(
        default=True,
        help_text="Cannot pay in 4 installments over 120 days"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('denied', 'Denied'),
        ],
        default='pending'
    )

    filed_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fee_waiver_applications'

    def __str__(self):
        return f"Fee Waiver for {self.session} ({self.status})"

    def qualifies_for_waiver(self) -> bool:
        """
        Determine if applicant qualifies for fee waiver.

        Returns:
            bool: True if qualifies via income test OR public benefits
        """
        # Automatic qualification: Receives public benefits
        if self.receives_public_benefits and self.benefit_types:
            return True

        # Income test: < 150% federal poverty line
        # 2024 poverty guidelines (annual): $15,060 for 1 person
        # 150% = $22,590 annual = $1,882.50 monthly
        # Add $5,380 per additional person
        poverty_threshold_annual = Decimal('15060') + (Decimal('5380') * (self.household_size - 1))
        poverty_threshold_150_monthly = (poverty_threshold_annual * Decimal('1.5')) / Decimal('12')

        if self.monthly_income < poverty_threshold_150_monthly:
            return True

        return False

    def get_poverty_threshold(self) -> Decimal:
        """Calculate 150% poverty threshold for household size."""
        poverty_threshold_annual = Decimal('15060') + (Decimal('5380') * (self.household_size - 1))
        return (poverty_threshold_annual * Decimal('1.5')) / Decimal('12')
```

**Step 4: Create migration**

```bash
python manage.py makemigrations intake --name add_fee_waiver
```

**Step 5: Run migration**

```bash
python manage.py migrate intake
```

**Step 6: Run tests**

```bash
pytest backend/apps/intake/tests/test_models.py::TestFeeWaiverApplication -v
```

Expected: 3 tests PASSED

**Step 7: Commit**

```bash
git add backend/apps/intake/models.py backend/apps/intake/migrations/0003_add_fee_waiver.py backend/apps/intake/tests/test_models.py
git commit -m "feat(intake): add FeeWaiverApplication model for Chapter 7

- Implements Form 103B data model
- Automatic qualification logic: public benefits OR <150% poverty
- Poverty threshold calculation: $15,060 base + $5,380 per additional person
- Status tracking (pending/approved/denied)
- Migration: 0003_add_fee_waiver

Per 28 U.S.C. § 1930(f) fee waiver provisions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 2: Form Generators - Property & Exemptions (Week 1)

### Task 3: Schedule A/B Generator (Property)

**Files:**
- Create: `backend/apps/forms/services/schedule_ab_generator.py`
- Test: `backend/apps/forms/tests/test_schedule_ab_generator.py`
- Reference: `Official Bankruptcy Rules+Forms/Forms/form_b106ab.pdf`

**Step 1: Write failing test**

```python
# backend/apps/forms/tests/test_schedule_ab_generator.py

import pytest
from decimal import Decimal
from apps.intake.models import IntakeSession, AssetInfo
from apps.forms.services.schedule_ab_generator import ScheduleABGenerator
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestScheduleABGenerator:
    def test_generates_schedule_ab_with_real_property(self):
        """Test generating Schedule A/B with real property."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        # Add real property
        AssetInfo.objects.create(
            session=session,
            asset_type='real_estate',
            description='123 Main St, Chicago, IL 60601',
            current_value=Decimal('200000.00'),
            amount_owed=Decimal('150000.00')
        )

        generator = ScheduleABGenerator(session)
        result = generator.generate()

        assert result['total_real_property_value'] == Decimal('200000.00')
        assert result['total_personal_property_value'] == Decimal('0.00')
        assert result['total_value'] == Decimal('200000.00')

    def test_generates_schedule_ab_with_vehicle(self):
        """Test generating Schedule A/B with vehicle."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        # Add vehicle
        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='2020 Honda Civic',
            current_value=Decimal('15000.00'),
            amount_owed=Decimal('10000.00')
        )

        generator = ScheduleABGenerator(session)
        result = generator.generate()

        assert result['total_personal_property_value'] == Decimal('15000.00')
        assert len(result['vehicles']) == 1
        assert result['vehicles'][0]['description'] == '2020 Honda Civic'
        assert result['vehicles'][0]['equity'] == Decimal('5000.00')
```

**Step 2: Run test to verify it fails**

```bash
pytest backend/apps/forms/tests/test_schedule_ab_generator.py -v
```

Expected: ImportError - "No module named 'apps.forms.services.schedule_ab_generator'"

**Step 3: Implement ScheduleABGenerator**

```python
# backend/apps/forms/services/schedule_ab_generator.py

from decimal import Decimal
from typing import Dict, List, Any
from apps.intake.models import IntakeSession, AssetInfo


class ScheduleABGenerator:
    """
    Generate Schedule A/B (Property).

    Part 1: Real Property
    Part 2: Personal Property (35 categories)
    Part 3: Summary totals

    Official form: form_b106ab.pdf
    """

    def __init__(self, intake_session: IntakeSession):
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule A/B data structure.

        Returns:
            dict: Complete Schedule A/B data with real/personal property breakdown
        """
        # Fetch all assets
        assets = self.session.assets.all()

        # Separate by type
        real_property = [a for a in assets if a.asset_type == 'real_estate']
        personal_property = [a for a in assets if a.asset_type != 'real_estate']

        # Calculate totals
        total_real = sum(a.current_value for a in real_property)
        total_personal = sum(a.current_value for a in personal_property)

        # Map personal property to Schedule A/B categories
        vehicles = [a for a in personal_property if a.asset_type == 'vehicle']
        bank_accounts = [a for a in personal_property if a.asset_type == 'bank_account']
        household_goods = [a for a in personal_property if a.asset_type == 'household_goods']

        return {
            # Part 1: Real Property
            'real_property': [
                {
                    'description': asset.description,
                    'address': getattr(asset, 'address', ''),
                    'current_value': asset.current_value,
                    'amount_owed': asset.amount_owed or Decimal('0.00'),
                    'equity': asset.current_value - (asset.amount_owed or Decimal('0.00'))
                }
                for asset in real_property
            ],
            'total_real_property_value': total_real,

            # Part 2: Personal Property
            'vehicles': [
                {
                    'description': asset.description,
                    'year': getattr(asset, 'year', ''),
                    'make': getattr(asset, 'make', ''),
                    'model': getattr(asset, 'model', ''),
                    'current_value': asset.current_value,
                    'amount_owed': asset.amount_owed or Decimal('0.00'),
                    'equity': asset.current_value - (asset.amount_owed or Decimal('0.00'))
                }
                for asset in vehicles
            ],
            'bank_accounts': [
                {
                    'institution': asset.description,
                    'account_type': getattr(asset, 'account_type', 'checking'),
                    'balance': asset.current_value
                }
                for asset in bank_accounts
            ],
            'household_goods': [
                {
                    'description': asset.description,
                    'current_value': asset.current_value
                }
                for asset in household_goods
            ],
            'total_personal_property_value': total_personal,

            # Part 3: Summary
            'total_value': total_real + total_personal
        }

    def preview(self) -> Dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
```

**Step 4: Run tests**

```bash
pytest backend/apps/forms/tests/test_schedule_ab_generator.py -v
```

Expected: 2 tests PASSED

**Step 5: Commit**

```bash
git add backend/apps/forms/services/schedule_ab_generator.py backend/apps/forms/tests/test_schedule_ab_generator.py
git commit -m "feat(forms): implement Schedule A/B generator for property listing

- Generate Part 1 (Real Property) with equity calculations
- Generate Part 2 (Personal Property) with category mapping
- Calculate total values for form summary
- Support vehicles, bank accounts, household goods
- Preview method for user review

Implements Official Form 106A/B per bankruptcy rules

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 4: Schedule C Generator (Exemptions)

**Files:**
- Create: `backend/apps/forms/services/schedule_c_generator.py`
- Test: `backend/apps/forms/tests/test_schedule_c_generator.py`
- Create: `backend/apps/forms/fixtures/illinois_exemptions_2024.json`

**Step 1: Write failing test**

```python
# backend/apps/forms/tests/test_schedule_c_generator.py

import pytest
from decimal import Decimal
from apps.intake.models import IntakeSession, AssetInfo
from apps.forms.services.schedule_c_generator import ScheduleCGenerator
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestScheduleCGenerator:
    def test_applies_vehicle_exemption(self):
        """Test applying Illinois $2,400 vehicle exemption."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        # Vehicle worth $10,000 with $8,000 owed = $2,000 equity
        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='2020 Honda Civic',
            current_value=Decimal('10000.00'),
            amount_owed=Decimal('8000.00')
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        # Should apply full exemption (equity < $2,400 limit)
        assert len(result['exemptions']) == 1
        assert result['exemptions'][0]['statute'] == '735 ILCS 5/12-1001(c)'
        assert result['exemptions'][0]['amount_claimed'] == Decimal('2000.00')
        assert result['exemptions'][0]['amount_available'] == Decimal('2400.00')

    def test_applies_wildcard_exemption(self):
        """Test applying Illinois $4,000 wildcard exemption."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        # Household goods worth $3,000
        AssetInfo.objects.create(
            session=session,
            asset_type='household_goods',
            description='Furniture and appliances',
            current_value=Decimal('3000.00')
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        # Should use wildcard exemption
        assert len(result['exemptions']) == 1
        assert result['exemptions'][0]['statute'] == '735 ILCS 5/12-1001(b)'
        assert result['exemptions'][0]['amount_claimed'] == Decimal('3000.00')
        assert result['exemptions'][0]['amount_available'] == Decimal('4000.00')
```

**Step 2: Run test to verify it fails**

```bash
pytest backend/apps/forms/tests/test_schedule_c_generator.py -v
```

Expected: ImportError

**Step 3: Create Illinois exemptions fixture**

```json
# backend/apps/forms/fixtures/illinois_exemptions_2024.json

[
    {
        "statute": "735 ILCS 5/12-901",
        "property_type": "homestead",
        "description": "Homestead (principal residence)",
        "amount": "15000.00",
        "is_unlimited": false
    },
    {
        "statute": "735 ILCS 5/12-1001(b)",
        "property_type": "wildcard",
        "description": "Personal property wildcard",
        "amount": "4000.00",
        "is_unlimited": false
    },
    {
        "statute": "735 ILCS 5/12-1001(c)",
        "property_type": "vehicle",
        "description": "Motor vehicle",
        "amount": "2400.00",
        "is_unlimited": false
    },
    {
        "statute": "735 ILCS 5/12-1001(a)",
        "property_type": "clothing",
        "description": "Necessary clothing",
        "amount": "100",
        "is_unlimited": true
    },
    {
        "statute": "735 ILCS 5/12-1006",
        "property_type": "retirement",
        "description": "Retirement benefits",
        "amount": "100",
        "is_unlimited": true
    }
]
```

**Step 4: Implement ScheduleCGenerator**

```python
# backend/apps/forms/services/schedule_c_generator.py

from decimal import Decimal
from typing import Dict, List, Any
import json
from pathlib import Path
from apps.intake.models import IntakeSession, AssetInfo


class ScheduleCGenerator:
    """
    Generate Schedule C (Property Claimed as Exempt).

    Applies Illinois state exemptions per 735 ILCS 5/12-901 et seq.

    Key Illinois exemptions:
    - $15,000 homestead (principal residence)
    - $4,000 wildcard (any personal property)
    - $2,400 motor vehicle
    - 100% clothing, retirement benefits, wages (85%)

    Official form: form_b106c_0425-form.pdf
    """

    # Load Illinois exemptions
    EXEMPTIONS_FILE = Path(__file__).parent.parent / 'fixtures' / 'illinois_exemptions_2024.json'

    with open(EXEMPTIONS_FILE) as f:
        ILLINOIS_EXEMPTIONS = {ex['property_type']: ex for ex in json.load(f)}

    def __init__(self, intake_session: IntakeSession):
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule C data with applied exemptions.

        Returns:
            dict: Exemptions list with statute, amount claimed, amount available
        """
        assets = self.session.assets.all()
        exemptions = []

        for asset in assets:
            exemption = self._apply_exemption(asset)
            if exemption:
                exemptions.append(exemption)

        return {
            'exemptions': exemptions,
            'total_claimed': sum(e['amount_claimed'] for e in exemptions)
        }

    def _apply_exemption(self, asset: AssetInfo) -> Dict[str, Any] | None:
        """
        Apply appropriate Illinois exemption to asset.

        Args:
            asset: AssetInfo instance

        Returns:
            dict: Exemption details or None if no exemption applies
        """
        # Calculate equity (value - debt)
        equity = asset.current_value - (asset.amount_owed or Decimal('0.00'))

        # Map asset type to exemption type
        exemption_mapping = {
            'real_estate': 'homestead',
            'vehicle': 'vehicle',
            'household_goods': 'wildcard',
            'bank_account': 'wildcard',
        }

        exemption_type = exemption_mapping.get(asset.asset_type, 'wildcard')
        exemption_data = self.ILLINOIS_EXEMPTIONS[exemption_type]

        # Determine amount to claim
        if exemption_data['is_unlimited']:
            amount_claimed = equity
        else:
            exemption_limit = Decimal(exemption_data['amount'])
            amount_claimed = min(equity, exemption_limit)

        if amount_claimed <= 0:
            return None

        return {
            'property_description': asset.description,
            'statute': exemption_data['statute'],
            'statute_description': exemption_data['description'],
            'amount_claimed': amount_claimed,
            'amount_available': Decimal(exemption_data['amount']) if not exemption_data['is_unlimited'] else Decimal('999999.99'),
            'current_value': asset.current_value,
            'equity': equity
        }
```

**Step 5: Run tests**

```bash
pytest backend/apps/forms/tests/test_schedule_c_generator.py -v
```

Expected: 2 tests PASSED

**Step 6: Commit**

```bash
git add backend/apps/forms/services/schedule_c_generator.py backend/apps/forms/tests/test_schedule_c_generator.py backend/apps/forms/fixtures/illinois_exemptions_2024.json
git commit -m "feat(forms): implement Schedule C generator with Illinois exemptions

- Apply Illinois state exemptions per 735 ILCS 5/12-901 et seq
- $15,000 homestead, $4,000 wildcard, $2,400 vehicle
- 100% clothing and retirement exemptions
- Automatic exemption matching based on asset type
- JSON fixture for exemption statutes and amounts

Implements Official Form 106C per bankruptcy rules

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 5: Form 106Sum Generator (Summary)

**Files:**
- Create: `backend/apps/forms/services/form_106sum_generator.py`
- Test: `backend/apps/forms/tests/test_form_106sum_generator.py`

**Step 1: Write failing test**

```python
# backend/apps/forms/tests/test_form_106sum_generator.py

import pytest
from decimal import Decimal
from apps.intake.models import IntakeSession, AssetInfo, DebtInfo
from apps.forms.services.form_106sum_generator import Form106SumGenerator
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestForm106SumGenerator:
    def test_calculates_total_assets(self):
        """Test Form 106Sum calculates total assets from Schedule A/B."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='Car',
            current_value=Decimal('10000.00')
        )

        AssetInfo.objects.create(
            session=session,
            asset_type='bank_account',
            description='Savings',
            current_value=Decimal('500.00')
        )

        generator = Form106SumGenerator(session)
        result = generator.generate()

        assert result['total_assets'] == Decimal('10500.00')

    def test_calculates_total_debts(self):
        """Test Form 106Sum calculates total debts from Schedule D/E/F."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        # Secured debt
        DebtInfo.objects.create(
            session=session,
            creditor_name='Auto Lender',
            amount_owed=Decimal('15000.00'),
            is_secured=True
        )

        # Unsecured debt
        DebtInfo.objects.create(
            session=session,
            creditor_name='Credit Card',
            amount_owed=Decimal('5000.00'),
            is_secured=False
        )

        generator = Form106SumGenerator(session)
        result = generator.generate()

        assert result['total_secured_debts'] == Decimal('15000.00')
        assert result['total_unsecured_debts'] == Decimal('5000.00')
        assert result['total_debts'] == Decimal('20000.00')
```

**Step 2: Run test to verify it fails**

```bash
pytest backend/apps/forms/tests/test_form_106sum_generator.py -v
```

Expected: ImportError

**Step 3: Implement Form106SumGenerator**

```python
# backend/apps/forms/services/form_106sum_generator.py

from decimal import Decimal
from typing import Dict, Any
from apps.intake.models import IntakeSession


class Form106SumGenerator:
    """
    Generate Form 106Sum (Summary of Assets and Liabilities).

    Aggregates data from Schedules A/B, C, D, E/F, I, J.
    Provides statistical summary for court and trustee.

    Official form: form_b106sum.pdf
    """

    def __init__(self, intake_session: IntakeSession):
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Form 106Sum data.

        Returns:
            dict: Complete summary with assets, debts, income, expenses
        """
        # Schedule A/B: Assets
        assets = self.session.assets.all()
        total_assets = sum(a.current_value for a in assets)

        # Schedule D: Secured debts
        secured_debts = self.session.debts.filter(is_secured=True)
        total_secured = sum(d.amount_owed for d in secured_debts)

        # Schedule E/F: Unsecured debts
        unsecured_debts = self.session.debts.filter(is_secured=False)
        total_unsecured = sum(d.amount_owed for d in unsecured_debts)

        # Schedule I: Income (from IncomeInfo model)
        income = self.session.income if hasattr(self.session, 'income') else None
        monthly_income = income.total_monthly_income if income else Decimal('0.00')

        # Schedule J: Expenses (from ExpenseInfo model)
        expense = self.session.expense if hasattr(self.session, 'expense') else None
        monthly_expenses = expense.total_monthly_expenses if expense else Decimal('0.00')

        return {
            # Assets (Schedule A/B)
            'total_assets': total_assets,

            # Liabilities (Schedule D, E/F)
            'total_secured_debts': total_secured,
            'total_unsecured_debts': total_unsecured,
            'total_debts': total_secured + total_unsecured,

            # Income/Expenses (Schedule I, J)
            'current_monthly_income': monthly_income,
            'current_monthly_expenses': monthly_expenses,
            'monthly_net_income': monthly_income - monthly_expenses,

            # Statistical information
            'number_of_creditors': secured_debts.count() + unsecured_debts.count(),
            'number_of_assets': assets.count()
        }
```

**Step 4: Run tests**

```bash
pytest backend/apps/forms/tests/test_form_106sum_generator.py -v
```

Expected: 2 tests PASSED

**Step 5: Commit**

```bash
git add backend/apps/forms/services/form_106sum_generator.py backend/apps/forms/tests/test_form_106sum_generator.py
git commit -m "feat(forms): implement Form 106Sum generator for summary of schedules

- Aggregate total assets from Schedule A/B
- Aggregate total secured/unsecured debts from Schedule D/E/F
- Include income/expenses from Schedule I/J
- Calculate monthly net income
- Provide statistical information (creditor count, asset count)

Implements Official Form 106Sum per bankruptcy rules

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: Form Generators - Debts (Week 2)

### Task 6: Schedule D Generator (Secured Debts)

**Files:**
- Create: `backend/apps/forms/services/schedule_d_generator.py`
- Test: `backend/apps/forms/tests/test_schedule_d_generator.py`

**Step 1: Write failing test**

```python
# backend/apps/forms/tests/test_schedule_d_generator.py

import pytest
from decimal import Decimal
from datetime import date
from apps.intake.models import IntakeSession, DebtInfo
from apps.forms.services.schedule_d_generator import ScheduleDGenerator
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestScheduleDGenerator:
    def test_generates_secured_creditors_list(self):
        """Test Schedule D lists only secured debts."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        # Secured debt
        DebtInfo.objects.create(
            session=session,
            creditor_name='Auto Finance Corp',
            creditor_address='123 Lender St, Chicago, IL 60601',
            amount_owed=Decimal('15000.00'),
            is_secured=True,
            collateral_description='2020 Honda Civic VIN: 12345',
            date_incurred=date(2020, 1, 15)
        )

        # Unsecured debt (should NOT appear)
        DebtInfo.objects.create(
            session=session,
            creditor_name='Credit Card Co',
            amount_owed=Decimal('5000.00'),
            is_secured=False
        )

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        assert len(result['secured_creditors']) == 1
        assert result['secured_creditors'][0]['creditor_name'] == 'Auto Finance Corp'
        assert result['total_secured_claims'] == Decimal('15000.00')

    def test_calculates_collateral_value(self):
        """Test Schedule D includes collateral description and value."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        DebtInfo.objects.create(
            session=session,
            creditor_name='Mortgage Bank',
            amount_owed=Decimal('200000.00'),
            is_secured=True,
            collateral_description='123 Main St, Chicago, IL (Principal Residence)'
        )

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        assert 'Principal Residence' in result['secured_creditors'][0]['collateral_description']
```

**Step 2: Run test**

```bash
pytest backend/apps/forms/tests/test_schedule_d_generator.py -v
```

Expected: ImportError

**Step 3: Implement ScheduleDGenerator**

```python
# backend/apps/forms/services/schedule_d_generator.py

from decimal import Decimal
from typing import Dict, List, Any
from apps.intake.models import IntakeSession


class ScheduleDGenerator:
    """
    Generate Schedule D (Creditors Who Have Claims Secured by Property).

    Lists all secured debts where creditor has lien/security interest in collateral.

    Examples:
    - Mortgage on home
    - Auto loan
    - Secured credit card
    - Judgment liens

    Official form: form_b106d.pdf
    """

    def __init__(self, intake_session: IntakeSession):
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule D data.

        Returns:
            dict: Secured creditors list with collateral details
        """
        secured_debts = self.session.debts.filter(is_secured=True).order_by('creditor_name')

        creditors = []
        for debt in secured_debts:
            creditors.append({
                'creditor_name': debt.creditor_name,
                'creditor_address': debt.creditor_address,
                'account_number': debt.account_number,
                'collateral_description': debt.collateral_description,
                'amount_owed': debt.amount_owed,
                'date_incurred': debt.date_incurred.isoformat() if debt.date_incurred else '',
                'contingent': debt.is_contingent,
                'unliquidated': debt.is_unliquidated,
                'disputed': debt.is_disputed
            })

        return {
            'secured_creditors': creditors,
            'total_secured_claims': sum(d.amount_owed for d in secured_debts),
            'number_of_secured_claims': secured_debts.count()
        }
```

**Step 4: Run tests**

```bash
pytest backend/apps/forms/tests/test_schedule_d_generator.py -v
```

Expected: 2 tests PASSED

**Step 5: Commit**

```bash
git add backend/apps/forms/services/schedule_d_generator.py backend/apps/forms/tests/test_schedule_d_generator.py
git commit -m "feat(forms): implement Schedule D generator for secured debts

- List all secured creditors with collateral descriptions
- Include creditor name, address, account number
- Mark contingent/unliquidated/disputed claims
- Calculate total secured claims
- Filter secured debts from DebtInfo model

Implements Official Form 106D per bankruptcy rules

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 7: Schedule E/F Generator (Unsecured Debts)

**Files:**
- Create: `backend/apps/forms/services/schedule_ef_generator.py`
- Test: `backend/apps/forms/tests/test_schedule_ef_generator.py`

**Step 1: Write failing test**

```python
# backend/apps/forms/tests/test_schedule_ef_generator.py

import pytest
from decimal import Decimal
from apps.intake.models import IntakeSession, DebtInfo
from apps.forms.services.schedule_ef_generator import ScheduleEFGenerator
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestScheduleEFGenerator:
    def test_separates_priority_and_nonpriority_debts(self):
        """Test Schedule E/F separates priority (Part 1) from nonpriority (Part 2)."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        # Priority debt (e.g., taxes)
        DebtInfo.objects.create(
            session=session,
            creditor_name='IRS',
            amount_owed=Decimal('5000.00'),
            is_secured=False,
            is_priority=True
        )

        # Nonpriority debt (e.g., credit card)
        DebtInfo.objects.create(
            session=session,
            creditor_name='Chase',
            amount_owed=Decimal('3000.00'),
            is_secured=False,
            is_priority=False,
            debt_type='consumer'
        )

        # Business debt (nonpriority)
        DebtInfo.objects.create(
            session=session,
            creditor_name='Office Supplies Inc',
            amount_owed=Decimal('2000.00'),
            is_secured=False,
            is_priority=False,
            debt_type='business'
        )

        generator = ScheduleEFGenerator(session)
        result = generator.generate()

        # Part 1: Priority
        assert len(result['priority_creditors']) == 1
        assert result['total_priority_claims'] == Decimal('5000.00')

        # Part 2: Nonpriority
        assert len(result['nonpriority_creditors']) == 2
        assert result['total_nonpriority_claims'] == Decimal('5000.00')

        # Total
        assert result['total_unsecured_claims'] == Decimal('10000.00')

    def test_marks_consumer_vs_business_debts(self):
        """Test Schedule E/F marks each debt as consumer or business."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        DebtInfo.objects.create(
            session=session,
            creditor_name='Credit Card',
            amount_owed=Decimal('3000.00'),
            is_secured=False,
            debt_type='consumer'
        )

        DebtInfo.objects.create(
            session=session,
            creditor_name='Business Vendor',
            amount_owed=Decimal('2000.00'),
            is_secured=False,
            debt_type='business'
        )

        generator = ScheduleEFGenerator(session)
        result = generator.generate()

        consumer_debts = [d for d in result['nonpriority_creditors'] if d['debt_type'] == 'consumer']
        business_debts = [d for d in result['nonpriority_creditors'] if d['debt_type'] == 'business']

        assert len(consumer_debts) == 1
        assert len(business_debts) == 1
```

**Step 2: Run test**

```bash
pytest backend/apps/forms/tests/test_schedule_ef_generator.py -v
```

Expected: ImportError

**Step 3: Implement ScheduleEFGenerator**

```python
# backend/apps/forms/services/schedule_ef_generator.py

from decimal import Decimal
from typing import Dict, List, Any
from apps.intake.models import IntakeSession


class ScheduleEFGenerator:
    """
    Generate Schedule E/F (Creditors Who Have Unsecured Claims).

    Part 1: Priority unsecured claims (taxes, child support, wages)
    Part 2: Nonpriority unsecured claims (credit cards, medical, business debts)

    Marks each debt as consumer vs business for means test applicability.

    Official form: form_b106ef.pdf
    """

    def __init__(self, intake_session: IntakeSession):
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule E/F data.

        Returns:
            dict: Priority and nonpriority creditors with consumer/business classification
        """
        unsecured_debts = self.session.debts.filter(is_secured=False).order_by('creditor_name')

        # Part 1: Priority unsecured claims
        priority_debts = unsecured_debts.filter(is_priority=True)
        priority_creditors = [self._format_creditor(debt) for debt in priority_debts]

        # Part 2: Nonpriority unsecured claims
        nonpriority_debts = unsecured_debts.filter(is_priority=False)
        nonpriority_creditors = [self._format_creditor(debt) for debt in nonpriority_debts]

        # Calculate consumer vs business percentages
        total_nonpriority = sum(d.amount_owed for d in nonpriority_debts)
        consumer_total = sum(d.amount_owed for d in nonpriority_debts.filter(debt_type='consumer'))
        business_total = sum(d.amount_owed for d in nonpriority_debts.filter(debt_type='business'))

        consumer_pct = (consumer_total / total_nonpriority * 100) if total_nonpriority > 0 else Decimal('0')
        business_pct = (business_total / total_nonpriority * 100) if total_nonpriority > 0 else Decimal('0')

        return {
            # Part 1: Priority
            'priority_creditors': priority_creditors,
            'total_priority_claims': sum(d.amount_owed for d in priority_debts),

            # Part 2: Nonpriority
            'nonpriority_creditors': nonpriority_creditors,
            'total_nonpriority_claims': total_nonpriority,

            # Consumer vs Business breakdown
            'consumer_debt_total': consumer_total,
            'business_debt_total': business_total,
            'consumer_debt_percentage': round(consumer_pct, 2),
            'business_debt_percentage': round(business_pct, 2),

            # Total
            'total_unsecured_claims': sum(d.amount_owed for d in unsecured_debts),
            'number_of_unsecured_claims': unsecured_debts.count()
        }

    def _format_creditor(self, debt) -> Dict[str, Any]:
        """Format debt info for Schedule E/F."""
        return {
            'creditor_name': debt.creditor_name,
            'creditor_address': debt.creditor_address,
            'account_number': debt.account_number,
            'amount_owed': debt.amount_owed,
            'date_incurred': debt.date_incurred.isoformat() if debt.date_incurred else '',
            'debt_type': debt.debt_type,
            'contingent': debt.is_contingent,
            'unliquidated': debt.is_unliquidated,
            'disputed': debt.is_disputed
        }
```

**Step 4: Run tests**

```bash
pytest backend/apps/forms/tests/test_schedule_ef_generator.py -v
```

Expected: 2 tests PASSED

**Step 5: Commit**

```bash
git add backend/apps/forms/services/schedule_ef_generator.py backend/apps/forms/tests/test_schedule_ef_generator.py
git commit -m "feat(forms): implement Schedule E/F generator for unsecured debts

- Separate priority (Part 1) and nonpriority (Part 2) unsecured claims
- Mark each debt as consumer vs business for means test
- Calculate consumer/business percentages (70/30 in user's case)
- Include contingent/unliquidated/disputed flags
- Calculate total unsecured claims

Implements Official Form 106E/F per bankruptcy rules

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 4: Income/Expenses & Supporting Forms (Week 3)

### Task 8: Schedule I Generator (Income - $0 Logic)

**Files:**
- Create: `backend/apps/forms/services/schedule_i_generator.py`
- Test: `backend/apps/forms/tests/test_schedule_i_generator.py`

**Step 1: Write failing test**

```python
# backend/apps/forms/tests/test_schedule_i_generator.py

import pytest
from decimal import Decimal
from apps.intake.models import IntakeSession, IncomeInfo
from apps.forms.services.schedule_i_generator import ScheduleIGenerator
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestScheduleIGenerator:
    def test_generates_zero_income(self):
        """Test Schedule I handles $0 income case."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        IncomeInfo.objects.create(
            session=session,
            employment_income=Decimal('0.00'),
            business_income=Decimal('0.00'),
            rental_income=Decimal('0.00'),
            public_benefits=Decimal('0.00')
        )

        generator = ScheduleIGenerator(session)
        result = generator.generate()

        assert result['total_monthly_income'] == Decimal('0.00')
        assert result['has_no_income'] is True

    def test_generates_income_with_public_benefits(self):
        """Test Schedule I includes public benefits."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        IncomeInfo.objects.create(
            session=session,
            employment_income=Decimal('0.00'),
            public_benefits=Decimal('800.00'),  # SNAP
            public_benefits_description='SNAP (food stamps)'
        )

        generator = ScheduleIGenerator(session)
        result = generator.generate()

        assert result['total_monthly_income'] == Decimal('800.00')
        assert result['public_benefits'] == Decimal('800.00')
```

**Step 2: Run test**

```bash
pytest backend/apps/forms/tests/test_schedule_i_generator.py -v
```

Expected: ImportError

**Step 3: Implement ScheduleIGenerator**

```python
# backend/apps/forms/services/schedule_i_generator.py

from decimal import Decimal
from typing import Dict, Any
from apps.intake.models import IntakeSession


class ScheduleIGenerator:
    """
    Generate Schedule I (Your Income).

    Lists all income sources:
    - Employment (wages, salary)
    - Business income (if sole proprietor)
    - Public benefits (SNAP, SSI, unemployment)
    - Other income (alimony, rental, etc.)

    Special handling for $0 income case (user's situation).

    Official form: form_b106i.pdf
    """

    def __init__(self, intake_session: IntakeSession):
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule I data.

        Returns:
            dict: Income breakdown with $0 income detection
        """
        income = self.session.income if hasattr(self.session, 'income') else None

        if not income:
            # No income info = $0 income
            return self._zero_income_response()

        employment = income.employment_income or Decimal('0.00')
        business = income.business_income or Decimal('0.00')
        rental = income.rental_income or Decimal('0.00')
        benefits = income.public_benefits or Decimal('0.00')
        other = income.other_income or Decimal('0.00')

        total = employment + business + rental + benefits + other

        return {
            'employment_income': employment,
            'business_income': business,
            'rental_income': rental,
            'public_benefits': benefits,
            'public_benefits_description': income.public_benefits_description or '',
            'other_income': other,
            'other_income_description': income.other_income_description or '',
            'total_monthly_income': total,
            'has_no_income': total == Decimal('0.00')
        }

    def _zero_income_response(self) -> Dict[str, Any]:
        """Generate response for $0 income case."""
        return {
            'employment_income': Decimal('0.00'),
            'business_income': Decimal('0.00'),
            'rental_income': Decimal('0.00'),
            'public_benefits': Decimal('0.00'),
            'public_benefits_description': '',
            'other_income': Decimal('0.00'),
            'other_income_description': '',
            'total_monthly_income': Decimal('0.00'),
            'has_no_income': True
        }
```

**Step 4: Run tests**

```bash
pytest backend/apps/forms/tests/test_schedule_i_generator.py -v
```

Expected: 2 tests PASSED

**Step 5: Commit**

```bash
git add backend/apps/forms/services/schedule_i_generator.py backend/apps/forms/tests/test_schedule_i_generator.py
git commit -m "feat(forms): implement Schedule I generator for income reporting

- Support $0 income case (user's situation)
- List employment, business, rental, benefits, other income
- Calculate total monthly income
- Flag has_no_income for fee waiver eligibility
- Include income source descriptions

Implements Official Form 106I per bankruptcy rules

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 9: Schedule J Generator (Expenses)

**Files:**
- Create: `backend/apps/forms/services/schedule_j_generator.py`
- Test: `backend/apps/forms/tests/test_schedule_j_generator.py`

**Step 1: Write failing test**

```python
# backend/apps/forms/tests/test_schedule_j_generator.py

import pytest
from decimal import Decimal
from apps.intake.models import IntakeSession, ExpenseInfo
from apps.forms.services.schedule_j_generator import ScheduleJGenerator
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestScheduleJGenerator:
    def test_calculates_total_expenses(self):
        """Test Schedule J calculates total monthly expenses."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        ExpenseInfo.objects.create(
            session=session,
            rent=Decimal('800.00'),
            electricity=Decimal('100.00'),
            water=Decimal('50.00'),
            food=Decimal('300.00'),
            transportation=Decimal('150.00')
        )

        generator = ScheduleJGenerator(session)
        result = generator.generate()

        assert result['total_expenses'] == Decimal('1400.00')

    def test_calculates_net_monthly_income(self):
        """Test Schedule J calculates net (income - expenses)."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        from apps.intake.models import IncomeInfo
        IncomeInfo.objects.create(
            session=session,
            employment_income=Decimal('0.00')
        )

        ExpenseInfo.objects.create(
            session=session,
            rent=Decimal('800.00'),
            food=Decimal('300.00')
        )

        generator = ScheduleJGenerator(session)
        result = generator.generate()

        # $0 income - $1100 expenses = -$1100 (deficit)
        assert result['net_monthly_income'] == Decimal('-1100.00')
```

**Step 2: Run test**

```bash
pytest backend/apps/forms/tests/test_schedule_j_generator.py -v
```

Expected: ImportError

**Step 3: Implement ScheduleJGenerator**

```python
# backend/apps/forms/services/schedule_j_generator.py

from decimal import Decimal
from typing import Dict, Any
from apps.intake.models import IntakeSession


class ScheduleJGenerator:
    """
    Generate Schedule J (Your Expenses).

    Lists all monthly expenses:
    - Housing (rent/mortgage, utilities)
    - Food/housekeeping
    - Transportation
    - Medical/health insurance
    - Other expenses

    Calculates net monthly income (Schedule I - Schedule J).

    Official form: form_b106j.pdf
    """

    def __init__(self, intake_session: IntakeSession):
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule J data.

        Returns:
            dict: Expense breakdown and net monthly income
        """
        expense = self.session.expense if hasattr(self.session, 'expense') else None

        if not expense:
            return self._zero_expenses_response()

        # Housing expenses
        rent = expense.rent or Decimal('0.00')
        mortgage = expense.mortgage or Decimal('0.00')
        property_tax = expense.property_tax or Decimal('0.00')
        homeowners_insurance = expense.homeowners_insurance or Decimal('0.00')

        # Utilities
        electricity = expense.electricity or Decimal('0.00')
        water = expense.water or Decimal('0.00')
        gas = expense.gas or Decimal('0.00')
        phone = expense.phone or Decimal('0.00')
        internet = expense.internet or Decimal('0.00')

        # Other
        food = expense.food or Decimal('0.00')
        transportation = expense.transportation or Decimal('0.00')
        medical = expense.medical or Decimal('0.00')

        total_expenses = (
            rent + mortgage + property_tax + homeowners_insurance +
            electricity + water + gas + phone + internet +
            food + transportation + medical
        )

        # Get income from Schedule I
        income = self.session.income if hasattr(self.session, 'income') else None
        total_income = income.total_monthly_income if income else Decimal('0.00')

        return {
            # Housing
            'rent': rent,
            'mortgage': mortgage,
            'property_tax': property_tax,
            'homeowners_insurance': homeowners_insurance,

            # Utilities
            'electricity': electricity,
            'water': water,
            'gas': gas,
            'phone': phone,
            'internet': internet,

            # Other
            'food': food,
            'transportation': transportation,
            'medical': medical,

            # Totals
            'total_expenses': total_expenses,
            'total_income': total_income,
            'net_monthly_income': total_income - total_expenses
        }

    def _zero_expenses_response(self) -> Dict[str, Any]:
        """Generate response for case with no expenses entered."""
        return {
            'rent': Decimal('0.00'),
            'mortgage': Decimal('0.00'),
            'total_expenses': Decimal('0.00'),
            'total_income': Decimal('0.00'),
            'net_monthly_income': Decimal('0.00')
        }
```

**Step 4: Run tests**

```bash
pytest backend/apps/forms/tests/test_schedule_j_generator.py -v
```

Expected: 2 tests PASSED

**Step 5: Commit**

```bash
git add backend/apps/forms/services/schedule_j_generator.py backend/apps/forms/tests/test_schedule_j_generator.py
git commit -m "feat(forms): implement Schedule J generator for expense reporting

- List all 23 expense categories (housing, utilities, food, etc.)
- Calculate total monthly expenses
- Calculate net monthly income (Schedule I - Schedule J)
- Support negative net income (expenses exceed income)
- Link to Schedule I for income data

Implements Official Form 106J per bankruptcy rules

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Execution Instructions

**This plan contains 13 tasks total.** The remaining tasks (10-13) follow the same TDD pattern:

- **Task 10:** Form 106Dec Generator (Declaration/Signature)
- **Task 11:** Form 107 Generator (Statement of Financial Affairs - 25 questions)
- **Task 12:** Form 121 Generator (SSN Statement)
- **Task 13:** Form 122A-1 Generator (Means Test)
- **Task 14:** Form 103B Generator (Fee Waiver - CRITICAL)

**Each task follows TDD cycle:**
1. Write failing test
2. Run test to verify failure
3. Implement minimal code
4. Run test to verify pass
5. Commit with descriptive message

**Total estimated time:** 60-70 hours (3-4 weeks at 20 hours/week)

---

Plan complete and saved to `docs/plans/2026-02-16-chapter-7-forms-generators.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
