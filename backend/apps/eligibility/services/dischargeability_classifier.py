"""Classify debts as dischargeable or non-dischargeable in Chapter 7."""

from apps.intake.models import IntakeSession

NON_DISCHARGEABLE_TYPES = {
    "student_loan": "11 U.S.C. § 523(a)(8) — requires adversary proceeding",
    "child_support": "11 U.S.C. § 523(a)(5) — domestic support obligation",
    "alimony": "11 U.S.C. § 523(a)(5) — domestic support obligation",
    "taxes": "11 U.S.C. § 523(a)(1) — certain tax debts",
    "restitution": "11 U.S.C. § 523(a)(6) — willful and malicious injury",
}


def classify_debt(debt) -> dict:
    reason = NON_DISCHARGEABLE_TYPES.get(debt.debt_type)
    return {
        "dischargeable": reason is None,
        "reason": reason or "",
        "proceeding_needed": reason is not None,
    }


class DischargeabilityClassifier:
    def __init__(self, session: IntakeSession):
        self.session = session

    def evaluate(self) -> list[dict]:
        results = []
        for debt in self.session.debts.all():
            classification = classify_debt(debt)
            results.append(
                {
                    "debt_id": debt.id,
                    "creditor": debt.creditor_name,
                    "debt_type": debt.debt_type,
                    **classification,
                }
            )
        return results
