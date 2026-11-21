"""
Writes Form 101 (11/26)'s schema whole, its step 2 addendum rows and the caps on the filer's
text (step 4 spec §8, plan 4b-R5, 4b-R10). Run it with the backend's Python, the one with the
backend's requirements installed, since the caps are measured with the filler's own text_fit.
From the repo root:

    python data/forms/field_index/tools/build_form_101.py

It puts `backend/` on the path and sets up Django itself (`config.settings.test` unless
DJANGO_SETTINGS_MODULE names another), so it needs no database and no other setup.

Never hand-edit `form_101.json`, `form_101.limits.json` or Form 101's addendum rows: change this
tool and run it again. `test_the_schema_and_its_rows_and_caps_are_what_the_tool_writes` fails on
any difference. It owns every Form 101 row of `step2_verification.json`.

The table is keyed by the index label (4b-R5): `build_form_101_index.py` reads each widget off
the PDF by page and rectangle and gives it a label unique on the form, and this tool looks the
name, page and tag up in the committed index by that label, exiting on zero or two matches. Like
the other schema tools it copies `export_state` and `dumps()` rather than importing them: the
tools folder isn't a package. Only `limits()` imports the backend, lazily.

The caps (Ruling T4-caps, method A) are measured in digit-wide letters, except a ZIP code's
digits and a state's capitals: an answer under its cap typed in capitals or wide letters can
still be refused at Generate, where check() names the box and the step. Task 7 measures the real
width as a detail gap, so Review names such an answer first (hand-off).
"""

import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INDEX_DIR = ROOT / "data" / "forms" / "field_index"
SCHEMAS_DIR = ROOT / "data" / "forms" / "schemas"
PDFS = ROOT / "data" / "forms" / "pdfs"
ADDENDUM = INDEX_DIR / "audit" / "step2_verification.json"

FORM_TYPE = "form_101"
TEMPLATE = "form_b101.pdf"

KIND = {"Text": "text", "CheckBox": "checkbox", "RadioButton": "radio"}
ON = {"true": "/On"}


# ---------------------------------------------------------------------------
# The binding helpers: each gives the parts of a field its table row decides
# ---------------------------------------------------------------------------


def derived(rule, *, tag=False, conditional_on=None):
    """A text box a derivation prints."""
    return {"source": "derived", "rule": rule, "tag": tag, "conditional_on": conditional_on}


def asked(
    binding,
    *,
    legal_review=False,
    conditional_on=None,
    repeat=None,
    capacity=None,
    row=None,
    tag=False,
):
    """A text box that prints the filer's own answer, a `petition.` key or a row's cell."""
    return {
        "source": "asked",
        "binding": binding,
        "legal_review": legal_review,
        "conditional_on": conditional_on,
        "repeat": repeat,
        "repeat_capacity": capacity,
        "row": row,
        "tag": tag,
    }


def asked_radio(binding, choices):
    """A yes/no radio: the answer → the group's own state for it, copied from the index."""
    return {"source": "asked", "type": "radio", "binding": binding, "choices": choices}


def single_box(rule, *, conditional_on=None, legal_review=False):
    """One choice's own box, ticked by a derivation that returns "true" for exactly its value."""
    return {
        "source": "derived",
        "type": "checkbox",
        "rule": rule,
        "choices": ON,
        "conditional_on": conditional_on,
        "legal_review": legal_review,
    }


def constant_box():
    """A box ticked for every filer."""
    return {"source": "constant", "type": "checkbox", "value": "true", "choices": ON}


# ---------------------------------------------------------------------------
# The table: every bound box of §8, by its index label
# ---------------------------------------------------------------------------

D1 = "Debtor 1, line {line}: {what}"
OTHER_NAMES = "petition_other_names_yes"
MAILING = "petition_mailing_yes"
VENUE = "petition_venue_other"
PRIOR = "petition_prior_bankruptcy_yes"
PENDING = "petition_pending_case_yes"
BUSINESS = "petition_sole_proprietor_yes"
HAZARD = "petition_hazard_yes"

