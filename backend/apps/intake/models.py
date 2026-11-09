"""Intake models for collecting bankruptcy petition data."""

import json
from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.db import models
from encrypted_model_fields.fields import (
    EncryptedBooleanField,
    EncryptedCharField,
    EncryptedTextField,
)

from .asset_lines import WHO
from .fields import EncryptedDecimalField
from .household import ANSWER_KEYS, SPOUSE_KEY
from .income import ENTRY_AMOUNT_KEYS, ENTRY_KEYS, floored_net, has_entry_figures

YES_NO = ("yes", "no")
HOME_PAYMENT_LINES = ("first", "additional")
LEASE_KINDS = ("residential", "vehicle", "other_personal_property", "other")


class IntakeSession(models.Model):
    """Multi-step intake session tracking."""

    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
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
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"Intake {self.id} - {self.user} ({self.status})"

    def reopen(self) -> None:
        """Set a completed intake back to in progress, because its intake data changed.

        The filer then presses Complete again, which re-runs the completion checks (spec
        §5.3). Form answers, SOFA and the filing fee are not intake data and never call this.

        The database decides, not this copy: an upload loads the session seconds before it
        reopens it, and the filer may have pressed Complete meanwhile. The copy is updated too,
        so a full save of it afterwards never writes a stale "completed" back.
        """
        reopened = IntakeSession.objects.filter(pk=self.pk, status="completed").update(
            status="in_progress"
        )
        if reopened or self.status == "completed":
            self.status = "in_progress"


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
    # Not asked since forms step 3e1, and read by nothing. Kept until step 5 migrates DebtorInfo.
    household_size = models.PositiveIntegerField(default=1)
    filing_type = models.CharField(
        max_length=20,
        choices=[("individual", "Individual"), ("joint", "Joint")],
        default="individual",
    )

    class Meta:
        db_table = "debtor_info"

    def __str__(self):
        return f"Debtor: {self.first_name} {self.last_name} (Session: {self.session_id})"


