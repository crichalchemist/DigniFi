"""What Form 108's answers still leave open, and which claims texts are too long for their boxes
(forms step 4e, 4e-R4, 4e-R11, E4, R-EXPLAIN).

Every gap here is a detail: Complete lets each through, and never through claim_step_gaps, whose
gaps are all gates. The filer decides each choice; a choice left open, or "[explain]" with no
words, prints no choice on Form 108, and Review names the row.

A text is listed too long when it is over its row's cap (the smallest cap among the boxes of the
row's own list, from form_108.limits.json, by length, as the browser's note counts) or when a box
it prints in can't take it (`intention_fit.too_long_texts`, measured by check()). The sentence
names the forms holding that cap and the forms whose box refuses it, never a form the row doesn't
print on. Generate refuses only what check() refuses.

`Gap` is imported inside each function (completion.py imports the forms registry), as
schedule_i.py does.
"""

import json
from collections.abc import Mapping
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .claim_rows import _entries, _entry, claim_rows, one_read_of_claims
from .claims import NAMELESS_CONTRACT, NAMELESS_DEBT, claim_row_name, is_form_108_lease
from .models import IntentionAnswers
from .schedule_i import DETAIL_TOO_LONG

# Approved by the owner on 2026-11-24 (E7, with E8's two rewordings); still in counsel's C-37
# review. The browser's copies are in frontend/src/constants/copy.ts. {name} is the creditor's
# or lessor's name, or "one amount owed" / "one contract" (4e-R21).
# DRAFT: counsel C-37
INTENTION_GAP_NONE = (
    "Choose what you plan to do with the property for {name}, or say you haven't decided."
)
# DRAFT: counsel C-37
INTENTION_GAP_UNDECIDED = "Your choice for {name} is open, so Form 108 shows no choice for it."
# DRAFT: counsel C-37
INTENTION_GAP_EXPLAIN = "Type your words for {name}, or choose another answer."
# DRAFT: counsel C-37
LEASE_GAP_NONE = "Say if the lease with {name} will be assumed, or that you haven't decided yet."
# DRAFT: counsel C-37
LEASE_GAP_UNDECIDED = (
    "Your answer for the lease with {name} is open, so Form 108 shows no answer for it."
)

UNDECIDED = "undecided"
RETAIN_EXPLAIN = "retain_explain"
# Form 108 Part 1's four choices and Part 2's two answers: a row with one of them is chosen.
_CHOSEN_INTENTIONS = IntentionAnswers.FORM_INTENTIONS
_CHOSEN_ASSUMED = tuple(answer for answer in IntentionAnswers.ASSUMED if answer != UNDECIDED)

# The stored texts the boxes print, and the "[explain]" words.
CLAIM_TEXT_KEYS = (
    "creditor_name",
    "collateral_description",
    "counterparty_name",
    "description",
    "explain",
)

# (text, the row's list) -> the boxes that print it, "<form>:<binding>" (4e-R4's table). A lease
# Form 108 asks about is in "leases"; a residential lease only in Schedule G's "contracts".
ROW_BOXES: dict[tuple[str, str], tuple[str, ...]] = {
    ("creditor_name", "secured"): (
        "form_108:claims.secured[].name",
        "schedule_d:claims.secured[].name",
    ),
    ("creditor_name", "priority"): ("schedule_e_f:claims.priority[].name",),
    ("creditor_name", "unsecured"): ("schedule_e_f:claims.unsecured[].name",),
    ("collateral_description", "secured"): (
        "form_108:claims.secured[].property",
        "schedule_d:claims.secured[].property",
    ),
    ("counterparty_name", "leases"): (
        "schedule_g:claims.contracts[].name",
        "form_108:claims.leases[].name",
    ),
    ("counterparty_name", "contracts"): ("schedule_g:claims.contracts[].name",),
    ("description", "leases"): (
        "schedule_g:claims.contracts[].purpose",
        "form_108:claims.leases[].purpose",
    ),
    ("description", "contracts"): ("schedule_g:claims.contracts[].purpose",),
    ("explain", "secured"): ("form_108:explain",),
}

# The forms' names in a sentence, in packet order.
FORM_WORDS = {
    "form_108": "Form 108",
    "schedule_d": "Schedule D",
    "schedule_e_f": "Schedule E/F",
    "schedule_g": "Schedule G",
}


def _read_limits() -> dict:
    # Read unconditionally: a missing file fails at import, never as a text with no cap.
    path = Path(settings.FORM_SCHEMAS_DIRECTORY) / "form_108.limits.json"
    read = json.loads(path.read_text())
    boxes, labels = read.get("boxes") or {}, read.get("labels") or {}
    for keys in ROW_BOXES.values():
        for key in keys:
            if key not in boxes:
                raise ImproperlyConfigured(f"{key} has no cap in form_108.limits.json")
    for key in CLAIM_TEXT_KEYS:
        if key not in labels:
            raise ImproperlyConfigured(f"{key} has no label in form_108.limits.json")
    return read


_LIMITS = _read_limits()
CLAIM_BOX_CAPS: dict[str, int] = _LIMITS["boxes"]
# {label} in DETAIL_TOO_LONG, approved by the owner (E7, E8)
# DRAFT: counsel C-37
CLAIM_TEXT_LABELS: dict[str, str] = _LIMITS["labels"]


