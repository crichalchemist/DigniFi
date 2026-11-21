"""What Form 101's questions still lack from the filer (forms step 4b spec §7.1).

Pure reading: the gaps come from the session's `PetitionAnswers` record, never from a form's
preconditions. The sentences are DigniFi's own; `petitionGaps.ts` copies them and
`test_petition_frontend_copy.py` pins the copy.
"""

import re
from datetime import datetime

from apps.forms.services.answer_records import PETITION_STEP_OF_KEY

from .completion import Gap
from .models import PetitionAnswers

STEP_1_GATES = (
    "other_names_answer",
    "itin_answer",
    "other_ssn_answer",
    "mailing_answer",
    "prior_bankruptcy_answer",
    "pending_case_answer",
    "sole_proprietor_answer",
)

GATE_OTHER_NAMES = "Say whether you have used another name in the last 8 years."
GATE_ITIN = "Say whether you have an ITIN."
GATE_OTHER_SSN = "Say whether you have used another Social Security number."
GATE_MAILING = "Say whether your mailing address is different from where you live."
GATE_PRIOR_BANKRUPTCY = "Say whether you have filed for bankruptcy in the last 8 years."
GATE_PENDING_CASE = "Say whether a spouse, partner or affiliate has a bankruptcy case pending."
GATE_SOLE_PROPRIETOR = "Say whether you are a sole proprietor of a business."
GATE_HAZARD = "Say whether you own property that poses a hazard or needs immediate attention."
GATE_RENTS = "Say whether you rent your residence."
GATE_EVICTION = "Say whether your landlord has an eviction judgment against you."
DETAIL_VENUE = "Choose why you are filing in this district."
DETAIL_VENUE_REASON = "Explain your other reason for filing here, or choose the first answer."
DETAIL_OTHER_NAMES = "Add the other name you used, or change your answer to No."
DETAIL_ITIN = "Type your 9-digit ITIN, or change your answer to No."
DETAIL_OTHER_SSN = "Type the other 9-digit Social Security number, or change your answer to No."
DETAIL_EIN = "Your EIN has 9 digits. Check what you typed."
DETAIL_MAILING = "Add your mailing address, or change your answer to No."
DETAIL_PRIOR_CASE = "Each earlier case needs its district and the date it was filed."
DETAIL_PRIOR_DATE = "A date is written as MM/DD/YYYY. Check the date of your earlier case."
DETAIL_PENDING_CASE = "Each pending case needs the name of the person who filed it."
DETAIL_BUSINESS = "Add your business's name, or change your answer to No."
DETAIL_HAZARD = "Say what the hazard is, or change your answer to No."
# The one template: {label} is the box's index label in plain words (TEXT_LABELS).
DETAIL_TOO_LONG = "Your answer for {label} is too long for its box on Form 101."

_GATE_SENTENCE = {
    "other_names_answer": GATE_OTHER_NAMES,
    "itin_answer": GATE_ITIN,
    "other_ssn_answer": GATE_OTHER_SSN,
    "mailing_answer": GATE_MAILING,
    "prior_bankruptcy_answer": GATE_PRIOR_BANKRUPTCY,
    "pending_case_answer": GATE_PENDING_CASE,
    "sole_proprietor_answer": GATE_SOLE_PROPRIETOR,
}

# Every key a detail can name, to the forms that print its box blank while it is open (4b-R12):
# Form 101 prints each, and Form 121 prints the ITIN and the other Social Security number too.
FORMS_OF_KEY: dict[str, tuple[str, ...]] = {key: ("form_101",) for key in PetitionAnswers.KEYS}
FORMS_OF_KEY.update({key: ("form_101", "form_121") for key in PetitionAnswers.SECRET_KEYS})

_HAZARD_KEYS = ("hazard_what", "hazard_why", "hazard_street", "hazard_city", "hazard_state")
_MAILING_KEYS = (
    "mailing_street",
    "mailing_po_box",
    "mailing_city",
    "mailing_state",
    "mailing_zip",
)


def is_nine_digits(value) -> bool:
    return isinstance(value, str) and len(re.sub(r"\D", "", value)) == 9


def is_mm_dd_yyyy(value) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        return False
    try:
        datetime.strptime(value, "%m/%d/%Y")
    except ValueError:
        return False
    return True


def _blank(value) -> bool:
    return not isinstance(value, str) or not value.strip()


def _detail(sentence: str, step: str, key: str) -> Gap:
    return Gap(sentence, step, Gap.DETAIL, forms=FORMS_OF_KEY[key])


def _has_a_row(answers: dict, key: str) -> bool:
    rows = answers.get(key) or []
    return any(not _blank(cell) for row in rows for cell in row.values())


def _bad_date(row: dict) -> bool:
    return not _blank(row.get("filed_on")) and not is_mm_dd_yyyy(row["filed_on"])


