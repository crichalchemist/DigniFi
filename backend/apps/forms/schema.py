"""
Schema dataclasses and loader for form field specifications.

Provides FieldSpec (individual field definition) and FormSchema (complete form specification),
plus load_schema() function to load form schemas from JSON files.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pypdf
from django.conf import settings

from apps.forms.field_index import export_state, load_index
from apps.forms.services.widgets import (
    TemplateMismatch,
    TemplateWidget,
    parse_key,
    template_widgets,
)


@dataclass(frozen=True)
class UIFieldSpec:
    step: str
    prompt: str
    widget: str
    help_text: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> UIFieldSpec:
        return cls(
            step=data.get("step", "Unknown Step"),
            prompt=data.get("prompt", ""),
            widget=data.get("widget", "text"),
            help_text=data.get("help_text"),
        )


@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single form field."""

    pdf_field: str  # an index full_name (apps.forms.field_index)
    type: str  # text | checkbox | radio | choice
    source: str  # constant | derived | asked | ingested | signature
    page: int
    label: str
    required: bool
    conditional_on: str | None  # PREDICATES key, or None = always applicable
    value: str | None
    rule: str | None
    ingest_key: str | None
    binding: str | None
    repeat: str | None
    repeat_capacity: int | None
    row: int | None
    legal_review: bool
    # checkbox/radio only: normalised answer → export state. {"true": state} is
    # a single box; {} means not mapped yet, and the binding emits nothing.
    choices: dict[str, str] | None = None
    # One widget of pdf_field: its index tag on `page`. None fills every widget of the name.
    tag: str | None = None
    ui: UIFieldSpec | None = None


@dataclass(frozen=True)
class PageNumberBoxes:
    """One template page's page-number boxes: `this` shows its position, `of` the page count."""

    page: int
    this: str | None  # a values key, or None when the page has no such box
    of: str | None


@dataclass(frozen=True)
class SheetColumn:
    """One column of an attached sheet: its label, the list binding its cells print, its width."""

    label: str
    binding: str  # "sofa.<collection>[].<attr>", "household.dependents[].<attr>" or "assets.…"
    width: float  # points
    # The slot bindings this column prints in words (3b spec §8.3). Its own binding then needs
    # no slot, and () prints a list the slots don't bind. None is an ordinary column.
    covers: tuple[str, ...] | None = None


@dataclass(frozen=True)
class SheetSpec:
    """An attached sheet (3a2 spec §5.3): the form's title, and the columns of the group's row."""

    title: str
    columns: tuple[SheetColumn, ...]
    line_width: float = 36.0  # points, the column that labels each row with its line


@dataclass(frozen=True)
class GroupTotals:
    """
    A group's total boxes (3c spec §5.3): each page prints the sum of its own rows' `column` in
    the box `page_boxes` names for it, and the last page prints every row's sum in `last_page_box`.
    """

    column: str  # the slots' list binding, "sofa.<collection>[].<attr>", whose amounts add up
    page_boxes: dict[int, str]  # template page → the key of the box that page's sum prints in
    last_page_box: str | None  # the key of the box the last page prints the whole sum in


@dataclass(frozen=True)
class GroupSpec:
    """
    A repeat group's declaration (3a2 spec §5.2, §5.3): the template page whose copies take
    the rows past its last slot, or the attached sheet that takes them, and the boxes that
    number the rows and the pages.
    """

    name: str
    extra_page: int | None
    number: str | None  # the entry number, such as "2.{n}", n the row's position in the group
    number_boxes: dict[int, str]  # slot row → the key of that slot's entry-number box
    sheet: SheetSpec | None = None
    totals: GroupTotals | None = None


def total_box_keys(group: GroupSpec) -> set[str]:
    """The keys of every box a group's totals print in."""
    if group.totals is None:
        return set()
    keys = set(group.totals.page_boxes.values())
    if group.totals.last_page_box:
        keys.add(group.totals.last_page_box)
    return keys


@dataclass(frozen=True)
class FormSchema:
    """Complete specification for a form, including all fields."""

    form_type: str
    template_filename: str
    template_version: str
    fields: list[FieldSpec]
    groups: dict[str, GroupSpec] = field(default_factory=dict)
    page_numbers: tuple[PageNumberBoxes, ...] = ()