# Line 18's boxes, by the lowest count of each range, as _creditor_count_range returns it.
CREDITOR_RANGES = [
    ("1-49", "1"),
    ("50-99", "50"),
    ("100-199", "100"),
    ("200-999", "200"),
    ("1,000-5,000", "1000"),
    ("5,001-10,000", "5001"),
    ("10,001-25,000", "10001"),
    ("25,001-50,000", "25001"),
    ("50,001-100,000", "50001"),
    ("more than 100,000", "more"),
]
# Lines 19 and 20's boxes, by the lowest figure of each range, as the range rules return it.
AMOUNT_RANGES = [
    ("$0-$50,000", "0"),
    ("$50,001-$100,000", "50001"),
    ("$100,001-$500,000", "100001"),
    ("$500,001-$1 million", "500001"),
    ("$1,000,001-$10 million", "1000001"),
    ("$10,000,001-$50 million", "10000001"),
    ("$50,000,001-$100 million", "50000001"),
    ("$100,000,001-$500 million", "100000001"),
    ("$500,000,001-$1 billion", "500000001"),
    ("$1,000,000,001-$10 billion", "1000000001"),
    ("$10,000,000,001-$50 billion", "10000000001"),
    ("more than $50 billion", "more"),
]


def _slot(binding, group, capacity, row, conditional_on, *, tag=False):
    return asked(
        binding,
        repeat=group,
        capacity=capacity,
        row=row,
        conditional_on=conditional_on,
        tag=tag,
    )


