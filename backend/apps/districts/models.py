"""
Models for the Bankruptcy Districts app.
Defines District, MedianIncome, PovertyGuideline, ExemptionCatalog, ExemptionLaw, and LocalRule.
"""

from decimal import Decimal

from django.core.validators import RegexValidator
from django.db import models

from .dated_tables import DatedTable


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

    code = models.CharField(max_length=8, unique=True, help_text="District code, e.g., 'ilnd'.")
    name = models.CharField(max_length=128, help_text="Full name of the district.")
    state = models.CharField(
        max_length=2,
        help_text="Two-letter state abbreviation.",
        db_index=True,
        validators=[
            RegexValidator(regex=r"^[A-Z]{2}$", message="State must be two uppercase letters.")
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
    created_at = models.DateTimeField(auto_now_add=True, help_text="Record creation time.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Record update time.")

    class Meta:
        verbose_name = "District"
        verbose_name_plural = "Districts"
        ordering = ["state", "name"]

    def __str__(self):
        return f"{self.name} ({self.code.upper()})"


class MedianIncome(DatedTable):
    """
    Median income thresholds per district and effective period, for means test qualification.

    Fields:
        district (District): Reference to the relevant district.
        effective_date (date): Date this threshold became effective.
        valid_through (date): Last day before the next Census update; empty means open-ended.
        source_url (str): The U.S. Trustee page the figures come from.
        family_size_1..8 (Decimal): Median annual household income by family size.
        created_at (datetime): Timestamp of record creation.
    """

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="median_incomes")
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
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Record creation time.")

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
            ValueError: If family_size is less than 1, or above 8 with no extra-person amount.
        """
        if family_size < 1:
            raise ValueError("Family size must be at least 1.")

        if family_size <= 8:
            return getattr(self, f"family_size_{family_size}")

        # For family size > 8, extrapolate by the table's own extra-person amount
        if self.family_size_additional is None:
            raise ValueError("This median income table has no amount for each extra person.")
        additional_people = family_size - 8
        return self.family_size_8 + (Decimal(additional_people) * self.family_size_additional)


class PovertyGuideline(DatedTable):
    """
    The HHS poverty guidelines for the 48 contiguous states and DC, the only ones ILND needs.

    National public data, so it has no district and is not encrypted. Each row is loaded by a
    data migration (docs/REFERENCE_TABLES.md).

    Fields:
        first_person (int): Yearly guideline for one person, in whole dollars.
        each_additional (int): Added for each person after the first, in whole dollars a year.
    """

    first_person = models.PositiveIntegerField(
        help_text="Yearly guideline for one person, in whole dollars."
    )
    each_additional = models.PositiveIntegerField(
        help_text="Added for each person after the first, in whole dollars a year."
    )

    class Meta:
        verbose_name = "Poverty Guideline"
        verbose_name_plural = "Poverty Guidelines"
        ordering = ["-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["effective_date"], name="poverty_guideline_unique_effective_date"
            )
        ]

    def __str__(self):
        return f"HHS Poverty Guidelines ({self.effective_date})"


class ExemptionCatalog(DatedTable):
    """
    One dated list of the Illinois and federal exemption laws a filer can pick for Schedule C.

    National public data, not encrypted, loaded by data migrations (docs/REFERENCE_TABLES.md).
    A new public act is a new catalog starting on its effective date.
    """

    class Meta:
        verbose_name = "Exemption Catalog"
        verbose_name_plural = "Exemption Catalogs"
        ordering = ["-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["effective_date"], name="exemption_catalog_unique_effective_date"
            )
        ]

    def __str__(self):
        return f"Exemption laws ({self.effective_date})"


class ExemptionLaw(models.Model):
    """
    One law of an exemption catalog, in the order the page lists it.

    National public data, not encrypted, loaded by data migrations (docs/REFERENCE_TABLES.md).

    Fields:
        catalog (ExemptionCatalog): The list this law belongs to.
        key (str): Stable name the page and a filer's claim use for the law.
        position (int): Place in the list, from 1: Illinois laws first, then federal.
        jurisdiction (str): "illinois" or "federal".
        citation (str): The statute as it is cited.
        limit_text (str): The law's own limit in words, or empty when it names none.
        source_url (str): Where the statute is published.
    """

    catalog = models.ForeignKey(ExemptionCatalog, on_delete=models.CASCADE, related_name="laws")
    key = models.CharField(max_length=40)
    position = models.PositiveSmallIntegerField()
    jurisdiction = models.CharField(
        max_length=8, choices=(("illinois", "Illinois"), ("federal", "Federal"))
    )
    citation = models.CharField(max_length=60)
    limit_text = models.TextField(blank=True, default="")
    source_url = models.URLField(max_length=300)

    class Meta:
        verbose_name = "Exemption Law"
        verbose_name_plural = "Exemption Laws"
        ordering = ["catalog", "position"]
        constraints = [
            models.UniqueConstraint(fields=["catalog", "key"], name="exemption_law_unique_key"),
            models.UniqueConstraint(
                fields=["catalog", "position"], name="exemption_law_unique_position"
            ),
        ]

    def __str__(self):
        return self.citation


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

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="local_rules")
    rule_number = models.CharField(max_length=16, help_text="Local rule number or identifier.")
    title = models.CharField(max_length=128, help_text="Short title of the rule.")
    description = models.TextField(help_text="Full description or requirements under the rule.")
    effective_date = models.DateField(help_text="Date when this rule became effective.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Record creation time.")

    class Meta:
        verbose_name = "Local Rule"
        verbose_name_plural = "Local Rules"
        ordering = ["district", "rule_number"]
        unique_together = [["district", "rule_number", "effective_date"]]

    def __str__(self):
        return f"{self.district.code.upper()} Rule {self.rule_number} ({self.title})"
