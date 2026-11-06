"""Write Schedule A/B's schema and its rows of the placement addendum, from the line catalog.

Each row's boxes come from the field index, found by the index's `line` (1.3 and 1.3. are one
row) and by the words printed beside each box, never by the box's name, since the template's
names mislead: 3.2's Make box is "If you own or have more than one describe here". Every
export state is the index's. A line the index gets wrong is fixed in this file, never there.

A binding this tool doesn't write yet is listed in LATER, and keeps its addendum row.

usage (from the repo root):
    python data/forms/field_index/tools/build_schedule_a_b.py
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from apps.intake.asset_lines import LINES  # noqa: E402 (a pure module: no Django)

TEMPLATE = "form_b106ab.pdf"
SCHEMA = ROOT / "data" / "forms" / "schemas" / "schedule_a_b.json"
INDEX = ROOT / "data" / "forms" / "field_index" / "form_b106ab.index.json"
ADDENDUM = ROOT / "data" / "forms" / "field_index" / "audit" / "step2_verification.json"
SPEC = "3b spec"

LINE_WIDTH = 48
# The widest amount DecimalField(12, 2) holds, "9999999999.99", is 69.5 pt at 10 pt, and a word
# never wraps, so a money column takes 73.5 pt with its padding. The rest goes to the words.
MONEY = 74
WHO_WORDS = {"Debtor 1 only": "only_you", "At least one of the debtors and another": "with_someone"}
KIND_WORDS = {
    "Single-family home": "single_family",
    "Duplex or multi-unit building": "duplex",
    "Condominium or cooperative": "condo",
    "Manufactured or mobile home": "manufactured",
    "Land": "land",
    "Investment property": "investment",
    "Timeshare": "timeshare",
    "Other": "other",
}
# The words beside a row's text box → the attribute it prints. Longest first.
PLACE_TEXT = {
    "City": "city",
    "State": "state",
    "ZIP Code": "zip",
    "County": "county",
    "Other information": "other_info",
    "Other": "other_kind",
    "Describe the nature": "nature",
}
VEHICLE_TEXT = {
    "Make": "make",
    "Model": "model",
    "Year": "year",
    "Approximate mileage": "mileage",
    "Other information": "other_info",
}
# The words a refusal names a box by, the way the form's own column reads.
ATTR_WORDS = {
    "street": "Street address",
    "street_2": "Second address line",
    "city": "City",
    "state": "State",
    "zip": "ZIP Code",
    "county": "County",
    "other_kind": "Other property kind",
    "nature": "Nature of your ownership interest",
    "other_info": "Other information",
    "make": "Make",
    "model": "Model",
    "year": "Year",
    "mileage": "Approximate mileage",
    "who": "Who has an interest",
    "community": "Community property",
    "entire": "Current value of the entire property",
    "value": "Current value of the portion you own",
    "description": "Describe",
    "personal_description": "Describe",
    "has_personal_info": "Do your lists include personally identifiable information",
}
# Lines and shapes this tool writes rows for. The rest of the catalog's shapes come later.
ROW_SHAPES = {"place", "vehicle", "vehicle_no_mileage", "item", "item_question", "cash"}
QUESTION_SHAPES = ROW_SHAPES | {"gate"}
# Arithmetic: the box's line → (its rule, its label, what the rule adds up).
TOTALS = {
    "2": ("ab_line_2", "Part 1 total: real estate", "Part 1, blank under line 1's No"),
    "5": ("total_vehicles", "Part 2 total: vehicles", "Part 2"),
    "15": ("total_household_items", "Part 3 total: personal and household items", "Part 3"),
    "36": ("total_financial_assets", "Part 4 total: financial assets", "Part 4"),
    "45": (
        "ab_line_45",
        "Part 5 total: business-related property",
        "Part 5, blank under line 37's No",
    ),
    "52": (
        "ab_line_52",
        "Part 6 total: farm and fishing property",
        "Part 6, blank under line 46's No",
    ),
    "54": ("total_other_assets", "Part 7 total: other property", "Part 7"),
    "55": (
        "total_real_property",
        "Part 1: Total real estate, line 2",
        "Part 1, printed under line 1's No too",
    ),
    "56": ("total_vehicles", "Part 2: Total vehicles, line 5", "Part 2"),
    "57": (
        "total_household_items",
        "Part 3: Total personal and household items, line 15",
        "Part 3",
    ),
    "58": ("total_financial_assets", "Part 4: Total financial assets, line 36", "Part 4"),
    "59": (
        "total_business_property",
        "Part 5: Total business-related property, line 45",
        "Part 5, printed under line 37's No too",
    ),
    "60": (
        "total_farm_property",
        "Part 6: Total farm- and fishing-related property, line 52",
        "Part 6, printed under line 46's No too",
    ),
    "61": ("total_other_assets", "Part 7: Total other property not listed, line 54", "Part 7"),
    "62": (
        "total_personal_property",
        "Total personal property. Add lines 56 through 61.",
        "Parts 2 to 7",
    ),
    "63": (
        "total_assets",
        "Total of all property on Schedule A/B. Add line 55 + line 62.",
        "Parts 1 to 7",
    ),
}
# Bindings a later task re-keys, written here as they stand, with their addendum rows kept.
LATER = [
    (
        "Check 17",
        "checkbox",
        5,
        "Deposits of money",
        "has_bank_accounts",
        {"yes": "/yes", "no": "/no"},
    ),
    (
        "check 21",
        "checkbox",
        6,
        "Retirement or pension accounts",
        "has_retirement_accounts",
        {"yes": "/yes", "no": "/no"},
    ),
    (
        "check 53",
        "checkbox",
        10,
        "Do you have other property of any kind you did not already list?",
        "has_other_assets",
        {"yes": "/On", "no": "/no"},
    ),
    (
        "53 Examples Season tickets country club membership",
        "text",
        10,
        "Line 53 Other property: Give specific information.",
        "other_asset_descriptions",
        None,
    ),
]


def export_state(on_state):
    """apps.forms.field_index.export_state, which imports Django settings."""
    return "/" + re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), on_state)


def split_line(row):
    """(line key, row number or None): the index writes 1.3 and 1.3. for one row."""
    key, _, number = row["line"].rstrip(".").partition(".")
    return key, int(number) if number else None


def field(pdf_field, kind, page, label, *, rule=None, binding=None, choices=None, group=None):
    """A schema binding, keys in the order every schema writes them."""
    out = {"pdf_field": pdf_field, "type": kind, "source": "derived" if rule else "asked"}
    if choices is not None:
        out["choices"] = choices
    out |= {
        "page": page,
        "label": label,
        "required": False,
        "conditional_on": None,
        "value": None,
        "rule": rule,
        "ingest_key": None,
        "binding": binding,
        "repeat": group[0] if group else None,
        "repeat_capacity": group[1] if group else None,
        "row": group[2] if group else None,
        "legal_review": False,
    }
    return out


def box_type(row):
    return "radio" if row["type"] == "RadioButton" else "checkbox"


def row_boxes(line, widgets):
    """{attr: index row} of one row's boxes, plus its ticks as {answer: index row} for who."""
    attrs, who, kinds = {}, {}, {}
    text = PLACE_TEXT if line.shape == "place" else VEHICLE_TEXT
    streets = sorted(
        (w for w in widgets if w["label"].startswith("Street address")), key=lambda w: w["rect"][1]
    )
    for attr, widget in zip(("street", "street_2"), streets, strict=False):
        attrs[attr] = widget
    for widget in widgets:
        words = widget["option_text"]
        if widget["kind"] == "checkbox":
            if words in WHO_WORDS:
                who[WHO_WORDS[words]] = widget
            elif words in KIND_WORDS:
                kinds[KIND_WORDS[words]] = widget
            elif words.startswith("Check if this is community property"):
                attrs["community"] = widget
            elif not words.startswith("Debtor"):
                raise ValueError(f"no meaning for box {widget['full_name']!r}: {words!r}")
        elif widget["kind"] == "amount":
            attrs["entire" if "entire" in widget["label"] else "value"] = widget
        elif widget not in streets:
            matched = [a for w, a in text.items() if widget["label"].startswith(w)]
            if not matched:
                raise ValueError(f"no meaning for box {widget['full_name']!r}: {widget['label']!r}")
            attrs[matched[0]] = widget
    return attrs, who, kinds


