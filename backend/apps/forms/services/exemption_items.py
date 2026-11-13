"""What Schedule C copies from Schedule A/B: a row's name, the line A/B prints for it, the value A/B
prints in its portion box, and whether its name fits Schedule C's description box (3g1 B6, B12,
B13, B16).

Worked out from A/B's own schema and index, so the line a filer sees on the exemptions page is
the one printed on A/B, a sheet's number included.

It also says what Schedule C prints (3g2): `exemption_rows` turns the filer's claims into the rows
of its slots, each cell a string, and `exemption_answer` reads lines 1, 3 and 3-1. Nothing there
chooses a law, an amount or an answer: each is the filer's own, and the rest is copied from A/B.
"""

import json
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import cache, partial

from apps.districts.exemptions import exemption_catalog_in_force
from apps.forms.field_index import index_path
from apps.forms.schema import load_schema
from apps.forms.services.derivations import money_or_blank
from apps.forms.services.fill_resolver import ASSET_CELLS
from apps.forms.services.pdf_filler import _as_printed, _refused_letter
from apps.forms.services.text_fit import fit, font_for, printable
from apps.forms.services.widgets import template_widgets
from apps.intake.asset_lines import LINE_BY_KEY, exemption_item_name, ordered_assets, rows_on
from apps.intake.exemptions import ordered_claims
from apps.intake.models import AssetInfo

SCHEDULE_C = "b_106c_0425-form.pdf"
_AB = "schedule_a_b"
_SLOT_BINDING = re.compile(r"assets\.line_(\d+)(?:_(\w+))?\[\]\.(\w+)")


@dataclass(frozen=True)
class ExemptionItem:
    id: int
    name: str
    line_label: str
    value: str | None
    description_fits: bool


@dataclass(frozen=True)
class _Group:
    capacity: int
    number: str
    labels: dict[int, str]  # slot row → the line A/B prints for it


@cache
def _groups() -> dict[tuple[str, str | None], _Group]:
    """Each A/B repeat group by (line, kind), with the label of every slot row."""
    schema = load_schema(_AB)
    index = json.loads(index_path(schema.template_filename).read_text())
    lines: dict[tuple[str, int, str | None], set[str]] = {}
    for widget in index:
        label = (widget.get("line") or "").rstrip(".").strip()
        if label:
            lines.setdefault((widget["full_name"], widget["page"], widget["tag"]), set()).add(label)

    groups: dict[tuple[str, str | None], _Group] = {}
    for name, spec in schema.groups.items():
        slots = [f for f in schema.fields if f.repeat == name]
        if not slots:
            continue
        keys = set()
        for field in slots:
            match = _SLOT_BINDING.fullmatch(field.binding or "")
            if match:
                keys.add((match.group(1), match.group(2)))
        if len(keys) != 1:
            raise ValueError(f"A/B group {name} binds {len(keys)} lines, not one")
        key = keys.pop()
        found: dict[int, set[str]] = {}
        for field in slots:
            labels = found.setdefault(field.row, set())
            for (full_name, page, tag), names in lines.items():
                if full_name == field.pdf_field and page == field.page:
                    if field.tag is None or tag == field.tag:
                        labels |= names
        capacity = slots[0].repeat_capacity
        for row in range(1, capacity + 1):
            if len(found.get(row, ())) != 1:
                raise ValueError(f"A/B group {name} row {row} has no single label")
        groups[key] = _Group(capacity, spec.number, {row: next(iter(found[row])) for row in found})
    return groups


def _group_of(row: AssetInfo) -> tuple[tuple[str, str | None], _Group | None]:
    line = LINE_BY_KEY[row.ab_line]
    kind = row.get_details().get("kind") if line.kinds else None
    key = (row.ab_line, kind)
    return key, _groups().get(key)


def ab_line_label(rows: Sequence[AssetInfo], row: AssetInfo) -> str:
    """The line A/B prints for a row: a box's own label, else the sheet's number (B13)."""
    key, group = _group_of(row)
    if group is None:
        return row.ab_line
    siblings = sorted(rows_on(list(rows), *key), key=lambda r: r.pk)
    position = 1 + [r.pk for r in siblings].index(row.pk)
    if position <= group.capacity:
        return group.labels[position]
    return group.number.format(n=position)


