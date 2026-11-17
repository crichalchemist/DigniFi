"""The 122A-2 page's answers: their keys, how a stale reference reads, and the page's gaps. Pure: no models, no forms module."""

import copy
from collections.abc import Collection, Mapping
from decimal import Decimal

from apps.eligibility.means_lines import (
    MISSING,
    MeansInputs,
    MeansTables,
    debt_lines,
    is_spouse_ref,
    line_30_cap,
    slot_candidates,
)
from apps.intake.claims import NAMELESS_DEBT, claim_row_name

ANSWER_KEYS: tuple[str, ...] = (
    "line_3_answer",
    "line_3_rows",
    "spouse_vehicles_answer",
    "spouse_vehicles",
    "spouse_loans_answer",
    "spouse_loans",
    "vehicle_claims",
    "vehicle_choice",
    "line_15_answer",
    "line_15_amount",
    "line_16",
    "line_17",
    "line_18",
    "line_19",
    "line_20",
    "line_21",
    "line_22_answer",
    "line_22_amount",
    "line_23",
    "line_25_answer",
    "line_25_health",
    "line_25_disability",
    "line_25_hsa",
    "line_25_spends",
    "line_25_actual",
    *(f"line_{n}_{part}" for n in range(26, 32) for part in ("answer", "amount")),
    "line_34_answer",
    "line_36_answer",
    "line_36_payment",
    "line_43_answer",
    "line_43_circumstances",
)

LIST_KEYS = ("line_3_rows", "spouse_vehicles", "spouse_loans", "line_43_circumstances")

PER_DEBT_KEYS = (
    "payments_left",
    "payment_changes",
    "total_60_months",
    "taxes_or_insurance",
    "necessary_for_support",
    "cure",
)

MAX_ROWS = 10

PROPERTY_CHOICES = ("home", "other")

# Server sentences the page also shows (each pinned to copy.ts).
MEANS_TOO_LONG = "This is too long for the box on Form 122A-2. Shorten it."
MEANS_LETTER = "This has a letter Form 122A-2 can't print. Change it."
MEANS_EXPLANATION_TOO_LONG = "This explanation is too long to print with line 43. Shorten it."
MEANS_EXPLANATION_LETTER = "This explanation has a letter Form 122A-2 can't print. Change it."
NOT_A_MEANS_ANSWER = "This is not one of the means test answers."
MEANS_ROW_LISTED_TWICE = "Each row can be sent only once in a save."

