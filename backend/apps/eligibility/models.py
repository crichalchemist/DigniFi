"""Means test and eligibility models."""

import json
from decimal import Decimal

from django.db import models
from django.utils import timezone
from encrypted_model_fields.fields import (
    EncryptedBooleanField,
    EncryptedCharField,
    EncryptedTextField,
)

from apps.districts.dated_tables import fill_date, in_force
from apps.districts.means_standards import NoMeansTestTable
from apps.intake.fields import EncryptedDecimalField
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
from .means_inputs import read_inputs, read_tables
from .means_lines import (
    AT_OR_BELOW_MEDIAN,
    CANNOT_WORK_OUT,
    NO_PRESUMPTION,
    PRESUMPTION,
    work_out,
)

# The means test's dated table, by the name its refusals log and calculation_details records.
MEDIAN_TABLE = "Census median income"

# passes_means_test by outcome, kept one release; empty while the result can't be worked out.
PASSES = {
    AT_OR_BELOW_MEDIAN: True,
    NO_PRESUMPTION: True,
    PRESUMPTION: False,
    CANNOT_WORK_OUT: None,
}


class MeansTest(models.Model):
    """Chapter 7 means test calculation (11 U.S.C. § 707(b))."""

    session = models.OneToOneField(
        "intake.IntakeSession", on_delete=models.CASCADE, related_name="means_test"
    )
    district = models.ForeignKey("districts.District", on_delete=models.PROTECT)

    # Inputs
    median_income_threshold = EncryptedDecimalField(
        max_digits=12, decimal_places=2, help_text="Median income for family size"
    )
    calculated_cmi = EncryptedDecimalField(
        max_digits=12, decimal_places=2, help_text="Current Monthly Income"
    )

    # Results
    passes_means_test = models.BooleanField(
        null=True,
        help_text=(
            "Kept one release; nothing reads it for a decision. True at or below the median "
            "or with no presumption, False under a presumption, empty while the result "
            "can't be worked out (DIG-226)."
        ),
    )
    outcome = EncryptedCharField(
        max_length=20,
        null=True,
        blank=True,
        help_text=(
            "at_or_below_median, cannot_work_out, no_presumption or presumption; "
            "empty until worked out after 3h1."
        ),
    )

    # Unused since 3h1; the housekeeping PR drops them.
    total_allowable_expenses = EncryptedDecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Unused since 3h1; the housekeeping PR drops it.",
    )
    disposable_income = EncryptedDecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Unused since 3h1; the housekeeping PR drops it.",
    )
    priority_debts_monthly = EncryptedDecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Unused since 3h1; the housekeeping PR drops it.",
    )
    passes_above_median = EncryptedBooleanField(
        default=False, help_text="Unused since 3h1; the housekeeping PR drops it."
    )
    above_median_calculated = EncryptedBooleanField(
        default=False, help_text="Unused since 3h1; the housekeeping PR drops it."
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
        return f"Means Test {self.id} - {self.outcome or 'not worked out yet'}"

    def calculate(self) -> str:
        """
        Calculate means test using 11 U.S.C. § 707(b) methodology.

        Returns:
            str: the outcome, one of at_or_below_median, cannot_work_out, no_presumption or
            presumption. It is Form 122A-2's arithmetic, never a verdict.

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

        # CMI is monthly; the Census median is annual, so annualize per 11 U.S.C. § 707(b)(7).
        annualized_cmi = cmi * Decimal("12")

        # The median comes first. Only above it are the 122A-2 tables read, so a filer at or
        # below the median is never refused for a lapsed 122A-2 table. Every caller has raised
        # the Income step's gaps above, before read_inputs counts the household (C-ORDER).
        details: dict = {}
        if not is_above_median(cmi, median_income_threshold):
            outcome = AT_OR_BELOW_MEDIAN
        else:
            try:
                tables, used = read_tables()
            except NoMeansTestTable as exc:
                outcome = CANNOT_WORK_OUT
                details["tables_gap"] = exc.table
            else:
                outcome = work_out(read_inputs(self.session), tables).outcome
                details["tables"] = used
        details.setdefault("tables", [])
        details.setdefault("tables_gap", None)
        passes_test = PASSES[outcome]

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
        self.outcome = outcome
        self.passes_means_test = passes_test
        self.set_calculation_details(details)

        return outcome
