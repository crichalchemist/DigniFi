"""Evaluate dischargeability and create adversary proceedings."""

from apps.eligibility.services.dischargeability_classifier import classify_debt
from apps.intake.models import AdversaryProceeding, IntakeSession


class DischargeabilityService:
    def __init__(self, session: IntakeSession):
        self.session = session

    def evaluate(self) -> list[dict]:
        results = []
        debts_to_update = []
        for debt in self.session.debts.all():
            classification = classify_debt(debt)

            # Update fields but don't save immediately
            if (
                debt.is_dischargeable != classification["dischargeable"]
                or debt.adversary_proceeding_needed != classification["proceeding_needed"]
            ):
                debt.is_dischargeable = classification["dischargeable"]
                debt.adversary_proceeding_needed = classification["proceeding_needed"]
                debts_to_update.append(debt)

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

        if debts_to_update:
            from apps.intake.models import DebtInfo

            DebtInfo.objects.bulk_update(
                debts_to_update, ["is_dischargeable", "adversary_proceeding_needed"]
            )

        return results

    def _ensure_proceeding(self, debt, classification):
        # Only creates for student loans as per classification
        AdversaryProceeding.objects.get_or_create(
            session=self.session,
            debt=debt,
            defaults={
                "proceeding_type": "student_loan",
                "lender_name": debt.creditor_name,
                "loan_amount": debt.amount_owed,
            },
        )
