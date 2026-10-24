"""
Fill resolver — turns a FormSchema + IntakeSession into {pdf_field: str}, or, for a
binding with a tag, {"<pdf_field>@<page>:<tag>": str}.

Source priority is encoded per-field in the schema (constant/derived/asked/
ingested/signature). This module resolves ``binding`` references; resolve_parts()
orchestrates dispatch, conditional sections, and repeat groups, whose rows past the
last slot continue on copies of an extra page or on an attached sheet, and resolve()
returns its form part.
"""

from __future__ import annotations

from apps.forms.schema import FieldSpec, FormSchema, GroupSpec, PageNumberBoxes
from apps.forms.services.derivations import DERIVATIONS, PREDICATES, RULE_FIXES
from apps.forms.services.widgets import TemplateWidget, page_count, parse_key, template_widgets
from apps.intake.models import FormAnswer, IntakeSession


class UnmappedChoice(Exception):
    """A checkbox or radio answer has no export state in its binding's choices."""

    def __init__(self, pdf_field: str):
        self.pdf_field = pdf_field
        super().__init__(f"No box on the form matches the answer for {pdf_field!r}")


# Single-box answers, compared case-insensitively (spec §5.1).
_TICK = {"yes", "y", "true", "1", "on"}
_NO_TICK = {"no", "n", "false", "0", "off", ""}


def resolve_binding(binding: str, session: IntakeSession) -> str | list[str]:
    """
    Resolve a schema ``binding``:

      - "answer:<form_type>.<key>" → the FormAnswer value, or "" if absent
      - "sofa.<collection>[].<attr>" → list of str over the collection
      - "sofa.<attr>" → scalar str on the SOFAReport
    """
    binding = binding.strip()

    if binding.startswith("answer:"):
        form_type, _, key = binding[len("answer:") :].partition(".")
        ans = FormAnswer.objects.filter(session=session, form_type=form_type, field_key=key).first()
        return ans.value if ans else ""

    if binding.startswith("sofa."):
        path = binding[len("sofa.") :]
        report = getattr(session, "sofa_report", None)
        if "[]." in path:
            coll_name, _, attr = path.partition("[].")
            if report is None:
                return []
            return [str(getattr(row, attr)) for row in getattr(report, coll_name).all()]
        if report is None:
            return ""
        return str(getattr(report, path))

    raise ValueError(f"unrecognized binding: {binding!r}")


def _section_applies(
    field: FieldSpec, session: IntakeSession, answer_cache: dict | None = None
) -> bool:
    if field.conditional_on is None:
        return True
    pred = PREDICATES.get(field.conditional_on)
    return bool(pred and pred(session, answer_cache=answer_cache))


def _scalar_value(
    field: FieldSpec, session: IntakeSession, ingested_cache: dict | None = None
) -> str | None:
    if field.source == "constant":
        return field.value
    if field.source == "derived":
        fn = DERIVATIONS.get(field.rule)
        if fn is None:
            raise ValueError(f"Unknown derivation rule {field.rule!r} on field {field.pdf_field!r}")
        return fn(session)
    if field.source == "asked":
        if not field.binding:
            raise RuntimeError(f"Field {field.pdf_field} has source='asked' but no binding")
        val = resolve_binding(field.binding, session)
        return val if isinstance(val, str) else None
    if field.source in ("ingested", "db_aggregate"):
        if not field.ingest_key:
            raise RuntimeError(
                f"Field {field.pdf_field} has source='{field.source}' but no ingest_key"
            )

        if ingested_cache is not None:
            return ingested_cache.get(field.ingest_key, "")

        from apps.documents.models import IngestedAggregate

        agg = IngestedAggregate.objects.filter(session=session, ingest_key=field.ingest_key).first()
        return agg.value if agg else ""
    # signature → nothing
    return None


def _key(field: FieldSpec) -> str:
    """The values key a binding fills: its full name, or "<name>@<page>:<tag>" for one widget."""
    if field.tag is None:
        return field.pdf_field
    return f"{field.pdf_field}@{field.page}:{field.tag}"


def fix_for(field: FieldSpec) -> dict[str, str]:
    """
    Where the filer changes a binding's value, for a refusal to link to (3a2 spec §4.5):
    {"step": <a WIZARD_STEPS key>}, {"page": <path>}, or {} when no filer edits it.
    """
    if field.source == "derived":
        return dict(RULE_FIXES[field.rule])  # a copy: the map is shared by every refusal
    if field.source in ("ingested", "db_aggregate"):
        return {"page": "/documents"}
    binding = (field.binding or "").strip()
    if binding.startswith("answer:"):
        # The form the binding names, which isn't always the one printing it: Form 101's
        # preparer prints on 106Dec and 107 too.
        form_type, _, _ = binding[len("answer:") :].partition(".")
        return {"page": f"/ask/{form_type}"}
    if binding.startswith("sofa."):
        return {"page": "/sofa"}
    # A constant or a signature: a refusal there is DigniFi's defect, not the filer's.
    return {}


def _unmapped(field: FieldSpec) -> bool:
    """A checkbox or radio binding whose choices are not mapped yet emits nothing."""
    return field.type in ("checkbox", "radio") and not field.choices