def _debtor_info_details(answers: dict) -> list[Gap]:
    step = "debtor_info"
    gaps = []
    venue = answers.get("venue_choice")
    if venue is None:
        gaps.append(_detail(DETAIL_VENUE, step, "venue_choice"))
    elif venue == "other" and _blank(answers.get("venue_reason")):
        gaps.append(_detail(DETAIL_VENUE_REASON, step, "venue_reason"))

    # Line 2 asks for both lists under the one Yes, so either list answers it.
    if (
        answers.get("other_names_answer") == "yes"
        and not _has_a_row(answers, "other_names")
        and not _has_a_row(answers, "other_business_names")
    ):
        gaps.append(_detail(DETAIL_OTHER_NAMES, step, "other_names"))
    if answers.get("itin_answer") == "yes" and not is_nine_digits(answers.get("itin")):
        gaps.append(_detail(DETAIL_ITIN, step, "itin"))
    if answers.get("other_ssn_answer") == "yes" and not is_nine_digits(answers.get("other_ssn")):
        gaps.append(_detail(DETAIL_OTHER_SSN, step, "other_ssn"))
    if answers.get("mailing_answer") == "yes" and all(
        _blank(answers.get(key)) for key in _MAILING_KEYS
    ):
        gaps.append(_detail(DETAIL_MAILING, step, "mailing_street"))
    if answers.get("sole_proprietor_answer") == "yes" and _blank(answers.get("business_name")):
        gaps.append(_detail(DETAIL_BUSINESS, step, "business_name"))
    ein = answers.get("ein")
    if not _blank(ein) and not is_nine_digits(ein):
        gaps.append(_detail(DETAIL_EIN, step, "ein"))

    if answers.get("prior_bankruptcy_answer") == "yes":
        rows = answers.get("prior_cases") or []
        if not _has_a_row(answers, "prior_cases") or any(
            _blank(row.get("district")) or _blank(row.get("filed_on")) for row in rows
        ):
            gaps.append(_detail(DETAIL_PRIOR_CASE, step, "prior_cases"))
        if any(_bad_date(row) for row in rows):
            gaps.append(_detail(DETAIL_PRIOR_DATE, step, "prior_cases"))
    if answers.get("pending_case_answer") == "yes":
        rows = answers.get("pending_cases") or []
        if not _has_a_row(answers, "pending_cases") or any(
            _blank(row.get("debtor")) for row in rows
        ):
            gaps.append(_detail(DETAIL_PENDING_CASE, step, "pending_cases"))
    return gaps


def _too_long(answers: dict, step: str, keys: list[str]) -> list[Gap]:
    """A detail for each of `keys` whose text is over its box's cap, naming the box."""
    gaps = []
    for key in keys:
        limit = PetitionAnswers.TEXT_LIMITS.get(key)
        value = answers.get(key)
        if limit is not None and isinstance(value, str) and len(value) > limit:
            label = PetitionAnswers.TEXT_LABELS.get(key, key.replace("_", " "))
            gaps.append(_detail(DETAIL_TOO_LONG.format(label=label), step, key))
    return gaps


def petition_step_gaps(session) -> list[Gap]:
    """Every question of Form 101 still open on steps 1, 5 and 7, in step order.

    A session with no record has every key unanswered. Nothing for 4d's or 4i's keys, and no
    `landlord_*` detail (4b2's).
    """
    record = getattr(session, "petition_answers", None)
    answers = record.get_answers() if record else {}
    # Only the keys steps 1 and 5 ask in 4b; 4d's, 4i's and the landlord's are other steps'.
    limited = list(PetitionAnswers.TEXT_LIMITS)
    step_1_keys = [k for k in limited if PETITION_STEP_OF_KEY.get(k) == "debtor_info"]
    hazard_keys = [k for k in limited if PETITION_STEP_OF_KEY.get(k) == "assets"]

    gaps = [
        Gap(_GATE_SENTENCE[key], "debtor_info", Gap.GATE)
        for key in STEP_1_GATES
        if key not in answers
    ]
    gaps += _debtor_info_details(answers)
    gaps += _too_long(answers, "debtor_info", step_1_keys)

    if "hazard_answer" not in answers:
        gaps.append(Gap(GATE_HAZARD, "assets", Gap.GATE))
    elif answers["hazard_answer"] == "yes" and _blank(answers.get("hazard_what")):
        gaps.append(_detail(DETAIL_HAZARD, "assets", "hazard_what"))
    gaps += _too_long(answers, "assets", hazard_keys)

    if "rents_residence" not in answers:
        gaps.append(Gap(GATE_RENTS, "contracts", Gap.GATE))
    elif answers["rents_residence"] == "yes" and "eviction_judgment" not in answers:
        gaps.append(Gap(GATE_EVICTION, "contracts", Gap.GATE))
    return gaps
