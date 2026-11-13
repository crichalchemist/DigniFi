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

import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from apps.eligibility.cmi import counted_spouse_income, household_members
from apps.forms.field_index import option_text
from apps.forms.schema import (
    FieldSpec,
    FormSchema,
    GroupSpec,
    PageNumberBoxes,
    SheetSpec,
    is_statement_group,
    number_box_keys,
)
from apps.forms.services.derivations import (
    DERIVATIONS,
    PREDICATES,
    RULE_FIXES,
    money_or_blank,
)
from apps.forms.services.widgets import TemplateWidget, page_count, parse_key, template_widgets
from apps.intake.asset_lines import (
    LINE_BY_KEY,
    PROPERTY_KIND_WORDS,
    PROPERTY_KINDS,
    WHO_WORDS,
    one_read_of_assets,
    ordered_assets,
    rows_on,
)
from apps.intake.claim_rows import (
    DEBT_TYPE_WORDS,
    ClaimRows,
    ContractRow,
    DebtRow,
    NoticeRow,
    claim_rows,
    one_read_of_claims,
)
from apps.intake.claims import PRIORITY_TYPES, account_last_4
from apps.intake.household import RELATIONSHIP_WORDS, dependents
from apps.intake.income import statement_rows
from apps.intake.models import AssetInfo, FormAnswer, IntakeSession

if TYPE_CHECKING:
    # Not imported at run time: exemption_items imports this module (the cycle R2 names).
    from apps.forms.services.exemption_items import ExemptionRow


class UnmappedChoice(Exception):
    """A checkbox or radio answer has no export state in its binding's choices."""

    def __init__(self, pdf_field: str):
        self.pdf_field = pdf_field
        super().__init__(f"No box on the form matches the answer for {pdf_field!r}")


# What a household dependent's answer prints as, by attribute (an unanswered one prints "").
_HOUSEHOLD_CELLS = {
    "relationship": RELATIONSHIP_WORDS.__getitem__,
    "age": str,  # 0 prints "0"
    "lives_with_you": lambda lives: "yes" if lives else "no",
}


def _detail(attr: str) -> Callable[[AssetInfo], str]:
    """A row's answer as typed, blank while it has none."""

    def cell(row: AssetInfo) -> str:
        value = row.get_details().get(attr)
        return "" if value is None else str(value)

    return cell


def _kind_ticked(kind: str) -> Callable[[AssetInfo], str]:
    return lambda row: "true" if kind in (row.get_details().get("property_kinds") or []) else ""


def _has_personal_info(row: AssetInfo) -> str:
    answer = row.get_details().get("has_personal_info")
    return "" if answer is None else ("yes" if answer else "no")


def _where(row: AssetInfo) -> str:
    """A place's address on one line, leaving out what the filer left blank."""
    details = row.get_details()
    state_zip = " ".join(filter(None, (details.get("state"), details.get("zip"))))
    parts = (details.get("street"), details.get("street_2"), details.get("city"))
    return ", ".join(filter(None, (*parts, state_zip, details.get("county"))))


def _what(row: AssetInfo) -> str:
    """The boxes a place's row ticks, in the form's words; Other with what the filer typed."""
    details = row.get_details()
    words = []
    for kind in details.get("property_kinds") or []:
        other = details.get("other_kind") if kind == "other" else None
        words.append(f"Other: {other}" if other else PROPERTY_KIND_WORDS[kind])
    return "; ".join(words)


def _interest(row: AssetInfo) -> str:
    """Who has an interest in a row, what kind of interest, and what else the filer said."""
    details = row.get_details()
    parts = (
        WHO_WORDS.get(details.get("who")),
        details.get("nature"),
        "Community property" if details.get("community") else None,
        details.get("other_info"),
    )
    return "; ".join(filter(None, parts))


def _year_and_miles(row: AssetInfo) -> str:
    """A vehicle's year over its mileage. A word never wraps, so a comma could refuse "Unknown,"."""
    details = row.get_details()
    return "\n".join(filter(None, (details.get("year"), details.get("mileage"))))


