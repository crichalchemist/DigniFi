"""Write Schedule A/B's schema and its rows of the placement addendum, from the line catalog.

Each row's boxes come from the field index, found by the index's `line` (1.3 and 1.3. are one
row) and by the words printed beside each box, never by the box's name, since the template's
names mislead: 3.2's Make box is "If you own or have more than one describe here". Where the
index gives only the line (18, 19, 42…), a column of boxes is read down the page. Every
export state is the index's. A line the index gets wrong is fixed in this file, never there.

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
    "percent": "% of ownership",
    "beneficiary": "Beneficiary",
}
# What a list line's text box asks, in the form's words.
TEXT_WORDS = {
    "17": "Institution name",
    "18": "Institution or issuer name",
    "19": "Name of entity",
    "20": "Issuer name",
    "21": "Institution name",
    "22": "Institution name or individual",
    "23": "Issuer name and description",
    "24": "Institution name and description",
    "28": "Give specific information",
    "29": "Give specific information",
    "31": "Company name",
    "42": "Name of entity",
    "44": "Give specific information",
    "53": "Give specific information",
}
# A labelled kind → (the words beside its boxes, its sheet row's letter, its sheet's title words).
# The letter keeps a sheet's row from reading as the form's own: 17c.3 is no savings account 17.3.
LABELLED = {
    "17": {
        "checking": ("Checking account", "c", "checking accounts"),
        "savings": ("Savings account", "s", "savings accounts"),
        "cd": ("Certificates of deposit", "d", "certificates of deposit"),
        "other": ("Other financial account", "o", "other financial accounts"),
    },
    "21": {
        "401k": ("401(k) or similar plan", "k", "401(k) or similar plans"),
        "pension": ("Pension plan", "p", "pension plans"),
        "ira": ("IRA", "i", "IRAs"),
        "retirement": ("Retirement account", "r", "retirement accounts"),
        "keogh": ("Keogh", "h", "Keogh accounts"),
        "additional": ("Additional account", "a", "additional accounts"),
    },
    "22": {
        "electric": ("Electric", "a", "electric"),
        "gas": ("Gas", "b", "gas"),
        "heating_oil": ("Heating oil", "c", "heating oil"),
        "security_deposit": (
            "Security deposit on rental unit",
            "d",
            "security deposits on rental units",
        ),
        "prepaid_rent": ("Prepaid rent", "e", "prepaid rent"),
        "telephone": ("Telephone", "f", "telephone"),
        "water": ("Water", "g", "water"),
        "rented_furniture": ("Rented furniture", "h", "rented furniture"),
        "other": ("Other", "i", "other deposits and prepayments"),
    },
}
# A kind on a line with one text box → the words beside its amount.
SHARED_AMOUNTS = {
    "28": {"federal": "Federal", "state": "State", "local": "Local"},
    "29": {
        "alimony": "Alimony",
        "maintenance": "Maintenance",
        "support": "Support",
        "divorce_settlement": "Divorce settlement",
        "property_settlement": "Property settlement",
    },
}
LIST_SHAPES = {"named", "named_share", "insurance"}
# The template gives line 24's rows 1 and 3 one text name, and row 2's text and amount another.
TAGGED_LINES = {"24"}
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


def export_state(on_state):
    """apps.forms.field_index.export_state, which imports Django settings."""
    return "/" + re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), on_state)


def split_line(row):
    """(line key, row number or None): the index writes 1.3 and 1.3. for one row."""
    key, _, number = row["line"].rstrip(".").partition(".")
    return key, int(number) if number else None


def field(
    pdf_field, kind, page, label, *, rule=None, binding=None, choices=None, group=None, tag=None
):
    """A schema binding, keys in the order every schema writes them."""
    out = {"pdf_field": pdf_field}
    if tag is not None:
        out["tag"] = tag
    out |= {"type": kind, "source": "derived" if rule else "asked"}
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


def slot(widget, label, attr, line, group, number, choices=None, kind=None):
    """One box of a row: (its binding, the index rows its addendum row cites)."""
    box = box_type(widget) if choices else "text"
    list_name = f"line_{line.key}_{kind}" if kind else f"line_{line.key}"
    spec = field(
        widget["full_name"],
        box,
        widget["page"],
        label,
        binding=f"assets.{list_name}[].{attr}",
        choices=choices,
        group=(group, dict(line.kinds)[kind] if kind else line.capacity, number),
        tag=widget["tag"] if line.key in TAGGED_LINES else None,
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


def down_the_page(widgets):
    return sorted(widgets, key=lambda w: w["rect"][1])


def box_attr(widget):
    """Which of a list row's answers a box prints. 42's % boxes are "amount"s to the index."""
    if widget["label"].startswith("% of ownership"):
        return "percent"
    if widget["label"].startswith("Beneficiary"):
        return "beneficiary"
    return "value" if widget["kind"] == "amount" else "description"


def list_fields(line, widgets, group):
    """The rows of a line the index doesn't number: each column of boxes, read down the page."""
    columns = {}
    for widget in down_the_page(w for w in widgets if w["kind"] != "checkbox"):
        columns.setdefault(box_attr(widget), []).append(widget)
    words = {**ATTR_WORDS, "description": TEXT_WORDS[line.key]}
    entries = []
    for attr, column in columns.items():
        if len(column) != line.capacity:
            raise ValueError(f"line {line.key}: {len(column)} {attr} boxes, not {line.capacity}")
        for number, widget in enumerate(column, start=1):
            label = f"Line {line.key}.{number}: {words[attr]}"
            entries.append(slot(widget, label, attr, line, group, number))
    return entries


