"""
The Chapter 7 packet: which forms a filer needs, and what each needs first (spec §5.6, §5.7).

Each form_type maps to applies(session), which says whether the form is part
of this filer's packet and never raises, and requires(session), which raises
PreconditionMissing when data the form can't be filled without is absent.
build_field_values() is the one path from a session to a form's printed values.
FORM_REGISTRY is in filing order.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from apps.eligibility.cmi import is_above_median
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import IntakeSession

_SSN = re.compile(r"\d{3}-\d{2}-\d{4}|\d{9}")


class PreconditionMissing(Exception):
    """A form can't be filled yet; the message tells the filer what is missing.

    step is the wizard step (a WIZARD_STEPS key) where the filer fixes it, or None.
    """

    def __init__(self, message: str, step: str | None = None) -> None:
        super().__init__(message)
        self.step = step


@dataclass(frozen=True)
class PacketForm:
    applies: Callable[[IntakeSession], bool]
    requires: Callable[[IntakeSession], None]


def _always(session: IntakeSession) -> bool:
    return True


def _never(session: IntakeSession) -> bool:
    # 122A-1Supp: nothing collects a claimed exemption from the presumption yet (step 4).
    return False


def _has_fee_waiver(session: IntakeSession) -> bool:
    return hasattr(session, "fee_waiver")


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


def _needs_means_test(session: IntakeSession) -> None:
    if not hasattr(session, "means_test"):
        raise PreconditionMissing(
            "Press Complete on the Review & Results step to run the eligibility check.",
            step="review",
        )


# form_type → PacketForm. Every key must match a GeneratedForm.FORM_TYPE_CHOICES value.
FORM_REGISTRY: dict[str, PacketForm] = {
    "form_101": PacketForm(_always, _needs_debtor_info),
    "form_103b": PacketForm(_has_fee_waiver, _nothing),
    "form_106dec": PacketForm(_always, _nothing),
    "form_106sum": PacketForm(_always, _nothing),
    "form_107": PacketForm(_always, _nothing),
    "form_121": PacketForm(_always, _needs_ssn),
    "form_122a1": PacketForm(_always, _needs_means_test),
    "form_122a1_supp": PacketForm(_never, _nothing),
    "form_122a2": PacketForm(_above_median, _nothing),
    "schedule_a_b": PacketForm(_always, _nothing),
    "schedule_c": PacketForm(_always, _nothing),
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
    The values a form prints for this session, as {full name: value}.

    Raises:
        KeyError: form_type is not registered.
        PreconditionMissing: the form needs data the session lacks.
    """
    FORM_REGISTRY[form_type].requires(session)
    return resolve(load_schema(form_type), session)
