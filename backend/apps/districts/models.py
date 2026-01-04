"""
Models for the Bankruptcy Districts app.
Defines District, MedianIncome, ExemptionSchedule, and LocalRule.
"""

from django.db import models
from django.core.validators import RegexValidator
from decimal import Decimal


class District(models.Model):
    """
    Represents a U.S. Bankruptcy Court District.

    Fields:
        code (str): Unique short alphanumeric code for the district (e.g., 'ilnd').
        name (str): Full name of the bankruptcy district.
        state (str): Two-letter uppercase state abbreviation (e.g., 'IL').
        court_name (str): Official name of the court.
        pro_se_efiling_allowed (bool): True if pro se E-filing is permitted in this district.
        filing_fee_chapter_7 (Decimal): Standard filing fee for Chapter 7 in this district.
        created_at (datetime): Timestamp of district record creation.
        updated_at (datetime): Timestamp of district record last update.
    """

    code = models.CharField(
        max_length=8, unique=True, help_text="District code, e.g., 'ilnd'."
    )
    name = models.CharField(max_length=128, help_text="Full name of the district.")
    state = models.CharField(
        max_length=2,
        help_text="Two-letter state abbreviation.",
        db_index=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z]{2}$", message="State must be two uppercase letters."
            )
        ],
    )
    court_name = models.CharField(
        max_length=128, help_text="Official name of the bankruptcy court."
    )
    pro_se_efiling_allowed = models.BooleanField(
        default=False, help_text="Is pro se E-filing allowed?"
    )
    filing_fee_chapter_7 = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Chapter 7 filing fee (USD)."
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Record creation time."
    )
    updated_at = models.DateTimeField(auto_now=True, help_text="Record update time.")

    class Meta:
        verbose_name = "District"
        verbose_name_plural = "Districts"
        ordering = ["state", "name"]

    def __str__(self):
        return f"{self.name} ({self.code.upper()})"


class MedianIncome(models.Model):
    """
    Median income thresholds per district and effective period, for means test qualification.

    Fields:
        district (District): Reference to the relevant district.
        effective_date (date): Date this threshold became effective.
        family_size_1..8 (Decimal): Median annual household income by family size.
        created_at (datetime): Timestamp of record creation.
    """

    district = models.ForeignKey(
        District, on_delete=models.CASCADE, related_name="median_incomes"
    )
    effective_date = models.DateField(
        help_text="Date when this median income threshold became effective."
    )
    family_size_1 = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="1-person household median income."
    )
    family_size_2 = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="2-person household median income."
    )
    family_size_3 = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="3-person household median income."
    )
    family_size_4 = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="4-person household median income."
    )
    family_size_5 = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="5-person household median income."
    )
    family_size_6 = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="6-person household median income."
    )
    family_size_7 = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="7-person household median income."
    )
    family_size_8 = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="8-person household median income."
    )
    family_size_additional = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount to add for each additional person above 8.",
        default=9900.00,
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Record creation time."
    )

    class Meta:
        verbose_name = "Median Income"
        verbose_name_plural = "Median Incomes"
        ordering = ["-effective_date", "district"]
        unique_together = [["district", "effective_date"]]

    def __str__(self):
        return f"{self.district.code.upper()} Median Income ({self.effective_date})"

    def get_median_income(self, family_size: int) -> Decimal:
        """
        Get median income for a given family size.

        Args:
            family_size: Number of people in the household (must be >= 1).

        Returns:
            Decimal: The median income for the specified family size.

        Raises:
            ValueError: If family_size is less than 1.
        """
        if family_size < 1:
            raise ValueError("Family size must be at least 1.")

        if family_size <= 8:
            return getattr(self, f"family_size_{family_size}")

        # For family size > 8, extrapolate
        additional_people = family_size - 8
        additional_amount = (
            self.family_size_additional
            if self.family_size_additional is not None
            else Decimal("9900.00")
        )
        return self.family_size_8 + (Decimal(additional_people) * additional_amount)


class ExemptionSchedule(models.Model):
    """
    Exemption amounts for key asset categories, by district and exemption type.

    Fields:
        district (District): Reference to the relevant district.
        exemption_type (str): Exemption type (homestead, vehicle, tools_of_trade, wildcard).
        amount (Decimal): Exemption amount in dollars.
        statute_citation (str): Legal citation for the exemption.
        description (str): Plain-language description of the exemption.
        created_at (datetime): Timestamp of record creation.
    """

    HOMESTEAD = "homestead"
    VEHICLE = "vehicle"
    TOOLS_OF_TRADE = "tools_of_trade"
    WILDCARD = "wildcard"

    EXEMPTION_TYPE_CHOICES = [
        (HOMESTEAD, "Homestead"),
        (VEHICLE, "Vehicle"),
        (TOOLS_OF_TRADE, "Tools of Trade"),
        (WILDCARD, "Wildcard"),
    ]

    district = models.ForeignKey(
        District, on_delete=models.CASCADE, related_name="exemption_schedules"
    )
    exemption_type = models.CharField(
        max_length=16, choices=EXEMPTION_TYPE_CHOICES, help_text="Type of exemption."
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Maximum exemption amount (USD)."
    )
    statute_citation = models.CharField(
        max_length=64, help_text="Legal citation for this exemption."
    )
    description = models.TextField(
        help_text="Plain language description of the exemption."
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Record creation time."
    )

    class Meta:
        verbose_name = "Exemption Schedule"
        verbose_name_plural = "Exemption Schedules"
        ordering = ["district", "exemption_type"]
        unique_together = [["district", "exemption_type", "statute_citation"]]

    def __str__(self):
        return (
            f"{self.district.code.upper()} {self.get_exemption_type_display()} - "
            f"{self.amount} ({self.statute_citation})"
        )


class LocalRule(models.Model):
    """
    Local bankruptcy court procedural rules by district.

    Fields:
        district (District): Reference to the relevant district.
        rule_number (str): Rule identifier (e.g., 'LR-101').
        title (str): Rule title.
        description (str): Full text or description of the rule.
        effective_date (date): Date the rule became effective.
        created_at (datetime): Timestamp of record creation.
    """

    district = models.ForeignKey(
        District, on_delete=models.CASCADE, related_name="local_rules"
    )
    rule_number = models.CharField(
        max_length=16, help_text="Local rule number or identifier."
    )
    title = models.CharField(max_length=128, help_text="Short title of the rule.")
    description = models.TextField(
        help_text="Full description or requirements under the rule."
    )
    effective_date = models.DateField(help_text="Date when this rule became effective.")
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Record creation time."
    )

    class Meta:
        verbose_name = "Local Rule"
        verbose_name_plural = "Local Rules"
        ordering = ["district", "rule_number"]
        unique_together = [["district", "rule_number", "effective_date"]]

    def __str__(self):
        return f"{self.district.code.upper()} Rule {self.rule_number} ({self.title})"