def _bindings():
    rows = [
        # The cover: the court split from the district's name, and Chapter 7 (B56, §8).
        ("Court: the district, before 'District of' (page 1)", derived("court_district", tag=True)),
        ("Court: the state, after 'District of' (page 1)", derived("court_state")),
        ("Chapter you are filing under, page 1: Chapter 7", constant_box()),
    ]
    # The running header: the name's parts on pages 2, 4 and 7, the whole name on 3, 5, 6 and 8.
    # A part too wide for its narrow box prints blank there, never refusing the form (owner
    # ruling, 2026-11-20); line 1 and the whole-name boxes print it whole.
    for page in (2, 4, 7):
        for part in ("first", "middle", "last"):
            rows.append(
                (f"Header, page {page}: Debtor 1 {part} name", derived(f"header_{part}_name"))
            )
    for page in (3, 5, 6, 8):
        rows.append((f"Header, page {page}: Debtor 1 name", derived("full_name")))
    # Line 1.
    for part in ("first", "middle", "last"):
        rows.append((D1.format(line=1, what=f"{part} name"), derived(f"{part}_name")))
    rows.append((D1.format(line=1, what="suffix"), asked("petition.name_suffix")))
    # Line 2: the filer's other names and business names, two of each, under the line's Yes.
    for n in (1, 2):
        for part in ("first", "middle", "last"):
            rows.append(
                (
                    D1.format(line=2, what=f"other name {n}, {part} name"),
                    _slot(f"petition.other_names[].{part}", "other_names", 2, n, OTHER_NAMES),
                )
            )
    for n in (1, 2):
        rows.append(
            (
                D1.format(line=2, what=f"business name {n}"),
                _slot(
                    "petition.other_business_names[].name",
                    "other_business_names",
                    2,
                    n,
                    OTHER_NAMES,
                ),
            )
        )
    # Line 3: one digit a box; the ITIN only under its Yes (Ruling T4-gates).
    for n in (1, 2, 3, 4):
        rows.append(
            (
                D1.format(line=3, what=f"last 4 of the SSN, digit {n} of 4"),
                derived(f"ssn_last4_digit_{n}"),
            )
        )
    for n in (1, 2, 3, 4):
        rows.append(
            (
                D1.format(line=3, what=f"last 4 of the ITIN, digit {n} of 4"),
                derived(f"itin_last4_digit_{n}", conditional_on="petition_itin_yes"),
            )
        )
    # Line 4: the first EIN, 2 + 7 digits, whatever line 12 says: spec §6.1 row 1e and §8 line 4
    # ask it with no gate (Ruling T4-gates, corrected).
    rows += [
        (D1.format(line=4, what="EIN 1, first 2 digits"), derived("ein_prefix")),
        (D1.format(line=4, what="EIN 1, last 7 digits"), derived("ein_suffix")),
    ]
    # Line 5: home from the intake; mailing under its Yes.
    rows += [
        (D1.format(line=5, what="home, number"), derived("home_number")),
        (D1.format(line=5, what="home, street"), derived("home_street")),
        (D1.format(line=5, what="home, city"), derived("city")),
        (D1.format(line=5, what="home, state"), derived("state")),
        (D1.format(line=5, what="home, ZIP code"), derived("zip_code")),
        (D1.format(line=5, what="home, county"), derived("county")),
        (
            D1.format(line=5, what="mailing, number"),
            derived("mailing_number", conditional_on=MAILING),
        ),
        (
            D1.format(line=5, what="mailing, street"),
            derived("mailing_street", conditional_on=MAILING),
        ),
        (
            D1.format(line=5, what="mailing, P.O. Box"),
            asked("petition.mailing_po_box", conditional_on=MAILING),
        ),
        (
            D1.format(line=5, what="mailing, city"),
            asked("petition.mailing_city", conditional_on=MAILING),
        ),
        (
            D1.format(line=5, what="mailing, state"),
            asked("petition.mailing_state", conditional_on=MAILING),
        ),
        (
            D1.format(line=5, what="mailing, ZIP code"),
            asked("petition.mailing_zip", conditional_on=MAILING),
        ),
    ]
    # Line 6: two single boxes and the other reason's four lines (Ruling T4-gates).
    rows += [
        (D1.format(line=6, what="lived in this district longer"), single_box("venue_lived_here")),
        (D1.format(line=6, what="another reason"), single_box("venue_other")),
    ]
    for n in (1, 2, 3, 4):
        rows.append(
            (
                D1.format(line=6, what=f"the other reason, line {n} of 4"),
                derived(f"venue_reason_line_{n}", conditional_on=VENUE),
            )
        )
    # Line 7 and line 8.
    rows += [
        ("Line 7: Chapter 7", constant_box()),
        ("Line 8: pay the entire fee when filing", single_box("fee_choice_pay_in_full")),
        ("Line 8: pay the fee in installments", single_box("fee_choice_installments")),
        ("Line 8: ask that the fee be waived", single_box("fee_choice_waiver")),
    ]
    # Line 9: the radio, then three rows (row 1's district by tag: the cover's twin, §5.5).
    rows.append(
        (
            "Line 9: No",
            asked_radio("petition.prior_bankruptcy_answer", {"no": "/No", "yes": "/Yes"}),
        )
    )
    for n in (1, 2, 3):
        for words, attr in (
            ("district", "district"),
            ("when", "filed_on"),
            ("case number", "case_number"),
        ):
            rows.append(
                (
                    f"Line 9: case {n}, {words}",
                    _slot(
                        f"petition.prior_cases[].{attr}",
                        "prior_cases",
                        3,
                        n,
                        PRIOR,
                        tag=(n, attr) == (1, "district"),
                    ),
                )
            )
    # Line 10: the radio, then two rows naming the other party.
    rows.append(
        (
            "Line 10: No",
            asked_radio("petition.pending_case_answer", {"no": "/No_2", "yes": "/Yes_2"}),
        )
    )
    pending_cells = (
        ("debtor", "debtor"),
        ("relationship to you", "relationship"),
        ("district", "district"),
        ("when", "filed_on"),
        ("case number", "case_number"),
    )
    for n in (1, 2):
        for words, attr in pending_cells:
            rows.append(
                (
                    f"Line 10: case {n}, {words}",
                    _slot(f"petition.pending_cases[].{attr}", "pending_cases", 2, n, PENDING),
                )
            )
    # Line 11: the rent radio and the eviction's two boxes, which read the rent's Yes.
    rows += [
        (
            "Line 11: rent your residence, No",
            asked_radio("petition.rents_residence", {"no": "/No_3", "yes": "/Yes_3"}),
        ),
        ("Line 11: eviction judgment, No", single_box("eviction_no")),
        ("Line 11: eviction judgment, Yes", single_box("eviction_yes")),
    ]
    # Line 12: two single boxes, the business under the line's own Yes, and the five kinds.
    rows += [
        ("Line 12: No", single_box("sole_proprietor_no")),
        ("Line 12: Yes", single_box("sole_proprietor_yes")),
        ("Line 12: name of business", asked("petition.business_name", conditional_on=BUSINESS)),
        ("Line 12: business, number", derived("business_number", conditional_on=BUSINESS)),
        ("Line 12: business, street", derived("business_street", conditional_on=BUSINESS)),
        ("Line 12: business, city", asked("petition.business_city", conditional_on=BUSINESS)),
        ("Line 12: business, state", asked("petition.business_state", conditional_on=BUSINESS)),
        ("Line 12: business, ZIP code", asked("petition.business_zip", conditional_on=BUSINESS)),
    ]
    for words, value in (
        ("Health Care Business", "health_care"),
        ("Single Asset Real Estate", "single_asset"),
        ("Stockbroker", "stockbroker"),
        ("Commodity Broker", "commodity_broker"),
        ("None of the above", "none"),
    ):
        rows.append((f"Line 12: {words}", single_box(f"business_kind_{value}")))
    # Line 13 (B9) and line 14 (step 5's hazard, details under its Yes).
    rows += [
        ("Line 13: No, not filing under Chapter 11", constant_box()),
        (
            "Line 14: No",
            asked_radio("petition.hazard_answer", {"no": "/No_6", "yes": "/Yes_4"}),
        ),
        (
            "Line 14: what is the hazard, first line",
            asked("petition.hazard_what", conditional_on=HAZARD),
        ),
        (
            "Line 14: why immediate attention is needed, first line",
            asked("petition.hazard_why", conditional_on=HAZARD),
        ),
        ("Line 14: where the property is, number", derived("hazard_number", conditional_on=HAZARD)),
        ("Line 14: where the property is, street", derived("hazard_street", conditional_on=HAZARD)),
        (
            "Line 14: where the property is, city",
            asked("petition.hazard_city", conditional_on=HAZARD),
        ),
        (
            "Line 14: where the property is, state",
            asked("petition.hazard_state", conditional_on=HAZARD),
        ),
        (
            "Line 14: where the property is, ZIP code",
            asked("petition.hazard_zip", conditional_on=HAZARD),
        ),
    ]
    # Line 15: seven single boxes, each a legal claim the court decides (F-5, C-40).
    for what, rule in (
        ("a briefing and a certificate", "credit_counseling_certificate"),
        ("a briefing and no certificate", "credit_counseling_no_certificate"),
        ("asked for counseling, a 30-day waiver", "credit_counseling_exigent"),
        ("not required to receive a briefing", "credit_counseling_not_required"),
        ("not required, incapacity", "not_required_incapacity"),
        ("not required, disability", "not_required_disability"),
        ("not required, active duty", "not_required_active_duty"),
    ):
        rows.append((D1.format(line=15, what=what), single_box(rule, legal_review=True)))
    # Line 16: four single boxes and 16c's text under "neither"; 16a's Yes a legal claim (F-5).
    rows += [
        ("Line 16a: consumer debts, No", single_box("debt_nature_16a_no")),
        ("Line 16a: consumer debts, Yes", single_box("debt_nature_16a_yes", legal_review=True)),
        ("Line 16b: business debts, No", single_box("debt_nature_16b_no")),
        ("Line 16b: business debts, Yes", single_box("debt_nature_16b_yes")),
        (
            "Line 16c: the type of debts",
            asked("petition.debt_nature_text", conditional_on="petition_debt_nature_neither"),
        ),
        ("Line 17: Yes, filing under Chapter 7", constant_box()),
    ]
    # Lines 18-20: one box a range.
    for words, value in CREDITOR_RANGES:
        rows.append((f"Line 18: {words} creditors", single_box(f"creditor_count_is_{value}")))
    for words, value in AMOUNT_RANGES:
        rows.append((f"Line 19: assets {words}", single_box(f"total_assets_is_{value}")))
    for words, value in AMOUNT_RANGES:
        rows.append((f"Line 20: liabilities {words}", single_box(f"total_debts_is_{value}")))
    # The notice page: the two awareness radios, the paid preparer, and the filer's contact.
    rows += [
        (
            "Notice page: aware of the consequences, No",
            asked_radio("petition.aware_consequences", {"no": "/No_8", "yes": "/Yes_6"}),
        ),
        (
            "Notice page: aware that fraud is a crime, No",
            asked_radio("petition.aware_fraud", {"no": "/No_9", "yes": "/Yes_7"}),
        ),
        ("Notice page: paid a non-attorney to help, No", single_box("paid_preparer_no")),
        ("Notice page: paid a non-attorney to help, Yes", single_box("paid_preparer_yes")),
        (
            "Notice page: the paid preparer's name",
            asked("petition.preparer_name", conditional_on="petition_paid_preparer_yes"),
        ),
        ("Notice page: Debtor 1 contact phone", derived("phone")),
        ("Notice page: Debtor 1 email address", derived("email")),
    ]
    return rows


