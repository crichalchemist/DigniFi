"""
The answers records the step 4 namespaces read (spec §7, §14.2).

`petition.`, `schedule_i.`, `intentions.` and `affairs.` each name a key of one record's
`get_answers()`. Forms step 4a registers the namespaces with nothing bound and no record
behind them, so a session without the record reads blank (a scalar) or empty (a row list):
never 0.00 and never a default, since blank means the filer has not answered.
"""

import re

ANSWER_NAMESPACES = ("petition.", "schedule_i.", "intentions.", "affairs.")

# The session's related name for each record. `affairs.` is by line: Form 107's lines 1 to 12
# are the financial affairs record's, 13 to 28 the property affairs record's (§7.4).
RECORD_OF_NAMESPACE = {
    "petition.": "petition_answers",
    "schedule_i.": "schedule_i_answers",
    "intentions.": "intention_answers",
}

# A step the wizard doesn't have yet; each leaves this tuple when its PR adds the step to
# frontend/src/constants/wizardSteps.ts.
NEW_STEP_KEYS = ("plans", "last_few_years_1", "last_few_years_2")

_AFFAIRS_LINE = re.compile(r"l(\d+)_")

# Every key of PetitionAnswers (§7.1) with the wizard step that asks it.
PETITION_STEP_OF_KEY = {
    **dict.fromkeys(
        (
            "name_suffix",
            "other_names_answer",
            "itin_answer",
            "itin",
            "other_ssn_answer",
            "other_ssn",
            "ein",
            "mailing_answer",
            "mailing_street",
            "mailing_po_box",
            "mailing_city",
            "mailing_state",
            "mailing_zip",
            "venue_choice",
            "venue_reason",
            "prior_bankruptcy_answer",
            "pending_case_answer",
            "sole_proprietor_answer",
            "business_name",
            "business_street",
            "business_city",
            "business_state",
            "business_zip",
            "business_kind",
            "other_names",
            "other_business_names",
            "prior_cases",
            "pending_cases",
        ),
        "debtor_info",
    ),
    **dict.fromkeys(
        (
            "hazard_answer",
            "hazard_what",
            "hazard_why",
            "hazard_street",
            "hazard_city",
            "hazard_state",
            "hazard_zip",
        ),
        "assets",
    ),
    **dict.fromkeys(
        (
            "debt_nature",
            "debt_nature_text",
            "disabled_veteran",
            "debts_on_duty",
            "reservist",
            "called_to_duty",
            "duty_category",
            "duty_released_on",
            "duty_ended_on",
        ),
        "debts",
    ),
    **dict.fromkeys(
        (
            "rents_residence",
            "eviction_judgment",
            "landlord_name",
            "landlord_street",
            "landlord_city",
            "landlord_state",
            "landlord_zip",
        ),
        "contracts",
    ),
    **dict.fromkeys(
        (
            "credit_counseling",
            "exigent_text",
            "not_required_reason",
            "aware_consequences",
            "aware_fraud",
            "paid_preparer",
            "preparer_name",
        ),
        "review",
    ),
}


def _unrecognized(binding: str) -> ValueError:
    return ValueError(f"unrecognized binding: {binding!r}")


def _affairs_line(binding: str) -> int:
    """The Form 107 line an `affairs.` key names by its `l<n>_` prefix, 1 to 28."""
    match = _AFFAIRS_LINE.match(binding[len("affairs.") :])
    if match is None or not 1 <= int(match[1]) <= 28:
        raise _unrecognized(binding)
    return int(match[1])


def _text(value) -> str:
    """A stored value as text: null and structure are blank, a typed 0 or False is not."""
    return "" if value is None or isinstance(value, dict | list) else str(value)


def record_value(session, binding: str) -> str | list[str]:
    """
    The value of an answers record's key: "<namespace>.<key>" is a str, "<namespace>.<key>[].<attr>"
    a list of str over a row list. Blank or [] when the session has no such record.
    """
    namespace = next(prefix for prefix in ANSWER_NAMESPACES if binding.startswith(prefix))
    key, is_list, attr = binding[len(namespace) :].partition("[].")
    if namespace == "affairs.":
        line = _affairs_line(binding)
        related = "financial_affairs" if line <= 12 else "property_affairs"
    else:
        related = RECORD_OF_NAMESPACE[namespace]
    record = getattr(session, related, None)
    if record is None:
        return [] if is_list else ""
    answers = record.get_answers()
    if not is_list:
        return _text(answers.get(key))
    rows = answers.get(key)
    if not isinstance(rows, list):
        return []
    return [_text(row.get(attr)) if isinstance(row, dict) else "" for row in rows]


def record_step(binding: str) -> str:
    """The wizard step that asks a binding's key (a WIZARD_STEPS key or one of NEW_STEP_KEYS)."""
    namespace = next(prefix for prefix in ANSWER_NAMESPACES if binding.startswith(prefix))
    key = binding[len(namespace) :].partition("[].")[0]
    if namespace == "petition.":
        step = PETITION_STEP_OF_KEY.get(key)
        if step is None:
            raise _unrecognized(binding)
        return step
    if namespace == "schedule_i.":
        return "expense_info" if key.startswith("schedule_j_") else "income_info"
    if namespace == "intentions.":
        return "plans"
    return "last_few_years_1" if _affairs_line(binding) <= 12 else "last_few_years_2"