# What a Schedule A/B row prints as, by attribute (3b spec §8). A box's cell is the answer its
# slot's choices take; where, what, interest and year_and_miles are the words a sheet prints for
# several boxes.
ASSET_CELLS: dict[str, Callable[[AssetInfo], str]] = {
    "description": lambda row: row.description or "",
    # Line 43's Describe sits under the Yes of "Do your lists include personally identifiable
    # information" (3b spec §5), so a description kept from before a No doesn't print.
    "personal_description": lambda row: (
        (row.description or "") if row.get_details().get("has_personal_info") else ""
    ),
    "value": lambda row: money_or_blank(row.current_value),
    "entire": lambda row: money_or_blank(row.entire_value),
    # Other's words sit beside its box, so words kept from before it was unticked don't print.
    "other_kind": lambda row: (_detail("other_kind")(row) if _kind_ticked("other")(row) else ""),
    **{
        attr: _detail(attr)
        for attr in (
            "who",
            "nature",
            "other_info",
            "street",
            "street_2",
            "city",
            "state",
            "zip",
            "county",
            "make",
            "model",
            "year",
            "mileage",
            "percent",
            "beneficiary",
        )
    },
    "has_personal_info": _has_personal_info,
    "community": lambda row: "true" if row.get_details().get("community") else "",
    **{f"kind_{kind}": _kind_ticked(kind) for kind in PROPERTY_KINDS},
    "where": _where,
    "what": _what,
    "interest": _interest,
    "year_and_miles": _year_and_miles,
}
# The cells that hold a box's answer ("with_someone", "true"): only a slot's choices give them
# words, so a column of words can't print one (forms.E007).
ASSET_BOX_CELLS = frozenset(
    {"who", "has_personal_info", "community", *(f"kind_{kind}" for kind in PROPERTY_KINDS)}
)
_ASSET_BINDING = re.compile(r"assets\.line_(\d+)(?:_(\w+))?\[\]\.(\w+)")


# --- claims.<list>[].<attr>: the rows Schedules D, E/F, G and H print (3c5 spec §9) ---
# CLAIM_CELLS formats the row objects apps.intake.claim_rows reads once; it never reads a model.


def _address_of(row) -> dict:
    """A row's name and address, whichever of the four row shapes it is."""
    if isinstance(row, DebtRow):
        d = row.debt
        return {
            "name": d.creditor_name,
            "street": d.street_address,
            "street_2": d.street_2,
            "city": d.city,
            "state": d.state,
            "zip": d.zip_code,
            "outside_us": d.outside_us,
        }
    if isinstance(row, NoticeRow):
        p = row.party
        return {
            "name": p.get("name"),
            "street": p.get("street_address"),
            "street_2": p.get("street_2"),
            "city": p.get("city"),
            "state": p.get("state"),
            "zip": p.get("zip_code"),
            "outside_us": p.get("outside_us"),
        }
    other = row.contract if isinstance(row, ContractRow) else row.codebtor
    return {
        "name": other.counterparty_name if isinstance(row, ContractRow) else other.name,
        "street": other.street_address,
        "street_2": other.street_2,
        "city": other.city,
        "state": other.state,
        "zip": other.zip_code,
        "outside_us": other.outside_us,
    }


def _address_cell(part: str) -> Callable[[Any], str]:
    def cell(row) -> str:
        address = _address_of(row)
        if part in ("state", "zip") and address["outside_us"]:
            return ""  # B49: an address outside the US prints no state or ZIP, whatever is stored
        if part == "street_joined":
            return ", ".join(filter(None, (address["street"], address["street_2"])))
        return address[part] or ""

    return cell


@dataclass(frozen=True, repr=False)
class CreditorEntry:
    """One name and address on the court's List of Creditors, with the step of its first row."""

    text: str
    step: str

    def __repr__(self) -> str:
        # A creditor's name and address never reach a log line or a traceback.
        return f"CreditorEntry(step={self.step!r}, text=<{len(self.text)} characters>)"


def _entry_key(parts: list[str]) -> tuple[str, ...]:
    """A name and address as one person: NFC, case-folded, whitespace runs collapsed (R5)."""
    return tuple(" ".join(unicodedata.normalize("NFC", p).casefold().split()) for p in parts)


