"""
Every gap Schedule C's exemptions page leaves, in page order (3g1 §5.5, P6, P14).

Pure: no model and nothing from apps.forms or apps.districts. The caller supplies the items
(each with `id`, `name` and `description_fits`) and the keys of the laws in force. The page's
`exemptionGaps.ts` copies this; each sentence is one literal in `copy.ts`, pinned by
`test_exemption_copy.py`.
"""

from collections.abc import Collection, Iterable, Sequence

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
