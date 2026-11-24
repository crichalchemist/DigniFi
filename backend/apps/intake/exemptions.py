"""
Every gap Schedule C's exemptions page leaves, in page order (3g1 §5.5, P6, P14).

Pure: no model and nothing from apps.forms or apps.districts. The caller supplies the items
(each with `id`, `name` and `description_fits`) and the keys of the laws in force. The page's
`exemptionGaps.ts` copies this; each sentence is one literal in `copy.ts`, pinned by
`test_exemption_copy.py`.

Also each secured debt's exempt state for Form 108 (`exempt_states`, 4e-R6), from the page's
own answers.
"""

from collections.abc import Collection, Iterable, Sequence

from apps.intake.asset_lines import LINE_BY_KEY
from apps.intake.claims import link_is_live

EXEMPTION_GAP_LINE_1 = "Choose which set of exemptions you are claiming."
EXEMPTION_GAP_NO_CLAIMS = (
    "Add the property you claim as exempt, or press “I'm not claiming any property as exempt.”"
)
EXEMPTION_GAP_NO_ITEMS = "Press “I'm not claiming any property as exempt.”"
EXEMPTION_GAP_ITEM_GONE = (
    "One claim is for property that is no longer on your property list."
    " Remove it or choose the property again."
)
EXEMPTION_GAP_LAW = "Choose the law for {name}."
EXEMPTION_GAP_LAW_CHANGED = (
    "The list of laws has changed since you chose a law for {name}. Choose a law again."
)
EXEMPTION_GAP_AMOUNT_KIND = "Choose a dollar amount or 100% of fair market value for {name}."
EXEMPTION_GAP_AMOUNT = "Enter the dollar amount you claim for {name}."
EXEMPTION_GAP_DESCRIPTION = "Type a shorter description of {name} for Schedule C."
EXEMPTION_GAP_LINE_3 = "Answer line 3, the homestead question."
EXEMPTION_GAP_LINE_3_1 = "Answer the second part of line 3."


def ordered_claims(claims: Iterable, items: Sequence) -> list:
    """Claims in print order: the item's A/B position, then claim id; no live item last (P14)."""
    position = {item.id: index for index, item in enumerate(items)}
    return sorted(claims, key=lambda c: (position.get(c.asset_id, len(position)), c.pk))


def _claim_gap(claim, item, law_keys: Collection[str]) -> str | None:
    if item is None:
        return EXEMPTION_GAP_ITEM_GONE
    name = item.name
    if claim.law is None and not (claim.other_law or "").strip():
        return EXEMPTION_GAP_LAW.format(name=name)
    if claim.law is not None and claim.law not in law_keys:
        return EXEMPTION_GAP_LAW_CHANGED.format(name=name)
    if claim.amount_kind is None:
        return EXEMPTION_GAP_AMOUNT_KIND.format(name=name)
    if claim.amount_kind == "dollars" and claim.amount is None:
        return EXEMPTION_GAP_AMOUNT.format(name=name)
    if not item.description_fits and not (claim.short_description or "").strip():
        return EXEMPTION_GAP_DESCRIPTION.format(name=name)
    return None


def exemption_gaps(session, items: Sequence, law_keys: Collection[str]) -> list[str]:
    """Each gap's sentence, in the order the page asks."""
    answers = getattr(session, "exemption_answers", None)
    claims = list(session.exemption_claims.all())
    gaps = []
    if answers is None or answers.line_1 is None:
        gaps.append(EXEMPTION_GAP_LINE_1)
    if not claims and not (answers is not None and answers.no_claims):
        gaps.append(EXEMPTION_GAP_NO_CLAIMS if items else EXEMPTION_GAP_NO_ITEMS)
    by_id = {item.id: item for item in items}
    for claim in ordered_claims(claims, items):
        gap = _claim_gap(claim, by_id.get(claim.asset_id), law_keys)
        if gap is not None:
            gaps.append(gap)
    line_3 = answers.line_3 if answers is not None else None
    if line_3 is None:
        gaps.append(EXEMPTION_GAP_LINE_3)
    elif line_3 == "yes" and answers.line_3_1 is None:
        gaps.append(EXEMPTION_GAP_LINE_3_1)
    return gaps


# Form 108's "Did you claim the property as exempt on Schedule C?" for a secured debt (R-EXEMPT,
# 4e-R6). Only two states tick a box: a claim Schedule C prints is Yes, and "I'm not claiming any
# property as exempt" is No. Every other state prints blank, never a No the filer didn't give.
EXEMPT_LISTED = "listed"
EXEMPT_NOT_CLAIMING = "not_claiming"
EXEMPT_LATER = "later"
EXEMPT_NOT_NAMED = "not_named"
EXEMPT_NO_PROPERTY = "no_property"
EXEMPT_BOX = {EXEMPT_LISTED: "yes", EXEMPT_NOT_CLAIMING: "no"}


def exempt_states(session) -> dict[int, str]:
    """Each secured debt's exempt state, drafts included, by debt id.

    In this order: "not claiming" on the exemptions page; no live link to property; the linked
    row has a claim Schedule C prints (a claim on a row of this session with an A/B line, as
    exemption_items reads them); the page never answered and no claim; else not named.
    The debts are a fresh read, never a prefetch: a save's reply must see the debts it wrote.
    """
    answers = getattr(session, "exemption_answers", None)
    claims = list(session.exemption_claims.all())
    lined = {row.pk for row in session.assets.all() if row.ab_line in LINE_BY_KEY}
    printed = {claim.asset_id for claim in claims if claim.asset_id in lined}
    states = {}
    for debt in session.debts.select_related("secured_by"):
        if not debt.is_secured:
            continue
        if answers is not None and answers.no_claims:
            state = EXEMPT_NOT_CLAIMING
        elif not link_is_live(debt.secured_by, session):
            state = EXEMPT_NO_PROPERTY
        elif debt.secured_by_id in printed:
            state = EXEMPT_LISTED
        elif answers is None and not claims:
            state = EXEMPT_LATER
        else:
            state = EXEMPT_NOT_NAMED
        states[debt.pk] = state
    return states