BINDINGS: list[tuple[str, dict]] = _bindings()

COLUMN_SPECS = {
    # line 9: the court, the date and the number of each earlier case
    "prior_cases": (
        "9.{n}",
        "line 9",
        [
            ("District", "district", 190),
            ("When", "filed_on", 90),
            ("Case number", "case_number", 178),
        ],
    ),
    # line 10: a case pending or filed by a spouse, partner or affiliate
    "pending_cases": (
        "10.{n}",
        "line 10",
        [
            ("Debtor", "debtor", 136),
            ("Relationship", "relationship", 90),
            ("District", "district", 90),
            ("When", "filed_on", 62),
            ("Case number", "case_number", 80),
        ],
    ),
    # line 2: two of each fit the page, and the serializer takes two (LIST_CAPS)
    "other_names": (
        "2.{n}",
        "line 2",
        [("First", "first", 152), ("Middle", "middle", 152), ("Last", "last", 154)],
    ),
    "other_business_names": ("2.{n}", "line 2", [("Business name", "name", 458)]),
}
TITLE = "Official Form 101, Voluntary Petition for Individuals Filing for Bankruptcy, {line}"
LINE_WIDTH = 46  # "10.9999" with its padding; the columns take the other 458 of the 504 pt


def _groups():
    groups = {}
    for name, (number, line, columns) in COLUMN_SPECS.items():
        groups[name] = {
            "number": number,
            "sheet": {
                "title": TITLE.format(line=line),
                "line_width": LINE_WIDTH,
                "columns": [
                    {"label": label, "binding": f"petition.{name}[].{attr}", "width": width}
                    for label, attr, width in columns
                ],
            },
        }
    return groups


