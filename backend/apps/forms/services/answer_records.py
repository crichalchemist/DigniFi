"""
The answers records the step 4 namespaces read (spec §7, §14.2).

`petition.`, `schedule_i.` and `affairs.` each name a key of one record's
`get_answers()`. Forms step 4a registers the namespaces with nothing bound and no record
behind them, so a session without the record reads blank (a scalar) or empty (a row list):
never 0.00 and never a default, since blank means the filer has not answered.
"""

import re
from datetime import datetime

ANSWER_NAMESPACES = ("petition.", "schedule_i.", "affairs.")

# The session's related name for each record. `affairs.` is by line: Form 107's lines 1 to 12
# are the financial affairs record's, 13 to 28 the property affairs record's (§7.4).
RECORD_OF_NAMESPACE = {
    "petition.": "petition_answers",
    "schedule_i.": "schedule_i_answers",
}

# A step the wizard doesn't have yet; each leaves this tuple when its PR adds the step to
# frontend/src/constants/wizardSteps.ts.
NEW_STEP_KEYS = ("last_few_years_1", "last_few_years_2")

# No leading zero: `l05_` is not how §7.4 spells line 5.
_AFFAIRS_LINE = re.compile(r"l([1-9]\d*)_")

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

# Form 101A's landlord block (4b2-R2): the one pair of answers that puts the form in the packet
# is a rent Yes and an eviction Yes, never the eviction answer alone (a rent No keeps a stale one).
LANDLORD_KEYS = (
    "landlord_name",
    "landlord_street",
    "landlord_city",
    "landlord_state",
    "landlord_zip",
)


def evicted_renter(answers: dict) -> bool:
    return answers.get("rents_residence") == "yes" and answers.get("eviction_judgment") == "yes"


def landlord_missing(answers: dict) -> bool:
    """True only under the pair, when any landlord key is not a non-blank string."""
    if not evicted_renter(answers):
        return False
    return any(
        not (isinstance(answers.get(key), str) and answers[key].strip()) for key in LANDLORD_KEYS
    )


def is_nine_digits(value) -> bool:
    # 0-9 only: \d would also count other scripts' digits, which the forms' font can't print
    return isinstance(value, str) and len(re.sub(r"[^0-9]", "", value)) == 9


def is_itin(value) -> bool:
    """An ITIN is nine digits whose first digit is 9 (PF2-U2)."""
    return is_nine_digits(value) and re.sub(r"[^0-9]", "", value)[0] == "9"


def is_mm_dd_yyyy(value) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        return False
    try:
        datetime.strptime(value, "%m/%d/%Y")
    except ValueError:
        return False
    return True


# The petition record's row lists whose `filed_on` prints only as a real MM/DD/YYYY date (PF2-2).
_DATED_ROW_LISTS = ("prior_cases", "pending_cases")
# The petition record's dates that print only as a real MM/DD/YYYY date (4d-R9).
_DATED_KEYS = ("duty_released_on", "duty_ended_on")


def _unrecognized(binding: str) -> ValueError:
    return ValueError(f"unrecognized binding: {binding!r}")


def _namespace(binding: str) -> str:
    """The answer namespace a binding starts with; a binding outside the three is unrecognized."""
    for prefix in ANSWER_NAMESPACES:
        if binding.startswith(prefix):
            return prefix
    raise _unrecognized(binding)


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
    namespace = _namespace(binding)
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
        value = _text(answers.get(key))
        if namespace == "petition." and key in _DATED_KEYS and value.strip():
            # A date the form can't read prints blank; the stored value stays as typed.
            return value if is_mm_dd_yyyy(value) else ""
        return value
    rows = answers.get(key)
    if not isinstance(rows, list):
        return []
    cells = [_text(row.get(attr)) if isinstance(row, dict) else "" for row in rows]
    if namespace == "petition." and key in _DATED_ROW_LISTS and attr == "filed_on":
        # A date the form can't read prints blank; the stored value stays as typed.
        cells = [c if not c.strip() or is_mm_dd_yyyy(c) else "" for c in cells]
    return cells


def record_step(binding: str) -> str:
    """The wizard step that asks a binding's key (a WIZARD_STEPS key or one of NEW_STEP_KEYS)."""
    namespace = _namespace(binding)
    key = binding[len(namespace) :].partition("[].")[0]
    if namespace == "petition.":
        step = PETITION_STEP_OF_KEY.get(key)
        if step is None:
            raise _unrecognized(binding)
        return step
    if namespace == "schedule_i.":
        return "expense_info" if key.startswith("schedule_j_") else "income_info"
    return "last_few_years_1" if _affairs_line(binding) <= 12 else "last_few_years_2"