def is_statement_group(schema: FormSchema, name: str) -> bool:
    """A group of a sheet and no slots: its rows come from one list binding (3e2 spec 9.2)."""
    group = schema.groups.get(name)
    return (
        group is not None
        and group.sheet is not None
        and group.extra_page is None
        and not any(f.repeat == name for f in schema.fields)
    )


def number_box_keys(schema: FormSchema) -> set[str]:
    """The keys of every box that holds a group's entry number (3c spec §5.4)."""
    return {key for group in schema.groups.values() for key in group.number_boxes.values()}


def page_number_keys(schema: FormSchema) -> set[str]:
    """The keys of every page-number box the form declares."""
    return {key for boxes in schema.page_numbers for key in (boxes.this, boxes.of) if key}


@lru_cache(maxsize=32)
def load_schema(form_type: str) -> FormSchema:
    """
    Load and parse form schema from JSON.

    Args:
        form_type: The form type identifier (e.g., 'form_101')

    Returns:
        FormSchema dataclass instance

    Raises:
        FileNotFoundError: If schema file does not exist
        json.JSONDecodeError: If schema file is invalid JSON
    """
    schema_path = Path(settings.FORM_SCHEMAS_DIRECTORY) / f"{form_type}.json"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path) as f:
        raw = json.load(f)

    # Convert field dicts to FieldSpec dataclass instances
    fields = []
    for field_data in raw["fields"]:
        ui_data = field_data.pop("ui", None)
        ui_spec = UIFieldSpec.from_dict(ui_data) if ui_data else None
        fields.append(FieldSpec(**field_data, ui=ui_spec))

    groups = {
        name: GroupSpec(
            name=name,
            extra_page=group.get("extra_page"),
            number=group.get("number"),
            number_boxes={int(row): key for row, key in group.get("number_boxes", {}).items()},
            sheet=_sheet(group["sheet"]) if "sheet" in group else None,
            totals=_totals(group["totals"]) if "totals" in group else None,
        )
        for name, group in raw.get("groups", {}).items()
    }

    return FormSchema(
        form_type=raw["form_type"],
        template_filename=raw["template_filename"],
        template_version=raw["template_version"],
        fields=fields,
        groups=groups,
        page_numbers=tuple(
            PageNumberBoxes(page=boxes["page"], this=boxes.get("this"), of=boxes.get("of"))
            for boxes in raw.get("page_numbers", [])
        ),
    )


def _totals(totals: dict) -> GroupTotals:
    """A group's "totals": {"column", "page_boxes": {"<page>": key}, "last_page_box": key}."""
    return GroupTotals(
        column=totals["column"],
        page_boxes={int(page): key for page, key in totals.get("page_boxes", {}).items()},
        last_page_box=totals.get("last_page_box"),
    )


def _sheet(sheet: dict) -> SheetSpec:
    """
    A group's "sheet": {"title": str, "columns": [{"label", "binding", "width"}]}, with an
    optional "line_width", and an optional "covers" list on a column.
    """
    return SheetSpec(
        title=sheet["title"],
        columns=tuple(
            SheetColumn(
                label=c["label"],
                binding=c["binding"],
                width=float(c["width"]),
                covers=tuple(c["covers"]) if "covers" in c else None,
            )
            for c in sheet["columns"]
        ),
        line_width=float(sheet.get("line_width", SheetSpec.line_width)),
    )


def _add_writer(writers: dict, writer: tuple, key: str) -> None:
    """Record `writer` as filling the widget(s) a values key names, if the key parses."""
    try:
        name, at, tag = parse_key(key)
    except ValueError:
        return  # E003 reports a key that names no widget
    writers.setdefault(name, []).append((writer, at, tag))


# Index widget types each binding type may target (spec §5.4 check 4).
_WIDGET_TYPES = {
    "text": {"Text"},
    "choice": {"ComboBox"},
    "checkbox": {"CheckBox", "RadioButton"},
    "radio": {"CheckBox", "RadioButton"},
}
_BINDING_NAMESPACES = ("answer:", "sofa.", "household.", "assets.")


