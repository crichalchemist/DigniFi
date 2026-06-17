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


PREDICATES: dict[str, Callable[[IntakeSession], bool]] = {
    "has_business": _has_business,
    "has_creditor_payments": _has_creditor_payments,
    "has_prior_income": _has_prior_income,
}
