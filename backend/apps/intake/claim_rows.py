"""The rows Schedules D, E/F, G and H print (3c5 spec §9), read once.

Business intent: every confirmed debt, notice party, contract and codebtor sits on its own row,
numbered over the printed lists alone, so a draft never shifts a line and every citation (D
Part 2, E/F Part 3, H) names the line its row prints on. A row prints an answer only where
claim_step_gaps would ask for it (R4): the filer can't see the rest.

The module imports no models: it reads a session's relations by attribute, as claims.py does.
Formatting to text is CLAIM_CELLS' job in fill_resolver.py.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from apps.intake.claims import PRIORITY_TYPES, asks_who, link_is_live, ordered_debts

CLAIM_LISTS = (
    "secured",
    "secured_notices",
    "priority",
    "unsecured",
    "unsecured_notices",
    "contracts",
    "codebtors",
)

# The wizard's words (constants/claims.ts); test_claims_frontend_copy.py pins them.
DEBT_TYPE_WORDS = {
    "credit_card": "Credit card",
    "medical": "Medical bill",
    "personal_loan": "Personal loan",
    "student_loan": "Student loan",
    "auto_loan": "Car or vehicle loan",
    "mortgage": "Mortgage or home loan",
    "utility": "Utility bill",
    "other": "Other amount owed",
}

_ONLY_YOU = "only_you"
_PER_BOX = 2  # R6: a H row's box holds at most two citations


@dataclass(frozen=True)
class DebtRow:
    line: str
    debt: Any
    with_another: bool
    value: Decimal | None
    unsecured: Decimal | None


@dataclass(frozen=True)
class NoticeRow:
    line: str
    party: dict
    part: str = ""


@dataclass(frozen=True)
class ContractRow:
    line: str
    contract: Any


@dataclass(frozen=True)
class CodebtorRow:
    codebtor: Any
    d_lines: tuple[str, ...]
    ef_lines: tuple[str, ...]
    g_lines: tuple[str, ...]


@dataclass(frozen=True)
class ClaimRows:
    secured: tuple[DebtRow, ...]
    secured_notices: tuple[NoticeRow, ...]
    priority: tuple[DebtRow, ...]
    unsecured: tuple[DebtRow, ...]
    unsecured_notices: tuple[NoticeRow, ...]
    contracts: tuple[ContractRow, ...]
    codebtors: tuple[CodebtorRow, ...]


# Session id -> its rows, while one_read_of_claims is open (as asset_lines.one_read_of_assets).
_ONE_READ: ContextVar[dict | None] = ContextVar("one_read_of_claims", default=None)


@contextmanager
def one_read_of_claims() -> Iterator[None]:
    """Within the block, claim_rows reads each session's rows once: every binding asks."""
    token = _ONE_READ.set({})
    try:
        yield
    finally:
        _ONE_READ.reset(token)


def _column_b(debt, linked, shared: bool) -> Decimal | None:
    """Column B (R5): the value of the property when the filer owns it alone, else None."""
    if linked is None or shared:
        return None
    if asks_who(linked):
        if linked.get_details().get("who") == _ONLY_YOU:
            return linked.entire_value
        return None
    if debt.collateral_who == _ONLY_YOU:
        return linked.current_value
    return None


def _debt_rows(debts, prefix: str, with_another: set, session, secured: bool) -> tuple:
    links = {}
    if secured:
        for debt in debts:
            if link_is_live(debt.secured_by, session):
                links[debt.pk] = debt.secured_by_id
    counts = {}
    for asset_id in links.values():
        counts[asset_id] = counts.get(asset_id, 0) + 1
    rows = []
    for number, debt in enumerate(debts, start=1):
        value = unsecured = None
        if secured and debt.pk in links:
            value = _column_b(debt, debt.secured_by, counts[links[debt.pk]] > 1)
        if value is not None:
            unsecured = max(Decimal("0"), debt.amount_owed - value)
        rows.append(DebtRow(f"{prefix}.{number}", debt, debt.pk in with_another, value, unsecured))
    return tuple(rows)


def _notice_rows(rows, part: str = "") -> tuple:
    return tuple(
        NoticeRow(row.line, party, part)
        for row in rows
        for party in (row.debt.get_notice_parties() or [])
    )