def validate_schema(
    schema: FormSchema, derivations: set[str], predicates: set[str]
) -> list[tuple[str, str]]:
    """
    Check a schema against its template and field index (spec §5.4, checks 2-7).

    Returns (code, message) pairs; an empty list means the schema is valid.
    apps.forms.checks reports each pair as a forms.<code> system-check error.
    """
    errors: list[tuple[str, str]] = []
    template = (Path(settings.PDF_FORMS_DIRECTORY) / schema.template_filename).read_bytes()
    if hashlib.sha256(template).hexdigest() != schema.template_version:
        errors.append(("E002", "template_version is not the template's SHA-256"))

    index = load_index(schema.template_filename)
    template_fields = pypdf.PdfReader(BytesIO(template)).get_fields() or {}
    # "@" marks a widget's own key in the resolved values: "<full name>@<page>:<tag>".
    for name in sorted(name for name in index if "@" in name):
        errors.append(("E003", f"{name!r}: a full name in the field index contains '@'"))
    # A template that has drifted from its index is an error, not a crash. The tag and
    # E006 checks need the widget map, so they are skipped for this form.
    try:
        widget_map: tuple[TemplateWidget, ...] | None = template_widgets(schema.template_filename)
    except TemplateMismatch as mismatch:
        errors.append(("E003", str(mismatch)))
        widget_map = None
    drawn: dict[str, list[TemplateWidget]] = {}
    for widget in widget_map or ():
        if widget.drawn:
            drawn.setdefault(widget.full_name, []).append(widget)

    for f in schema.fields:
        widgets = index.get(f.pdf_field)
        if widgets is None:
            errors.append(("E003", f"{f.pdf_field!r} is not a full name in the field index"))
            continue
        if (
            f.tag is not None
            and widget_map is not None
            and not any((w.page, w.tag) == (f.page, f.tag) for w in drawn.get(f.pdf_field, ()))
        ):
            errors.append(
                ("E003", f"{f.pdf_field!r} has no drawn widget {f.tag!r} on page {f.page}")
            )
        # An untagged binding's page decides which copy rows it fills (3a2 spec §5.2).
        if (
            f.tag is None
            and widget_map is not None
            and not any(w.page == f.page for w in drawn.get(f.pdf_field, ()))
        ):
            errors.append(("E003", f"{f.pdf_field!r} has no drawn widget on page {f.page}"))

        types = {w.type for w in widgets}
        if any(w.basis == "form_control" for w in widgets):
            errors.append(("E004", f"{f.pdf_field!r} is a push button"))
        elif not types <= _WIDGET_TYPES.get(f.type, set()):
            errors.append(("E004", f"{f.pdf_field!r} is bound as {f.type} but is {sorted(types)}"))
        is_box = f.type in ("checkbox", "radio")
        if is_box and f.choices is None:
            errors.append(("E004", f"{f.pdf_field!r}: a {f.type} binding needs choices"))
        if not is_box and f.choices is not None:
            errors.append(
                ("E004", f"{f.pdf_field!r}: choices go on checkbox and radio only, not on {f.type}")
            )

        if f.choices:
            # The filler lower-cases the answer before the lookup (spec §5.1).
            for key in sorted(k for k in f.choices if k != k.lower()):
                errors.append(
                    (
                        "E004",
                        f"{f.pdf_field!r}: choices key {key!r} isn't lower-case, "
                        "so no answer can match it",
                    )
                )
            states = {export_state(w.on_state) for w in widgets if w.on_state}
            for state in sorted(set(f.choices.values()) - states):
                errors.append(("E005", f"{f.pdf_field!r} has no state {state!r}"))
        if f.type == "choice" and f.source == "constant":
            # .get: a template that has drifted from its index is an error, not a crash.
            options = [str(o) for o in template_fields.get(f.pdf_field, {}).get("/Opt", [])]
            if f.value not in options:
                errors.append(("E005", f"{f.pdf_field!r} has no option {f.value!r}"))

        if f.source == "TBD":
            errors.append(("E007", f"{f.pdf_field!r}: source is still TBD"))
        if f.source == "derived" and f.rule not in derivations:
            errors.append(("E007", f"{f.pdf_field!r}: unknown derivation rule {f.rule!r}"))
        if f.conditional_on is not None and f.conditional_on not in predicates:
            errors.append(("E007", f"{f.pdf_field!r}: unknown predicate {f.conditional_on!r}"))
        if f.binding is not None and not f.binding.startswith(_BINDING_NAMESPACES):
            errors.append(("E007", f"{f.pdf_field!r}: unknown binding namespace {f.binding!r}"))
        if f.repeat is not None and not f.repeat_capacity:
            errors.append(("E007", f"repeat group {f.repeat!r} has no repeat_capacity"))

    # Who writes each widget: every binding, and every box a group numbers a row or a page
    # in. A key fills every drawn widget of its name, or with a tag only that one. A widget
    # shows one value, so two writers that would fill it conflict, rows of one repeat group
    # included. A page count is the same on every page: one "of" key is one writer.
    writers: dict[str, list[tuple[tuple, int | None, str | None]]] = {}
    for i, f in enumerate(schema.fields):
        if f.pdf_field in index:  # any other name is reported above (E003)
            writers.setdefault(f.pdf_field, []).append((("binding", i), f.page, f.tag))
    for group_name, group in schema.groups.items():
        for row, key in group.number_boxes.items():
            _add_writer(writers, ("number", group_name, row), key)
        if group.totals is not None:
            for page, key in group.totals.page_boxes.items():
                _add_writer(writers, ("total", group_name, page), key)
            if group.totals.last_page_box:
                _add_writer(writers, ("last total", group_name), group.totals.last_page_box)
    for p in schema.page_numbers:
        if p.this:
            _add_writer(writers, ("this", p.page), p.this)
        if p.of:
            _add_writer(writers, ("of", p.of), p.of)
    for name, entries in writers.items():
        for widget in drawn.get(name, ()):
            fills = {
                writer
                for writer, page, tag in entries
                if tag is None or (page, tag) == (widget.page, widget.tag)
            }
            if len(fills) > 1:
                errors.append(
                    ("E006", f"{name!r} is bound {len(fills)} times on page {widget.page}")
                )
                break

    # A repeat group fills its slots, rows 1 to repeat_capacity, and its rows past the last
    # slot continue on copies of its extra page, the page of its last slots (3a2 spec §5.2).
    # Each box that numbers a row or a page prints on that row's or page's page.
    # Here: fill_resolver imports this module.
    from apps.forms.services.fill_resolver import ASSET_BOX_CELLS, ASSET_CELLS, _unmapped

    slots: dict[str, list[FieldSpec]] = {}
    for f in schema.fields:
        if f.repeat is not None:
            slots.setdefault(f.repeat, []).append(f)
    for name, rows in slots.items():
        # A group applies whole or not at all, and its capacity is its slots: a capacity
        # below them would print a row on the form and on a copy, one above them no row.
        capacities = {f.repeat_capacity for f in rows}
        mapped = [f for f in rows if not _unmapped(f)]
        if len(capacities) > 1:
            errors.append(("E007", f"repeat group {name!r} has more than one repeat_capacity"))
        else:
            (capacity,) = capacities  # None or 0 is reported above, per field
            if capacity and {f.row for f in mapped} != set(range(1, capacity + 1)):
                errors.append(
                    (
                        "E007",
                        f"repeat group {name!r}: its slot rows aren't exactly 1 to its "
                        f"repeat_capacity, {capacity}",
                    )
                )
        if len({f.conditional_on for f in rows}) > 1:
            errors.append(("E007", f"repeat group {name!r} has more than one conditional_on"))
        # An untagged binding fills every widget of its name, so a slot whose name is drawn
        # more than once would print its row in each, or tick each box that shares its state.
        # A column of boxes that each have their own state ticks only the answer's box.
        for f in mapped:
            widgets = drawn.get(f.pdf_field, ())
            if f.type in ("checkbox", "radio"):
                states = [s for w in widgets for s in set(w.states)]
                twinned = len(states) > len(set(states))
            else:
                twinned = len(widgets) > 1
            if f.tag is None and twinned:
                errors.append(
                    (
                        "E007",
                        f"repeat group {name!r}: {f.pdf_field!r} is drawn {len(widgets)} times, "
                        f"on pages {_pages_drawn(f.pdf_field, drawn)}, so its slot needs a tag",
                    )
                )
        # A copy takes a row's boxes from one page, and prints rows in row order. A missing
        # row is reported above, against the capacity, and a missing page by E003.
        paged = [f for f in mapped if f.row is not None and f.page is not None]
        row_pages: dict[int, set[int]] = {}
        for f in paged:
            row_pages.setdefault(f.row, set()).add(f.page)
        page_of: dict[int, int] = {}
        for row, on in sorted(row_pages.items()):
            if len(on) > 1:
                errors.append(
                    ("E007", f"repeat group {name!r}: row {row} is on pages {sorted(on)}, not one")
                )
            else:
                (page_of[row],) = on
        order = sorted(page_of)
        for before, after in zip(order, order[1:], strict=False):
            if page_of[after] < page_of[before]:
                errors.append(
                    (
                        "E007",
                        f"repeat group {name!r}: row {after} is on a page before row {before}'s",
                    )
                )
        group = schema.groups.get(name)
        pages = {f.page for f in paged}
        if group is None:
            errors.append(("E007", f"repeat group {name!r} isn't declared in groups"))
        elif group.extra_page is not None and group.sheet is not None:
            errors.append(("E007", f"group {name!r} names both an extra_page and a sheet"))
        elif group.sheet is not None:
            # The rows a sheet prints are the slots' rows: a column of another list would
            # print rows that aren't the group's, or leave some of them out. A cell prints its
            # slot's text, or a box's answer in the words the form prints beside the state it
            # maps to, so a box whose choices are {}, a single box's {"true": …} or two answers
            # on one state is refused (a one-key map of another answer isn't yet).
            # A column that covers slots prints its own list as it is, by position, and only a
            # row past the slots reads it: its list must be the one its slots bind, and its
            # cell words, never a box's answer.
            slot_lists = {f.binding.partition("[].")[0] for f in rows if f.binding}
            for column in group.sheet.columns:
                if column.covers is not None:
                    listed, _, attr = column.binding.partition("[].")
                    wrong = None
                    if slot_lists != {listed}:
                        wrong = "which isn't the one list its slots bind"
                    elif listed.startswith("assets.") and attr not in ASSET_CELLS:
                        wrong = "which no Schedule A/B row can print"
                    elif listed.startswith("assets.") and attr in ASSET_BOX_CELLS:
                        wrong = "a box's answer, not words"
                    if wrong:
                        errors.append(
                            (
                                "E007",
                                f"group {name!r}: sheet column {column.label!r} covers slots "
                                f"but binds {column.binding!r}, {wrong}",
                            )
                        )
                    continue
                bound = [f for f in rows if f.binding == column.binding]
                if not bound:
                    errors.append(
                        (
                            "E007",
                            f"group {name!r}: sheet column {column.label!r} binds "
                            f"{column.binding!r}, which no slot of the group binds",
                        )
                    )
                elif any(
                    _unmapped(f)
                    or set(f.choices) == {"true"}  # a single box: its No would print blank
                    or len(set(f.choices.values())) < len(f.choices)
                    for f in bound
                    if f.type in ("checkbox", "radio")
                ):
                    errors.append(
                        (
                            "E007",
                            f"group {name!r}: sheet column {column.label!r} binds a box that "
                            "doesn't give every answer its own state",
                        )
                    )
            # And every slot's value prints in a column, or the rows past the slots would
            # drop it: every slot's binding needs a column, a box's included, and a slot with
            # no binding (a constant, a derived value, a box ticked for every row) can't
            # continue. (A sheet with no columns is reported as such below.)
            columns = {column.binding for column in group.sheet.columns}
            for column in group.sheet.columns:
                columns.update(column.covers or ())
            unprinted = {f.binding for f in rows if f.binding} - columns if columns else set()
            for binding in sorted(unprinted):
                errors.append(
                    (
                        "E007",
                        f"group {name!r}: no sheet column prints {binding!r}, "
                        "which a slot of the group binds",
                    )
                )
            for f in rows if columns else ():
                if f.binding:
                    continue
                if f.type in ("checkbox", "radio"):
                    errors.append(
                        (
                            "E007",
                            f"group {name!r}: a box slot fills {f.pdf_field!r} on row {f.row}, "
                            "and a sheet can't tick a box",
                        )
                    )
                else:
                    errors.append(
                        (
                            "E007",
                            f"group {name!r}: no sheet column prints {f.pdf_field!r} on row "
                            f"{f.row}, a slot of the group that binds no list",
                        )
                    )
        elif group.extra_page is None:
            errors.append(("E007", f"group {name!r} names neither an extra_page nor a sheet"))
        elif group.extra_page not in pages:
            errors.append(
                ("E007", f"group {name!r}: extra_page {group.extra_page} holds none of its slots")
            )
        elif group.extra_page != max(pages):
            errors.append(
                (
                    "E007",
                    f"group {name!r}: extra_page {group.extra_page} isn't the page of its "
                    f"last slots, {max(pages)}",
                )
            )
    # A copy's place in the form comes from its page and its number (3c spec §5.1): one group
    # to each extra page. The form's page-number boxes count every group's copies (§5.2).
    continued = {
        name: group.extra_page
        for name, group in schema.groups.items()
        if group.extra_page is not None
    }
    names = list(continued)
    for i, first in enumerate(names):
        for second in names[i + 1 :]:
            if continued[first] == continued[second]:
                errors.append(
                    (
                        "E007",
                        f"groups {first!r} and {second!r} both continue on copies of "
                        f"page {continued[first]}",
                    )
                )
    if schema.page_numbers and not continued:
        errors.append(("E007", "no group continues on copies, so the form numbers no pages"))
    numbered_pages = {p.page for p in schema.page_numbers}
    if schema.page_numbers:
        for name, page in continued.items():
            if page not in numbered_pages:
                errors.append(
                    (
                        "E007",
                        f"group {name!r} continues on copies of page {page}, "
                        "which has no page-number boxes",
                    )
                )
    if widget_map is not None:
        for p in schema.page_numbers:
            for key in (p.this, p.of):
                if key and not _drawn_on(key, p.page, drawn):
                    errors.append(
                        ("E003", f"page numbers: {key!r} is no drawn widget on page {p.page}")
                    )
                    continue
                if key and _isnt_text_box(key, drawn):
                    errors.append(
                        (
                            "E003",
                            f"page numbers: box {key!r} on page {p.page} isn't a text box",
                        )
                    )
            # A page's position prints in one box: an untagged key whose name has more than
            # one drawn widget would print it in each. A page count is the same in all.
            widgets = drawn.get(p.this, ()) if p.this else ()  # a tagged key has "@"
            if len(widgets) > 1:
                errors.append(
                    (
                        "E003",
                        f"page numbers: {p.this!r} is drawn {len(widgets)} times, on pages "
                        f"{_pages_drawn(p.this, drawn)}, so it needs a tag",
                    )
                )
    for name, group in schema.groups.items():
        if group.totals is not None:
            errors += _totals_errors(name, group, slots.get(name, []))
        if group.sheet is not None:
            errors += _sheet_errors(name, group, schema.template_filename)
            bound = {f.binding for f in slots.get(name, [])}
            for column in group.sheet.columns:
                for binding in sorted(set(column.covers or ()) - bound):
                    errors.append(
                        (
                            "E007",
                            f"group {name!r}: sheet column {column.label!r} covers {binding!r}, "
                            "which no slot of the group binds",
                        )
                    )
        if is_statement_group(schema, name):
            for column in group.sheet.columns:
                if not _STATEMENT_BINDING.fullmatch(column.binding):
                    errors.append(
                        (
                            "E007",
                            f"group {name!r}: statement column {column.label!r} binds "
                            f"{column.binding!r}, not an income.statement[].<attr> list",
                        )
                    )
        # A sheet labels each row with the line it continues, its number.
        numbered_rows = group.number is not None or group.number_boxes or group.sheet is not None
        if numbered_rows and "{n}" not in (group.number or ""):
            errors.append(("E007", f"group {name!r}: number must contain {{n}}"))
        elif group.number is not None:
            try:
                first, second = group.number.format(n=1), group.number.format(n=2)
            except Exception:  # any way it fails at Generate is a schema error here
                errors.append(("E007", f"group {name!r}: number {group.number!r} doesn't format"))
            else:
                if first == second:  # "2.{{n}}" prints "2.{n}" for every row
                    errors.append(
                        (
                            "E007",
                            f"group {name!r}: number {group.number!r} prints the same "
                            "for every row",
                        )
                    )
                elif group.sheet is not None:
                    # The sheet's rows start past the slots: each row's line must print whole
                    # in the line column, or Generate fails for that row and every later one.
                    from apps.forms.services.sheets import fits_line_column

                    capacities = {f.repeat_capacity for f in slots.get(name, [])}
                    # A statement group has no slots: its rows start at 1.
                    statement = is_statement_group(schema, name)
                    capacity = 0 if statement else None
                    if not statement and len(capacities) == 1:
                        capacity = capacities.pop()
                    if statement or capacity:
                        # Its first line, and row 9999's: Helvetica's digits are all one
                        # width, so while the number prints n in decimal no line up to that
                        # row is wider (R65(2)). Another format can be: "{{n}}{n:x}" prints
                        # a wider line at row 4096 than at row 9999.
                        for n, which in (
                            (capacity + 1, "its first line"),
                            (9999, "row 9999's line"),
                        ):
                            line = group.number.format(n=n)
                            width = group.sheet.line_width
                            if not fits_line_column(line, schema.template_filename, width):
                                errors.append(
                                    (
                                        "E007",
                                        f"group {name!r}: its sheet can't print {which}, "
                                        f"{line!r}, whole in the {width:g} pt line column",
                                    )
                                )
                                break
        if widget_map is None:
            continue
        # A row is on its mapped boxes' page: an unmapped box prints nothing, wherever it is.
        rows = [f for f in slots.get(name, []) if not _unmapped(f)]
        boxes = []
        for row, key in group.number_boxes.items():
            page = next((f.page for f in rows if f.row == row), None)
            if page is None:
                errors.append(
                    ("E003", f"group {name!r}: {key!r} numbers row {row}, which isn't a slot row")
                )
            else:
                boxes.append((key, page))
        if group.totals is not None and group.extra_page is not None:  # else E007 above
            boxes += [(key, page) for page, key in group.totals.page_boxes.items()]
            if group.totals.last_page_box:
                boxes.append((group.totals.last_page_box, group.extra_page))
        for key, page in boxes:
            if not _drawn_on(key, page, drawn):
                errors.append(
                    ("E003", f"group {name!r}: {key!r} is no drawn widget on page {page}")
                )
        # A row's number prints in one box: an untagged key whose name has more than one
        # drawn widget would print it in each.
        for key in [*group.number_boxes.values(), *sorted(total_box_keys(group))]:
            widgets = drawn.get(key, ())  # a tagged key has "@", so it is never a name here
            if len(widgets) > 1:
                errors.append(
                    (
                        "E003",
                        f"group {name!r}: {key!r} is drawn {len(widgets)} times, on pages "
                        f"{_pages_drawn(key, drawn)}, so it needs a tag",
                    )
                )
        # A figure can't tick a box or fill a combo: every filer with a row would be refused.
        for key in sorted(total_box_keys(group)):
            if _isnt_text_box(key, drawn):
                errors.append(("E003", f"group {name!r}: total box {key!r} isn't a text box"))
        # An entry number is text too (R13). A name drawn nowhere has no widget to be a non-text one.
        for key in sorted(set(group.number_boxes.values())):
            if _isnt_text_box(key, drawn):
                errors.append(("E003", f"group {name!r}: number box {key!r} isn't a text box"))
    return errors