GROUPS = _groups()

# The filer's text keys, each with the box it prints in (the Street box for a street, which the
# whole line takes when it starts with no number) and the box in plain words for DETAIL_TOO_LONG
# (F-16). venue_reason is measured across its four lines (4b-R10, Ruling T4-caps).
LIMITED = [
    ("name_suffix", "Debtor 1, line 1: suffix", "line 1's suffix"),
    ("mailing_street", "Debtor 1, line 5: mailing, street", "line 5's mailing street"),
    ("mailing_po_box", "Debtor 1, line 5: mailing, P.O. Box", "line 5's P.O. Box"),
    ("mailing_city", "Debtor 1, line 5: mailing, city", "line 5's mailing city"),
    ("mailing_state", "Debtor 1, line 5: mailing, state", "line 5's mailing state"),
    ("mailing_zip", "Debtor 1, line 5: mailing, ZIP code", "line 5's mailing ZIP code"),
    ("venue_reason", "Debtor 1, line 6: the other reason, line 1 of 4", "line 6's other reason"),
    ("business_name", "Line 12: name of business", "line 12's business name"),
    ("business_street", "Line 12: business, street", "line 12's business street"),
    ("business_city", "Line 12: business, city", "line 12's business city"),
    ("business_state", "Line 12: business, state", "line 12's business state"),
    ("business_zip", "Line 12: business, ZIP code", "line 12's business ZIP code"),
    ("hazard_what", "Line 14: what is the hazard, first line", "line 14's hazard"),
    (
        "hazard_why",
        "Line 14: why immediate attention is needed, first line",
        "line 14's reason the property needs attention",
    ),
    ("hazard_street", "Line 14: where the property is, street", "line 14's property street"),
    ("hazard_city", "Line 14: where the property is, city", "line 14's property city"),
    ("hazard_state", "Line 14: where the property is, state", "line 14's property state"),
    ("hazard_zip", "Line 14: where the property is, ZIP code", "line 14's property ZIP code"),
    ("debt_nature_text", "Line 16c: the type of debts", "line 16c's type of debts"),
    ("preparer_name", "Notice page: the paid preparer's name", "the paid preparer's name"),
]
VENUE_LINES = 4