class IncomeDetail(models.Model):
    """What the filer and the spouse each answer on the Income step beyond the ten (3e2 spec §4).

    Every column is encrypted and starts unanswered (null), so nothing counts as $0 or "no"
    until the filer says so. business_and_rental is JSON in the filer's order: null means
    unanswered and [] means none.
    """

    # The Income step's ten monthly amounts, by source (forms step 2 spec §5.5; 3e2 spec §4.1:
    # interest and dividends take the place of rental)
    SOURCE_FIELDS: ClassVar[tuple[str, ...]] = (
        "monthly_gross_wages",
        "monthly_overtime",
        "monthly_tips",
        "monthly_interest_and_dividends",
        "monthly_pension",
        "monthly_social_security",
        "monthly_unemployment",
        "monthly_child_support",
        "monthly_alimony",
        "monthly_other_income",
    )
    CURRENT_FIELDS: ClassVar[tuple[str, ...]] = (
        "current_monthly_gross_wages",
        "current_monthly_overtime",
        "current_monthly_tips",
        "current_monthly_interest_and_dividends",
        "current_monthly_pension",
        "current_monthly_social_security",
        "current_monthly_unemployment",
        "current_monthly_child_support",
        "current_monthly_alimony",
        "current_monthly_other_income",
    )
    DEDUCTION_FIELDS: ClassVar[tuple[str, ...]] = (
        "payroll_tax",
        "payroll_mandatory_retirement",
        "payroll_voluntary_retirement",
        "payroll_retirement_loan",
        "payroll_insurance",
        "payroll_support",
        "payroll_union_dues",
        "payroll_other",
    )

    monthly_interest_and_dividends = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_gross_wages = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_overtime = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_tips = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_interest_and_dividends = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_pension = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_social_security = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_unemployment = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_child_support = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_alimony = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    current_monthly_other_income = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    business_and_rental = EncryptedTextField(null=True, blank=True)
    # The id the next new entry gets. Ids are never reused.
    next_entry_id = models.PositiveIntegerField(default=1)
    income_now_different = EncryptedCharField(max_length=3, null=True, blank=True)
    assistance_answer = EncryptedCharField(max_length=3, null=True, blank=True)
    cash_assistance_kind = EncryptedCharField(max_length=100, blank=True, default="")
    noncash_assistance_kind = EncryptedCharField(max_length=100, blank=True, default="")
    cash_assistance_amount = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    noncash_assistance_value = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    payroll_tax = EncryptedDecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payroll_mandatory_retirement = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    payroll_voluntary_retirement = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    payroll_retirement_loan = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    payroll_insurance = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    payroll_support = EncryptedDecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payroll_union_dues = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    payroll_other = EncryptedDecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payroll_other_specify = EncryptedCharField(max_length=100, blank=True, default="")

    class Meta:
        abstract = True

    def get_entries(self) -> list[dict] | None:
        """The stored list, or None while the filer hasn't answered."""
        if self.business_and_rental is None:
            return None
        return json.loads(self.business_and_rental)

    def store_entries(self, rows: list[dict] | None) -> list[dict] | None:
        """Store the list in the order sent and return it as stored. Doesn't save.

        An entry keeps its id when the stored list holds it and no earlier entry in this list
        kept it; every other entry gets next_entry_id, which then goes up by one. Each entry
        holds its id and the six answers, None for one it didn't send, the amounts as
        two-place strings. Storing None resets nothing.
        """
        if rows is None:
            self.business_and_rental = None
            return None
        stored_ids = {row["id"] for row in self.get_entries() or []}
        kept = set()
        saved = []
        for row in rows:
            entry_id = row.get("id")
            if entry_id in stored_ids and entry_id not in kept:
                kept.add(entry_id)
            else:
                entry_id = self.next_entry_id
                self.next_entry_id += 1
            entry = {"id": entry_id}
            for key in ENTRY_KEYS:
                value = row.get(key)
                if key in ENTRY_AMOUNT_KEYS and value is not None:
                    value = str(Decimal(value).quantize(Decimal("0.01")))
                entry[key] = value
            saved.append(entry)
        self.business_and_rental = json.dumps(saved)
        return saved


class IncomeInfo(IncomeDetail):
    """Income data for means test."""

    # Form 122A-1 line 1's four answers (3e1 spec §3.2). Null means unanswered; there is no fifth.
    MARITAL_ANSWERS: ClassVar[tuple[str, ...]] = (
        "not_married",
        "married_spouse_filing",
        "married_together",
        "married_separately",
    )

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="income_info"
    )
    # Line 1's answer, encrypted. The serializer takes only MARITAL_ANSWERS.
    marital_status = EncryptedCharField(max_length=30, null=True, blank=True)
    # The total the Income step saved before step 2. It is no longer written, and stays for
    # one release as the only record of what an earlier filer entered.
    monthly_income = EncryptedTextField(null=True, blank=True, help_text="6-month income array")
    # JSON text of the array, encrypted; get_monthly_income() parses it.
    # No default: an amount the filer never gave stays empty. A default of 0 would give
    # every earlier filer $0 income, and so a passed means test.
    monthly_gross_wages = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    monthly_overtime = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    monthly_tips = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    monthly_rental_income = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="After the property's costs",
    )
    monthly_pension = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    monthly_social_security = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    monthly_unemployment = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    monthly_child_support = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Child support received",
    )
    monthly_alimony = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Alimony received",
    )
    monthly_other_income = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    # The last day of the six-month window the figures cover (3e2 spec §4.4)
    income_period_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "income_info"

    def __str__(self) -> str:
        return f"IncomeInfo (Session: {self.session_id})"

    def get_monthly_income(self) -> list | None:
        """The old six-month total as the array it was saved as, or None."""
        if self.monthly_income is None:
            return None
        return json.loads(self.monthly_income)

    def calculate_total_monthly_income(self) -> float | None:
        """The ten monthly amounts added up, Social Security included, plus the floored
        business and rental nets of the averages.

        An amount left empty counts as zero once another one was given. None when the filer
        gave none of them and no entry has a figure, so a total saved before step 2 never
        reads as $0.
        """
        given = [
            getattr(self, field) for field in self.SOURCE_FIELDS if getattr(self, field) is not None
        ]
        entries = self.get_entries()
        if not given and not has_entry_figures(entries):
            return None
        total = sum(given, Decimal("0"))
        total += floored_net(entries, "business") + floored_net(entries, "rental")
        return float(total)


