"""What an intake still lacks, in one list (forms step 4a spec §5.7).

Complete, the read-only gaps endpoint and the forms' preparation all read `completion_gaps`, so
the filer sees the same words, in the same order, wherever the list is shown.
"""

from apps.eligibility.cmi import counted_spouse_income, income_step_gaps
from apps.forms.registry import PreconditionMissing, _needs_county, _needs_ssn

from .asset_lines import asset_step_gaps
from .claims import claim_step_gaps
from .income import deductions_blank, schedule_i_line4

# The wizard's last step is Review, step 9: the length of WIZARD_STEPS in
# frontend/src/constants/wizardSteps.ts, which test_wizard_step_count_is_the_browsers pins.
WIZARD_STEP_COUNT = 9

TAKE_HOME_PAY_NOT_ENTERED = (
    "Enter what is taken out of your pay on the Take-home pay step. "
    "If nothing is, enter $0 in one box."
)
SPOUSE_TAKE_HOME_PAY_NOT_ENTERED = (
    "Enter what is taken out of your spouse's pay on the Take-home pay step. "
    "If nothing is, enter $0 in one box."
)
EXPENSES_INCLUDE_OTHERS_UNANSWERED = (
    "Answer whether your expenses include anyone else's, on the Expenses step."
)
EXPENSES_STEP_NEVER_SAVED = "Go through the Expenses step, even if you have no expenses to enter."


class Gap(Exception):
    """One thing an intake still lacks, in the filer's words.

    `step` is the WIZARD_STEPS key that fixes it. `kind` is "gate" (Complete refuses while it
    is open) or "detail" (the forms print it blank). str(gap) is the sentence.
    """

    GATE = "gate"
    DETAIL = "detail"

    def __init__(self, message: str, step: str, kind: str):
        super().__init__(message)
        self.message = message
        self.step = step
        self.kind = kind


GATE = Gap.GATE
DETAIL = Gap.DETAIL


def completion_gaps(session) -> list[Gap]:
    """Every gap Complete checks, in its order: wizard order, with the claims tail last.

    The claims tail (the legacy gaps, then the line 4 question) comes after Codebtors' gaps, out
    of wizard order on purpose (3c4). Reads only: never the packet, a form's preconditions or
    the means test.
    """
    gaps = []

    # The forms' own identity checks, so Complete and the forms say the same thing.
    try:
        _needs_ssn(session)  # checks the name and address first
    except PreconditionMissing as exc:
        gaps.append(Gap(str(exc), exc.step, GATE))

    try:
        _needs_county(session)
    except PreconditionMissing as exc:
        gaps.append(Gap(str(exc), exc.step, GATE))

    # Every gap the Income step leaves, in order: the same check the means test refuses
    # with (3e1 spec §9.1).
    gaps.extend(Gap(str(gap), gap.step, GATE) for gap in income_step_gaps(session))

    # Take-home pay and Schedule J line 3 are Complete's alone: the means test and the forms
    # don't read them (3e2 spec §8).
    for row, message in (
        (getattr(session, "income_info", None), TAKE_HOME_PAY_NOT_ENTERED),
        (counted_spouse_income(session), SPOUSE_TAKE_HOME_PAY_NOT_ENTERED),
    ):
        if row is not None and schedule_i_line4(row) > 0 and deductions_blank(row):
            gaps.append(Gap(message, "take_home_pay", GATE))

    if not hasattr(session, "expense_info"):
        gaps.append(Gap(EXPENSES_STEP_NEVER_SAVED, "expense_info", GATE))
    elif session.expense_info.expenses_include_others is None:
        gaps.append(Gap(EXPENSES_INCLUDE_OTHERS_UNANSWERED, "expense_info", GATE))

    # Schedule A/B's walk: every gap, after Schedule J line 3 and before the scanned debts,
    # which is wizard order (3b spec §7).
    gaps.extend(Gap(str(gap), gap.step, GATE) for gap in asset_step_gaps(session))

    # The claims steps' walk (3c3): Assets' "Do you live here?" first, then the Debts block
    # (a scanned debt the filer hasn't confirmed first, DIG-163), Contracts and Codebtors; then,
    # out of wizard order on purpose (3c4), the legacy gaps and the line 4 question.
    gaps.extend(Gap(str(gap), gap.step, GATE) for gap in claim_step_gaps(session))

    return gaps