# The letters a key's cap is measured in (Ruling T4-caps, method A). The browser's maxLength is
# the cap (spec §5.7), so a cap must never shut out an ordinary answer; a text the page lets
# through that its box can't hold is refused at Generate by check(), which names the box and the
# step (§5.7 again):
# - a ZIP code is digits and a hyphen: its widest, a digit, makes the cap exact;
# - a state is a postal abbreviation, capital letters: its widest, W, makes the cap exact;
# - every other text, the venue reason included, is measured in digits, Helvetica's 0.556 em,
#   wider than every small letter but m and w and narrower than most capitals: ordinary
#   mixed-case words at the cap fit, and words mostly of capitals or wide letters may not.
# So an answer under its cap typed in capitals or wide letters can still be refused at Generate.
# Hand-off to Task 7: measure the real width as a detail gap, so Review names such an answer.
ZIP_LETTERS = "0123456789-"
STATE_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TEXT_LETTERS = "0123456789"


def measuring_letters(key):
    """The letters `key`'s cap is measured in."""
    if key.endswith("_zip"):
        return ZIP_LETTERS
    if key.endswith("_state"):
        return STATE_LETTERS
    return TEXT_LETTERS


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


def export_state(on_state):
    """The index's on-state as the PDF's export state: the name escapes decoded."""
    return "/" + re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), on_state)


def _by_label(index, label):
    found = [row for row in index if row["label"] == label]
    if len(found) != 1:
        sys.exit(f"{len(found)} index rows labelled {label!r}")
    return found[0]


def _named(index, name):
    return [row for row in index if row["full_name"] == name]