class Household(models.Model):
    """The filer's county and the people in their home or whom they support (3e1 spec §4.1).

    Both are encrypted. members is JSON in the filer's order, so no encrypted column is ever
    sorted. Null means unanswered; [] means the filer said no one.
    """

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="household"
    )
    county = EncryptedCharField(max_length=20, null=True, blank=True)
    members = EncryptedTextField(null=True, blank=True)
    # The id the next new row gets. Ids are never reused.
    next_member_id = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "household"

    def __str__(self) -> str:
        return f"Household (Session: {self.session_id})"

    def get_members(self) -> list[dict] | None:
        """The stored list, or None while the filer hasn't answered."""
        if self.members is None:
            return None
        return json.loads(self.members)

    def store_members(self, rows: list[dict] | None) -> list[dict] | None:
        """Store the list in the order sent and return it as stored. Doesn't save.

        A row keeps its id when the stored list holds it and no earlier row in this list
        kept it; every other row gets next_member_id, which then goes up by one. Each row
        holds its id, the four answers, and spouse_is_dependent on the spouse's row only,
        with None for an answer the row didn't send. Storing None resets nothing.
        """
        if rows is None:
            self.members = None
            return None
        stored_ids = {row["id"] for row in self.get_members() or []}
        kept = set()
        saved = []
        for row in rows:
            member_id = row.get("id")
            if member_id in stored_ids and member_id not in kept:
                kept.add(member_id)
            else:
                member_id = self.next_member_id
                self.next_member_id += 1
            member = {"id": member_id, **{key: row.get(key) for key in ANSWER_KEYS}}
            if member["relationship"] == "spouse":
                member[SPOUSE_KEY] = row.get(SPOUSE_KEY)
            saved.append(member)
        self.members = json.dumps(saved)
        return saved


class SpouseIncome(IncomeDetail):
    """The spouse's monthly income by the filer's ten sources (3e1 spec §5.2).

    Asked of a filer who lives with their spouse. Encrypted from the start, and kept when the
    marriage answer changes.
    """

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="spouse_income"
    )
    # No default: an amount the filer never gave stays empty.
    monthly_gross_wages = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    monthly_overtime = EncryptedDecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monthly_tips = EncryptedDecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monthly_rental_income = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="After the property's costs",
    )
    monthly_pension = EncryptedDecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monthly_social_security = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    monthly_unemployment = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    monthly_child_support = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Child support received",
    )
    monthly_alimony = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Alimony received",
    )
    monthly_other_income = EncryptedDecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "spouse_income"

    def __str__(self) -> str:
        return f"SpouseIncome (Session: {self.session_id})"


