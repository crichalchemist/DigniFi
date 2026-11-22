"""What Form 101's questions still lack from the filer (forms step 4b spec §7.1).

Pure reading: the gaps come from the session's `PetitionAnswers` record, never from a form's
preconditions. The sentences are DigniFi's own; 4b-ii adds the browser's copy
(`petitionGaps.ts`) and the test that pins it (`test_petition_frontend_copy.py`).
"""

from apps.forms.services import petition_fit
from apps.forms.services.answer_records import (
    PETITION_STEP_OF_KEY,
    is_itin,
    is_mm_dd_yyyy,
    is_nine_digits,
)

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
GATE_OTHER_SSN = "Say whether you have used any other Social Security number. Answer Yes or No."
GATE_MAILING = "Say whether your mailing address is different from where you live."
GATE_PRIOR_BANKRUPTCY = "Say whether you have filed for bankruptcy in the last 8 years."
GATE_PENDING_CASE = "Say whether a spouse, partner or affiliate has a bankruptcy case pending."
GATE_SOLE_PROPRIETOR = "Say whether you are a sole proprietor of a business."
GATE_HAZARD = "Say whether any property you own poses a hazard or needs attention right away."
GATE_RENTS = "Say whether you rent your residence."
GATE_EVICTION = "Say whether your landlord has an eviction judgment against you."
DETAIL_VENUE = "Choose why you are filing in this district."
# Wording approved by the owner on 2026-11-21; still in counsel's C-40 review.
# DRAFT: counsel C-40
DETAIL_VENUE_REASON = "Explain your other reason for filing here."
DETAIL_OTHER_NAMES = "Add the other name you used, or change your answer to No."
DETAIL_ITIN = "Type your 9-digit ITIN, or change your answer to No."
# Nine digits whose first is not 9: a number, but not an ITIN (owner ruling Q7, 2026-11-21).
DETAIL_ITIN_NINE = "An ITIN starts with 9. Check what you typed, or change your answer to No."
DETAIL_OTHER_SSN = "Type the other 9-digit Social Security number, or change your answer to No."
DETAIL_EIN = "Your EIN has 9 digits. Check what you typed."
DETAIL_MAILING = "Add your mailing address, or change your answer to No."
DETAIL_PRIOR_CASE = "Each earlier case needs its district and the date it was filed."
DETAIL_PRIOR_DATE = "A date is written as MM/DD/YYYY. Check the date of your earlier case."
DETAIL_PENDING_DATE = "A date is written as MM/DD/YYYY. Check the date of the pending case."
DETAIL_PENDING_CASE = "Each pending case needs the name of the person who filed it."
DETAIL_BUSINESS = "Add your business's name, or change your answer to No."
DETAIL_HAZARD = "Say what the hazard is, or change your answer to No."
# A one-off text's template: {label} is the box's index label in plain words (TEXT_LABELS).
DETAIL_TOO_LONG = "Your answer for {label} is too long for its box on Form 101."
# A row cell's (owner ruling Q5): {label} from CELL_LABELS, {noun} from ROW_NOUNS, {n} the row's
# place in its list, counted from 1.
DETAIL_TOO_LONG_ROW = "Your answer for {label}, in {noun} {n}, is too long to fit on Form 101."

# The row lists step 1 asks, in the form's line order (2, 9, 10), each printed under its line's
# Yes; their cells have no character cap and are measured where they print (PF2-10a).
ROW_LIST_GATES = {
    "other_names": "other_names_answer",
    "other_business_names": "other_names_answer",
    "prior_cases": "prior_bankruptcy_answer",
    "pending_cases": "pending_case_answer",
}
# Each list's row cells in plain words, written by build_form_101.py into form_101.limits.json.
CELL_LABELS: dict[str, dict[str, str]] = PetitionAnswers.CELL_LABELS
# What the filer calls a row of each list: line 2's are names, lines 9's and 10's cases.
ROW_NOUNS = {
    "other_names": "name",
    "other_business_names": "name",
    "prior_cases": "case",
    "pending_cases": "case",
}

_GATE_SENTENCE = {
    "other_names_answer": GATE_OTHER_NAMES,
    "itin_answer": GATE_ITIN,
    "other_ssn_answer": GATE_OTHER_SSN,
    "mailing_answer": GATE_MAILING,
    "prior_bankruptcy_answer": GATE_PRIOR_BANKRUPTCY,
    "pending_case_answer": GATE_PENDING_CASE,
    "sole_proprietor_answer": GATE_SOLE_PROPRIETOR,
}