def _field(index, label, spec):
    """The schema field the table row (label, spec) binds, and the index rows it fills."""
    row = _by_label(index, label)
    name = row["full_name"]
    widgets = _named(index, name)
    kind = KIND[row["type"]]
    if spec.get("type") == "radio" or kind == "radio":
        if {w["type"] for w in widgets} != {"RadioButton"} or spec.get("type") != "radio":
            sys.exit(f"{label!r}: a radio is bound only by asked_radio, to every kid")
        states = {export_state(w["on_state"]) for w in widgets}
        if set(spec["choices"].values()) != states:
            sys.exit(f"{label!r}: choices {spec['choices']} aren't the group's states {states}")
    elif spec.get("tag"):
        widgets = [row]
    elif len(widgets) != 1:
        sys.exit(f"{label!r}: {name!r} has {len(widgets)} widgets, so it needs a tag")
    if spec.get("type") == "checkbox" and kind != "checkbox":
        sys.exit(f"{label!r}: a single box bound to a {row['type']}")
    if spec.get("choices") == ON and export_state(row["on_state"]) != "/On":
        sys.exit(f"{label!r}: its box isn't ticked by /On")
    out = {"pdf_field": name}
    if spec.get("tag"):
        out["tag"] = row["tag"]
    out |= {"type": spec.get("type", kind), "source": spec["source"]}
    if "choices" in spec:
        out["choices"] = spec["choices"]
    out |= {
        "page": row["page"],
        "label": label,
        "required": False,
        "conditional_on": spec.get("conditional_on"),
        "value": spec.get("value"),
        "rule": spec.get("rule"),
        "ingest_key": None,
        "binding": spec.get("binding"),
        "repeat": spec.get("repeat"),
        "repeat_capacity": spec.get("repeat_capacity"),
        "row": spec.get("row"),
        "legal_review": spec.get("legal_review", False),
    }
    return out, widgets


def _placed(index):
    return [_field(index, label, spec) for label, spec in BINDINGS]


def schema(index, sha256):
    """Form 101's schema from the committed index and the template's hash."""
    return {
        "form_type": FORM_TYPE,
        "template_filename": TEMPLATE,
        "template_version": sha256,
        "groups": GROUPS,
        "fields": [spec for spec, _ in _placed(index)],
    }


def _producer(spec):
    return f"{spec['source']}:{spec['rule'] or spec['binding'] or spec['value']}"


def _section(widget):
    """§8's row for the widget: its line, or the notice page, or the cover and headers."""
    if widget["line"]:
        return f"line {widget['line']}"
    if widget["label"].startswith("Notice page"):
        return "the notice page"
    return "the cover and running headers"


def _line_words(widget):
    return f" line {widget['line']}" if widget["line"] else ""


def _basis(spec):
    if spec["source"] == "constant":
        return "prints for every filer (§8: the cover and line 7's Chapter 7, line 13, line 17)."
    if spec["rule"] and spec["type"] == "checkbox":
        return f"{spec['rule']} ticks it for its own answer and leaves it blank for another (B56)."
    if spec["rule"]:
        return f"{spec['rule']} prints it (§8, B56)."
    if spec["type"] == "radio":
        return f"{spec['binding']} picks the group's own state for the filer's No or Yes (§5.3)."
    if spec["repeat"]:
        return f"Row {spec['row']} of group {spec['repeat']} prints {spec['binding']} here."
    return f"{spec['binding']} prints the filer's own answer."


def _evidence(spec, widgets):
    words = "; ".join(
        f"p{w['page']} {w['tag']}{_line_words(w)}, {w['label']!r} ({w['basis']})" for w in widgets
    )
    gate = f" Printed only while {spec['conditional_on']} holds." if spec["conditional_on"] else ""
    return (
        f"Field index: {spec['pdf_field']} {words}. Spec §8's row for {_section(widgets[0])}: "
        f"{_basis(spec)}{gate} Read by test_form_101_schema.py and tier 1."
    )


def addendum_rows(index):
    """One confirmed addendum row a binding, keyed by (box, the whole binding key)."""
    return [
        {
            "schema": FORM_TYPE,
            "pdf_field": spec["pdf_field"],
            "producer": _producer(spec),
            "original_verdicts": [],
            "final_verdicts": ["correct"],
            "status": "confirmed",
            "correct_target": spec["pdf_field"],
            "evidence": _evidence(spec, widgets),
        }
        for spec, widgets in _placed(index)
    ]


