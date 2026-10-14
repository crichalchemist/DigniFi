"""Means test and eligibility models."""

import json
from decimal import Decimal

from django.db import models
from django.utils import timezone
from encrypted_model_fields.fields import EncryptedTextField

from .cmi import current_monthly_income, is_above_median


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
    passes_means_test = models.BooleanField(help_text="True if CMI < median income", db_index=True)

    # Above-median calculation fields
    total_allowable_expenses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Monthly allowable expenses (IRS standards + actual)",
    )
    disposable_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Monthly disposable income after deductions",
    )
    priority_debts_monthly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Monthly priority debt payments",
    )
    passes_above_median = models.BooleanField(
        default=False, help_text="True if disposable income < $756.25/mo"
    )
    above_median_calculated = models.BooleanField(
        default=False, help_text="Whether above-median calculation was performed"
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
        return f"Means Test {self.id} - {'Passes' if self.passes_means_test else 'Fails'}"

    def calculate(self) -> bool:
        """
        Calculate means test using 11 U.S.C. § 707(b) methodology.

        Returns:
            bool: True if debtor passes means test (CMI × 12 at or below the median income, or
            above it with disposable income under the threshold)

        Raises:
            ValueError: If required intake data is missing
        """
        # Get income info from session
        try:
            income_info = self.session.income_info
        except AttributeError as err:
            raise ValueError("IntakeSession must have income_info to calculate means test") from err

        # Current Monthly Income (CMI): the Income step's amounts, without Social Security
        cmi = current_monthly_income(income_info)

        # Get family size for median income lookup. The wizard collects
        # household_size on the debtor step; sessions without it fall back
        # to deriving family size from marital status + dependents.
        debtor_info = getattr(self.session, "debtor_info", None)
        if debtor_info is not None and (debtor_info.household_size or 0) >= 1:
            family_size = debtor_info.household_size
        else:
            family_size = income_info.number_of_dependents + 1  # Filer + dependents
            if income_info.marital_status in ["married_joint", "married_separate"]:
                family_size += 1  # Add spouse

        # Get median income threshold from district
        try:
            median_income_record = self.district.median_incomes.latest("effective_date")
        except Exception as err:
            raise ValueError(
                f"No median income data found for district {self.district.code}"
            ) from err

        median_income_threshold = median_income_record.get_median_income(family_size)

        # Determine if passes means test. CMI is monthly; the Census median
        # is annual, so annualize per 11 U.S.C. § 707(b)(7).
        annualized_cmi = cmi * Decimal("12")
        passes_test = not is_above_median(cmi, median_income_threshold)

        # Initialize calculation details (used by above-median pathway below)
        details: dict = {}

        # Above-median pathway: calculate allowable expenses
        if not passes_test:
            from apps.eligibility.services.expense_deduction_calculator import (
                ExpenseDeductionCalculator,
            )

            ded_calc = ExpenseDeductionCalculator(self.session)
            ded_result = ded_calc.calculate()

            self.total_allowable_expenses = ded_result.allowable_expenses
            self.disposable_income = ded_result.disposable_income
            self.priority_debts_monthly = ded_result.priority_debts_monthly
            self.above_median_calculated = True

            # $756.25/mo = $9,075 over 60 months (2024 threshold)
            threshold = Decimal("756.25")
            self.passes_above_median = ded_result.disposable_income < threshold
            passes_test = self.passes_above_median

            details["above_median"] = {
                "allowable_expenses": float(ded_result.allowable_expenses),
                "disposable_income": float(ded_result.disposable_income),
                "priority_debts": float(ded_result.priority_debts_monthly),
                "passes_above_median": self.passes_above_median,
            }
        else:
            # At or below the median: an earlier above-median result no longer holds (DIG-128).
            self.total_allowable_expenses = Decimal("0")
            self.disposable_income = Decimal("0")
            self.priority_debts_monthly = Decimal("0")
            self.passes_above_median = False
            self.above_median_calculated = False

        # Calculate fee waiver eligibility (CMI < 150% of poverty line)
        # For MVP, simplified: qualifies if income is very low (< 60% of median)
        qualifies_fee_waiver = annualized_cmi < (median_income_threshold * Decimal("0.60"))

        # Store calculation details (encrypted). JSON has no Decimal, and an empty box stays empty.
        income_by_source = {}
        for field in income_info.SOURCE_FIELDS:
            amount = getattr(income_info, field)
            income_by_source[field] = None if amount is None else float(amount)
        details.update(
            {
                "cmi": float(cmi),
                "annualized_cmi": float(annualized_cmi),
                "median_income_threshold": float(median_income_threshold),
                "family_size": family_size,
                "income_by_source": income_by_source,
                "marital_status": income_info.marital_status,
                "number_of_dependents": income_info.number_of_dependents,
                "passes_test": passes_test,
                "qualifies_fee_waiver": qualifies_fee_waiver,
                "calculated_at": timezone.now().isoformat(),
                "statute_citation": "11 U.S.C. § 707(b)",
            }
        )

        # Update model fields
        self.calculated_cmi = cmi
        self.median_income_threshold = median_income_threshold
        self.passes_means_test = passes_test
        self.qualifies_for_fee_waiver = qualifies_fee_waiver
        self.set_calculation_details(details)

        return passes_test
