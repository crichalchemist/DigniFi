"""The 122A-2 page's answers: their keys, how a stale reference reads, and the page's gaps. Pure: no models, no forms module."""

import copy
from collections.abc import Collection, Mapping

from apps.eligibility.means_lines import is_spouse_ref

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
MEANS_EXPLANATION_TOO_LONG = "This explanation is too long to print with line 43. Shorten it."
MEANS_EXPLANATION_LETTER = "This explanation has a letter Form 122A-2 can't print. Change it."
NOT_A_MEANS_ANSWER = "This is not one of the means test answers."


def _unanswered(key: str):
    if key in LIST_KEYS:
        return []
    if key == "vehicle_claims":
        return {}
    if key == "vehicle_choice":
        return [None, None]
    return None


def normalized_answers(
    stored: Mapping, filer_vehicles: Collection[str], open_debts: Collection[int]
) -> dict:
    """Every answer key, a reference to a row that has gone read as unanswered. Copies; never
    changes `stored`.

    `filer_vehicles` holds the refs of the filer's Schedule A/B vehicles, `open_debts` the ids of
    the confirmed debts Amounts Owed doesn't list as secured.
    """
    out = {}
    for key in ANSWER_KEYS:
        value = stored.get(key)
        out[key] = _unanswered(key) if value is None else copy.deepcopy(value)

    out["vehicle_claims"] = {
        ref: answer for ref, answer in out["vehicle_claims"].items() if ref in filer_vehicles
    }
    live = set(filer_vehicles)
    if out["spouse_vehicles_answer"] == "yes":
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
