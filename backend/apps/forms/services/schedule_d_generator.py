"""
Schedule D (Creditors Who Hold Claims Secured by Property) Generator Service.

Generates Official Bankruptcy Form 106D: Creditors Who Hold Claims
Secured by Property.

Schedule D lists all creditors with claims secured by collateral
(mortgages, car loans, judgment liens). Each entry includes the
creditor, collateral description, and claim status flags
(contingent, unliquidated, disputed).

Official form: b_106d (part of the 106 series).
"""

from decimal import Decimal
from functools import reduce
from typing import Any

from apps.intake.models import DebtInfo, IntakeSession


def _format_date(debt: DebtInfo) -> str:
    """Format date_incurred as ISO string, empty when absent."""
    return debt.date_incurred.isoformat() if debt.date_incurred else ""


def _debt_to_entry(debt: DebtInfo) -> dict[str, Any]:
    """Transform a single secured DebtInfo into a Schedule D entry."""
    return {
        "creditor_name": debt.creditor_name,
        "creditor_address": "",  # DebtInfo model lacks address field; placeholder for future
        "account_number": debt.account_number or "",
        "collateral_description": debt.collateral_description or "",
        "amount_owed": debt.amount_owed,
        "date_incurred": _format_date(debt),
        "contingent": debt.is_contingent,
        "unliquidated": debt.is_unliquidated,
        "disputed": debt.is_disputed,
    }


def _sum_amounts(acc: Decimal, entry: dict[str, Any]) -> Decimal:
    """Accumulate amount_owed across entries."""
    return acc + entry["amount_owed"]


class ScheduleDGenerator:
    """
    Generate Schedule D (Creditors Who Hold Claims Secured by Property).

    Filters session debts to only secured claims (is_secured=True),
    ordered alphabetically by creditor name. Computes total secured
    claims using functools.reduce over encrypted decimal fields.

    Official form: b_106d
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> dict[str, Any]:
        """
        Build Schedule D data from secured debts on this session.

        Returns dict with secured_creditors list, total_secured_claims,
        and number_of_secured_claims suitable for PDF field population.
        """
        secured_debts = list(self.session.debts.filter(is_secured=True).order_by("creditor_name"))

        secured_creditors = [_debt_to_entry(debt) for debt in secured_debts]

        total_secured_claims = reduce(
            _sum_amounts,
            secured_creditors,
            Decimal("0.00"),
        )

        return {
            "secured_creditors": secured_creditors,
            "total_secured_claims": total_secured_claims,
            "number_of_secured_claims": len(secured_creditors),
        }

    def preview(self) -> dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()

    def pdf_field_map(self) -> dict:
        """Map session data to Official Form 106D (form_b106d.pdf)."""
        from decimal import ROUND_HALF_UP, Decimal

        TWO = Decimal("0.01")
        ZERO = Decimal("0.00")

        def fmt(d):
            return str((d or ZERO).quantize(TWO, rounding=ROUND_HALF_UP))

        session = self.session
        di = session.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()
        secured_debts = list(DebtInfo.objects.filter(session=session, is_secured=True))

        result: dict = {
            "Bankruptcy District Information": session.district.name,
            "Debtor 1": full_name,
        }

        for i, debt in enumerate(secured_debts[:6], start=1):
            base = str(i)
            result[base] = debt.creditor_name or ""
            result[f"{base}_2"] = ""
            result[f"{base}_3"] = debt.collateral_description or ""
            result[f"{base}_4"] = ""
            result[f"{base}_5"] = fmt(debt.amount_owed)

        total = sum((d.amount_owed or ZERO) for d in secured_debts)
        result["undefined_44"] = fmt(total)

        return result
