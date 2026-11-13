"""
The Chapter 7 packet: which forms a filer needs, and what each needs first (spec §5.6, §5.7).

Each form_type maps to applies(session), which says whether the form is part
of this filer's packet and never raises, and requires(session), which raises
PreconditionMissing when data the form can't be filled without is absent.
Form 101 and 103B also need the filer's answers on the filing-fee page (forms step 3f
spec §7): line 8, and for a waiver 103B lines 4, 5, 7 and 9.
build_parts() is the path the views take from a session to a form's printed values: the
parts document they check, store and draw. build_field_values() returns the form's
{key: value}.
FORM_REGISTRY is in filing order.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from apps.districts.exemptions import exemption_catalog_in_force
from apps.eligibility.cmi import is_above_median
from apps.forms.schema import load_schema
from apps.forms.services.exemption_items import exemption_items
from apps.forms.services.fill_resolver import resolve, resolve_parts
from apps.intake.exemptions import exemption_gaps
from apps.intake.models import IntakeSession

_SSN = re.compile(r"\d{3}-\d{2}-\d{4}|\d{9}")


class PreconditionMissing(Exception):
    """A form can't be filled yet; the message tells the filer what is missing.

    step is the wizard step (a WIZARD_STEPS key) where the filer fixes it, or None.
    page is the route (such as /filing-fee) where the filer fixes it, or None.
    Exactly one of step and page is set.
    """

    def __init__(self, message: str, step: str | None = None, page: str | None = None) -> None:
        super().__init__(message)
        self.step = step
        self.page = page


@dataclass(frozen=True)
class PacketForm:
    applies: Callable[[IntakeSession], bool]
    requires: Callable[[IntakeSession], None]


def _always(session: IntakeSession) -> bool:
    return True


def _never(session: IntakeSession) -> bool:
    # 122A-1Supp: nothing collects a claimed exemption from the presumption yet (step 4).
    return False


def payment_choice(session: IntakeSession) -> str | None:
    """The filer's Form 101 line 8 answer, or None before they choose. Never raises."""
    fee = getattr(session, "filing_fee", None)
    return fee.payment_choice if fee is not None else None


def _asks_fee_waiver(session: IntakeSession) -> bool:
    return payment_choice(session) == "waiver"


def _above_median(session: IntakeSession) -> bool:
    """
    Annualized income above the median, from the stored MeansTest, by the means test's own
    comparison: income exactly at the median counts as below it (DIG-136).

    Not above_median_calculated: a row calculated before DIG-128 was fixed can still carry it.
    """
    means_test = getattr(session, "means_test", None)
    if means_test is None:
        return False
    return is_above_median(means_test.calculated_cmi, means_test.median_income_threshold)


def _nothing(session: IntakeSession) -> None:
    return None


def _needs_debtor_info(session: IntakeSession) -> None:
    if not hasattr(session, "debtor_info"):
        raise PreconditionMissing(
            "Enter your name and address on the Your Information step.", step="debtor_info"
        )


def _needs_ssn(session: IntakeSession) -> None:
    _needs_debtor_info(session)
    if not _SSN.fullmatch((session.debtor_info.ssn or "").strip()):
        raise PreconditionMissing(
            "Enter your 9-digit Social Security number on the Your Information step.",
            step="debtor_info",
        )


def _needs_county(session: IntakeSession) -> None:
    # Step 1 stores it on the household (3e1 spec §6); a session saved before 3e1 has none.
    household = getattr(session, "household", None)
    if household is None or not household.county:
        raise PreconditionMissing(
            "Choose your county on the Your Information step.", step="debtor_info"
        )


def _needs_fee_choice(session: IntakeSession) -> None:
    if payment_choice(session) is None:
        raise PreconditionMissing("Choose how you will pay the filing fee.", page="/filing-fee")


def _needs_debtor_info_county_and_fee_choice(session: IntakeSession) -> None:
    _needs_debtor_info(session)
    _needs_county(session)
    _needs_fee_choice(session)