def _entry_text(parts: dict[str, str]) -> str:
    """The lines of one entry (R6): name, street, street 2, then the city line; blanks left out."""
    city_line = ", ".join(filter(None, (parts["city"], parts["state"])))
    city_line = " ".join(filter(None, (city_line, parts["zip"])))
    lines = (parts["name"], parts["street"], parts["street_2"], city_line)
    return "\n".join(line for line in lines if line)


def creditor_entries(rows: ClaimRows) -> list[CreditorEntry]:
    """
    The List of Creditors' entries, one per name and address, from the rows Schedules D, E/F,
    G and H print (3c6 R5). The first row with a name and address makes the entry and gives
    its step; later rows with the same one add nothing.
    """
    # DRAFT: counsel C-9 (C4: the seven lists in print order; H line 2's spouse is not on the list)
    # DRAFT: counsel C-9 (C5: no entry for the filer, and no name is matched against theirs)
    sources = (
        (rows.secured, "debts"),
        (rows.secured_notices, "debts"),
        (rows.priority, "debts"),
        (rows.unsecured, "debts"),
        (rows.unsecured_notices, "debts"),
        (rows.contracts, "contracts"),
        (rows.codebtors, "codebtors"),
    )
    seen: set[tuple[str, ...]] = set()
    entries = []
    for listed, step in sources:
        for row in listed:
            parts = {
                part: _address_cell(part)(row)
                for part in ("name", "street", "street_2", "city", "state", "zip")
            }
            key = _entry_key(list(parts.values()))
            if key in seen:
                continue
            seen.add(key)
            entries.append(CreditorEntry(text=_entry_text(parts), step=step))
    return entries


def _tick(on: bool) -> str:
    return "true" if on else ""


def _status(kind: str) -> Callable[[DebtRow], str]:
    return lambda row: _tick(kind in (row.debt.get_claim_status() or []))


def _priority_type(kind: str) -> Callable[[DebtRow], str]:
    return lambda row: _tick(row.debt.priority_answer == kind)


def _lien_kind(kind: str) -> Callable[[DebtRow], str]:
    return lambda row: _tick(kind in ((row.debt.get_lien() or {}).get("kinds") or []))


def _lien_other_text(row: DebtRow) -> str:
    lien = row.debt.get_lien() or {}
    return (lien.get("other") or "") if "other" in (lien.get("kinds") or []) else ""


def _other_type_words(row: DebtRow) -> str:
    debt_type = row.debt.debt_type
    return "" if debt_type == "student_loan" else DEBT_TYPE_WORDS.get(debt_type, "")


def _lines(lines: tuple[str, ...]) -> str:
    return ", ".join(lines)


_ADDRESS_PARTS = ("name", "city", "state", "zip")


def _addressed(*extra: str) -> dict[str, Callable[[Any], str]]:
    return {part: _address_cell(part) for part in (*_ADDRESS_PARTS, *extra)}


_DEBT_COMMON = {
    "who": lambda row: "another" if row.with_another else "debtor_1",
    "who_debtor_1": lambda row: _tick(not row.with_another),
    "who_another": lambda row: _tick(row.with_another),
    "community": lambda row: _tick(row.debt.community_debt == "yes"),
    "date": lambda row: row.debt.date_incurred or "",
    "contingent": _status("contingent"),
    "unliquidated": _status("unliquidated"),
    "disputed": _status("disputed"),
    "last_4": lambda row: account_last_4(row.debt.account_number),
    "amount": lambda row: money_or_blank(row.debt.amount_owed),
}