class ExpenseInfo(models.Model):
    """Monthly expense data for means test calculation."""

    DATA_SOURCE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("manual", "Manually Entered"),
        ("plaid", "Plaid API"),
        ("uploaded_document", "Uploaded Document"),
    ]

    AMOUNT_FIELDS: ClassVar[tuple[str, ...]] = (
        "rent_or_mortgage",
        "real_estate_taxes",
        "home_insurance",
        "home_maintenance",
        "hoa_dues",
        "utilities",
        "food_and_groceries",
        "childcare",
        "clothing",
        "personal_care",
        "medical_expenses",
        "vehicle_maintenance",
        "entertainment",
        "charitable_contributions",
        "vehicle_insurance",
        "insurance_not_deducted",
        "taxes_not_deducted",
        "vehicle_payment",
        "child_support_paid",
        "support_others",
        "other_property_mortgages",
        "other_property_taxes",
        "other_property_insurance",
        "other_property_upkeep",
        "other_property_hoa_dues",
        "other_expenses",
    )
    SPECIFY_FIELDS: ClassVar[tuple[str, ...]] = (
        "taxes_specify",
        "support_others_specify",
        "other_expenses_specify",
    )

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
    rent_or_mortgage = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Monthly housing payment",
    )
    utilities = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Gas, electric, water, etc.",
    )
    home_maintenance = EncryptedDecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="Repairs and upkeep"
    )

    # Transportation
    vehicle_payment = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Car loan or lease payment",
    )
    vehicle_insurance = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    vehicle_maintenance = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Gas, repairs, registration",
    )

    # Living expenses
    food_and_groceries = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    clothing = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    medical_expenses = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Out-of-pocket healthcare costs",
    )

    # Other recurring expenses
    childcare = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    child_support_paid = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Court-ordered support payments",
    )
    insurance_not_deducted = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Health, life, or disability insurance not deducted from paycheck",
    )
    other_expenses = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Other necessary monthly expenses",
    )

    # Schedule J lines DigniFi never asked before 3e2: $0 when left empty
    real_estate_taxes = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    home_insurance = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    hoa_dues = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    personal_care = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    entertainment = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    charitable_contributions = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    taxes_not_deducted = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    support_others = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    other_property_mortgages = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    other_property_taxes = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    other_property_insurance = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    other_property_upkeep = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    other_property_hoa_dues = EncryptedDecimalField(max_digits=10, decimal_places=2, default=0)
    taxes_specify = EncryptedCharField(max_length=100, blank=True, default="")
    support_others_specify = EncryptedCharField(max_length=100, blank=True, default="")
    other_expenses_specify = EncryptedCharField(max_length=100, blank=True, default="")
    # Line 3: null until the filer answers
    expenses_include_others = EncryptedCharField(max_length=3, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expense_info"

    def __str__(self) -> str:
        total = self.calculate_total_monthly_expenses()
        return f"ExpenseInfo: ${total}/month (Session: {self.session_id})"

    def calculate_total_monthly_expenses(self) -> float:
        """Calculate total monthly expenses for means test."""
        # Decimal(...) because an unsaved default is the int 0.
        return float(sum(Decimal(getattr(self, f)) for f in self.AMOUNT_FIELDS))


class AssetInfo(models.Model):
    """Asset and property information (encrypted PII for account numbers)."""

    ASSET_TYPE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("real_property", "Real Estate/Home"),
        ("vehicle", "Vehicle"),
        ("bank_account", "Bank Account"),
        ("retirement_account", "Retirement Account (401k, IRA)"),
        ("personal_property", "Personal Property (furniture, jewelry, collectibles)"),
        ("other", "Other Asset"),
    ]

    DATA_SOURCE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("manual", "Manually Entered"),
        ("plaid", "Plaid API"),
        ("uploaded_document", "Uploaded Document"),
    ]

    session = models.ForeignKey(IntakeSession, on_delete=models.CASCADE, related_name="assets")
    asset_type = models.CharField(max_length=30, choices=ASSET_TYPE_CHOICES, null=True, blank=True)
    # The Schedule A/B line this row is on (3b spec §3.1). An old row has none.
    ab_line = EncryptedCharField(max_length=10, null=True, blank=True)
    # JSON: what the line asks beyond a description and a value (kind, who, percent, ...).
    details = EncryptedTextField(blank=True, default="{}")
    data_source = models.CharField(
        max_length=30,
        choices=DATA_SOURCE_CHOICES,
        default="manual",
        help_text="Source of asset data for audit trail",
    )

    # Asset description
    description = EncryptedCharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Brief description (e.g., '2015 Honda Civic', '123 Main St')",
    )
    current_value = EncryptedDecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current fair market value",
    )
    entire_value = EncryptedDecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Value of the entire property, when the filer owns a share",
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
    financial_institution = EncryptedCharField(
        max_length=100, blank=True, default="", help_text="Bank or institution name"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_info"

    def __str__(self) -> str:
        return f"Asset on line {self.ab_line} (Session: {self.session_id})"

    def get_details(self) -> dict:
        return json.loads(self.details)

    def set_details(self, value: dict) -> None:
        self.details = json.dumps(value)


class AssetLineAnswers(models.Model):
    """The filer's answers to Schedule A/B's Yes and No lines (3b spec §3.2).

    A JSON object of line key to "yes" or "no", encrypted. A key that is absent is unanswered.
    """

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="asset_lines"
    )
    answers = EncryptedTextField(default="{}")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_line_answers"

    def __str__(self) -> str:
        return f"AssetLineAnswers (Session: {self.session_id})"

    def get_answers(self) -> dict:
        return json.loads(self.answers)

    def merge(self, sent: dict) -> None:
        """Set each sent answer; a null removes the key. Doesn't save."""
        answers = self.get_answers()
        for key, value in sent.items():
            if value is None:
                answers.pop(key, None)
            else:
                answers[key] = value
        self.answers = json.dumps(answers)


