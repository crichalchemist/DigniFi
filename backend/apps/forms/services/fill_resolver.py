"""
Fill resolver — turns a FormSchema + IntakeSession into {pdf_field: str}, or, for a
binding with a tag, {"<pdf_field>@<page>:<tag>": str}.

Source priority is encoded per-field in the schema (constant/derived/asked/
ingested/signature). This module resolves ``binding`` references; resolve()
(Task 8) orchestrates dispatch, conditional sections, and repeat groups.
"""

from __future__ import annotations

from apps.forms.schema import FieldSpec, FormSchema
from apps.forms.services.derivations import DERIVATIONS, PREDICATES
from apps.intake.models import FormAnswer, IntakeSession


class RepeatOverflow(Exception):
    """A bound collection exceeded its template's pre-printed row capacity."""

    def __init__(self, form_type: str, group: str, capacity: int, actual: int):
        self.form_type = form_type
        self.group = group
        self.capacity = capacity
        self.actual = actual
        super().__init__(
            f"{form_type}: repeat group {group!r} has {actual} rows but template "
            f"holds {capacity}. A continuation attachment is required."
        )


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


def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
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
    # is never resolved and never counts toward RepeatOverflow (spec §5.1).
    groups: dict[str, list[FieldSpec]] = {}
    for f in schema.fields:
        if f.repeat is None or _unmapped(f):
            continue
        if _section_applies(f, session, answer_cache=_form_answers):
            groups.setdefault(f.repeat, []).append(f)

    for group_name, fields in groups.items():
        capacity = fields[0].repeat_capacity or 0
        resolved_cols = {_key(f): resolve_binding(f.binding, session) for f in fields if f.binding}
        actual = max(
            (len(v) for v in resolved_cols.values() if isinstance(v, list)),
            default=0,
        )
        if actual > capacity:
            raise RepeatOverflow(schema.form_type, group_name, capacity, actual)
        for f in fields:
            if f.legal_review and f.source != "asked":
                continue
            if f.binding:
                vals = resolved_cols.get(_key(f))
                if isinstance(vals, list) and f.row and f.row <= len(vals):
                    emitted = _emit(f, str(vals[f.row - 1]))
                    if emitted is not None:
                        out[_key(f)] = emitted
            else:
                emitted = _emit(f, _scalar_value(f, session, ingested_cache=_ingested_cache))
                if emitted is not None:
                    out[_key(f)] = emitted

    return out