CLAIM_CELLS: dict[str, dict[str, Callable[[Any], str]]] = {
    "secured": {
        **_addressed("street", "street_2"),
        **_DEBT_COMMON,
        "property": lambda row: row.debt.collateral_description or "",
        **{f"lien_{kind}": _lien_kind(kind) for kind in ("agreement", "statutory", "judgment")},
        "lien_other": _lien_kind("other"),
        "lien_other_text": _lien_other_text,
        "value": lambda row: money_or_blank(row.value),
        "unsecured": lambda row: money_or_blank(row.unsecured),
    },
    "priority": {
        **_addressed("street", "street_2"),
        **_DEBT_COMMON,
        "offset": lambda row: row.debt.offset_answer or "",
        "priority_amount": lambda row: money_or_blank(row.debt.priority_amount),
        "nonpriority_amount": lambda row: money_or_blank(row.debt.nonpriority_amount),
        **{f"type_{kind}": _priority_type(kind) for kind in PRIORITY_TYPES},
        "other_specify": lambda row: (
            (row.debt.priority_other or "") if row.debt.priority_answer == "other" else ""
        ),
    },
    "unsecured": {
        **_addressed("street_joined"),
        **_DEBT_COMMON,
        "student_loans": lambda row: _tick(row.debt.debt_type == "student_loan"),
        "other_type": lambda row: _tick(
            bool(row.debt.debt_type) and row.debt.debt_type != "student_loan"
        ),
        "other_type_words": _other_type_words,
        "offset": lambda row: row.debt.offset_answer or "",
    },
    "secured_notices": {
        **_addressed("street", "street_2"),
        "line": lambda row: row.line,
        "last_4": lambda row: row.party.get("last_4") or "",
    },
    "unsecured_notices": {
        **_addressed("street", "street_2"),
        "line": lambda row: row.line,
        "last_4": lambda row: row.party.get("last_4") or "",
        "part": lambda row: row.part,
    },
    "contracts": {
        **_addressed("street_joined"),
        "purpose": lambda row: row.contract.description or "",
    },
    "codebtors": {
        **_addressed("street_joined"),
        "on_d": lambda row: _tick(bool(row.d_lines)),
        "d_lines": lambda row: _lines(row.d_lines),
        "on_ef": lambda row: _tick(bool(row.ef_lines)),
        "ef_lines": lambda row: _lines(row.ef_lines),
        "on_g": lambda row: _tick(bool(row.g_lines)),
        "g_lines": lambda row: _lines(row.g_lines),
    },
    # The List of Creditors' rows are CreditorEntry objects, not a ClaimRows list (3c6 R5).
    "creditor_list": {"entry": lambda entry: entry.text},
}
# The cells that print a dollar amount: the only columns a group's total box may add (R14).
CLAIM_MONEY_CELLS = frozenset(
    {"amount", "value", "unsecured", "priority_amount", "nonpriority_amount"}
)
_CLAIM_BINDING = re.compile(r"claims\.(\w+)\[\]\.(\w+)")
# Schedule C's slot columns, one getter per ExemptionRow field (3g2 R1).
EXEMPTION_CELLS: dict[str, Callable[[ExemptionRow], str]] = {
    "description": lambda row: row.description,
    "line": lambda row: row.line,
    "value": lambda row: row.value,
    "amount_kind": lambda row: row.amount_kind,
    "amount": lambda row: row.amount,
    "law": lambda row: row.law,
}
_EXEMPTION_ROWS_BINDING = re.compile(r"exemptions\.claims\[\]\.(\w+)")
_EXEMPTION_ANSWER_BINDING = re.compile(r"exemptions\.(line_1|line_3|line_3_1)")


def is_money_binding(binding: str) -> bool:
    """Whether a binding's cells are dollar amounts, so a total box can add them (R14)."""
    match = _CLAIM_BINDING.fullmatch(binding.strip())
    if match:
        return match[2] in CLAIM_MONEY_CELLS
    return binding.strip() == "sofa.creditor_payments[].total_paid"


# Single-box answers, compared case-insensitively (spec §5.1).
_TICK = {"yes", "y", "true", "1", "on"}
_NO_TICK = {"no", "n", "false", "0", "off", ""}


