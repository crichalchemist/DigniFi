"""Calculate allowable expense deductions for above-median means test."""

from dataclasses import dataclass
from decimal import Decimal

from apps.eligibility.services.irs_standards import get_local_standard, get_national_standard
from apps.intake.models import IntakeSession


@dataclass
class ExpenseDeductionResult:
    national_food_allowance: Decimal
    national_health_allowance: Decimal
    local_housing_allowance: Decimal
    local_transport_allowance: Decimal
    actual_total_expenses: Decimal
    allowable_expenses: Decimal
    priority_debts_monthly: Decimal
    disposable_income: Decimal
    family_size: int


class ExpenseDeductionCalculator:
    def __init__(self, session: IntakeSession):
        self.session = session
        self.district = session.district

    def calculate(self) -> ExpenseDeductionResult:
        family_size = self._get_family_size()
        age_under_65 = self._is_under_65()

        food_std = get_national_standard("food", family_size)
        health_std = get_national_standard("health_care", family_size, age_under_65)

        housing_std = get_local_standard(self.district.code, "housing", family_size) or Decimal("0")
        transport_std = get_local_standard(self.district.code, "transport_operating") or Decimal(
            "0"
        )

        actual = self._get_actual_expenses()

        food_allowance = min(actual["food"], food_std)
        health_allowance = min(actual["health"], health_std)
        housing_allowance = min(actual["housing"], housing_std)
        transport_allowance = min(actual["transport"], transport_std)

        total_allowable = (
            food_allowance + health_allowance + housing_allowance + transport_allowance
        )

        priority = self._get_priority_debts_monthly()

        cmi = self._get_cmi()
        disposable = cmi - total_allowable - priority

        return ExpenseDeductionResult(
            national_food_allowance=food_allowance,
            national_health_allowance=health_allowance,
            local_housing_allowance=housing_allowance,
            local_transport_allowance=transport_allowance,
            actual_total_expenses=actual["total"],
            allowable_expenses=total_allowable,
            priority_debts_monthly=priority,
            disposable_income=disposable,
            family_size=family_size,
        )

    def _get_family_size(self) -> int:
        di = getattr(self.session, "debtor_info", None)
        if di and (di.household_size or 0) >= 1:
            return di.household_size
        try:
            ii = self.session.income_info
            size = ii.number_of_dependents + 1
            if ii.marital_status in ("married_joint", "married_separate"):
                size += 1
            return size
        except Exception:
            return 1

    def _is_under_65(self) -> bool:
        di = getattr(self.session, "debtor_info", None)
        if di and di.date_of_birth:
            from datetime import date

            age = (date.today() - di.date_of_birth).days // 365
            return age < 65
        return True

    def _get_actual_expenses(self) -> dict[str, Decimal]:
        zero = Decimal("0")
        try:
            ei = self.session.expense_info
            return {
                "food": Decimal(str(ei.food_and_groceries or zero)),
                "health": Decimal(str(ei.medical_expenses or zero)),
                "housing": Decimal(str(ei.rent_or_mortgage or zero)),
                "transport": Decimal(str(ei.vehicle_payment or zero)),
                "total": Decimal(str(ei.calculate_total_monthly_expenses())),
            }
        except Exception:
            return {"food": zero, "health": zero, "housing": zero, "transport": zero, "total": zero}

    def _get_priority_debts_monthly(self) -> Decimal:
        from apps.intake.models import DebtInfo

        zero = Decimal("0")
        priority = DebtInfo.objects.filter(session=self.session, is_priority=True)
        return sum((d.monthly_payment or zero for d in priority), zero)

    def _get_cmi(self) -> Decimal:
        try:
            ii = self.session.income_info
            total = sum(Decimal(str(v)) for v in (ii.monthly_income or []))
            return total / Decimal("6") if total else Decimal("0")
        except Exception:
            return Decimal("0")