def labelled_fields(line, kind, widgets, group):
    """One kind's rows on a line that prints each kind on its own rows, by the words beside them."""
    words = LABELLED[line.key][kind][0]
    columns = {}
    for widget in down_the_page(w for w in widgets if w["label"].rstrip(": ") == words):
        columns.setdefault(box_attr(widget), []).append(widget)
    capacity = dict(line.kinds)[kind]
    box_words = {**ATTR_WORDS, "description": TEXT_WORDS[line.key]}
    entries = []
    for attr, column in columns.items():
        if len(column) != capacity:
            raise ValueError(f"line {line.key}, {kind}: {len(column)} {attr} boxes, not {capacity}")
        for number, widget in enumerate(column, start=1):
            label = f"Line {line.key}, {words} {number}: {box_words[attr]}"
            entries.append(slot(widget, label, attr, line, group, number, kind=kind))
    return entries


def shared_text_field(line, widgets, rule):
    """The one text box of a line whose rows share it."""
    (text,) = [w for w in widgets if w["kind"] == "text"]
    label = f"Line {line.key}: {TEXT_WORDS[line.key]}"
    return field(text["full_name"], "text", text["page"], label, rule=rule), [text]


def shared_amount_fields(line, widgets):
    """One amount for each kind of a line whose rows share a text box; the kind's rule adds it up."""
    entries = []
    for kind, words in SHARED_AMOUNTS[line.key].items():
        (box,) = [w for w in widgets if w["kind"] == "amount" and w["label"].rstrip(": ") == words]
        label = f"Line {line.key}: {words}"
        rule = f"ab_line_{line.key}_{kind}"
        entries.append((field(box["full_name"], "text", box["page"], label, rule=rule), [box]))
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


