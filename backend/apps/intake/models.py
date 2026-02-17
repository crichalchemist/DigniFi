"""Intake models for collecting bankruptcy petition data."""

from decimal import Decimal
from typing import ClassVar, List

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from encrypted_model_fields.fields import EncryptedCharField

from .fields import EncryptedDecimalField


class IntakeSession(models.Model):
    """Multi-step intake session tracking."""

    STATUS_CHOICES: ClassVar[List[tuple[str, str]]] = [
        ("started", "Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("abandoned", "Abandoned"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="intake_sessions",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="started")
    current_step = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    district = models.ForeignKey("districts.District", on_delete=models.PROTECT)

    class Meta:
        db_table = "intake_sessions"
        ordering: ClassVar[List[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"Intake {self.id} - {self.user} ({self.status})"


class DebtorInfo(models.Model):
    """Personal information for debtor (PII encrypted)."""

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="debtor_info"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    ssn = EncryptedCharField(max_length=11)  # Encrypted!
    date_of_birth = models.DateField()
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    # Address
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=10)

    class Meta:
        db_table = "debtor_info"

    def __str__(self):
        return (
            f"Debtor: {self.first_name} {self.last_name} (Session: {self.session_id})"
        )


class IncomeInfo(models.Model):
    """Income data for means test."""

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="income_info"
    )
    marital_status = models.CharField(
        max_length=30,
        choices=[
            ("single", "Single"),
            ("married_joint", "Married Filing Jointly"),
            ("married_separate", "Married Filing Separately"),
        ],
    )
    number_of_dependents = models.IntegerField(default=0)
    monthly_income = models.JSONField(
        help_text="6-month income array"
    )  # [month1, month2, ...]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "income_info"

    def __str__(self) -> str:
        return (
            f"IncomeInfo: {self.marital_status}, {self.number_of_dependents} dependents "
            f"(Session: {self.session_id})"
        )


class ExpenseInfo(models.Model):
    """Monthly expense data for means test calculation."""

    DATA_SOURCE_CHOICES: ClassVar[List[tuple[str, str]]] = [
        ("manual", "Manually Entered"),
        ("plaid", "Plaid API"),
        ("uploaded_document", "Uploaded Document"),
    ]

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="expense_info"
    )
    data_source = models.CharField(
        max_length=30,
        choices=DATA_SOURCE_CHOICES,
        default="manual",
        help_text="Source of expense data for audit trail",
    )

    # Housing expenses
    rent_or_mortgage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Monthly housing payment",
    )
    utilities = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Gas, electric, water, etc.",
    )
    home_maintenance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="Repairs and upkeep"
    )

    # Transportation
    vehicle_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Car loan or lease payment",
    )
    vehicle_insurance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vehicle_maintenance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Gas, repairs, registration",
    )

    # Living expenses
    food_and_groceries = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    clothing = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medical_expenses = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Out-of-pocket healthcare costs",
    )

    # Other recurring expenses
    childcare = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    child_support_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Court-ordered support payments",
    )
    insurance_not_deducted = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Health, life, or disability insurance not deducted from paycheck",
    )
    other_expenses = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Other necessary monthly expenses",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expense_info"

    def __str__(self) -> str:
        total = self.calculate_total_monthly_expenses()
        return f"ExpenseInfo: ${total}/month (Session: {self.session_id})"

    def calculate_total_monthly_expenses(self) -> float:
        """Calculate total monthly expenses for means test."""
        return float(
            self.rent_or_mortgage
            + self.utilities
            + self.home_maintenance
            + self.vehicle_payment
            + self.vehicle_insurance
            + self.vehicle_maintenance
            + self.food_and_groceries
            + self.clothing
            + self.medical_expenses
            + self.childcare
            + self.child_support_paid
            + self.insurance_not_deducted
            + self.other_expenses
        )