class ClaimAnswers(models.Model):
    """The filer's own answers to Schedules D, E/F, G and H beyond any one row (3c3 spec §7.1).

    A JSON object of key to answer, encrypted. A key that is absent is unanswered.
    """

    KEYS: ClassVar[tuple[str, ...]] = (
        "no_debts",
        "contracts_answer",
        "codebtors_answer",
        "community_lived",
        "community_spouse_lived_with",
        "community_state",
        "community_spouse_name",
        "community_spouse_street_address",
        "community_spouse_street_2",
        "community_spouse_city",
        "community_spouse_state",
        "community_spouse_zip_code",
        "community_spouse_outside_us",
    )
    TEXT_LIMITS: ClassVar[dict[str, int]] = {
        "community_state": 100,
        "community_spouse_name": 255,
        "community_spouse_street_address": 255,
        "community_spouse_street_2": 255,
        "community_spouse_city": 100,
        "community_spouse_state": 2,
        "community_spouse_zip_code": 10,
    }

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="claim_answers"
    )
    answers = EncryptedTextField(default="{}")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "claim_answers"

    def __str__(self) -> str:
        return f"ClaimAnswers (Session: {self.session_id})"

    def get_answers(self) -> dict:
        return json.loads(self.answers)

    def merge(self, sent: dict) -> None:
        """Set each sent answer; a null removes the key. Doesn't save."""
        answers = self.get_answers()
        for key, value in sent.items():
            if value is None:
                answers.pop(key, None)
            else:
                answers[key] = value
        self.answers = json.dumps(answers)


class DebtInfoQuerySet(models.QuerySet):
    def confirmed(self):
        """The debts the filer has confirmed, without the drafts read from scanned documents.

        A scanned debt stays a draft until the filer presses Continue on the Amounts Owed step
        (`update_step` 7) (DIG-163).
        Every reader that feeds a form or the means test reads through this.
        """
        return self.filter(is_draft=False)


