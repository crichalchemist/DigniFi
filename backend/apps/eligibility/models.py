"""Means test and eligibility models."""

import json
from decimal import Decimal
from django.db import models
from django.utils import timezone
from encrypted_model_fields.fields import EncryptedTextField


class MeansTest(models.Model):
    """Chapter 7 means test calculation (11 U.S.C. § 707(b))."""

    session = models.OneToOneField(
        "intake.IntakeSession", on_delete=models.CASCADE, related_name="means_test"
    )
    district = models.ForeignKey("districts.District", on_delete=models.PROTECT)

    # Inputs
    median_income_threshold = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Median income for family size"
    )
    calculated_cmi = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Current Monthly Income"
    )

    # Results
    passes_means_test = models.BooleanField(
        help_text="True if CMI < median income", db_index=True
    )
    # Encrypted calculation details to protect potential PII
    # Using EncryptedTextField as JSON storage since EncryptedJSONField is not available
    calculation_details = EncryptedTextField(
        default="{}", help_text="Full calculation breakdown (JSON)"
    )

    def get_calculation_details(self) -> dict:
        """
        Deserialize calculation_details from JSON string to dict.
        Returns empty dict if value is empty/blank.
        """
        if not self.calculation_details:
            return {}
        return json.loads(self.calculation_details)

    def set_calculation_details(self, data: dict) -> None:
        """
        Serialize dict to JSON string for calculation_details.
        Raises TypeError if data is not a dict.
        """
        if not isinstance(data, dict):
            raise TypeError("calculation_details must be a dictionary")
        self.calculation_details = json.dumps(data)

    # Fee waiver eligibility (28 U.S.C. § 1930(f))
    qualifies_for_fee_waiver = models.BooleanField(default=False)

    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "means_tests"

    def __str__(self) -> str:
        return (
            f"Means Test {self.id} - {'Passes' if self.passes_means_test else 'Fails'}"
        )

    def calculate(self) -> bool:
        """
        Calculate means test using 11 U.S.C. § 707(b) methodology.

        Returns:
            bool: True if debtor passes means test (CMI < median income)

        Raises:
            ValueError: If required intake data is missing
        """
        # Get income info from session
        try:
            income_info = self.session.income_info
        except AttributeError:
            raise ValueError("IntakeSession must have income_info to calculate means test")

        # Calculate Current Monthly Income (CMI) - average of last 6 months
        monthly_income_data = income_info.monthly_income
        if not isinstance(monthly_income_data, list) or len(monthly_income_data) != 6:
            raise ValueError(
                "monthly_income must be a list of 6 monthly income values"
            )

        total_6_month_income = sum(Decimal(str(amt)) for amt in monthly_income_data)
        cmi = total_6_month_income / Decimal("6")

        # Get family size for median income lookup
        family_size = income_info.number_of_dependents + 1  # Filer + dependents
        if income_info.marital_status in ["married_joint", "married_separate"]:
            family_size += 1  # Add spouse

        # Get median income threshold from district
        try:
            median_income_record = self.district.median_incomes.latest("effective_date")
        except Exception:
            raise ValueError(
                f"No median income data found for district {self.district.code}"
            )

        median_income_threshold = median_income_record.get_median_income(family_size)

        # Determine if passes means test
        passes_test = cmi < median_income_threshold

        # Calculate fee waiver eligibility (CMI < 150% of poverty line)
        # For MVP, simplified: qualifies if income is very low (< 60% of median)
        qualifies_fee_waiver = cmi < (median_income_threshold * Decimal("0.60"))

        # Store calculation details (encrypted)
        details = {
            "cmi": float(cmi),
            "median_income_threshold": float(median_income_threshold),
            "family_size": family_size,
            "monthly_income_breakdown": monthly_income_data,
            "marital_status": income_info.marital_status,
            "number_of_dependents": income_info.number_of_dependents,
            "passes_test": passes_test,
            "qualifies_fee_waiver": qualifies_fee_waiver,
            "calculated_at": timezone.now().isoformat(),
            "statute_citation": "11 U.S.C. § 707(b)",
        }

        # Update model fields
        self.calculated_cmi = cmi
        self.median_income_threshold = median_income_threshold
        self.passes_means_test = passes_test
        self.qualifies_for_fee_waiver = qualifies_fee_waiver
        self.set_calculation_details(details)

        return passes_test
