"""
Factual/clerical derivations (DERIVATIONS) and section-applicability
predicates (PREDICATES) for the fill engine.

UPL boundary: these encode ONLY facts and clerical transforms. No legal
conclusion (exemption-statute choice, debt priority, means-test verdict) may
live here — those are ``asked`` + ``legal_review`` in the schema.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from apps.intake.models import IntakeSession


def _full_name(session: IntakeSession) -> str:
    try:
        di = session.debtor_info
    except IntakeSession.debtor_info.RelatedObjectDoesNotExist:
        return ""
    return f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()


def _family_size(session: IntakeSession) -> str:
    return str(session.debtor_info.household_size)


DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
    "full_name": _full_name,
    "family_size": _family_size,
    "first_name": lambda s: s.debtor_info.first_name,
    "middle_name": lambda s: s.debtor_info.middle_name or "",
    "last_name": lambda s: s.debtor_info.last_name,
    "ssn_last_4": lambda s: (s.debtor_info.ssn or "")[-4:],
    "street_address": lambda s: s.debtor_info.street_address,
    "city": lambda s: s.debtor_info.city,
    "state": lambda s: s.debtor_info.state,
    "zip_code": lambda s: s.debtor_info.zip_code,
    "phone": lambda s: s.debtor_info.phone or "",
    "email": lambda s: s.debtor_info.email or "",
    "chapter": lambda s: "7",
    "debtor_type": lambda s: "Individual",
    "district_name": lambda s: s.district.name,
    "today_iso": lambda s: date.today().isoformat(),
    "joint_filer_check": lambda s: (
        "true" if _form_answer_predicate(s, "joint_filer_gate") else ""
    ),
}


def _has_business(session: IntakeSession, answer_cache: dict | None = None) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_business)


def _has_creditor_payments(session: IntakeSession, answer_cache: dict | None = None) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_creditor_payments)


def _has_prior_income(session: IntakeSession, answer_cache: dict | None = None) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_prior_income)


def _form_answer_predicate(
    session: IntakeSession, key: str, answer_cache: dict | None = None
) -> bool:
    """Check if a FormAnswer entry has a truthy value.

    Form-type agnostic: looks up by session + field_key across all form types,
    so the same predicate works for both Form 107 and Form 101 schemas.
    If answer_cache is provided (from resolve()), uses it to avoid DB hits.
    """
    if answer_cache is not None:
        ans = answer_cache.get(key)
        return bool(ans and ans.value and ans.value.lower() in ("yes", "y", "true", "1"))

    from apps.intake.models import FormAnswer

    ans = FormAnswer.objects.filter(session=session, field_key=key).first()
    return bool(ans and ans.value and ans.value.lower() in ("yes", "y", "true", "1"))


PREDICATES: dict[str, Callable[[IntakeSession], bool]] = {
    # SOFAReport-backed predicates
    "has_business": _has_business,
    "has_creditor_payments": _has_creditor_payments,
    "has_prior_income": _has_prior_income,
    # FormAnswer-backed section gates (user answered "Yes" to gate question)
    "has_insider_payments": lambda s, answer_cache=None: _form_answer_predicate(
        s, "insider_payments_gate", answer_cache
    ),
    "has_legal_actions": lambda s, answer_cache=None: _form_answer_predicate(
        s, "legal_actions_gate", answer_cache
    ),
    "has_financial_accounts": lambda s, answer_cache=None: _form_answer_predicate(
        s, "financial_accounts_gate", answer_cache
    ),
    "has_property_loss": lambda s, answer_cache=None: _form_answer_predicate(
        s, "property_loss_gate", answer_cache
    ),
    "has_property_transfers": lambda s, answer_cache=None: _form_answer_predicate(
        s, "property_transfers_gate", answer_cache
    ),
    "has_closed_accounts": lambda s, answer_cache=None: _form_answer_predicate(
        s, "closed_accounts_gate", answer_cache
    ),
    "has_safe_deposit": lambda s, answer_cache=None: _form_answer_predicate(
        s, "safe_deposit_gate", answer_cache
    ),
    "has_environmental": lambda s, answer_cache=None: _form_answer_predicate(
        s, "environmental_gate", answer_cache
    ),
    "has_prior_bankruptcy": lambda s, answer_cache=None: _form_answer_predicate(
        s, "prior_bankruptcy_gate", answer_cache
    ),
    "has_accountant": lambda s, answer_cache=None: _form_answer_predicate(
        s, "accountant_gate", answer_cache
    ),
    "has_joint_filer": lambda s, answer_cache=None: _form_answer_predicate(
        s, "joint_filer_gate", answer_cache
    ),
    "has_address_history": lambda s, answer_cache=None: _form_answer_predicate(
        s, "address_history_gate", answer_cache
    ),
    "has_attorney": lambda s, answer_cache=None: _form_answer_predicate(
        s, "attorney_gate", answer_cache
    ),
}
