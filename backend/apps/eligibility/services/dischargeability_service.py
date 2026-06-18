"""Evaluate dischargeability and create adversary proceedings."""

from apps.eligibility.services.dischargeability_classifier import classify_debt
from apps.intake.models import AdversaryProceeding, IntakeSession


class DischargeabilityService:
    def __init__(self, session: IntakeSession):
        self.session = session

    def evaluate(self) -> list[dict]:
        results = []
        for debt in self.session.debts.all():
            classification = classify_debt(debt)
            debt.is_dischargeable = classification["dischargeable"]
            debt.adversary_proceeding_needed = classification["proceeding_needed"]
            debt.save(update_fields=["is_dischargeable", "adversary_proceeding_needed"])

            if classification["proceeding_needed"]:
                self._ensure_proceeding(debt, classification)

            results.append(
                {
                    "debt_id": debt.id,
                    "creditor": debt.creditor_name,
                    "debt_type": debt.debt_type,
                    **classification,
                }
            )
        return results

    def _ensure_proceeding(self, debt, classification):
        proceeding_type = "student_loan" if debt.debt_type == "student_loan" else "other"
        AdversaryProceeding.objects.get_or_create(
            session=self.session,
            debt=debt,
            defaults={
                "proceeding_type": proceeding_type,
                "lender_name": debt.creditor_name,
                "loan_amount": debt.amount_owed,
            },
        )