def resolve_binding(binding: str, session: IntakeSession) -> str | list[str]:
    """
    Resolve a schema ``binding``:

      - "answer:<form_type>.<key>" → the FormAnswer value, or "" if absent
      - "sofa.<collection>[].<attr>" → list of str over the collection
      - "sofa.<attr>" → scalar str on the SOFAReport
      - "household.dependents[].<attr>" → list of str over Schedule J line 2's dependents
      - "assets.line_<key>[].<attr>" or "assets.line_<key>_<kind>[].<attr>" → list of str over
        that line's Schedule A/B rows, or those of that kind, in the form's order
      - "claims.<list>[].<attr>" → list of str over one of claim_rows' seven lists (secured,
        secured_notices, priority, unsecured, unsecured_notices, contracts, codebtors), each cell
        from CLAIM_CELLS; or over `creditor_list`, the List of Creditors' entries
        (`creditor_entries`: a CreditorEntry, its `entry` cell the entry's text)
      - "exemptions.claims[].<attr>" → list of str over Schedule C's printed claims, each cell
        from EXEMPTION_CELLS
      - "exemptions.line_1" | "exemptions.line_3" | "exemptions.line_3_1" → the filer's answer
        as a str, "" when unanswered
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

    if binding.startswith("household."):
        collection, _, attr = binding[len("household.") :].partition("[].")
        cell = _HOUSEHOLD_CELLS.get(attr) if collection == "dependents" else None
        if cell is None:
            raise ValueError(f"unrecognized binding: {binding!r}")
        # A list never answered raises IncomeStepGap here: it is a gap, never "no dependents".
        values = (row.get(attr) for row in dependents(household_members(session)))
        return ["" if value is None else cell(value) for value in values]

    if binding.startswith("income.statement[]."):
        attr = binding[len("income.statement[].") :]
        if attr not in ("owner", "description", "gross", "expenses", "net"):
            raise ValueError(f"unrecognized binding: {binding!r}")
        filer = getattr(session, "income_info", None)
        if filer is None:
            return []
        return [row[attr] for row in statement_rows(filer, counted_spouse_income(session))]

    if binding.startswith("assets."):
        match = _ASSET_BINDING.fullmatch(binding)
        key, kind, attr = match.groups() if match else (None, None, None)
        line = LINE_BY_KEY.get(key)
        if (
            line is None
            or attr not in ASSET_CELLS
            or (kind is not None and kind not in dict(line.kinds))
        ):
            raise ValueError(f"unrecognized binding: {binding!r}")
        return [ASSET_CELLS[attr](row) for row in rows_on(ordered_assets(session), key, kind)]

    if binding.startswith("claims."):
        match = _CLAIM_BINDING.fullmatch(binding)
        cell = CLAIM_CELLS.get(match[1], {}).get(match[2]) if match else None
        if cell is None:
            raise ValueError(f"unrecognized binding: {binding!r}")
        if match[1] == "creditor_list":
            return [cell(entry) for entry in creditor_entries(claim_rows(session))]
        return [cell(row) for row in getattr(claim_rows(session), match[1])]

    if binding.startswith("exemptions."):
        # exemption_items imports this module, so it is imported here (R2).
        from apps.forms.services.exemption_items import exemption_answer, exemption_rows

        rows_match = _EXEMPTION_ROWS_BINDING.fullmatch(binding)
        if rows_match and rows_match[1] in EXEMPTION_CELLS:
            cell = EXEMPTION_CELLS[rows_match[1]]
            return [cell(row) for row in exemption_rows(session)]
        answer_match = _EXEMPTION_ANSWER_BINDING.fullmatch(binding)
        if answer_match:
            return exemption_answer(session, answer_match[1])
        raise ValueError(f"unrecognized binding: {binding!r}")

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


def binding_fix(binding: str) -> dict[str, str]:
    """Where the filer changes what a binding reads, from its namespace; {} for no namespace."""
    binding = binding.strip()
    if binding.startswith("answer:"):
        # The form the binding names, which isn't always the one printing it: Form 101's
        # preparer prints on 106Dec and 107 too.
        form_type, _, _ = binding[len("answer:") :].partition(".")
        return {"page": f"/ask/{form_type}"}
    if binding.startswith("sofa."):
        return {"page": "/sofa"}
    if binding.startswith(("household.", "income.")):
        return {"step": "income_info"}
    if binding.startswith("assets."):
        return {"step": "assets"}
    if binding.startswith("claims."):
        match = _CLAIM_BINDING.match(binding)
        if match:
            if match[1] == "contracts":
                return {"step": "contracts"}
            if match[1] == "codebtors":
                return {"step": "codebtors"}
        return {"step": "debts"}
    if binding.startswith("exemptions."):
        return {"page": "/exemptions"}
    # A constant or a signature: a refusal there is DigniFi's defect, not the filer's.
    return {}


def row_fixes(binding: str, session: IntakeSession) -> list[dict[str, str]] | None:
    """
    One fix per entry for a list binding whose rows come from different steps, in the order
    the binding lists them; None for every other binding (R8). Only the List of Creditors'
    entries have them: each entry's fix is the step of its first row.
    """
    if binding.strip() == "claims.creditor_list[].entry":
        return [{"step": e.step} for e in creditor_entries(claim_rows(session))]
    return None


def fix_for(field: FieldSpec) -> dict[str, str]:
    """
    Where the filer changes a binding's value, for a refusal to link to (3a2 spec §4.5):
    {"step": <a WIZARD_STEPS key>}, {"page": <path>}, or {} when no filer edits it.
    """
    if field.source == "derived":
        return dict(RULE_FIXES[field.rule])  # a copy: the map is shared by every refusal
    if field.source in ("ingested", "db_aggregate"):
        return {"page": "/documents"}
    return binding_fix(field.binding or "")


def group_fix(schema: FormSchema, name: str) -> dict[str, str]:
    """Where the filer changes a group's rows: the fix of its first slot with a binding."""
    for field in schema.fields:
        if field.repeat == name and field.binding:
            return fix_for(field)
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
    A page-number box stays out of a copy only because `_number_pages` runs after every
    `_copies` has read these headers.
    """
    drawn: dict[str, list[TemplateWidget]] = {}
    for widget in template_widgets(schema.template_filename):
        if widget.drawn:
            drawn.setdefault(widget.full_name, []).append(widget)
    own = {_key(f) for f in schema.fields if f.repeat is not None}
    for group in schema.groups.values():
        own |= set(group.number_boxes.values())
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
    the group does, and repeats the form's page headers. The group's `fields` decide its
    slots and `printed` the cells that print, as on the form's pages.
    """
    page = group.extra_page
    slots = sorted({f.row for f in fields if f.page == page and f.row})
    positions = list(range(capacity + 1, actual + 1))
    copies = []
    by_binding = {b: row_fixes(b, session) for b in {f.binding for f in printed if f.binding}}
    for start in range(0, len(positions), len(slots)):
        values: dict[str, str] = {}
        fixes: dict[str, dict[str, str]] = {}
        # The last copy may hold fewer rows than the page has slots.
        for row, position in zip(slots, positions[start : start + len(slots)], strict=False):
            for f in printed:
                if f.row == row and f.page == page:
                    emitted = _cell(f, position, columns, session, ingested_cache)
                    if emitted is not None:
                        values[_key(f)] = emitted
                        # The entry's own step, by its position in the list, never the slot's row.
                        listed = by_binding.get(f.binding)
                        if listed is not None and position <= len(listed):
                            fixes[_key(f)] = dict(listed[position - 1])
            if row in group.number_boxes:
                values[group.number_boxes[row]] = group.number.format(n=position)
        copy = {"kind": "copy", "page": page, "number": len(copies) + 1, "values": values}
        if fixes:
            copy["fixes"] = dict(sorted(fixes.items()))
        copies.append(copy)

    headers = _headers(schema, form, page)
    for copy in copies:
        copy["values"] = {**headers, **copy["values"]}
    return copies


