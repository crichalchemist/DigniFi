"""What Schedule I lines 1, 11 and 13 and Schedule J line 24 still lack from the filer (4c).

The gaps come from the session's `ScheduleIAnswers` record alone, read by attribute, and nothing
here writes. They join Complete's list only, never `income_step_gaps`: no answer here reaches
CMI, the means test, Form 103B lines 1 to 3 or the household counts.

A text is listed too long when it is over its character cap (`ScheduleIAnswers.TEXT_LIMITS`),
by length alone, and only while its box prints: a text the step hides behind a later answer
prints nothing, so its length is no gap. Generate's own check still refuses a text within its
cap that its box can't take.

`married_together` and the sentences import nothing from the forms or from Complete's module,
so the forms' derivations can import them without a cycle; `Gap` is imported inside
`schedule_i_step_gaps` alone.
"""

from .models import ScheduleIAnswers

# Wording approved by the owner on 2026-11-22 (4c owner copy W5-W15); still in counsel's C-42
# review. The browser's copies are in frontend/src/constants/copy.ts.
# DRAFT: counsel C-42
GATE_LINE_11 = "Say if anyone else pays part of your Schedule J expenses on a regular basis."
GATE_LINE_13 = "Say whether you expect your income to go up or down in the year after you file."
GATE_J24 = "Say whether you expect your expenses to go up or down in the year after you file."
DETAIL_EMPLOYMENT = "Choose Employed or Not employed."
DETAIL_SPOUSE_EMPLOYMENT = "Choose Employed or Not employed for your spouse."
DETAIL_EMPLOYER = "Add your employer's name, or change your answer to Not employed."
DETAIL_SPOUSE_EMPLOYER = (
    "Add your spouse's employer's name, or change their answer to Not employed."
)
DETAIL_LINE_11_AMOUNT = "Add how much others pay each month, or change your answer to No."
DETAIL_LINE_13 = "Explain the change you expect in your income, or change your answer to No."
DETAIL_J24 = "Explain the change you expect in your expenses, or change your answer to No."
# {label} is the key's label in schedule_i.limits.json, {form} the form whose box it prints in.
DETAIL_TOO_LONG = "Your answer for {label} is too long for its box on {form}."

# Each gap's kind, by the key it concerns: "gate" (Complete refuses while it is open) or
# "detail" (Complete lets it through), Gap.GATE and Gap.DETAIL spelled out (4c-R1, D1, D2). A
# text's too-long gap is a detail too.
KIND_OF: dict[str, str] = {
    **dict.fromkeys(ScheduleIAnswers.TEXT_KEYS, "detail"),
    "employment_status": "detail",
    "spouse_employment_status": "detail",
    "line_11_answer": "gate",
    "line_11_amount": "detail",
    "line_13_answer": "gate",
    "schedule_j_line_24_answer": "gate",
}

_SPOUSE = "spouse_"
_J24 = "schedule_j_"
# The texts each Yes shows; every other text is line 1's.
_TEXT_UNDER_YES = {
    "line_11_text": "line_11_answer",
    "line_13_text": "line_13_answer",
    "schedule_j_line_24_text": "schedule_j_line_24_answer",
}


def married_together(session) -> bool:
    """Whether the filer is married with the spouse at home, not filing (`married_together`): the
    one read of the marriage answer for Schedule I's spouse column."""
    income_info = getattr(session, "income_info", None)
    return getattr(income_info, "marital_status", None) == "married_together"


def _blank(value) -> bool:
    return not isinstance(value, str) or not value.strip()


def _no_amount(value) -> bool:
    # A typed 0 is an amount; only nothing, or a blank string, is none.
    return value is None or (isinstance(value, str) and not value.strip())


def text_shows(answers: dict, key: str, together: bool) -> bool:
    """Whether the key's box prints (4c-R5): an occupation once its status is answered, an
    employer's name, address and tenure under Employed, the spouse's only for a filer married
    with the spouse at home (not filing), and each line's text under its own Yes."""
    if key in _TEXT_UNDER_YES:
        return answers.get(_TEXT_UNDER_YES[key]) == "yes"
    prefix = _SPOUSE if key.startswith(_SPOUSE) else ""
    if prefix and not together:
        return False
    status = answers.get(f"{prefix}employment_status")
    if key == f"{prefix}occupation":
        return status is not None
    return status == "employed"