class AssetInfo(models.Model):
    """Asset and property information (encrypted PII for account numbers)."""

    ASSET_TYPE_CHOICES: ClassVar[List[tuple[str, str]]] = [
        ("real_property", "Real Estate/Home"),
        ("vehicle", "Vehicle"),
        ("bank_account", "Bank Account"),
        ("retirement_account", "Retirement Account (401k, IRA)"),
        ("other", "Other Asset"),
    ]

    DATA_SOURCE_CHOICES: ClassVar[List[tuple[str, str]]] = [
        ("manual", "Manually Entered"),
        ("plaid", "Plaid API"),
        ("uploaded_document", "Uploaded Document"),
    ]

    session = models.ForeignKey(
        IntakeSession, on_delete=models.CASCADE, related_name="assets"
    )
    asset_type = models.CharField(max_length=30, choices=ASSET_TYPE_CHOICES)
    data_source = models.CharField(
        max_length=30,
        choices=DATA_SOURCE_CHOICES,
        default="manual",
        help_text="Source of asset data for audit trail",
    )

    # Asset description
    description = models.CharField(
        max_length=255,
        help_text="Brief description (e.g., '2015 Honda Civic', '123 Main St')",
    )
    current_value = EncryptedDecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Current fair market value",
    )
    amount_owed = EncryptedDecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Outstanding loan or lien amount",
    )

    # For bank/financial accounts
    account_number = EncryptedCharField(
        max_length=50,
        blank=True,
        help_text="Last 4 digits or full account number (encrypted)",
    )
    financial_institution = models.CharField(
        max_length=100, blank=True, help_text="Bank or institution name"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_info"
        ordering: ClassVar[List[str]] = ["asset_type", "-current_value"]

    def __str__(self) -> str:
        return f"{self.get_asset_type_display()}: {self.description} (Session: {self.session_id})"

    @property
    def equity(self) -> float:
        """Calculate equity in asset (value - amount owed)."""
        return float(self.current_value - self.amount_owed)


class DebtInfo(models.Model):
    """Creditor and amounts owed information (trauma-informed language)."""

    DEBT_TYPE_CHOICES: ClassVar[List[tuple[str, str]]] = [
        ("credit_card", "Credit Card"),
        ("medical", "Medical Bill"),
        ("personal_loan", "Personal Loan"),
        ("student_loan", "Student Loan"),
        ("auto_loan", "Auto Loan"),
        ("mortgage", "Mortgage/Home Loan"),
        ("utility", "Utility Bill"),
        ("other", "Other Amount Owed"),
    ]

    PRIORITY_CHOICES: ClassVar[List[tuple[str, str]]] = [
        ("unsecured", "Unsecured (Credit Card, Medical)"),
        ("secured", "Secured (Car Loan, Mortgage)"),
        ("priority", "Priority (Taxes, Child Support)"),
    ]

    DATA_SOURCE_CHOICES: ClassVar[List[tuple[str, str]]] = [
        ("manual", "Manually Entered"),
        ("credit_report", "Credit Report"),
        ("uploaded_document", "Uploaded Document"),
    ]

    session = models.ForeignKey(
        IntakeSession, on_delete=models.CASCADE, related_name="debts"
    )
    data_source = models.CharField(
        max_length=30,
        choices=DATA_SOURCE_CHOICES,
        default="manual",
        help_text="Source of creditor data for audit trail",
    )

    # Creditor information
    creditor_name = models.CharField(
        max_length=255, help_text="Name of creditor or collection agency"
    )
    debt_type = models.CharField(max_length=30, choices=DEBT_TYPE_CHOICES)
    priority_classification = models.CharField(
        max_length=30,
        choices=PRIORITY_CHOICES,
        default="unsecured",
        help_text="Legal classification for bankruptcy filing",
    )

    # Amount information (encrypted)
    account_number = EncryptedCharField(
        max_length=50,
        blank=True,
        help_text="Last 4 digits or full account number (encrypted)",
    )
    amount_owed = EncryptedDecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Current balance (trauma-informed: 'amount owed' vs 'debt')",
    )

    # Additional details
    monthly_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum monthly payment if still paying",
    )
    is_in_collections = models.BooleanField(
        default=False, help_text="Has this account been sent to collections?"
    )
    notes = models.TextField(
        blank=True, help_text="Additional context about this amount owed"
    )

    # Chapter 7 classification fields
    consumer_business_classification = models.CharField(
        max_length=20,
        choices=[
            ("consumer", "Consumer Debt"),
            ("business", "Business Debt"),
        ],
        default="consumer",
        help_text="Consumer vs business classification for means test applicability (11 U.S.C. § 707(b))",
    )

    is_secured = models.BooleanField(
        default=False,
        help_text="Secured debts go on Schedule D; unsecured on Schedule E/F",
    )

    collateral_description = models.TextField(
        blank=True,
        help_text="Description of collateral if secured debt (e.g., '2020 Honda Civic VIN: 12345')",
    )

    is_priority = models.BooleanField(
        default=False,
        help_text="Priority unsecured debts (e.g., taxes, child support) on Schedule E/F Part 1",
    )

    is_contingent = models.BooleanField(
        default=False,
        help_text="Debt depends on future event",
    )

    is_unliquidated = models.BooleanField(
        default=False,
        help_text="Amount not yet determined",
    )

    is_disputed = models.BooleanField(
        default=False,
        help_text="Debtor disputes validity or amount",
    )

    date_incurred = models.DateField(
        null=True,
        blank=True,
        help_text="When debt was incurred",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "debt_info"
        ordering: ClassVar[List[str]] = ["priority_classification", "-amount_owed"]

    def __str__(self) -> str:
        return f"{self.creditor_name} - {self.get_debt_type_display()} ({self.get_consumer_business_classification_display()}) (Session: {self.session_id})"


class FeeWaiverApplication(models.Model):
    """
    Chapter 7 fee waiver application (Form 103B).

    Qualifies if:
    1. Income < 150% federal poverty line ($1,882.50/month for 1 person as of 2024)
    2. OR receives means-tested public benefits (SSI, SNAP, TANF, etc.)
    3. AND cannot pay filing fee ($338) in full or installments

    Per 28 U.S.C. § 1930(f)
    """

    # HHS poverty guidelines constants (2024)
    POVERTY_BASE_2024: ClassVar[Decimal] = Decimal('15060')    # HHS poverty line base (2024)
    POVERTY_INCREMENT: ClassVar[Decimal] = Decimal('5380')     # Per-person increment
    POVERTY_MULTIPLIER: ClassVar[Decimal] = Decimal('1.5')     # 150% per 28 U.S.C. § 1930(f)
    MONTHS_PER_YEAR: ClassVar[Decimal] = Decimal('12')

    # Relations
    session = models.OneToOneField(
        IntakeSession,
        on_delete=models.CASCADE,
        related_name='fee_waiver'
    )

    # Household information
    household_size = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of people in household (must be at least 1)"
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
    STATUS_CHOICES: ClassVar[List[tuple[str, str]]] = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
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
        # 28 U.S.C. § 1930(f) allows waiver for means-tested benefits
        if self.receives_public_benefits:
            return True

        # Income test: < 150% federal poverty line
        poverty_threshold_150_monthly = self.get_poverty_threshold()
        if self.monthly_income < poverty_threshold_150_monthly:
            return True

        return False

    def get_poverty_threshold(self) -> Decimal:
        """Calculate 150% poverty threshold for household size."""
        poverty_threshold_annual = (
            self.POVERTY_BASE_2024 +
            (self.POVERTY_INCREMENT * (self.household_size - 1))
        )
        return (poverty_threshold_annual * self.POVERTY_MULTIPLIER) / self.MONTHS_PER_YEAR