def slot(widget, label, attr, line, group, number, choices=None):
    """One box of a row: (its binding, the index rows its addendum row cites)."""
    kind = box_type(widget) if choices else "text"
    spec = field(
        widget["full_name"],
        kind,
        widget["page"],
        label,
        binding=f"assets.line_{line.key}[].{attr}",
        choices=choices,
        group=(group, line.capacity, number),
    )
    return spec, [widget]


def row_fields(line, number, widgets, group):
    """The bindings of one row of a place or a vehicle."""
    attrs, who, kinds = row_boxes(line, widgets)
    at = f"Line {line.key}.{number}"
    entries = []
    for attr, widget in attrs.items():
        choices = {"true": export_state(widget["on_state"])} if attr == "community" else None
        label = f"{at}: {ATTR_WORDS[attr]}"
        entries.append(slot(widget, label, attr, line, group, number, choices))
    choices = {answer: export_state(w["on_state"]) for answer, w in sorted(who.items())}
    label = f"{at}: {ATTR_WORDS['who']}"
    entries.append(slot(who["only_you"], label, "who", line, group, number, choices))
    for kind, widget in kinds.items():
        choices = {"true": export_state(widget["on_state"])}
        label = f"{at}: {widget['option_text']}"
        entries.append(slot(widget, label, f"kind_{kind}", line, group, number, choices))
    return entries