# The page's gaps, in page order (each pinned to copy.ts).
MEANS_GAP_LINE_3 = "Answer line 3, about your spouse's income."
MEANS_GAP_LINE_3_NO_ROW = (
    "Add each use of your spouse's income on line 3, or change the answer to No."
)
MEANS_GAP_LINE_3_ROW = (
    "Enter what your spouse's income was used for, and the amount, on each row of line 3."
)
MEANS_GAP_SPOUSE_VEHICLES = (
    "Answer whether your spouse has a vehicle that isn't on your property list."
)
MEANS_GAP_SPOUSE_VEHICLES_NO_ROW = "Add each of your spouse's vehicles, or change the answer to No."
MEANS_GAP_SPOUSE_VEHICLE_DESCRIBE = "Describe each of your spouse's vehicles."
MEANS_GAP_SPOUSE_VEHICLE_LEASED = "Answer whether {name} is leased."
MEANS_GAP_SPOUSE_LOANS = (
    "Answer whether your spouse owes a loan on your home, a vehicle or other property."
)
MEANS_GAP_SPOUSE_LOANS_NO_ROW = "Add each of your spouse's loans, or change the answer to No."
MEANS_GAP_SPOUSE_LOAN_ON_AMOUNTS_OWED = (
    "Answer whether each of your spouse's loans is on your Amounts Owed step."
)
MEANS_GAP_SPOUSE_LOAN_WHICH = (
    "For each of your spouse's loans that is on your Amounts Owed step, choose which one it is."
)
MEANS_GAP_SPOUSE_LOAN_CREDITOR = "Enter who your spouse owes on each of their loans."
MEANS_GAP_SPOUSE_LOAN_SECURED_BY = "Say what secures your spouse's loan from {name}."
MEANS_GAP_SPOUSE_LOAN_PROPERTY = (
    "Describe the property that secures your spouse's loan from {name}."
)
MEANS_GAP_SPOUSE_LOAN_PAYMENT = "Enter the monthly payment on your spouse's loan from {name}."
MEANS_GAP_VEHICLE = "Answer whether you claim an expense for {name}."
MEANS_GAP_VEHICLE_CHOICE = "Choose your Vehicle 1 and your Vehicle 2."
MEANS_GAP_LINE_15 = "Answer the question on line 15."
MEANS_GAP_LINE_15_AMOUNT = "Enter the amount for line 15."
MEANS_GAP_LINE_15_CAP = (
    "Line 15 can't be more than {amount}, the IRS amount for public transportation."
)
MEANS_GAP_AMOUNT = "Enter the amount for line {n}. Enter 0 if you have none."
MEANS_GAP_OPT_IN = "Answer line {n}."
MEANS_GAP_OPT_IN_AMOUNT = "Enter the amount for line {n}."
MEANS_GAP_LINE_25_AMOUNTS = "Enter the three amounts on line 25."
MEANS_GAP_LINE_25_SPENDS = "Answer whether you actually spend the line 25 total."
MEANS_GAP_LINE_25_ACTUAL = "Enter how much you actually spend, on line 25."
MEANS_GAP_LINE_30_CAP = (
    "Line 30 can't be more than {amount}, which is 5% of the IRS food and "
    "clothing amounts for {n} people."
)
MEANS_GAP_LINE_30_CAP_ONE = (
    "Line 30 can't be more than {amount}, which is 5% of the IRS food and "
    "clothing amounts for 1 person."
)
MEANS_GAP_PAYMENTS_LEFT = "Enter how many payments you have left to {name}."
MEANS_GAP_PAYMENT_CHANGES = "Answer whether your payment to {name} will change."
MEANS_GAP_SIXTY_MONTH_TOTAL = "Enter the total you will owe {name} in the 60 months after you file."
MEANS_GAP_TAXES = "Say if the payment to {name} pays for taxes or insurance too."
MEANS_GAP_LINE_34 = "Answer line 34, about debts secured by property you need for support."
MEANS_GAP_SUPPORT = "Say if your debt to {name} is secured by property you need for support."
MEANS_GAP_CURE = "Enter the cure amount for {name}. Enter 0 if there is none."
MEANS_GAP_LINE_36 = "Answer line 36."
MEANS_GAP_LINE_36_PAYMENT = "Enter the projected monthly plan payment on line 36."
MEANS_GAP_LINE_43 = "Answer the question on line 43."
MEANS_GAP_LINE_43_NONE = "Add each special circumstance on line 43, or change the answer to No."
MEANS_GAP_LINE_43_EXPLANATION = "Give the explanation for circumstance {n} on line 43."
MEANS_GAP_LINE_43_AMOUNT = (
    "Enter the average monthly amount for circumstance {n} on line 43. Enter 0 if there is none."
)


def _unanswered(key: str):
    if key in LIST_KEYS:
        return []
    if key == "vehicle_claims":
        return {}
    if key == "vehicle_choice":
        return [None, None]
    return None


