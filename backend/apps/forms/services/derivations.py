"""
Factual/clerical derivations (DERIVATIONS) and section-applicability
predicates (PREDICATES) for the fill engine.

UPL boundary: these encode ONLY facts and clerical transforms. No legal
conclusion (exemption-statute choice, debt priority, means-test verdict) may
live here — those are ``asked`` + ``legal_review`` in the schema.
"""

from __future__ import annotations

from collections.abc import Callable

from apps.intake.models import IntakeSession


def _full_name(session: IntakeSession) -> str:
    di = session.debtor_info
    return f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()


def _family_size(session: IntakeSession) -> str:
    return str(session.debtor_info.household_size)


DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
    "full_name": _full_name,
    "family_size": _family_size,
    "chapter": lambda s: "7",
    "debtor_type": lambda s: "Individual",
    "district_name": lambda s: s.district.name,
}


def _has_business(session: IntakeSession) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_business)


def _has_creditor_payments(session: IntakeSession) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_creditor_payments)


def _has_prior_income(session: IntakeSession) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_prior_income)


def _form_answer_predicate(session: IntakeSession, key: str) -> bool:
    """Check if a FormAnswer entry has a truthy value."""
    from apps.intake.models import FormAnswer

    ans = FormAnswer.objects.filter(session=session, form_type="form_107", field_key=key).first()
    return bool(ans and ans.value and ans.value.lower() in ("yes", "y", "true", "1"))


PREDICATES: dict[str, Callable[[IntakeSession], bool]] = {
    # SOFAReport-backed predicates
    "has_business": _has_business,
    "has_creditor_payments": _has_creditor_payments,
    "has_prior_income": _has_prior_income,
    # FormAnswer-backed section gates (user answered "Yes" to gate question)
    "has_insider_payments": lambda s: _form_answer_predicate(s, "insider_payments_gate"),
    "has_legal_actions": lambda s: _form_answer_predicate(s, "legal_actions_gate"),
    "has_financial_accounts": lambda s: _form_answer_predicate(s, "financial_accounts_gate"),
    "has_property_loss": lambda s: _form_answer_predicate(s, "property_loss_gate"),
    "has_property_transfers": lambda s: _form_answer_predicate(s, "property_transfers_gate"),
    "has_closed_accounts": lambda s: _form_answer_predicate(s, "closed_accounts_gate"),
    "has_safe_deposit": lambda s: _form_answer_predicate(s, "safe_deposit_gate"),
    "has_environmental": lambda s: _form_answer_predicate(s, "environmental_gate"),
    "has_prior_bankruptcy": lambda s: _form_answer_predicate(s, "prior_bankruptcy_gate"),
    "has_accountant": lambda s: _form_answer_predicate(s, "accountant_gate"),
    "has_joint_filer": lambda s: _form_answer_predicate(s, "joint_filer_gate"),
    "has_address_history": lambda s: _form_answer_predicate(s, "address_history_gate"),
    "has_attorney": lambda s: _form_answer_predicate(s, "attorney_gate"),
}