def item_fields(line, widgets, group):
    """The bindings of a line with one row: its text box, its amount and, on 43, its question."""
    entries = []
    for widget in widgets:
        if widget["kind"] == "amount":
            attr = "value"
        elif widget["kind"] != "text":
            continue
        else:
            attr = "personal_description" if line.shape == "item_question" else "description"
        entries.append(slot(widget, f"Line {line.key}: {ATTR_WORDS[attr]}", attr, line, group, 1))
    if line.shape == "item_question":
        question = [w for w in widgets if w["full_name"] == "check 43_1"]
        choices = {
            "no" if w["option_text"].startswith("No") else "yes": export_state(w["on_state"])
            for w in question
        }
        label = f"Line 43: {ATTR_WORDS['has_personal_info']}"
        entries.append(slot(question[0], label, "has_personal_info", line, group, 1, choices))
    return entries


def question_field(line, widgets):
    """A line's own Yes/No box: two widgets of one name, read by the words beside each."""
    no = next(w for w in widgets if w["option_text"].startswith("No"))
    yes = next(w for w in widgets if w["option_text"].startswith("Yes"))
    choices = {"yes": export_state(yes["on_state"]), "no": export_state(no["on_state"])}
    label = f"Line {line.key}: Yes or No"
    spec = field(
        no["full_name"], box_type(no), no["page"], label, rule=f"ab_has_{line.key}", choices=choices
    )
    return spec, [no, yes]


def sheet_columns(line):
    """A line's sheet: each slot's value in a column; a place's and a vehicle's boxes in words."""
    list_name = f"assets.line_{line.key}[]"

    def column(label, attr, width, covers=None):
        out = {"label": label, "binding": f"{list_name}.{attr}", "width": width}
        if covers is not None:
            out["covers"] = [f"{list_name}.{name}" for name in covers]
        return out

    money = [column("Entire", "entire", MONEY), column("Portion", "value", MONEY)]
    interest = ["who", "community", "other_info"]
    # A word never wraps, and one wider than its column less 4 pt refuses the whole form, so each
    # column holds the widest real word it takes, at 10 pt. Make: "Harley-Davidson", 73.9. Model:
    # "Thunderbird", 53.9. Miles: "Unknown", 41.7. Line 1's Who: a PIN, 91.2. Line 4's Who: a VIN,
    # 103.9, which line 3's five other columns leave no room for (reported for a ruling).
    if line.shape == "place":
        kinds = [f"kind_{kind}" for kind in KIND_WORDS.values()]
        return [
            column(
                "Where it is",
                "where",
                128,
                ["street", "street_2", "city", "state", "zip", "county"],
            ),
            column("What it is", "what", 80, [*kinds, "other_kind"]),
            column(
                "Who has an interest", "interest", 100, ["who", "nature", "community", "other_info"]
            ),
            *money,
        ]
    if line.shape == "vehicle":
        return [
            column("Make", "make", 78),
            column("Model", "model", 64),
            column("Year", "year", 30),
            column("Miles", "mileage", 46),
            column("Who has an interest", "interest", 90, interest),
            *money,
        ]
    if line.shape == "vehicle_no_mileage":
        return [
            column("Make", "make", 78),
            column("Model", "model", 76),
            column("Year", "year", 46),
            column("Who has an interest", "interest", 108, interest),
            *money,
        ]
    portion = column("Portion", "value", MONEY)
    if line.shape == "cash":
        return [portion]
    if line.shape == "item_question":
        return [
            column("Personal information", "has_personal_info", 100),
            column("Describe", "personal_description", 282),
            portion,
        ]
    return [column("Describe", "description", 382), portion]