def _chunks(lines: list[str]) -> list[tuple[str, ...]]:
    return [tuple(lines[i : i + _PER_BOX]) for i in range(0, len(lines), _PER_BOX)]


def _codebtor_rows(codebtors, secured, priority, unsecured, contracts) -> tuple:
    d_line = {("debt", row.debt.pk): row.line for row in secured}
    # Part 1's lines come before Part 2's (B12)
    ef_line = {("debt", row.debt.pk): row.line for row in (*priority, *unsecured)}
    g_line = {("contract", row.contract.pk): row.line for row in contracts}
    rows = []
    for codebtor in codebtors:
        keys = {(link.get("kind"), link.get("id")) for link in codebtor.get_links()}
        chunks = [
            _chunks([line for key, line in table.items() if key in keys])
            for table in (d_line, ef_line, g_line)
        ]
        for k in range(max(1, *(len(c) for c in chunks))):
            d, ef, g = (c[k] if k < len(c) else () for c in chunks)
            rows.append(CodebtorRow(codebtor, d, ef, g))
    return tuple(rows)


def _read(session) -> ClaimRows:
    debts = ordered_debts(list(session.debts.confirmed().select_related("secured_by")))
    contracts = sorted(session.executory_contracts.all(), key=lambda row: row.pk)
    codebtors = sorted(session.codebtors.all(), key=lambda row: row.pk)
    contract_rows = tuple(ContractRow(f"2.{n}", c) for n, c in enumerate(contracts, start=1))
    secured_debts = [d for d in debts if d.is_secured]
    unsecured_debts = [d for d in debts if not d.is_secured]
    # a codebtor's link to a debt makes it owed with another (R3): live links only
    debt_ids = {d.pk for d in debts}
    with_another = {
        link.get("id")
        for codebtor in codebtors
        for link in codebtor.get_links()
        if link.get("kind") == "debt" and link.get("id") in debt_ids
    }
    secured = _debt_rows(secured_debts, "2", with_another, session, True)
    # the filer's answer alone moves a debt into E/F Part 1 (B15)
    priority_debts = [d for d in unsecured_debts if d.priority_answer in PRIORITY_TYPES]
    part_2_debts = [d for d in unsecured_debts if d.priority_answer not in PRIORITY_TYPES]
    priority = _debt_rows(priority_debts, "2", with_another, session, False)
    unsecured = _debt_rows(part_2_debts, "4", with_another, session, False)
    return ClaimRows(
        secured=secured,
        secured_notices=_notice_rows(secured),
        priority=priority,
        unsecured=unsecured,
        unsecured_notices=_notice_rows(priority, "1") + _notice_rows(unsecured, "2"),
        contracts=contract_rows,
        codebtors=_codebtor_rows(codebtors, secured, priority, unsecured, contract_rows),
    )


def claim_rows(session) -> ClaimRows:
    """The seven lists (R2), read once within one_read_of_claims."""
    held = _ONE_READ.get()
    if held is not None and session.pk in held:
        return held[session.pk]
    rows = _read(session)
    if held is not None:
        held[session.pk] = rows
    return rows


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def community_answers(session) -> dict[str, str]:
    """H line 2's answers, gated as _community_gaps asks them (R4); "" where not asked."""
    row = getattr(session, "claim_answers", None)
    answers = row.get_answers() if row is not None else {}
    keys = (
        "lived",
        "spouse_lived_with",
        "state",
        "spouse_name",
        "spouse_street",
        "spouse_street_2",
        "spouse_city",
        "spouse_state",
        "spouse_zip",
    )
    result = dict.fromkeys(keys, "")
    lived = _text(answers.get("community_lived"))
    result["lived"] = lived
    if lived != "yes":
        return result
    with_spouse = _text(answers.get("community_spouse_lived_with"))
    result["spouse_lived_with"] = with_spouse
    if with_spouse != "yes":
        return result
    stored = {
        "state": "community_state",
        "spouse_name": "community_spouse_name",
        "spouse_street": "community_spouse_street_address",
        "spouse_street_2": "community_spouse_street_2",
        "spouse_city": "community_spouse_city",
        "spouse_state": "community_spouse_state",
        "spouse_zip": "community_spouse_zip_code",
    }
    for key, name in stored.items():
        result[key] = _text(answers.get(name))
    if answers.get("community_spouse_outside_us") is True:
        result["spouse_state"] = ""
        result["spouse_zip"] = ""
    return result
