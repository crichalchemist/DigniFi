"""Means test and eligibility models."""

import json
from django.db import models
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