def _number_pages(schema: FormSchema, form: dict[str, str], copies: list[dict]) -> None:
    """
    With copies, every page-number box counts the copies of every group (3c spec §5.2): a page's
    position is its page number plus the copies of each page before it, and copy n of a page
    prints n places after that page. E007 keeps one group to each extra page.
    """
    if not copies:
        return
    copies_of = Counter(copy["page"] for copy in copies)
    total = page_count(schema.template_filename) + len(copies)

    def position(page: int) -> int:
        return page + sum(count for extra, count in copies_of.items() if extra < page)

    boxes_of = {boxes.page: boxes for boxes in schema.page_numbers}
    for boxes in schema.page_numbers:
        _number_page(form, boxes, position(boxes.page), total)
    for copy in copies:
        if copy["page"] in boxes_of:
            at = position(copy["page"]) + copy["number"]
            _number_page(copy["values"], boxes_of[copy["page"]], at, total)


def _line_width(sheet: SheetSpec) -> dict[str, float]:
    """A sheet part's line_width: only one that isn't 36 pt, so older documents stay as filed."""
    return {} if sheet.line_width == SheetSpec.line_width else {"line_width": sheet.line_width}


def _sheet(
    group: GroupSpec,
    fields: list[FieldSpec],
    printed: list[FieldSpec],
    columns: dict[str, str | list[str]],
    capacity: int,
    actual: int,
    session: IntakeSession,
    ingested_cache: dict,
    template_filename: str,
) -> dict:
    """
    The attached sheet that prints the group's rows past `capacity` (3a2 spec §5.3): each row
    labelled with its line, the group's number for its position, and a cell per column,
    the column's binding for that row as the group's slot of that binding prints it; a box's
    answer prints as the words the form prints beside the box it ticks (the field index's
    `option_text`). A column that covers slots prints its own list, already in words. A column
    whose slots the UPL guard keeps blank is blank, as on the form and its copies.
    The sheet carries the filer's name for its header (R23), and its title, its columns'
    labels and widths and any wider line column (R63), so a filed sheet redraws as it was filed.
    """
    covering = {
        column.label: resolve_binding(column.binding, session)
        for column in group.sheet.columns
        if column.covers is not None
    }
    rows = []
    for position in range(capacity + 1, actual + 1):
        cells = []
        for column in group.sheet.columns:
            if column.covers is not None:
                covered = [f for f in fields if f.binding in column.covers]
                shown = all(f in printed for f in covered)
                cells.append(covering[column.label][position - 1] if shown else "")
                continue
            slots = [f for f in fields if f.binding == column.binding]  # one at least: E007
            emitted = None
            if all(f in printed for f in slots):
                emitted = _cell(slots[0], position, columns, session, ingested_cache)
            if emitted is not None and slots[0].type in ("checkbox", "radio"):
                # E005 ties every choices value to one of the box's states.
                emitted = option_text(template_filename, slots[0].pdf_field, emitted)
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
        **_line_width(group.sheet),
    }


