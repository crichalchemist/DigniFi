"""What Schedule C copies from Schedule A/B: a row's name, the line A/B prints for it, the value A/B
prints in its portion box, and whether its name fits Schedule C's description box (3g1 B6, B12,
B13, B16).

Worked out from A/B's own schema and index, so the line a filer sees on the exemptions page is
the one printed on A/B, a sheet's number included.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache, partial

from apps.forms.field_index import index_path
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import ASSET_CELLS
from apps.forms.services.pdf_filler import _as_printed, _refused_letter
from apps.forms.services.text_fit import fit, font_for, printable
from apps.forms.services.widgets import template_widgets
from apps.intake.asset_lines import LINE_BY_KEY, exemption_item_name, ordered_assets, rows_on
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