def sheet_columns(line, kind=None):
    """A line's sheet: each slot's value in a column; a place's and a vehicle's boxes in words."""
    list_name = f"assets.line_{line.key}_{kind}[]" if kind else f"assets.line_{line.key}[]"

    def column(label, attr, width, covers=None):
        out = {"label": label, "binding": f"{list_name}.{attr}", "width": width}
        if covers is not None:
            out["covers"] = [f"{list_name}.{name}" for name in covers]
        return out

    money = [column("Entire", "entire", MONEY), column("Portion", "value", MONEY)]
    interest = ["who", "community", "other_info"]
    # A word never wraps, and one wider than its column less 4 pt refuses the whole form, so each
    # column is sized on words measured at 10 pt, not on every word a filer could type. Make:
    # "Harley-Davidson", 73.9. Year, and Year and miles: "Unknown", 41.68, 0.32 pt to spare. Line 1's
    # Who: a PIN, 91.2. A vehicle's Model and Who share 184 pt, split for a watercraft's "WaveRunner"
    # (58.35, 0.15 pt to spare) and a MINI-format VIN (117.24, 0.26 pt to spare), the widest format
    # measured, so a wider word on either is refused; no width takes every legal VIN (17 W's is
    # 160.5). Line 3 has no room for a VIN beside a Year and a Miles column, so one column prints
    # both answers, each on its own line.
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
            column("Model", "model", 62.5),
            column("Year and miles", "year_and_miles", 46, ["year", "mileage"]),
            column("Who has an interest", "interest", 121.5, interest),
            *money,
        ]
    if line.shape == "vehicle_no_mileage":
        return [
            column("Make", "make", 78),
            column("Model", "model", 62.5),
            column("Year", "year", 46),
            column("Who has an interest", "interest", 121.5, interest),
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
    if line.shape == "named_share":
        return [
            column(TEXT_WORDS[line.key], "description", 306),
            column("% of ownership", "percent", 76),
            portion,
        ]
    if line.shape == "insurance":
        return [
            column(TEXT_WORDS[line.key], "description", 191),
            column("Beneficiary", "beneficiary", 191),
            column("Surrender or refund value", "value", MONEY),
        ]
    if line.shape == "shared_box":
        # The value is the slot. The text box prints the first rows, so a row past them keeps its
        # own words here, in a column no slot binds.
        return [column(TEXT_WORDS[line.key], "description", 382, []), portion]
    if line.shape in LIST_SHAPES or line.shape == "labelled":
        return [column(TEXT_WORDS[line.key], "description", 382), portion]
    return [column("Describe", "description", 382), portion]


def sheet_group(number, title, columns):
    return {
        "number": number,
        "sheet": {
            "title": f"Official Form 106A/B, Schedule A/B: Property, line {title}",
            "line_width": LINE_WIDTH,
            "columns": columns,
        },
    }


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
        own = [w for w in rows if w["kind"] == "checkbox" and w["full_name"] != "check 43_1"]
        placed.append(question_field(line, own))
        if line.shape == "gate":
            continue
        if line.shape == "labelled":
            for kind, (_, letter, words) in LABELLED[line.key].items():
                group = f"ab_{line.key}_{kind}"
                placed += labelled_fields(line, kind, [w for _, w in widgets], group)
                groups[group] = sheet_group(
                    f"{line.key}{letter}.{{n}}",
                    f"{line.key}, {words}",
                    sheet_columns(line, kind),
                )
            continue
        if line.key in SHARED_AMOUNTS:
            placed.append(shared_text_field(line, rows, f"ab_line_{line.key}_text"))
            placed += shared_amount_fields(line, rows)
            continue
        group = f"ab_{line.key}"
        if line.shape in ("place", "vehicle", "vehicle_no_mileage"):
            for number in range(1, line.capacity + 1):
                boxes = [w for n, w in widgets if n == number]
                placed += row_fields(line, number, boxes, group)
        elif line.shape == "shared_box":
            placed.append(shared_text_field(line, rows, f"ab_line_{line.key}_text"))
            amounts = down_the_page(w for w in rows if w["kind"] == "amount")
            for number, widget in enumerate(amounts, start=1):
                label = f"Line {line.key}: {ATTR_WORDS['value']}, row {number}"
                placed.append(slot(widget, label, "value", line, group, number))
        elif line.shape in LIST_SHAPES:
            placed += list_fields(line, rows, group)
        else:
            placed += item_fields(line, rows, group)
        groups[group] = sheet_group(f"{line.key}.{{n}}", line.key, sheet_columns(line))
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
    ]
    return fields, groups, placed


# What backend/apps/forms/tests/test_printed_page.py reads off a drawn page, branch by branch.
# This tool draws nothing, so a row cites the test that does, and only for what that test reads.
EVERY_NO = "test_every_line_says_no_for_a_filer_with_nothing_and_totals_print_zero"
EVERY_ROW_BOX = "test_every_row_box_prints_its_own_answer_on_the_page"
EVERY_LIST_BOX = "test_every_list_box_prints_its_own_answer_on_the_page"
TWO_REFUNDS = "test_two_federal_refunds_add_up_and_their_texts_join"
SHARED_AMOUNT = "test_a_shared_amount_adds_what_the_filer_knows"
LINE_53 = "test_line_53_s_fourth_row_goes_on_a_sheet_with_its_text"
NOTHING_LISTED_READ = (
    f"test_printed_page.py's {EVERY_NO} reads this box off the drawn page with nothing listed, "
    f"as 0.00, or blank on lines 2, 45 and 52."
)
RULE_READS = {
    "ab_line_28_text": f"{TWO_REFUNDS} reads the joined text",
    "ab_line_53_text": f"{LINE_53} reads the joined text",
    "ab_line_28_federal": f"{TWO_REFUNDS} reads the sum",
    "ab_line_28_state": f"{TWO_REFUNDS} reads this box blank",
    "ab_line_29_support": f"{SHARED_AMOUNT} reads the sum, a $0 and an unknown value",
    "ab_line_29_alimony": f"{SHARED_AMOUNT} reads this box blank",
}
YES_READS = {
    "17": "test_a_savings_account_prints_on_17_3_not_17_1",
    "19": "test_line_19_prints_entity_share_and_value",
    "28": TWO_REFUNDS,
    "31": "test_line_31_prints_company_beneficiary_and_a_zero_value",
    "53": LINE_53,
}
ROW_TEST_SHAPES = {"place", "vehicle", "vehicle_no_mileage", "item", "item_question", "cash"}
SHAPE_BY_KEY = {line.key: line.shape for line in LINES}
GATE_BY_KEY = {line.key: line.gate for line in LINES}
GATE_ANSWERS = "test_a_yes_to_a_gate_answers_every_line_under_it_and_prints_its_total"
NO_READS_UNDER_A_GATE = {"39", "48"}