class DebtInfo(models.Model):
    """Creditor and amounts owed information (trauma-informed language)."""

    DEBT_TYPE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("credit_card", "Credit Card"),
        ("medical", "Medical Bill"),
        ("personal_loan", "Personal Loan"),
        ("student_loan", "Student Loan"),
        ("auto_loan", "Auto Loan"),
        ("mortgage", "Mortgage/Home Loan"),
        ("utility", "Utility Bill"),
        ("other", "Other Amount Owed"),
    ]

    PRIORITY_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("unsecured", "Unsecured (Credit Card, Medical)"),
        ("secured", "Secured (Car Loan, Mortgage)"),
        ("priority", "Priority (Taxes, Child Support)"),
    ]

    DATA_SOURCE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("manual", "Manually Entered"),
        ("credit_report", "Credit Report"),
        ("uploaded_document", "Uploaded Document"),
    ]

    session = models.ForeignKey(IntakeSession, on_delete=models.CASCADE, related_name="debts")
    data_source = models.CharField(
        max_length=30,
        choices=DATA_SOURCE_CHOICES,
        default="manual",
        help_text="Source of creditor data for audit trail",
    )

    # Creditor information
    # Draft until counsel rules on C-17 (DIG-280).
    creditor_name = EncryptedCharField(max_length=255, help_text="Name of creditor")
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
    monthly_payment = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum monthly payment if still paying",
    )
    is_in_collections = models.BooleanField(
        default=False, help_text="Has this account been sent to collections?"
    )
    notes = EncryptedTextField(blank=True, help_text="Additional context about this amount owed")

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

    collateral_description = EncryptedTextField(
        blank=True,
        help_text="Description of collateral if secured debt (e.g., '2020 Honda Civic VIN: 12345')",
    )

    is_priority = models.BooleanField(
        default=False,
        help_text="Priority unsecured debts (e.g., taxes, child support) on Schedule E/F Part 1",
    )

    date_incurred = EncryptedTextField(
        null=True,
        blank=True,
        help_text="When debt was incurred",
    )

    is_draft = models.BooleanField(
        default=False,
        help_text="True for entries auto-created from scanned documents, pending user confirmation",
    )
    source_document = models.ForeignKey(
        "documents.UploadedDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="draft_debts",
        help_text="Document scan that generated this entry",
    )

    is_dischargeable = models.BooleanField(default=True)
    adversary_proceeding_needed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # The creditor's address (Schedules D and E/F), 3c3.
    street_address = EncryptedCharField(max_length=255, blank=True, default="")
    street_2 = EncryptedCharField(max_length=255, blank=True, default="")
    city = EncryptedCharField(max_length=100, blank=True, default="")
    state = EncryptedCharField(max_length=2, blank=True, default="")
    zip_code = EncryptedCharField(max_length=10, blank=True, default="")
    outside_us = EncryptedBooleanField(default=False)

    secured_by = models.ForeignKey(
        AssetInfo,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="secured_debts",
    )
    home_payment_line = EncryptedCharField(
        max_length=10,
        choices=[(v, v) for v in HOME_PAYMENT_LINES],
        null=True,
        blank=True,
    )
    collateral_who = EncryptedCharField(
        max_length=20, choices=[(v, v) for v in WHO], null=True, blank=True
    )
    offset_answer = EncryptedCharField(
        max_length=3, choices=[(v, v) for v in YES_NO], null=True, blank=True
    )
    community_debt = EncryptedCharField(
        max_length=3, choices=[("yes", "yes")], blank=True, default=""
    )
    lien = EncryptedTextField(null=True, blank=True)
    claim_status = EncryptedTextField(null=True, blank=True)
    notice_parties = EncryptedTextField(null=True, blank=True)
    next_notice_party_id = models.PositiveIntegerField(default=1)

    objects = DebtInfoQuerySet.as_manager()

    LIEN_KINDS: ClassVar[tuple[str, ...]] = ("agreement", "statutory", "judgment", "other")
    CLAIM_STATUSES: ClassVar[tuple[str, ...]] = ("contingent", "unliquidated", "disputed")
    MAX_NOTICE_PARTIES = 10
    NOTICE_PARTY_KEYS: ClassVar[tuple[str, ...]] = (
        "name",
        "street_address",
        "street_2",
        "city",
        "state",
        "zip_code",
        "outside_us",
        "last_4",
    )
    # The JSON columns _save_rows_by_id stores with json.dumps.
    JSON_ANSWERS: ClassVar[tuple[str, ...]] = ("lien", "claim_status")
    # The longest range of dates the narrowest date box, Schedule D's, prints whole at 6 pt,
    # typed with a hyphen (3c3 R21).
    DATE_INCURRED_MAX_LENGTH = 15

    class Meta:
        db_table = "debt_info"

    def __str__(self) -> str:
        return f"DebtInfo {self.pk} ({self.get_debt_type_display()}, {self.get_consumer_business_classification_display()})"

    def get_lien(self) -> dict | None:
        return None if self.lien is None else json.loads(self.lien)

    def get_claim_status(self) -> list[str] | None:
        return None if self.claim_status is None else json.loads(self.claim_status)

    def get_notice_parties(self) -> list[dict] | None:
        return None if self.notice_parties is None else json.loads(self.notice_parties)

    def store_notice_parties(self, rows: list[dict] | None) -> list[dict] | None:
        """Store the list in the order sent and return it as stored. Doesn't save.

        A row keeps its id when the stored list holds it and no earlier row in this list
        kept it; every other row gets next_notice_party_id, which then goes up by one.
        Storing None resets nothing.
        """
        if rows is None:
            self.notice_parties = None
            return None
        stored_ids = {row["id"] for row in self.get_notice_parties() or []}
        kept = set()
        saved = []
        for row in rows:
            party_id = row.get("id")
            if party_id in stored_ids and party_id not in kept:
                kept.add(party_id)
            else:
                party_id = self.next_notice_party_id
                self.next_notice_party_id += 1
            party = {"id": party_id}
            for key in self.NOTICE_PARTY_KEYS:
                missing = False if key == "outside_us" else ""
                value = row.get(key)
                party[key] = missing if value is None else value
            saved.append(party)
        self.notice_parties = json.dumps(saved)
        return saved