def _added(amounts: list[str]) -> str:
    """The sum of printed amounts, to the cent."""
    return money_or_blank(sum((Decimal(a) for a in amounts), Decimal(0)))


def _write_totals(
    group: GroupSpec, printed: list[FieldSpec], form: dict[str, str], copies: list[dict]
) -> None:
    """
    A group's total boxes (3c spec §5.3). Each page and each copy prints the sum of its own rows
    in its own box, and a page with no row leaves its box blank. The last-page box prints every
    row's sum on the last copy, or the extra page with no copy, even with no row at all.
    """
    totals = group.totals
    column = [f for f in printed if f.binding == totals.column]
    everything = []
    for values, pages in (
        (form, sorted({f.page for f in column})),
        *((copy["values"], [copy["page"]]) for copy in copies),
    ):
        for page in pages:
            amounts = [values[_key(f)] for f in column if f.page == page and _key(f) in values]
            everything += amounts
            if amounts and page in totals.page_boxes:
                values[totals.page_boxes[page]] = _added(amounts)
    if totals.last_page_box:
        last = copies[-1]["values"] if copies else form
        last[totals.last_page_box] = _added(everything)


def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
    """The values the form's own pages print: resolve_parts()'s form part."""
    return resolve_parts(schema, session)["parts"][0]["values"]


def resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
    """
    The form's values as the parts it prints, in printing order (3a2 spec §6):
    {"version": 2, "parts": [{"kind": "form", "values": {key: value}}, *copies, *sheets]}.

    A repeat group fills its slots in row order. Rows past its last slot continue on
    copies of the extra page its declaration names (3a2 spec §5.2), each
    {"kind": "copy", "page": <extra page>, "number": <from 1>, "values": {key: value}}.
    A form or copy part of a form whose schema declares number boxes also carries
    "number_boxes": [key, ...], every number-box key of that schema, sorted, whether or not the
    part prints that box (none declared, no key; page-number and total boxes are not listed)
    (R11). Those keys skip /MaxLen when the part is checked or drawn, and only a single-line,
    fixed-size box among them takes the right bearing at 6 pt (R15). A form or copy part also
    carries "fixes": {key: fix}, keys sorted, the step of the entry each box prints, only when
    a slot it fills has per-row fixes (`row_fixes`, R8; only the List of Creditors'
    `claims.creditor_list[].entry` has them). A group may instead
    continue on the attached sheet it declares (3a2 spec §5.3, R23, R63), one part for all of
    them:
    {"kind": "sheet", "group": <group>, "title": <its title>,
    "columns": [{"label": str, "width": <points>}], "name": <the filer's full name>,
    "rows": [{"line": "3.5", "cells": [<one per column>]}]}, plus "line_width": <points> only
    when the sheet's isn't 36.
    """
    # A/B's rules and bindings each ask for the rows: measured at 0.62 s more with 20 rows, a read
    # per rule. The read stays in this call, never on the session, so a session held across a save
    # prints what the save stored. Schedule C's claim rows are a third read, for all 90 slots.
    from apps.forms.services.exemption_items import one_read_of_exemptions  # cycle, as above (R2)

    with one_read_of_assets(), one_read_of_claims(), one_read_of_exemptions():
        return _resolve_parts(schema, session)