def limits(index):
    """
    Each of the filer's text keys → as many of the widest of its measuring letters
    (`measuring_letters`) as fit its box's inner width at 6 pt: exact for a ZIP code and a
    state, ordinary words for the other texts (Ruling T4-caps, method A).

    venue_reason wraps at spaces into four one-line boxes, so its cap is two lines' worth of
    line 1's inner width. `_venue_reason_lines` starts a new line only when the next word doesn't
    fit after a space, so any line, a space and the first word of the next together are wider
    than a line. The cap counts each break's space as a character, so a reason that needs a
    fifth line is longer than two lines' worth of its letters, however the words break. That
    holds while no single word is wider than a line, which check() refuses at Generate, naming
    the box.
    """
    from apps.forms.services.text_fit import MIN_SIZE, _width, font_for, reverse_cmap_for
    from apps.forms.services.widgets import template_widgets

    widgets = template_widgets(TEMPLATE)
    caps, labels = {}, {}
    for key, label, words in LIMITED:
        row = _by_label(index, label)
        (box,) = [w for w in widgets if (w.page, w.tag) == (row["page"], row["tag"])]
        font = font_for(TEMPLATE, box.font)
        cmap = reverse_cmap_for(TEMPLATE, box.font)
        widest = max(_width(font, cmap, c, MIN_SIZE) for c in measuring_letters(key))
        room = box.width - 4 * box.margin
        lines = VENUE_LINES // 2 if key == "venue_reason" else 1
        caps[key] = math.floor(lines * room / widest)
        labels[key] = words
    return {"limits": caps, "labels": labels}


def owned(row):
    return row["schema"] == FORM_TYPE


_SCALAR_ARRAY = re.compile(
    r'^( *(?:"[^"\n]*": )?)\[\n((?: *(?:"(?:[^"\\\n]|\\.)*"|-?\d+(?:\.\d+)?),?\n)+) *\](,?)$', re.M
)


def _on_one_line(match):
    items = [item.strip().rstrip(",") for item in match[2].splitlines()]
    line = f"{match[1]}[{', '.join(items)}]{match[3]}"
    return line if len(line) <= 80 else match[0]


def dumps(data):
    """json.dumps as prettier writes it: a short list of scalars on one line."""
    return _SCALAR_ARRAY.sub(_on_one_line, json.dumps(data, indent=2, ensure_ascii=False)) + "\n"


def merged(existing, ours):
    """existing with our rows put at the first Form 101 row's place, else at the start."""
    at = next((i for i, r in enumerate(existing) if owned(r)), 0)
    before = [r for r in existing[:at] if not owned(r)]
    after = [r for r in existing[at:] if not owned(r)]
    return [*before, *ours, *after]


def merged_text(existing_text, rows):
    """The addendum file's text once our rows are merged into it."""
    return dumps(merged(json.loads(existing_text), rows))


def _setup_django():
    import django
    from django.conf import settings

    if not settings.configured:
        sys.path.insert(0, str(ROOT / "backend"))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
        django.setup()


def main():
    _setup_django()
    index = json.loads((INDEX_DIR / f"{Path(TEMPLATE).stem}.index.json").read_text())
    sha256 = hashlib.sha256((PDFS / TEMPLATE).read_bytes()).hexdigest()
    built = schema(index, sha256)
    rows = addendum_rows(index)
    (SCHEMAS_DIR / f"{FORM_TYPE}.json").write_text(dumps(built))
    (SCHEMAS_DIR / f"{FORM_TYPE}.limits.json").write_text(dumps(limits(index)))
    ADDENDUM.write_text(merged_text(ADDENDUM.read_text(), rows))
    print(f"bindings for {FORM_TYPE}: {len(built['fields'])}; addendum rows: {len(rows)}")


if __name__ == "__main__":
    main()