def normalized_answers(
    stored: Mapping,
    filer_vehicles: Collection[str],
    open_debts: Collection[int],
    keep_hidden: bool = False,
) -> dict:
    """Every answer key, a reference to a row that has gone read as unanswered. Copies; never
    changes `stored`.

    `filer_vehicles` holds the refs of the filer's Schedule A/B vehicles, `open_debts` the ids of
    the confirmed debts Amounts Owed doesn't list as secured. A spouse vehicle row is a vehicle
    to refer to only under "spouse vehicles: Yes", so under No a loan's link to it reads as
    unanswered; `keep_hidden` keeps it, for the page, which shows what the filer typed and sends
    it back (DIG-513).
    """
    out = {}
    for key in ANSWER_KEYS:
        value = stored.get(key)
        out[key] = _unanswered(key) if value is None else copy.deepcopy(value)

    out["vehicle_claims"] = {
        ref: answer for ref, answer in out["vehicle_claims"].items() if ref in filer_vehicles
    }
    live = set(filer_vehicles)
    if keep_hidden or out["spouse_vehicles_answer"] == "yes":
        live.update(row.get("ref") for row in out["spouse_vehicles"])
    pair = (list(out["vehicle_choice"]) + [None, None])[:2]
    out["vehicle_choice"] = [ref if ref in live else None for ref in pair]

    taken: set[int] = set()
    for loan in out["spouse_loans"]:
        debt = loan.get("debt")
        on_list = loan.get("on_amounts_owed") == "yes"
        if on_list and debt in open_debts and debt not in taken:
            taken.add(debt)
        else:
            loan["debt"] = None
        secured_by = loan.get("secured_by")
        if secured_by in PROPERTY_CHOICES:
            continue
        keeps = secured_by in live
        if on_list and not is_spouse_ref(secured_by or ""):
            keeps = False
        if not keeps:
            loan["secured_by"] = None
    return out