def _emit(field: FieldSpec, value: str | None) -> str | None:
    """Turn a resolved value into what the filler writes. None = leave the box alone."""
    if field.type in ("checkbox", "radio"):
        key = "" if value is None else str(value).strip().lower()
        if set(field.choices) == {"true"}:  # a single box
            if key in _TICK:
                return field.choices["true"]
            if key in _NO_TICK:
                return None
        elif key == "":
            return None
        elif key in field.choices:
            return field.choices[key]
        raise UnmappedChoice(field.pdf_field)
    if value is None or value == "":
        return None
    return str(value)


def _cell(
    field: FieldSpec,
    position: int | None,
    columns: dict[str, str | list[str]],
    session: IntakeSession,
    ingested_cache: dict,
) -> str | None:
    """What a repeat group's binding prints for the row at `position` (from 1) in the group."""
    if not field.binding:
        return _emit(field, _scalar_value(field, session, ingested_cache=ingested_cache))
    vals = columns.get(_key(field))
    if isinstance(vals, list) and position and position <= len(vals):
        return _emit(field, str(vals[position - 1]))
    return None


def _number_page(values: dict[str, str], boxes: PageNumberBoxes, position: int, total: int) -> None:
    """A page's position in the form, and the form's page count, in its page-number boxes."""
    if boxes.this:
        values[boxes.this] = str(position)
    if boxes.of:
        values[boxes.of] = str(total)


def _headers(schema: FormSchema, form: dict[str, str], page: int) -> dict[str, str]:
    """
    The form's values a copy of `page` repeats: those of a box whose full name prints on
    `page` and on another page too, such as "Debtor 1" and "Case number" (R24). Never a
    box that prints on one page alone, such as a page total, and never a group's own box.
    """
    drawn: dict[str, list[TemplateWidget]] = {}
    for widget in template_widgets(schema.template_filename):
        if widget.drawn:
            drawn.setdefault(widget.full_name, []).append(widget)
    own = {_key(f) for f in schema.fields if f.repeat is not None}
    for group in schema.groups.values():
        own |= set(group.number_boxes.values())
        own |= {key for boxes in group.page_numbers for key in (boxes.this, boxes.of) if key}
    headers = {}
    for key, value in form.items():
        name, at, tag = parse_key(key)
        widgets = drawn.get(name, [])
        here = [
            w for w in widgets if w.page == page and (tag is None or (at, tag) == (w.page, w.tag))
        ]
        if key not in own and here and any(w.page != page for w in widgets):
            headers[key] = value
    return headers


def _copies(
    schema: FormSchema,
    group: GroupSpec,
    fields: list[FieldSpec],
    printed: list[FieldSpec],
    columns: dict[str, str | list[str]],
    capacity: int,
    actual: int,
    form: dict[str, str],
    session: IntakeSession,
    ingested_cache: dict,
) -> list[dict]:
    """
    The copies of the group's extra page that print its rows past `capacity` (3a2 spec §5.2):
    each holds as many rows as that page has slots, in the slots' order, numbers them as
    the group does, and repeats the form's page headers. With copies, every page-number
    box counts them, the form's own (written into `form`) included (R21). The group's
    `fields` decide its slots and `printed` the cells that print, as on the form's pages.
    """
    page = group.extra_page
    slots = sorted({f.row for f in fields if f.page == page and f.row})
    positions = list(range(capacity + 1, actual + 1))
    copies = []
    for start in range(0, len(positions), len(slots)):
        values: dict[str, str] = {}
        # The last copy may hold fewer rows than the page has slots.
        for row, position in zip(slots, positions[start : start + len(slots)], strict=False):
            for f in printed:
                if f.row == row and f.page == page:
                    emitted = _cell(f, position, columns, session, ingested_cache)
                    if emitted is not None:
                        values[_key(f)] = emitted
            if row in group.number_boxes:
                values[group.number_boxes[row]] = group.number.format(n=position)
        copies.append({"kind": "copy", "page": page, "number": len(copies) + 1, "values": values})

    if group.page_numbers:
        total = page_count(schema.template_filename) + len(copies)
        for boxes in group.page_numbers:
            # Copy n prints right after page `page`, as page `page` + n of the form.
            position = boxes.page if boxes.page <= page else boxes.page + len(copies)
            _number_page(form, boxes, position, total)
            if boxes.page == page:
                for copy in copies:
                    _number_page(copy["values"], boxes, page + copy["number"], total)
    headers = _headers(schema, form, page)
    for copy in copies:
        copy["values"] = {**headers, **copy["values"]}
    return copies