def _needs_fee_waiver_answers(session: IntakeSession) -> None:
    """103B lines 4, 5, 7 and 9, checked in the form's order; the first gap is refused."""
    fee = getattr(session, "filing_fee", None)  # with none, every answer is unanswered

    def answer(name: str) -> str | None:
        return getattr(fee, name) if fee is not None else None

    def blank(text: str | None) -> bool:
        return not (text or "").strip()

    if answer("income_change_answer") is None:
        raise PreconditionMissing(
            "Answer whether you expect your family's income to go up or down by more than 10%"
            " in the next 6 months.",
            page="/filing-fee",
        )
    if answer("income_change_answer") == "yes" and blank(answer("income_change_explanation")):
        raise PreconditionMissing(
            "Explain how you expect your family's income to change.", page="/filing-fee"
        )
    if blank(answer("installments_explanation")):
        raise PreconditionMissing(
            "Tell the court why you can't pay the filing fee in installments.", page="/filing-fee"
        )
    if answer("others_covered_answer") is None:
        raise PreconditionMissing(
            "Answer whether your expenses cover anyone not counted in your family.",
            page="/filing-fee",
        )
    if answer("others_covered_answer") == "yes" and blank(answer("others_covered_who")):
        raise PreconditionMissing("Say who else your expenses cover.", page="/filing-fee")
    if answer("expense_change_answer") is None:
        raise PreconditionMissing(
            "Answer whether you expect your expenses to go up or down by more than 10% in the"
            " next 6 months.",
            page="/filing-fee",
        )
    if answer("expense_change_answer") == "yes" and blank(answer("expense_change_explanation")):
        raise PreconditionMissing(
            "Explain how you expect your expenses to change.", page="/filing-fee"
        )


def _needs_exemption_answers(session: IntakeSession) -> None:
    """Schedule C's page: line 1, the claims, line 3 and 3-1; the first gap is refused.

    The list of laws is read only when a claim names one, so a filer who claims nothing is
    never stopped by a missing list (P5).
    """
    claims = list(session.exemption_claims.all())
    law_keys = set()
    if any(claim.law is not None for claim in claims):
        law_keys = {law.key for law in exemption_catalog_in_force().laws.all()}
    gaps = exemption_gaps(session, exemption_items(session), law_keys)
    if gaps:
        raise PreconditionMissing(gaps[0], page="/exemptions")


def _needs_means_test(session: IntakeSession) -> None:
    if not hasattr(session, "means_test"):
        raise PreconditionMissing(
            "Press Complete on the Review & Results step to run the eligibility check.",
            step="review",
        )


# form_type → PacketForm. Every key must match a GeneratedForm.FORM_TYPE_CHOICES value.
FORM_REGISTRY: dict[str, PacketForm] = {
    "form_101": PacketForm(_always, _needs_debtor_info_county_and_fee_choice),
    "form_103b": PacketForm(_asks_fee_waiver, _needs_fee_waiver_answers),
    "form_106dec": PacketForm(_always, _nothing),
    "form_106sum": PacketForm(_always, _nothing),
    "form_107": PacketForm(_always, _nothing),
    "form_121": PacketForm(_always, _needs_ssn),
    "list_of_creditors": PacketForm(_always, _nothing),
    "form_122a1": PacketForm(_always, _needs_means_test),
    "form_122a1_supp": PacketForm(_never, _nothing),
    "form_122a2": PacketForm(_above_median, _nothing),
    "schedule_a_b": PacketForm(_always, _nothing),
    "schedule_c": PacketForm(_always, _needs_exemption_answers),
    "schedule_d": PacketForm(_always, _nothing),
    "schedule_e_f": PacketForm(_always, _nothing),
    "schedule_g": PacketForm(_always, _nothing),
    "schedule_h": PacketForm(_always, _nothing),
    "schedule_i": PacketForm(_always, _nothing),
    "schedule_j": PacketForm(_always, _nothing),
}


def get_all_form_types() -> list[str]:
    """Return all registered form type keys in filing order."""
    return list(FORM_REGISTRY.keys())


def packet(session: IntakeSession) -> list[str]:
    """The form types this filer's packet holds, in filing order."""
    return [form_type for form_type, form in FORM_REGISTRY.items() if form.applies(session)]


def build_field_values(form_type: str, session: IntakeSession) -> dict[str, str]:
    """
    The values the form's own pages print for this session (build_parts' form part), as
    {key: value}, a key being a full name or "<full name>@<page>:<tag>". Rows past a
    group's last slot print on copies or an attached sheet, which only build_parts returns.

    Raises:
        KeyError: form_type is not registered.
        PreconditionMissing: the form needs data the session lacks.
    """
    FORM_REGISTRY[form_type].requires(session)
    return resolve(load_schema(form_type), session)


def build_parts(form_type: str, session: IntakeSession) -> dict:
    """
    The parts a form prints for this session, as GeneratedForm.field_values stores them:
    {"version": 2, "parts": [...]} (spec §6).

    Raises:
        KeyError: form_type is not registered.
        PreconditionMissing: the form needs data the session lacks.
    """
    FORM_REGISTRY[form_type].requires(session)
    return resolve_parts(load_schema(form_type), session)
