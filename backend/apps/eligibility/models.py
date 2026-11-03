"""Means test and eligibility models."""

import json
from decimal import Decimal

from django.db import models
from django.utils import timezone
from encrypted_model_fields.fields import EncryptedTextField

from apps.districts.dated_tables import fill_date, in_force
from apps.intake.household import count_family_size
from apps.intake.income import floored_net

from .cmi import (
    counted_spouse_income,
    household_cmi,
    household_members,
    income_step_gaps,
    is_above_median,
    spouse_monthly_income,
)

# The means test's dated table, by the name its refusals log and calculation_details records.
MEDIAN_TABLE = "Census median income"


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
            IncomeStepGap: The first gap the Income step leaves (3e1 spec §9.1), before any
                count is read, so no household is sized until the filer has answered it
            ValueError: If required intake data is missing
            NoTableInForce: If no median income table is in force on the fill date
        """
        gaps = income_step_gaps(self.session)
        if gaps:
            raise gaps[0]
        income_info = self.session.income_info

        # Current Monthly Income (CMI), without Social Security: the filer's, plus the spouse's
        # (122A-1 column B) for a filer living with them (3e1 spec §5.3)
        cmi = household_cmi(self.session)
        spouse_cmi = spouse_monthly_income(self.session)

        # 122A-1 line 13, which sizes the median: the filer and everyone living with them
        family_size = count_family_size(household_members(self.session))

        # The district's median income table in force on the day the forms are filled.
        # None in force raises NoTableInForce; no older table stands in.
        median_table = in_force(
            self.district.median_incomes.all(),
            fill_date(),
            MEDIAN_TABLE,
            self.district.code,
        )

        median_income_threshold = median_table.get_median_income(family_size)

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

        # Store calculation details (encrypted). JSON has no Decimal, and an empty box stays empty.
        income_by_source = {}
        for field in income_info.SOURCE_FIELDS:
            amount = getattr(income_info, field)
            income_by_source[field] = None if amount is None else float(amount)
        spouse_row = counted_spouse_income(self.session)
        spouse_entries = None if spouse_row is None else spouse_row.get_entries()
        entries = income_info.get_entries()
        details.update(
            {
                "business_net": f"{floored_net(entries, 'business'):.2f}",
                "rental_net": f"{floored_net(entries, 'rental'):.2f}",
                "spouse_business_net": (
                    None if spouse_row is None else f"{floored_net(spouse_entries, 'business'):.2f}"
                ),
                "spouse_rental_net": (
                    None if spouse_row is None else f"{floored_net(spouse_entries, 'rental'):.2f}"
                ),
                "cmi": float(cmi),
                "annualized_cmi": float(annualized_cmi),
                "median_income_threshold": float(median_income_threshold),
                "median_table": {
                    "name": MEDIAN_TABLE,
                    "effective_date": median_table.effective_date.isoformat(),
                    "valid_through": (
                        median_table.valid_through.isoformat()
                        if median_table.valid_through
                        else None
                    ),
                    "source_url": median_table.source_url,
                },
                "family_size": family_size,
                "income_by_source": income_by_source,
                "marital_status": income_info.marital_status,
                "spouse_cmi": None if spouse_cmi is None else float(spouse_cmi),
                "passes_test": passes_test,
                "calculated_at": timezone.now().isoformat(),
                "statute_citation": "11 U.S.C. § 707(b)",
            }
        )

        # Update model fields
        self.calculated_cmi = cmi
        self.median_income_threshold = median_income_threshold
        self.passes_means_test = passes_test
        self.set_calculation_details(details)

        return passes_test
