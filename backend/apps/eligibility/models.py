"""Means test and eligibility models."""

from django.db import models


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
    passes_means_test = models.BooleanField(help_text="True if CMI < median income")
    calculation_details = models.JSONField(
        default=dict, help_text="Full calculation breakdown"
    )

    # Fee waiver eligibility (28 U.S.C. § 1930(f))
    qualifies_for_fee_waiver = models.BooleanField(default=False)

    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "means_tests"

    def __str__(self) -> str:
        return (
            f"Means Test {self.id} - {'Passes' if self.passes_means_test else 'Fails'}"
        )