def _sheet(
    group: GroupSpec,
    fields: list[FieldSpec],
    printed: list[FieldSpec],
    columns: dict[str, str | list[str]],
    capacity: int,
    actual: int,
    session: IntakeSession,
    ingested_cache: dict,
) -> dict:
    """
    The attached sheet that prints the group's rows past `capacity` (3a2 spec §5.3): each row
    labelled with its line, the group's number for its position, and a cell per column,
    the column's binding for that row as the group's slot of that binding prints it. A
    column whose slots the UPL guard keeps blank is blank, as on the form and its copies.
    The sheet carries the filer's name for its header (R23), and its title and its columns'
    labels and widths (R63), so a filed sheet redraws as it was filed.
    """
    rows = []
    for position in range(capacity + 1, actual + 1):
        cells = []
        for column in group.sheet.columns:
            slots = [f for f in fields if f.binding == column.binding]  # one at least: E007
            emitted = None
            if all(f in printed for f in slots):
                emitted = _cell(slots[0], position, columns, session, ingested_cache)
            cells.append(emitted or "")
        rows.append({"line": group.number.format(n=position), "cells": cells})
    name = DERIVATIONS["full_name"](session)
    return {
        "kind": "sheet",
        "group": group.name,
        "title": group.sheet.title,
        "columns": [{"label": c.label, "width": c.width} for c in group.sheet.columns],
        "name": name,
        "rows": rows,
    }


def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
    """The values the form's own pages print: resolve_parts()'s form part."""
    return resolve_parts(schema, session)["parts"][0]["values"]


def resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
    """
    The form's values as the parts it prints, in printing order (3a2 spec §6):
    {"version": 2, "parts": [{"kind": "form", "values": {key: value}}, *copies, *sheets]}.

    A repeat group fills its slots in row order. Rows past its last slot continue on
    copies of the extra page its declaration names (3a2 spec §5.2), each
    {"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}},
    or on the attached sheet it declares (3a2 spec §5.3, R23, R63), one part for all of them:
    {"kind": "sheet", "group": <group>, "title": <its title>,
    "columns": [{"label": str, "width": <points>}], "name": <the filer's full name>,
    "rows": [{"line": "3.5", "cells": [<one per column>]}]}.
    """
    out: dict[str, str] = {}

    from apps.documents.models import IngestedAggregate

    # Fetch ingested aggregates once to avoid N+1 queries in _scalar_value
    _ingested_cache = {
        agg.ingest_key: agg.value for agg in IngestedAggregate.objects.filter(session=session)
    }

    # Prefetch SOFAReport collections to avoid N+1 in repeat group resolution
    report = getattr(session, "sofa_report", None)
    if report is not None:
        _ = list(report.prior_income.all())
        _ = list(report.creditor_payments.all())

    # Batch-fetch all FormAnswer rows for this session once (avoids per-predicate DB hits)
    _form_answers = {(fa.field_key): fa for fa in FormAnswer.objects.filter(session=session)}

    # Non-repeat fields
    for f in schema.fields:
        if f.repeat is not None or _unmapped(f):
            continue
        if not _section_applies(f, session, answer_cache=_form_answers):
            continue
        # UPL guard: legal_review fields fill only from an explicit asked answer
        if f.legal_review and f.source != "asked":
            continue
        emitted = _emit(f, _scalar_value(f, session, ingested_cache=_ingested_cache))
        if emitted is not None:
            out[_key(f)] = emitted

    # Repeat groups. An unmapped box is dropped before any lookup, so its binding
    # is never resolved and never counts as a row (spec §5.1).
    groups: dict[str, list[FieldSpec]] = {}
    for f in schema.fields:
        if f.repeat is None or _unmapped(f):
            continue
        if _section_applies(f, session, answer_cache=_form_answers):
            groups.setdefault(f.repeat, []).append(f)

    copies: list[dict] = []
    sheets: list[dict] = []
    overflowing = []
    for group_name, fields in groups.items():
        capacity = fields[0].repeat_capacity or 0
        resolved_cols = {_key(f): resolve_binding(f.binding, session) for f in fields if f.binding}
        actual = max(
            (len(v) for v in resolved_cols.values() if isinstance(v, list)),
            default=0,
        )
        # UPL guard, as above
        printed = [f for f in fields if not (f.legal_review and f.source != "asked")]
        for f in printed:
            emitted = _cell(f, f.row, resolved_cols, session, _ingested_cache)
            if emitted is not None:
                out[_key(f)] = emitted
        group = schema.groups.get(group_name)
        if group is not None:
            for row, key in group.number_boxes.items():
                if row <= min(actual, capacity):
                    out[key] = group.number.format(n=row)
        if actual > capacity and group is not None and group.sheet is not None:
            sheets.append(
                _sheet(
                    group,
                    fields,
                    printed,
                    resolved_cols,
                    capacity,
                    actual,
                    session,
                    _ingested_cache,
                )
            )
        elif actual > capacity:
            if group is None or group.extra_page is None:
                # The startup check refuses such a schema (forms.E007); never drop a row.
                raise ValueError(f"{schema.form_type}: group {group_name!r} names no extra page")
            overflowing.append((group, fields, printed, resolved_cols, capacity, actual))

    # Copies once the form's own values are all in: they repeat its page headers.
    for group, fields, printed, resolved_cols, capacity, actual in overflowing:
        copies += _copies(
            schema,
            group,
            fields,
            printed,
            resolved_cols,
            capacity,
            actual,
            out,
            session,
            _ingested_cache,
        )
    return {"version": 2, "parts": [{"kind": "form", "values": out}, *copies, *sheets]}
