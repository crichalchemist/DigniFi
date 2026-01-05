"""Intake models for collecting bankruptcy petition data."""

from typing import ClassVar, List

from django.db import models
from django.conf import settings
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "debt_info"
        ordering: ClassVar[List[str]] = ["priority_classification", "-amount_owed"]

    def __str__(self) -> str:
        return f"{self.creditor_name} - {self.get_debt_type_display()} (Session: {self.session_id})"