def build(index):
    """(the schema's fields, its groups, what each addendum row cites: (binding, index rows, …))."""
    by_key = {}
    for row in index:
        key, number = split_line(row)
        by_key.setdefault(key, []).append((number, row))
    groups = {}
    placed = []
    for line in LINES:
        widgets = by_key.get(line.key, [])
        rows = [w for number, w in widgets if number is None]
        if line.shape in QUESTION_SHAPES:
            own = [w for w in rows if w["kind"] == "checkbox" and w["full_name"] != "check 43_1"]
            placed.append(question_field(line, own))
        if line.shape not in ROW_SHAPES:
            continue
        group = f"ab_{line.key}"
        if line.shape in ("place", "vehicle", "vehicle_no_mileage"):
            for number in range(1, line.capacity + 1):
                boxes = [w for n, w in widgets if n == number]
                placed += row_fields(line, number, boxes, group)
        else:
            placed += item_fields(line, rows, group)
        groups[group] = {
            "number": f"{line.key}.{{n}}",
            "sheet": {
                "title": f"Official Form 106A/B, Schedule A/B: Property, line {line.key}",
                "line_width": LINE_WIDTH,
                "columns": sheet_columns(line),
            },
        }
    for key, (rule, label, adds) in TOTALS.items():
        boxes = [w for _, w in by_key[key]]
        spec = field(boxes[0]["full_name"], "text", boxes[0]["page"], label, rule=rule)
        placed.append((spec, boxes, adds))
    fields = [
        field("Debtor 1", "text", 1, "Debtor 1", rule="full_name"),
        field(
            "Bankruptcy District Information",
            "choice",
            1,
            "District Information",
            rule="district_name",
        ),
        *(entry[0] for entry in placed),
        *(
            field(pdf_field, kind, page, label, rule=rule, choices=choices)
            for pdf_field, kind, page, label, rule, choices in LATER
        ),
    ]
    return fields, groups, placed


def evidence(entry):
    """What a row of the addendum cites: the box's index label, and why the binding belongs there."""
    spec, boxes, *adds = entry
    words = "; ".join(
        f"p{w['page']} line {w['line']}, {w['option_text'] or w['label']!r} ({w['basis']})"
        for w in boxes
    )
    cite = f"Field index: {spec['pdf_field']} {words}."
    if adds:
        return (
            f"{cite} {spec['rule']} adds the portions on {adds[0]}, an unknown value counting as "
            f"zero, sheets included. {SPEC} §8.2. Filled page rendered and read at build."
        )
    if spec["rule"]:
        return (
            f"{cite} {spec['rule']} says yes with a row on the line, no with none and the line "
            f"shown, blank when a gate's No hid it, with the index's export state for each. "
            f"[Q24], {SPEC} §8.1. Filled page rendered and read at build."
        )
    line = spec["binding"].split("[")[0].removeprefix("assets.line_")
    attr = spec["binding"].rpartition(".")[2]
    return (
        f"{cite} Row {spec['row']} of line {line} prints {attr} here: the words beside the box, "
        f"not its name, decide. {SPEC} §5, §8.1. Filled page rendered and read at build."
    )


def addendum_row(entry):
    spec = entry[0]
    producer = f"derived:{spec['rule']}" if spec["rule"] else f"asked:{spec['binding']}"
    return {
        "schema": "schedule_a_b",
        "pdf_field": spec["pdf_field"],
        "producer": producer,
        "original_verdicts": [],
        "final_verdicts": ["correct"],
        "status": "confirmed",
        "correct_target": spec["pdf_field"],
        "evidence": evidence(entry),
    }


# A multi-line array of strings or numbers, as json.dumps writes it.
_SCALAR_ARRAY = re.compile(
    r'^( *(?:"[^"\n]*": )?)\[\n((?: *(?:"(?:[^"\\\n]|\\.)*"|-?\d+(?:\.\d+)?),?\n)+) *\](,?)$', re.M
)


def _on_one_line(match):
    items = [item.strip().rstrip(",") for item in match[2].splitlines()]
    line = f"{match[1]}[{', '.join(items)}]{match[3]}"
    return line if len(line) <= 80 else match[0]


def dumps(data):
    """JSON as prettier writes it here: 2 spaces, and an array of scalars on one line if it fits."""
    return _SCALAR_ARRAY.sub(_on_one_line, json.dumps(data, indent=2, ensure_ascii=False)) + "\n"


def main():
    index = json.loads(INDEX.read_text())
    fields, groups, placed = build(index)
    version = hashlib.sha256((ROOT / "data" / "forms" / "pdfs" / TEMPLATE).read_bytes()).hexdigest()
    SCHEMA.write_text(
        dumps(
            {
                "form_type": "schedule_a_b",
                "template_filename": TEMPLATE,
                "template_version": version,
                "groups": groups,
                "fields": fields,
            }
        )
    )

    rows = json.loads(ADDENDUM.read_text())
    later = {(f"derived:{rule}", pdf_field) for pdf_field, _, _, _, rule, _ in LATER}
    ab_rows = [addendum_row(entry) for entry in placed]
    ab_rows += [
        r
        for r in rows
        if r["schema"] == "schedule_a_b" and (r["producer"], r["pdf_field"]) in later
    ]
    first = next(i for i, r in enumerate(rows) if r["schema"] == "schedule_a_b")
    rest = [r for r in rows[first:] if r["schema"] != "schedule_a_b"]
    ADDENDUM.write_text(dumps([*rows[:first], *ab_rows, *rest]))
    print(f"{len(fields)} bindings, {len(groups)} groups, {len(ab_rows)} addendum rows")


if __name__ == "__main__":
    main()