def _resolve_parts(schema: FormSchema, session: IntakeSession) -> dict:
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
    form_fixes: dict[str, dict[str, str]] = {}
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
        by_binding = {b: row_fixes(b, session) for b in {f.binding for f in printed if f.binding}}
        for f in printed:
            emitted = _cell(f, f.row, resolved_cols, session, _ingested_cache)
            if emitted is not None:
                out[_key(f)] = emitted
                listed = by_binding.get(f.binding)
                if listed is not None and f.row and f.row <= len(listed):
                    form_fixes[_key(f)] = dict(listed[f.row - 1])
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
                    schema.template_filename,
                )
            )
        elif actual > capacity:
            if group is None or group.extra_page is None:
                # The startup check refuses such a schema (forms.E007); never drop a row.
                raise ValueError(f"{schema.form_type}: group {group_name!r} names no extra page")
            overflowing.append((group, fields, printed, resolved_cols, capacity, actual))

    # Copies once the form's own values are all in: they repeat its page headers.
    copies_of: dict[str, list[dict]] = {}
    for group, fields, printed, resolved_cols, capacity, actual in overflowing:
        copies_of[group.name] = _copies(
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
        copies += copies_of[group.name]
    # Printing order, however the schema declares its groups (sorted is stable). Then the pages
    # are numbered once, counting every group's copies (3c spec §5.2): the order matters, since
    # numbering runs only after every group's copies, and their headers, exist.
    copies.sort(key=lambda copy: copy["page"])
    _number_pages(schema, out, copies)
    for group_name, group in schema.groups.items():
        if group.totals is None:
            continue
        # Every slot, not `groups`' own: a section that doesn't apply still prints "0.00" (R2).
        fields = [f for f in schema.fields if f.repeat == group_name and not _unmapped(f)]
        printed = [f for f in fields if not (f.legal_review and f.source != "asked")]
        # A column the UPL guard keeps blank on any slot adds up to no total (R3).
        if all(f in printed for f in fields if f.binding == group.totals.column):
            _write_totals(group, printed, out, copies_of.get(group_name, []))
    for name, group in schema.groups.items():
        if not is_statement_group(schema, name):
            continue
        columns = [resolve_binding(c.binding, session) for c in group.sheet.columns]
        if columns and columns[0]:
            sheets.append(
                {
                    "kind": "sheet",
                    "group": name,
                    "title": group.sheet.title,
                    "columns": [{"label": c.label, "width": c.width} for c in group.sheet.columns],
                    "name": DERIVATIONS["full_name"](session),
                    "rows": [
                        {"line": group.number.format(n=i), "cells": [col[i - 1] for col in columns]}
                        for i in range(1, len(columns[0]) + 1)
                    ],
                    **_line_width(group.sheet),
                }
            )
    form_part = {"kind": "form", "values": out}
    if form_fixes:
        form_part["fixes"] = dict(sorted(form_fixes.items()))
    # The boxes that take more room than /MaxLen are stored with each part, so a filed document
    # keeps them whatever its schema declares later (R11): none declared, no key.
    number_keys = sorted(number_box_keys(schema))
    if number_keys:
        for part in (form_part, *copies):
            part["number_boxes"] = number_keys
    return {"version": 2, "parts": [form_part, *copies, *sheets]}