def _isnt_text_box(key: str, drawn) -> bool:
    """True when a box key names a drawn widget that is not a text box; a bad key is no."""
    try:
        box_name, _, _ = parse_key(key)
    except ValueError:
        return False  # _drawn_on has reported it
    return any(w.kind != "Text" for w in drawn.get(box_name, ()))


_STATEMENT_BINDING = re.compile(r"income\.statement\[\]\.(?:owner|description|gross|expenses|net)")
_LIST_BINDING = re.compile(
    r"(?:sofa\.\w+|household\.dependents|income\.statement|assets\.line_\w+)\[\]\.\w+"
)


def _totals_errors(name: str, group: GroupSpec, rows: list[FieldSpec]) -> list[tuple[str, str]]:
    """What keeps a group's total boxes from adding up its own rows (3c spec §5.3)."""
    from apps.forms.services.fill_resolver import _unmapped  # here: it imports this module

    totals = group.totals
    if group.extra_page is None:
        return [("E007", f"group {name!r}: only a group continued on copies has total boxes")]
    errors = []
    if not totals.page_boxes and not totals.last_page_box:
        errors.append(("E007", f"group {name!r}: its totals name no box"))
    column = [f for f in rows if f.binding == totals.column]
    if not column or any(f.type != "text" for f in column):
        errors.append(
            (
                "E007",
                f"group {name!r}: its totals add {totals.column!r}, "
                "which isn't a text slot of the group",
            )
        )
    slot_pages = {f.page for f in rows if not _unmapped(f)}
    for page, key in sorted(totals.page_boxes.items()):
        if page not in slot_pages:
            errors.append(
                (
                    "E007",
                    f"group {name!r}: total box {key!r} is for page {page}, "
                    "which holds none of its slots",
                )
            )
    return errors