def _money(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def _amount(value) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _blank(text) -> bool:
    return text is None or not str(text).strip()


def _opt_in_gaps(answers: Mapping, line: int) -> list[str]:
    answer = answers[f"line_{line}_answer"]
    if answer is None:
        return [MEANS_GAP_OPT_IN.format(n=line)]
    if answer == "yes" and answers[f"line_{line}_amount"] is None:
        return [MEANS_GAP_OPT_IN_AMOUNT.format(n=line)]
    return []


def _loan_identity_given(loan: Mapping) -> bool:
    answer = loan.get("on_amounts_owed")
    if answer == "yes":
        return loan.get("debt") is not None
    if answer == "no":
        return not _blank(loan.get("creditor"))
    return False


def _spouse_vehicle_gaps(answers: Mapping) -> list[str]:
    answer = answers["spouse_vehicles_answer"]
    if answer is None:
        return [MEANS_GAP_SPOUSE_VEHICLES]
    rows = answers["spouse_vehicles"]
    if answer != "yes":
        return []
    if not rows:
        return [MEANS_GAP_SPOUSE_VEHICLES_NO_ROW]
    gaps = []
    if any(_blank(row.get("description")) for row in rows):
        gaps.append(MEANS_GAP_SPOUSE_VEHICLE_DESCRIBE)
    for row in rows:
        if not _blank(row.get("description")) and row.get("leased") is None:
            gaps.append(MEANS_GAP_SPOUSE_VEHICLE_LEASED.format(name=row["description"]))
    return gaps


def _spouse_loan_gaps(inputs: MeansInputs, answers: Mapping) -> list[str]:
    answer = answers["spouse_loans_answer"]
    if answer is None:
        return [MEANS_GAP_SPOUSE_LOANS]
    rows = answers["spouse_loans"]
    if answer != "yes":
        return []
    if not rows:
        return [MEANS_GAP_SPOUSE_LOANS_NO_ROW]
    gaps = []
    if any(row.get("on_amounts_owed") is None for row in rows):
        gaps.append(MEANS_GAP_SPOUSE_LOAN_ON_AMOUNTS_OWED)
    if any(row.get("on_amounts_owed") == "yes" and row.get("debt") is None for row in rows):
        gaps.append(MEANS_GAP_SPOUSE_LOAN_WHICH)
    if any(row.get("on_amounts_owed") == "no" and _blank(row.get("creditor")) for row in rows):
        gaps.append(MEANS_GAP_SPOUSE_LOAN_CREDITOR)
    names = {debt.ref: debt.creditor for debt in inputs.secured_debts}
    for row in rows:
        if not _loan_identity_given(row):
            continue
        name = claim_row_name(names.get(row.get("ref"), row.get("creditor")), NAMELESS_DEBT)
        secured_by = row.get("secured_by")
        if secured_by is None:
            gaps.append(MEANS_GAP_SPOUSE_LOAN_SECURED_BY.format(name=name))
        elif secured_by in PROPERTY_CHOICES and _blank(row.get("property")):
            gaps.append(MEANS_GAP_SPOUSE_LOAN_PROPERTY.format(name=name))
        if row.get("payment") is None:
            gaps.append(MEANS_GAP_SPOUSE_LOAN_PAYMENT.format(name=name))
    return gaps


def _vehicle_gaps(inputs: MeansInputs, tables: MeansTables, answers: Mapping) -> list[str]:
    gaps = []
    for vehicle in inputs.vehicles:
        if is_spouse_ref(vehicle.ref) and _blank(vehicle.name):
            continue
        if vehicle.claimed is None:
            gaps.append(MEANS_GAP_VEHICLE.format(name=vehicle.name))
    candidates = slot_candidates(inputs)
    if candidates is not MISSING and len(candidates) > 2:
        refs = {vehicle.ref for vehicle in candidates}
        first, second = answers["vehicle_choice"]
        if first not in refs or second not in refs or first == second:
            gaps.append(MEANS_GAP_VEHICLE_CHOICE)
    if any(vehicle.claimed for vehicle in inputs.vehicles):
        answer = answers["line_15_answer"]
        amount = _amount(answers["line_15_amount"])
        if answer is None:
            gaps.append(MEANS_GAP_LINE_15)
        elif answer == "yes" and amount is None:
            gaps.append(MEANS_GAP_LINE_15_AMOUNT)
        elif answer == "yes" and amount > tables.public_transport:
            gaps.append(MEANS_GAP_LINE_15_CAP.format(amount=_money(tables.public_transport)))
    return gaps


def _line_25_gaps(answers: Mapping) -> list[str]:
    answer = answers["line_25_answer"]
    if answer is None:
        return [MEANS_GAP_OPT_IN.format(n=25)]
    if answer != "yes":
        return []
    gaps = []
    if any(answers[key] is None for key in ("line_25_health", "line_25_disability", "line_25_hsa")):
        gaps.append(MEANS_GAP_LINE_25_AMOUNTS)
    spends = answers["line_25_spends"]
    if spends is None:
        gaps.append(MEANS_GAP_LINE_25_SPENDS)
    elif spends == "no" and answers["line_25_actual"] is None:
        gaps.append(MEANS_GAP_LINE_25_ACTUAL)
    return gaps


def _line_30_cap_gap(inputs: MeansInputs, tables: MeansTables, answers: Mapping) -> list[str]:
    people = None if inputs.ages is None else len(inputs.ages)
    amount = _amount(answers["line_30_amount"])
    if answers["line_30_answer"] != "yes" or amount is None or not people:
        return []
    cap = line_30_cap(tables, people)
    if amount <= cap:
        return []
    if people == 1:
        return [MEANS_GAP_LINE_30_CAP_ONE.format(amount=_money(cap))]
    return [MEANS_GAP_LINE_30_CAP.format(amount=_money(cap), n=people)]


def _debt_gaps(inputs: MeansInputs, answers: Mapping, lines: Mapping) -> list[str]:
    loans = {row.get("ref"): row for row in answers["spouse_loans"]}
    named = [
        debt
        for debt in inputs.secured_debts
        if not is_spouse_ref(debt.ref) or _loan_identity_given(loans.get(debt.ref, {}))
    ]
    gaps = []
    for debt in named:
        name = claim_row_name(debt.creditor, NAMELESS_DEBT)
        if debt.payments_left is None:
            gaps.append(MEANS_GAP_PAYMENTS_LEFT.format(name=name))
        if debt.payment_changes is None:
            gaps.append(MEANS_GAP_PAYMENT_CHANGES.format(name=name))
        elif debt.payment_changes == "yes" and debt.total_60_months is None:
            gaps.append(MEANS_GAP_SIXTY_MONTH_TOTAL.format(name=name))
        if lines[debt.ref] == "33d" and debt.taxes_or_insurance is None:
            gaps.append(MEANS_GAP_TAXES.format(name=name))
    if answers["line_34_answer"] is None:
        gaps.append(MEANS_GAP_LINE_34)
    elif answers["line_34_answer"] == "yes":
        for debt in named:
            if lines[debt.ref] is None:
                continue
            name = claim_row_name(debt.creditor, NAMELESS_DEBT)
            if debt.necessary_for_support is None:
                gaps.append(MEANS_GAP_SUPPORT.format(name=name))
            elif debt.necessary_for_support == "yes" and debt.cure is None:
                gaps.append(MEANS_GAP_CURE.format(name=name))
    return gaps


def _line_43_gaps(answers: Mapping) -> list[str]:
    answer = answers["line_43_answer"]
    if answer is None:
        return [MEANS_GAP_LINE_43]
    if answer != "yes":
        return []
    rows = answers["line_43_circumstances"]
    if not rows:
        return [MEANS_GAP_LINE_43_NONE]
    gaps = []
    for number, row in enumerate(rows, start=1):
        if _blank(row.get("explanation")):
            gaps.append(MEANS_GAP_LINE_43_EXPLANATION.format(n=number))
        if row.get("amount") is None:
            gaps.append(MEANS_GAP_LINE_43_AMOUNT.format(n=number))
    return gaps


def means_test_gaps(inputs: MeansInputs, tables: MeansTables, answers: Mapping) -> list[str]:
    """Every answer Form 122A-2 still needs, as the page's sentences, in the page's order (R7).

    `answers` is `normalized_answers`' dict; `inputs` gives the vehicles, the debts, the
    marital answer and the household's ages.
    """
    gaps: list[str] = []
    together = inputs.marital_status == "married_together"
    if together:
        three = answers["line_3_answer"]
        if three is None:
            gaps.append(MEANS_GAP_LINE_3)
        elif three == "yes":
            rows = answers["line_3_rows"]
            if not rows:
                gaps.append(MEANS_GAP_LINE_3_NO_ROW)
            elif any(_blank(row.get("purpose")) or row.get("amount") is None for row in rows):
                gaps.append(MEANS_GAP_LINE_3_ROW)
        gaps += _spouse_vehicle_gaps(answers)
        gaps += _spouse_loan_gaps(inputs, answers)
    gaps += _vehicle_gaps(inputs, tables, answers)
    for line in (16, 17, 18, 19, 20, 21):
        if answers[f"line_{line}"] is None:
            gaps.append(MEANS_GAP_AMOUNT.format(n=line))
    gaps += _opt_in_gaps(answers, 22)
    if answers["line_23"] is None:
        gaps.append(MEANS_GAP_AMOUNT.format(n=23))
    gaps += _line_25_gaps(answers)
    for line in range(26, 32):
        gaps += _opt_in_gaps(answers, line)
        if line == 30:
            gaps += _line_30_cap_gap(inputs, tables, answers)
    gaps += _debt_gaps(inputs, answers, debt_lines(inputs))
    if answers["line_36_answer"] is None:
        gaps.append(MEANS_GAP_LINE_36)
    elif answers["line_36_answer"] == "yes" and answers["line_36_payment"] is None:
        gaps.append(MEANS_GAP_LINE_36_PAYMENT)
    gaps += _line_43_gaps(answers)
    return gaps