class FilingFee(models.Model):
    """
    How the filer will pay the filing fee (Form 101 line 8), and Form 103B's own
    questions 4, 5, 7 and 9 for a filer who asks for a waiver (3f spec §4). Every answer
    is encrypted; null means unanswered. It is not intake data: saving it never reopens
    a completed intake.
    """

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="filing_fee"
    )
    payment_choice = EncryptedCharField(max_length=20, null=True, blank=True)
    income_change_answer = EncryptedCharField(max_length=3, null=True, blank=True)
    income_change_explanation = EncryptedTextField(blank=True, default="")
    installments_explanation = EncryptedTextField(blank=True, default="")
    others_covered_answer = EncryptedCharField(max_length=3, null=True, blank=True)
    others_covered_who = EncryptedTextField(blank=True, default="")
    expense_change_answer = EncryptedCharField(max_length=3, null=True, blank=True)
    expense_change_explanation = EncryptedTextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    PAYMENT_CHOICES: ClassVar[tuple[str, ...]] = ("pay_in_full", "installments", "waiver")
    YES_NO_FIELDS: ClassVar[tuple[str, ...]] = (
        "income_change_answer",
        "others_covered_answer",
        "expense_change_answer",
    )
    # Measured against 103B's `4 type`, `5 Type`, `undefined_8` and `undefined_10`
    # (PDFFormFiller.check at the smallest font, rounded down to a multiple of 10).
    TEXT_LIMITS: ClassVar[dict[str, int]] = {
        "income_change_explanation": 520,
        "installments_explanation": 520,
        "others_covered_who": 420,
        "expense_change_explanation": 420,
    }

    class Meta:
        db_table = "filing_fees"

    def __str__(self) -> str:
        return f"Filing fee (Session: {self.session_id})"


class SOFAReport(models.Model):
    """Statement of Financial Affairs (Form 107) structured data, per session.

    Boolean flags gate conditional sections (drive PREDICATES in the fill engine).
    """

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="sofa_report"
    )
    has_prior_income = models.BooleanField(default=False)
    has_creditor_payments = models.BooleanField(default=False)
    has_business = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sofa_reports"


class SOFAPriorIncome(models.Model):
    """A prior-year income row (Form 107 Q1/Q2)."""

    report = models.ForeignKey(SOFAReport, on_delete=models.CASCADE, related_name="prior_income")
    year = models.PositiveIntegerField()
    source = models.CharField(max_length=255, help_text="e.g. Wages, Operating a business")
    gross_amount = EncryptedDecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "sofa_prior_income"
        ordering = ["-year"]


class SOFACreditorPayment(models.Model):
    """A payment-to-creditor row (Form 107 Q6/Q7)."""

    report = models.ForeignKey(
        SOFAReport, on_delete=models.CASCADE, related_name="creditor_payments"
    )
    creditor_name = models.CharField(max_length=255)
    total_paid = EncryptedDecimalField(max_digits=12, decimal_places=2)
    dates_of_payments = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "sofa_creditor_payments"