def _sheet_errors(name: str, group: GroupSpec, template: str) -> list[tuple[str, str]]:
    """
    What keeps a group's attached sheet from printing every row whole (3a2 spec §5.3): its
    columns must fit the 7 in between the sheet's margins beside the line column, each
    print a list's rows, and each label, like the title, print whole in its width, in the
    letters the form's template prints.
    """
    from apps.forms.services.sheets import (  # here: it imports this module
        WIDTH,
        inner_width,
        prints_whole,
    )

    sheet = group.sheet
    errors = []
    if not sheet.columns:
        errors.append(("E007", f"group {name!r}: its sheet has no columns for its rows"))
    total = sheet.line_width + sum(c.width for c in sheet.columns)
    if total > WIDTH:
        errors.append(
            (
                "E007",
                f"group {name!r}: its sheet's columns and line column are {total:g} pt wide, "
                f"more than the {WIDTH:g} pt (7 in) between its margins",
            )
        )
    if not prints_whole(f"{sheet.title} (attached sheet)", WIDTH, template):
        errors.append(("E007", f"group {name!r}: its sheet can't print its title whole"))
    # A label names one column, to the filer and to a refusal's fix (sheets._fixes).
    labels = [column.label for column in sheet.columns]
    for label in sorted({label for label in labels if labels.count(label) > 1}):
        errors.append(
            ("E007", f"group {name!r}: its sheet has more than one column labelled {label!r}")
        )
    for column in sheet.columns:
        if not _LIST_BINDING.fullmatch(column.binding):
            errors.append(
                (
                    "E007",
                    f"group {name!r}: sheet column {column.label!r} binds {column.binding!r}, "
                    "not a sofa.<collection>[].<attr>, household.dependents[].<attr>, "
                    "income.statement[].<attr> or assets.line_<key>[].<attr> list",
                )
            )
        width = inner_width(column.width)
        if width <= 0 or not prints_whole(column.label, width, template):
            errors.append(
                (
                    "E007",
                    f"group {name!r}: sheet column {column.label!r} can't print its label "
                    f"whole in {column.width:g} pt",
                )
            )
    return errors


def _pages_drawn(name: str, drawn: dict[str, list[TemplateWidget]]) -> list[int]:
    """The pages a full name is drawn on, in order."""
    return sorted({w.page for w in drawn.get(name, ())})


def _drawn_on(key: str, page: int | None, drawn: dict[str, list[TemplateWidget]]) -> bool:
    """Whether a values key fills a drawn widget on `page`."""
    try:
        name, at, tag = parse_key(key)
    except ValueError:
        return False
    return any(
        w.page == page and (tag is None or (w.page, w.tag) == (at, tag))
        for w in drawn.get(name, ())
    )