# Every key a detail can name, to the forms that print its box blank while it is open (4b-R12).
# Form 101 prints the ITIN's last four but has no box for the other Social Security number, so
# `itin` names both forms and `other_ssn` names Form 121 alone (PF2-T7-7). Form 103B line 20
# prints Form 101 line 9's earlier cases (PF2-T10-3).
FORMS_OF_KEY: dict[str, tuple[str, ...]] = {key: ("form_101",) for key in PetitionAnswers.KEYS}
FORMS_OF_KEY["itin"] = ("form_101", "form_121")
FORMS_OF_KEY["other_ssn"] = ("form_121",)
FORMS_OF_KEY["prior_cases"] = ("form_101", "form_103b")
_MAILING_KEYS = (
    "mailing_street",
    "mailing_po_box",
    "mailing_city",
    "mailing_state",
    "mailing_zip",
)


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
    itin = answers.get("itin")
    if answers.get("itin_answer") == "yes" and not is_itin(itin):
        sentence = DETAIL_ITIN_NINE if is_nine_digits(itin) else DETAIL_ITIN
        gaps.append(_detail(sentence, step, "itin"))
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
        if any(_bad_date(row) for row in rows):
            gaps.append(_detail(DETAIL_PENDING_DATE, step, "pending_cases"))
    return gaps


def text_shows(answers: dict, key: str) -> bool:
    """Whether the key's box prints: a text under a No is hidden, so its length is no gap. A row
    list's cells print only under its line's Yes."""
    if key in ROW_LIST_GATES:
        return answers.get(ROW_LIST_GATES[key]) == "yes"
    for prefix, gate in (
        ("mailing_", "mailing_answer"),
        ("business_", "sole_proprietor_answer"),
        ("hazard_", "hazard_answer"),
    ):
        if key.startswith(prefix):
            return answers.get(gate) == "yes"
    if key == "venue_reason":
        return answers.get("venue_choice") == "other"
    return True


def _too_long(answers: dict, step: str, keys: list[str], too_wide: dict) -> list[Gap]:
    """A detail for each of `keys` whose text is over its box's cap, or under it and still too
    wide for a box it prints in (`too_wide`, measured as check() measures it), naming the box
    once."""
    gaps = []
    for key in keys:
        if not text_shows(answers, key):
            continue
        limit = PetitionAnswers.TEXT_LIMITS.get(key)
        value = answers.get(key)
        over = limit is not None and isinstance(value, str) and len(value) > limit
        if over or (key, None, None) in too_wide:
            label = PetitionAnswers.TEXT_LABELS.get(key, key.replace("_", " "))
            gaps.append(_detail(DETAIL_TOO_LONG.format(label=label), step, key))
    return gaps


def _cells_too_long(answers: dict, too_wide: dict) -> list[Gap]:
    """A detail for each row cell too wide where it prints, naming its row (PF2-10a, owner ruling
    Q5): by line, then row by row, then the row's cells in the line's order. The detail names
    only the forms whose box refuses the cell: Form 103B's line 20 boxes are not Form 101's."""
    gaps = []
    for list_key in ROW_LIST_GATES:
        if not text_shows(answers, list_key):
            continue
        rows = sorted({row for key, _, row in too_wide if key == list_key})
        for n in rows:
            for attr, label in CELL_LABELS[list_key].items():
                if (list_key, attr, n) in too_wide:
                    sentence = DETAIL_TOO_LONG_ROW.format(
                        label=label, noun=ROW_NOUNS[list_key], n=n
                    )
                    refusing = too_wide[(list_key, attr, n)]
                    forms = tuple(f for f in FORMS_OF_KEY[list_key] if f in refusing)
                    gaps.append(Gap(sentence, "debtor_info", Gap.DETAIL, forms=forms))
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
    measured = [*step_1_keys, *hazard_keys, *ROW_LIST_GATES]
    too_wide = petition_fit.too_long(session, [k for k in measured if text_shows(answers, k)])

    gaps = [
        Gap(_GATE_SENTENCE[key], "debtor_info", Gap.GATE)
        for key in STEP_1_GATES
        if key not in answers
    ]
    gaps += _debtor_info_details(answers)
    gaps += _too_long(answers, "debtor_info", step_1_keys, too_wide)
    gaps += _cells_too_long(answers, too_wide)

    if "hazard_answer" not in answers:
        gaps.append(Gap(GATE_HAZARD, "assets", Gap.GATE))
    elif answers["hazard_answer"] == "yes" and _blank(answers.get("hazard_what")):
        gaps.append(_detail(DETAIL_HAZARD, "assets", "hazard_what"))
    gaps += _too_long(answers, "assets", hazard_keys, too_wide)

    if "rents_residence" not in answers:
        gaps.append(Gap(GATE_RENTS, "contracts", Gap.GATE))
    elif answers["rents_residence"] == "yes" and "eviction_judgment" not in answers:
        gaps.append(Gap(GATE_EVICTION, "contracts", Gap.GATE))
    return gaps