class FormAnswer(models.Model):
    """Generic key/value answer store for the sparse long tail of form fields."""

    session = models.ForeignKey(
        IntakeSession, on_delete=models.CASCADE, related_name="form_answers"
    )
    form_type = models.CharField(max_length=20)
    field_key = models.CharField(max_length=100)
    value = models.TextField(blank=True)

    class Meta:
        db_table = "form_answers"
        unique_together = [["session", "form_type", "field_key"]]


class ExecutoryContract(models.Model):
    """Executory contract or unexpired lease (Schedule G)."""

    CONTRACT_TYPE_CHOICES = [
        ("lease", "Lease"),
        ("contract", "Executory Contract"),
        ("other", "Other"),
    ]

    session = models.ForeignKey(
        IntakeSession, on_delete=models.CASCADE, related_name="executory_contracts"
    )
    counterparty_name = EncryptedCharField(
        max_length=255, help_text="Name of other party to the contract or lease"
    )
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES, blank=True)
    description = EncryptedTextField(
        blank=True, help_text="Brief description of the contract or lease"
    )
    street_address = EncryptedCharField(max_length=255, blank=True, default="")
    street_2 = EncryptedCharField(max_length=255, blank=True, default="")
    city = EncryptedCharField(max_length=100, blank=True, default="")
    state = EncryptedCharField(max_length=2, blank=True, default="")
    zip_code = EncryptedCharField(max_length=10, blank=True, default="")
    outside_us = EncryptedBooleanField(default=False)
    lease_kind = EncryptedCharField(
        max_length=25, choices=[(v, v) for v in LEASE_KINDS], null=True, blank=True
    )
    monthly_payment = EncryptedDecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vehicle_asset = models.ForeignKey(
        AssetInfo,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vehicle_leases",
    )
    owed_debt = models.ForeignKey(
        DebtInfo,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owing_contracts",
    )
    owes_now = EncryptedCharField(
        max_length=3, choices=[(v, v) for v in YES_NO], null=True, blank=True
    )

    LEASE_KINDS: ClassVar[tuple[str, ...]] = LEASE_KINDS

    class Meta:
        db_table = "executory_contracts"


class Codebtor(models.Model):
    """Codebtor information (Schedule H)."""

    RELATIONSHIP_CHOICES = [
        ("spouse", "Spouse"),
        ("former_spouse", "Former Spouse"),
        ("relative", "Relative"),
        ("friend", "Friend"),
        ("business_partner", "Business Partner"),
        ("other", "Other"),
    ]

    session = models.ForeignKey(IntakeSession, on_delete=models.CASCADE, related_name="codebtors")
    name = EncryptedCharField(max_length=255, help_text="Full name of codebtor")
    street_address = EncryptedCharField(max_length=255, blank=True)
    street_2 = EncryptedCharField(max_length=255, blank=True, default="")
    city = EncryptedCharField(max_length=100, blank=True)
    state = EncryptedCharField(max_length=2, blank=True)
    zip_code = EncryptedCharField(max_length=10, blank=True)
    outside_us = EncryptedBooleanField(default=False)
    relationship = EncryptedCharField(max_length=20, choices=RELATIONSHIP_CHOICES, blank=True)
    links = EncryptedTextField(default="[]")

    LINK_KINDS: ClassVar[tuple[str, ...]] = ("debt", "contract")
    JSON_ANSWERS: ClassVar[tuple[str, ...]] = ("links",)

    class Meta:
        db_table = "codebtors"

    def get_links(self) -> list[dict]:
        return json.loads(self.links)


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
    session = models.ForeignKey(
        "intake.IntakeSession", on_delete=models.CASCADE, related_name="adversary_proceedings"
    )
    debt = models.ForeignKey("intake.DebtInfo", on_delete=models.CASCADE, null=True, blank=True)
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