def page_check(rule):
    """What a line's shared box rests on: the test that reads it, or the index and tier 2."""
    if rule in RULE_READS:
        return f"test_printed_page.py's {RULE_READS[rule]} off the drawn page."
    return (
        "No test reads this box with an answer: its evidence is the index's words above, and "
        "tier 2 checks this row against the binding."
    )


def answer_check(key):
    """What a line's Yes/No box rests on: a test reads each answer only where this says it does."""
    gate = GATE_BY_KEY[key]
    if gate is None:
        no = f"test_printed_page.py's {EVERY_NO} reads its No off the drawn page."
    else:
        no = f"test_printed_page.py's {EVERY_NO} reads this box blank under line {gate}'s No. "
        if key in NO_READS_UNDER_A_GATE:
            no += f"{GATE_ANSWERS} reads its No."
        else:
            no += "No test reads its No: the index's export state above is that box's evidence."
    if SHAPE_BY_KEY[key] in ROW_TEST_SHAPES or SHAPE_BY_KEY[key] == "gate":
        return f"{no} {EVERY_ROW_BOX} reads its Yes."
    if key in YES_READS:
        return f"{no} {YES_READS[key]} reads its Yes."
    return f"{no} No test reads its Yes: the index's export state above is that box's evidence."


def slot_check(key):
    """Which test reads a row's box off the drawn page, by the shape of the row's line."""
    shape = SHAPE_BY_KEY[key]
    if shape == "shared_box":
        return f"test_printed_page.py's {LINE_53} reads this box off the drawn page."
    test = EVERY_ROW_BOX if shape in ROW_TEST_SHAPES else EVERY_LIST_BOX
    return f"test_printed_page.py's {test} reads this box off the drawn page."


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
            f"zero, sheets included. {SPEC} §8.2. {NOTHING_LISTED_READ}"
        )
    if spec["rule"] and spec["rule"].endswith("_text"):
        return (
            f"{cite} {spec['rule']} prints the rows' texts in order, joined with a semicolon: the "
            f"line's one text box. {SPEC} §5. {page_check(spec['rule'])}"
        )
    if spec["rule"] and spec["rule"].startswith("ab_line_"):
        return (
            f"{cite} {spec['rule']} adds the known values of the rows of its kind, blank when none "
            f"is known: the form's one amount for that kind. {SPEC} §5. "
            f"{page_check(spec['rule'])}"
        )
    if spec["rule"]:
        return (
            f"{cite} {spec['rule']} says yes with a row on the line, no with none and the line "
            f"shown, blank when a gate's No hid it, with the index's export state for each. "
            f"[Q24], {SPEC} §8.1. {answer_check(spec['rule'].removeprefix('ab_has_'))}"
        )
    line = spec["binding"].split("[")[0].removeprefix("assets.line_").replace("_", ", ", 1)
    attr = spec["binding"].rpartition(".")[2]
    return (
        f"{cite} Row {spec['row']} of line {line} prints {attr} here: the words beside the box, "
        f"not its name, decide. {SPEC} §5, §8.1. {slot_check(line.split(',')[0])}"
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
    ab_rows = [addendum_row(entry) for entry in placed]
    first = next(i for i, r in enumerate(rows) if r["schema"] == "schedule_a_b")
    rest = [r for r in rows[first:] if r["schema"] != "schedule_a_b"]
    ADDENDUM.write_text(dumps([*rows[:first], *ab_rows, *rest]))
    print(f"{len(fields)} bindings, {len(groups)} groups, {len(ab_rows)} addendum rows")


if __name__ == "__main__":
    main()