def ab_value(row: AssetInfo) -> str | None:
    """The value A/B prints in the row's portion box; None when unknown or A/B prints none (B16)."""
    _, group = _group_of(row)
    if group is None:
        return None
    return ASSET_CELLS["value"](row) or None


def _widget(name: str):
    for widget in template_widgets(SCHEDULE_C):
        if widget.full_name == name and widget.page == 1:
            return widget
    raise ValueError(f"Schedule C has no box {name}")


def _fits(name: str, text: str) -> bool:
    widget = _widget(name)
    printed = _as_printed(text)
    prints = partial(printable, font_for(SCHEDULE_C, widget.font))
    if _refused_letter(printed, prints, widget.comb) is not None:
        return False
    return fit(widget, SCHEDULE_C, printed) is not None


def fits_description(text: str) -> bool:
    """The text prints in Schedule C's description box, letters and size alike (B6, P10)."""
    return _fits("description", text)


def fits_law(text: str) -> bool:
    """The text prints in Schedule C's law box, letters and size alike (B6, P10)."""
    return _fits("2.1", text)


def exemption_items(session) -> list[ExemptionItem]:
    """Every row of the session with an A/B line, in A/B order."""
    rows = ordered_assets(session)
    items = []
    for row in rows:
        if row.ab_line not in LINE_BY_KEY:
            continue
        name = exemption_item_name(row)
        items.append(
            ExemptionItem(
                id=row.pk,
                name=name,
                line_label=ab_line_label(rows, row),
                value=ab_value(row),
                description_fits=fits_description(name),
            )
        )
    return items


@dataclass(frozen=True, repr=False)
class ExemptionRow:
    """One claim as Schedule C prints it: every cell a string, "" when blank (3g2 R3-R8)."""

    description: str
    line: str
    value: str
    amount_kind: str
    amount: str
    law: str


# Session id -> its rows, while one_read_of_exemptions is open (as claim_rows.one_read_of_claims).
_ONE_READ: ContextVar[dict | None] = ContextVar("one_read_of_exemptions", default=None)


@contextmanager
def one_read_of_exemptions() -> Iterator[None]:
    """Within the block, exemption_rows reads each session's rows once: every box asks (R2)."""
    token = _ONE_READ.set({})
    try:
        yield
    finally:
        _ONE_READ.reset(token)


def _read_rows(session) -> list[ExemptionRow]:
    items = exemption_items(session)
    by_id = {item.id: item for item in items}
    # A claim with no live item never prints: the gate refuses it, but a resolve can run ungated.
    claims = ordered_claims(
        [c for c in session.exemption_claims.all() if c.asset_id in by_id], items
    )
    citations: dict[str, str] = {}
    if any(c.law is not None for c in claims):
        # Read only when a printed claim names a law; no list in force propagates, as the gate's does.
        laws = exemption_catalog_in_force().laws.all()
        citations = {law.key: law.citation for law in laws}
    rows = []
    for claim in claims:
        item = by_id[claim.asset_id]
        short = (claim.short_description or "").strip()
        # R4: the short words print only while the item's name doesn't fit.
        description = short if short and not item.description_fits else item.name
        if claim.law is not None:
            law = citations.get(claim.law, "")
        else:
            law = (claim.other_law or "").strip()
        rows.append(
            ExemptionRow(
                description=description,
                line=item.line_label,
                value=item.value or "",
                amount_kind=claim.amount_kind or "",
                amount=money_or_blank(claim.amount) if claim.amount_kind == "dollars" else "",
                law=law,
            )
        )
    return rows


def exemption_rows(session) -> list[ExemptionRow]:
    """The rows Schedule C prints, in print order; held once under one_read_of_exemptions."""
    held = _ONE_READ.get()
    if held is not None and session.pk in held:
        return held[session.pk]
    rows = _read_rows(session)
    if held is not None:
        held[session.pk] = rows
    return rows


def exemption_answer(session, key: str) -> str:
    """Line 1, line 3 or line 3-1 as the filer answered; "" when unanswered (R7)."""
    answers = getattr(session, "exemption_answers", None)
    if answers is None:
        return ""
    if key == "line_3_1" and answers.line_3 != "yes":
        return ""
    return getattr(answers, key) or ""
