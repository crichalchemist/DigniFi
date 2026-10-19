"""
Schema dataclasses and loader for form field specifications.

Provides FieldSpec (individual field definition) and FormSchema (complete form specification),
plus load_schema() function to load form schemas from JSON files.
"""

from __future__ import annotations

import hashlib
import json
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
class GroupSpec:
    """
    A repeat group's declaration (3a2 spec §5.2): the template page whose copies take the
    rows past its last slot, and the boxes that number the rows and the pages.
    """

    name: str
    extra_page: int | None
    number: str | None  # the entry number, such as "2.{n}", n the row's position in the group
    number_boxes: dict[int, str]  # slot row → the key of that slot's entry-number box
    page_numbers: tuple[PageNumberBoxes, ...]


@dataclass(frozen=True)
class FormSchema:
    """Complete specification for a form, including all fields."""

    form_type: str
    template_filename: str
    template_version: str
    fields: list[FieldSpec]
    groups: dict[str, GroupSpec] = field(default_factory=dict)


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
            page_numbers=tuple(
                PageNumberBoxes(page=boxes["page"], this=boxes.get("this"), of=boxes.get("of"))
                for boxes in group.get("page_numbers", [])
            ),
        )
        for name, group in raw.get("groups", {}).items()
    }

    return FormSchema(
        form_type=raw["form_type"],
        template_filename=raw["template_filename"],
        template_version=raw["template_version"],
        fields=fields,
        groups=groups,
    )


# Index widget types each binding type may target (spec §5.4 check 4).
_WIDGET_TYPES = {
    "text": {"Text"},
    "choice": {"ComboBox"},
    "checkbox": {"CheckBox", "RadioButton"},
    "radio": {"CheckBox", "RadioButton"},
}
_BINDING_NAMESPACES = ("answer:", "sofa.")


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
        boxes = [(("number", group_name, row), key) for row, key in group.number_boxes.items()]
        for p in group.page_numbers:
            if p.this:
                boxes.append((("this", group_name, p.page), p.this))
            if p.of:
                boxes.append((("of", p.of), p.of))
        for writer, key in boxes:
            try:
                name, at, tag = parse_key(key)
            except ValueError:
                continue  # E003 below reports a key that names no widget
            writers.setdefault(name, []).append((writer, at, tag))
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
    from apps.forms.services.fill_resolver import _unmapped  # here: it imports this module

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
        elif group.extra_page is None:
            errors.append(("E007", f"group {name!r} names no extra_page"))
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
    # 3a2 numbers a form's pages counting one group's copies only (R21, R56).
    continued = [
        repr(name) for name, group in schema.groups.items() if group.extra_page is not None
    ]
    if len(continued) > 1:
        errors.append(
            (
                "E007",
                f"groups {', '.join(continued[:-1])} and {continued[-1]} "
                f"{'both' if len(continued) == 2 else 'all'} declare extra_page; "
                "3a2 continues one group per form on copies",
            )
        )
    for name, group in schema.groups.items():
        if (group.number is not None or group.number_boxes) and "{n}" not in (group.number or ""):
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
        boxes += [(key, p.page) for p in group.page_numbers for key in (p.this, p.of) if key]
        for key, page in boxes:
            if not _drawn_on(key, page, drawn):
                errors.append(
                    ("E003", f"group {name!r}: {key!r} is no drawn widget on page {page}")
                )
        # A row's or a page's number prints in one box: an untagged key whose name has more
        # than one drawn widget would print it in each. A page count is the same in all.
        numbered = [*group.number_boxes.values(), *(p.this for p in group.page_numbers if p.this)]
        for key in numbered:
            widgets = drawn.get(key, ())  # a tagged key has "@", so it is never a name here
            if len(widgets) > 1:
                errors.append(
                    (
                        "E003",
                        f"group {name!r}: {key!r} is drawn {len(widgets)} times, on pages "
                        f"{_pages_drawn(key, drawn)}, so it needs a tag",
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