def row_cap(text: str, list_name: str) -> tuple[int, tuple[str, ...]]:
    """The smallest cap among the boxes of the row's own list, and the forms holding it, in packet
    order."""
    keys = ROW_BOXES[(text, list_name)]
    cap = min(CLAIM_BOX_CAPS[key] for key in keys)
    holders = {key.split(":")[0] for key in keys if CLAIM_BOX_CAPS[key] == cap}
    return cap, tuple(form for form in FORM_WORDS if form in holders)


def contract_text_list(contract) -> str | None:
    """The list a contract's texts are measured in: "leases" for a lease Form 108 asks about
    (is_form_108_lease), "contracts" for a residential lease (Schedule G only), and None for a
    contract that isn't a lease, whose texts no approved label fits (4e-R4)."""
    if contract.contract_type != "lease":
        return None
    return "leases" if is_form_108_lease(contract) else "contracts"


def intention_row_gap(name: str, entry: Mapping) -> str | None:
    """A secured row's open choice in the filer's words, from the stored entry: none chosen,
    "I haven't decided yet.", or "[explain]" whose words are blank (R-BLANK-EXPLAIN); else None.
    """
    intention = entry.get("intention")
    if intention == UNDECIDED:
        return INTENTION_GAP_UNDECIDED.format(name=name)
    if intention == RETAIN_EXPLAIN and not str(entry.get("explain") or "").strip():
        return INTENTION_GAP_EXPLAIN.format(name=name)
    if intention in _CHOSEN_INTENTIONS:
        return None
    return INTENTION_GAP_NONE.format(name=name)


def lease_row_gap(name: str, entry: Mapping) -> str | None:
    """A lease's open answer in the filer's words, from the stored entry; else None."""
    assumed = entry.get("assumed")
    if assumed == UNDECIDED:
        return LEASE_GAP_UNDECIDED.format(name=name)
    if assumed in _CHOSEN_ASSUMED:
        return None
    return LEASE_GAP_NONE.format(name=name)


def intention_step_gaps(session) -> list:
    """Each open row of Your Plans, one detail at most a row, in Form 108's order: Part 1 in
    Schedule D's order, then Part 2's leases."""
    from .completion import Gap

    rows = claim_rows(session)
    record = getattr(session, "intention_answers", None)
    secured, leases = _entries(record, "secured"), _entries(record, "leases")
    sentences = [
        intention_row_gap(
            claim_row_name(row.debt.creditor_name, NAMELESS_DEBT), _entry(secured, row.debt.pk)
        )
        for row in rows.secured
    ] + [
        lease_row_gap(
            claim_row_name(row.contract.counterparty_name, NAMELESS_CONTRACT),
            _entry(leases, row.contract.pk),
        )
        for row in rows.leases
    ]
    return [Gap(s, "plans", Gap.DETAIL, forms=("form_108",)) for s in sentences if s]


def claim_text_gaps(session) -> list:
    """Each claims text too long for its row's boxes: the Amounts Owed step's (each debt in
    Schedule D's then E/F's order, its name then its property), the Contracts & Leases step's
    (each lease by id, its lessor then its description), then Your Plans' "[explain]" words,
    measured only under a stored retain_explain (4e-R16). One detail a text a row."""
    # Imported here: the forms' measure imports most of the forms app.
    from apps.forms.services.intention_fit import too_long_texts

    from .completion import Gap

    with one_read_of_claims():
        rows = claim_rows(session)
        refused = too_long_texts(session, CLAIM_TEXT_KEYS)
    secured_entries = _entries(getattr(session, "intention_answers", None), "secured")
    gaps = []

    def check(kind: str, pk: int, text: str, list_name: str, value, step: str) -> None:
        if not isinstance(value, str) or not value:
            return
        cap, cap_forms = row_cap(text, list_name)
        forms = set(refused.get((kind, pk, text), ()))
        # The "[explain]" words print trimmed (F6), so their cap counts them trimmed (T5-R1); a
        # name or description counts as stored
        if len(value.strip() if text == "explain" else value) > cap:
            forms |= set(cap_forms)
        if forms:
            ordered = tuple(form for form in FORM_WORDS if form in forms)
            sentence = DETAIL_TOO_LONG.format(
                label=CLAIM_TEXT_LABELS[text],
                form=" and ".join(FORM_WORDS[form] for form in ordered),
            )
            gaps.append(Gap(sentence, step, Gap.DETAIL, forms=ordered))

    for list_name in ("secured", "priority", "unsecured"):
        for row in getattr(rows, list_name):
            debt = row.debt
            check("debt", debt.pk, "creditor_name", list_name, debt.creditor_name, "debts")
            if list_name == "secured":
                check(
                    "debt",
                    debt.pk,
                    "collateral_description",
                    list_name,
                    debt.collateral_description,
                    "debts",
                )
    for row in rows.contracts:
        contract = row.contract
        list_name = contract_text_list(contract)
        if list_name is None:
            continue
        for text in ("counterparty_name", "description"):
            check("lease", contract.pk, text, list_name, getattr(contract, text), "contracts")
    for row in rows.secured:
        if _entry(secured_entries, row.debt.pk).get("intention") == RETAIN_EXPLAIN:
            check("debt", row.debt.pk, "explain", "secured", row.explain, "plans")
    return gaps
