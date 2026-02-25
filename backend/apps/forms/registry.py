"""
Registry mapping form types to their generator classes.

Provides a single dispatch point so the view layer can resolve any
form_type string to the correct generator without hardcoded if/elif chains.
"""

from typing import Any

from apps.intake.models import IntakeSession

from .services import (
    Form101Generator,
    Form103BGenerator,
    Form106DecGenerator,
    Form106SumGenerator,
    Form107Generator,
    Form121Generator,
    Form122A1Generator,
    ScheduleABGenerator,
    ScheduleCGenerator,
    ScheduleDGenerator,
    ScheduleEFGenerator,
    ScheduleIGenerator,
    ScheduleJGenerator,
)


# form_type string → generator class
# Every key must match a GeneratedForm.FORM_TYPE_CHOICES value.
FORM_REGISTRY: dict[str, type] = {
    "form_101": Form101Generator,
    "form_103b": Form103BGenerator,
    "form_106dec": Form106DecGenerator,
    "form_106sum": Form106SumGenerator,
    "form_107": Form107Generator,
    "form_121": Form121Generator,
    "form_122a1": Form122A1Generator,
    "schedule_a_b": ScheduleABGenerator,
    "schedule_c": ScheduleCGenerator,
    "schedule_d": ScheduleDGenerator,
    "schedule_e_f": ScheduleEFGenerator,
    "schedule_i": ScheduleIGenerator,
    "schedule_j": ScheduleJGenerator,
}


def get_generator(form_type: str, session: IntakeSession) -> Any:
    """
    Instantiate the generator for a given form type.

    Raises KeyError if form_type is not in the registry.
    Raises ValueError if the generator rejects the session data.
    """
    generator_cls = FORM_REGISTRY[form_type]
    return generator_cls(session)


def get_all_form_types() -> list[str]:
    """Return all registered form type keys in filing order."""
    return list(FORM_REGISTRY.keys())