def schedule_i_step_gaps(session) -> list:
    """Every gap of the record, in 4c-R2's order: the Income step's (line 1's employment, the
    spouse's, the employer, the spouse's employer, line 11, line 13, then each text too long, in
    the record's key order), then Schedule J line 24's, which the Expenses step asks.

    Each `Gap` carries its own step, `income_info` or `expense_info`, and Complete's list splices
    them where those steps' gaps end. A session with no record has every key unanswered.
    """
    # Imported here: completion.py's module imports the forms registry, and the forms import
    # married_together from this module.
    from .completion import Gap

    record = getattr(session, "schedule_i_answers", None)
    answers = record.get_answers() if record else {}
    together = married_together(session)
    fee = getattr(session, "filing_fee", None)
    waiver = getattr(fee, "payment_choice", None) == "waiver"

    def gap(sentence: str, key: str) -> Gap:
        kind = KIND_OF[key]
        step = "expense_info" if key.startswith(_J24) else "income_info"
        if kind == Gap.GATE:
            forms = ()
        elif key.startswith(_J24):
            forms = ("schedule_j",)
        elif key == "line_11_amount" and waiver:
            # Form 103B line 8 copies line 11's amount, and only a waiver's packet holds 103B.
            forms = ("schedule_i", "form_103b")
        else:
            forms = ("schedule_i",)
        return Gap(sentence, step, kind, forms=forms)

    def too_long(keys) -> list[Gap]:
        found = []
        for key in keys:
            value = answers.get(key)
            limit = ScheduleIAnswers.TEXT_LIMITS[key]
            if text_shows(answers, key, together) and isinstance(value, str) and len(value) > limit:
                form = "Schedule J" if key.startswith(_J24) else "Schedule I"
                label = ScheduleIAnswers.TEXT_LABELS[key]
                found.append(gap(DETAIL_TOO_LONG.format(label=label, form=form), key))
        return found

    gaps = []
    if "employment_status" not in answers:
        gaps.append(gap(DETAIL_EMPLOYMENT, "employment_status"))
    if together and "spouse_employment_status" not in answers:
        gaps.append(gap(DETAIL_SPOUSE_EMPLOYMENT, "spouse_employment_status"))
    if answers.get("employment_status") == "employed" and _blank(answers.get("employer_name")):
        gaps.append(gap(DETAIL_EMPLOYER, "employer_name"))
    if (
        together
        and answers.get("spouse_employment_status") == "employed"
        and _blank(answers.get("spouse_employer_name"))
    ):
        gaps.append(gap(DETAIL_SPOUSE_EMPLOYER, "spouse_employer_name"))

    if "line_11_answer" not in answers:
        gaps.append(gap(GATE_LINE_11, "line_11_answer"))
    elif answers["line_11_answer"] == "yes" and _no_amount(answers.get("line_11_amount")):
        gaps.append(gap(DETAIL_LINE_11_AMOUNT, "line_11_amount"))
    if "line_13_answer" not in answers:
        gaps.append(gap(GATE_LINE_13, "line_13_answer"))
    elif answers["line_13_answer"] == "yes" and _blank(answers.get("line_13_text")):
        gaps.append(gap(DETAIL_LINE_13, "line_13_text"))

    texts = [key for key in ScheduleIAnswers.KEYS if key in ScheduleIAnswers.TEXT_LIMITS]
    gaps += too_long(key for key in texts if not key.startswith(_J24))

    if "schedule_j_line_24_answer" not in answers:
        gaps.append(gap(GATE_J24, "schedule_j_line_24_answer"))
    elif answers["schedule_j_line_24_answer"] == "yes" and _blank(
        answers.get("schedule_j_line_24_text")
    ):
        gaps.append(gap(DETAIL_J24, "schedule_j_line_24_text"))
    gaps += too_long(key for key in texts if key.startswith(_J24))
    return gaps
