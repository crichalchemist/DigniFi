"""
A radio or choice box bound to a petition answer prints only answers the filer can have
(PF2-12 (a), DIG-522 item 12).

Business intent: `_emit` raises UnmappedChoice (a 422) for a stored answer the box's
`choices` don't name, so a filer whose answer the box can't print is stuck at Generate.
`PetitionAnswers.RADIO_KEYS` is the save's guard against that, and it defends only the
keys that are in it. This walks every schema, so a new radio can't be bound without its
key being a {no, yes} (or listed-choice) answer in RADIO_KEYS.
"""

from apps.forms.registry import FORM_REGISTRY
from apps.forms.schema import load_schema
from apps.intake.models import PetitionAnswers

PREFIX = "petition."


def _radio_bindings():
    """(form_type, pdf_field, key, choices) of every non-single-box petition binding."""
    found = []
    for form_type in FORM_REGISTRY:
        for field in load_schema(form_type).fields:
            binding = field.binding or ""
            if not binding.startswith(PREFIX) or "[" in binding:
                continue
            if field.type not in ("radio", "checkbox", "choice"):
                continue
            choices = field.choices or {}
            if set(choices) == {"true"}:
                continue  # a single box
            found.append((form_type, field.pdf_field, binding[len(PREFIX) :], choices))
    return found


def test_each_bound_radio_prints_every_answer_its_key_can_hold():
    found = _radio_bindings()
    assert found, "no petition radio is bound: the walk reads nothing"
    for form_type, pdf_field, key, choices in found:
        where = f"{form_type} {pdf_field!r} ({key})"
        if key in PetitionAnswers.YES_NO_KEYS:
            assert set(choices) == {"no", "yes"}, where
        else:
            assert key in PetitionAnswers.CHOICE_KEYS, f"{where} is neither a yes/no nor a choice"
            assert set(choices) == set(PetitionAnswers.CHOICE_KEYS[key]), where


def test_the_save_guards_exactly_the_keys_a_radio_prints():
    keys = {key for _form, _field, key, _choices in _radio_bindings()}
    assert keys == set(PetitionAnswers.RADIO_KEYS)
