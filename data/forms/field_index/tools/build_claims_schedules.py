"""
Writes the claims schedules' schemas whole, and the step 2 addendum rows whose producer it
writes (`asked:claims.…` and `derived:schedule_h_…`) (3c5 R7). Run it from anywhere:

    python data/forms/field_index/tools/build_claims_schedules.py

Never hand-edit a schema it owns or its addendum rows: change this tool and run it again.
`test_the_claims_schedules_are_what_the_generator_writes` fails on any difference. It owns
Schedules D, G and H; Schedule E/F joins in Task 6.

Like `build_schedule_a_b.py`, it reads only the repo (the field index and the templates) and
copies `field()`, `dumps()`, `addendum_row()` and `export_state` rather than importing them: the
tools folder isn't a package.
"""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INDEX_DIR = ROOT / "data" / "forms" / "field_index"
SCHEMAS_DIR = ROOT / "data" / "forms" / "schemas"
PDFS = ROOT / "data" / "forms" / "pdfs"
ADDENDUM = INDEX_DIR / "audit" / "step2_verification.json"

SCHEDULES = ("schedule_d", "schedule_g", "schedule_h")
TEMPLATES = {
    "schedule_d": "form_b106d.pdf",
    "schedule_g": "form_b106g.pdf",
    "schedule_h": "form_b106h.pdf",
}

# R9: a slot's label is the part and the cell in words, with no line.
PART_WORDS = {"d_part_1": "Part 1", "d_part_2": "Part 2", "g": "Contract or lease", "h": "Codebtor"}
CELL_WORDS = {
    "name": "Name",
    "street": "Street",
    "street_joined": "Street",
    "street_2": "Second street line",
    "city": "City",
    "state": "State",
    "zip": "ZIP code",
    "who": "Who owes the debt",
    "who_debtor_1": "Who owes the debt",
    "who_another": "Who owes the debt",
    "community": "Community debt",
    "date": "Date debt was incurred",
    "property": "Describe the property",
    "contingent": "Contingent",
    "unliquidated": "Unliquidated",
    "disputed": "Disputed",
    "lien_agreement": "An agreement you made",
    "lien_statutory": "Statutory lien",
    "lien_judgment": "Judgment lien",
    "lien_other": "Other lien",
    "lien_other_text": "Other lien",
    "last_4": "Last 4 digits of account number",
    "value": "Column B: Value of collateral",
    "unsecured": "Column C: Unsecured portion",
    "purpose": "What the contract or lease is for",
    "on_d": "Schedule D, line",
    "d_lines": "Schedule D, line",
    "on_ef": "Schedule E/F, line",
    "ef_lines": "Schedule E/F, line",
    "on_g": "Schedule G, line",
    "g_lines": "Schedule G, line",
}


def label(group, attr):
    if attr == "name":
        words = "Creditor's name" if group == "d_part_1" else CELL_WORDS[attr]
    elif attr == "amount":
        words = "Column A: Amount of claim"
    elif attr == "line":
        words = "Line in Part 1"
    else:
        words = CELL_WORDS[attr]
    return f"{PART_WORDS[group]}: {words}"


def export_state(on_state):
    """The index's on-state as the PDF's export state: the name escapes decoded."""
    return "/" + re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), on_state)


def field(
    pdf_field, kind, page, label, *, rule=None, binding=None, choices=None, group=None, tag=None
):
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


class Index:
    """One template's field index, by full name. Names are found by name, never by tag: G's
    and H's tags run in a different order from row to row."""

    def __init__(self, template):
        self.rows = json.loads((INDEX_DIR / f"{Path(template).stem}.index.json").read_text())
        self.by_name = {}
        for row in self.rows:
            self.by_name.setdefault(row["full_name"], []).append(row)

    def widgets(self, name, tag=None):
        found = self.by_name.get(name)
        if not found:
            raise KeyError(f"no index row named {name!r}")
        if tag is not None:
            found = [w for w in found if w["tag"] == tag]
            if len(found) != 1:
                raise KeyError(f"{name!r} has no one widget tagged {tag!r}")
        return found


KIND = {"Text": "text", "CheckBox": "checkbox", "RadioButton": "radio"}
YES_NO = {"yes": "/yes", "no": "/no"}
DISTRICT = ("Bankruptcy District Information", "choice", 1, "District Information")


WHO_WORDS = {"debtor_1": "Debtor 1 only", "another": "At least one of the debtors and another"}


def choices_for(widgets, attr):
    """A tick's answer → export state map, from the index's on-state: one box (or a stacked
    pair that shares one state). R3: `who` is one name with four named states, so it maps the
    two answers DigniFi prints to their states, read by the option text."""
    if attr == "who":
        by_words = {w["option_text"]: export_state(w["on_state"]) for w in widgets}
        return {answer: by_words[words] for answer, words in WHO_WORDS.items()}
    (state,) = {export_state(w["on_state"]) for w in widgets}
    return {"true": state}


def slot(index, group, capacity, row, list_name, attr, name, tag=None):
    widgets = index.widgets(name, tag)
    kinds = {w["type"] for w in widgets}
    assert len(kinds) == 1, (name, kinds)
    kind = KIND[kinds.pop()]
    pages = {w["page"] for w in widgets}
    assert len(pages) == 1, (name, tag, pages)
    spec = field(
        name,
        kind,
        pages.pop(),
        label(group, attr),
        binding=f"claims.{list_name}[].{attr}",
        choices=choices_for(widgets, attr) if kind != "text" else None,
        group=(group, capacity, row),
        tag=tag,
    )
    return spec, widgets


def rule_field(index, name, rule, words, choices=None):
    widgets = index.widgets(name)
    kind = KIND[widgets[0]["type"]]
    spec = field(name, kind, widgets[0]["page"], words, rule=rule, choices=choices)
    return spec, widgets


# Schedule G: page 1 rows 1-5, page 2 rows 6-13 (appendix: row maps).
def g_slots():
    return {
        n: [
            ("name", f"Company Name 2.{n}", None),
            ("purpose", f"Contact Info 2.{n}", None),
            ("street_joined", f"Street 2.{n}", None),
            ("city", f"City 2.{n}", None),
            ("state", f"State 2.{n}", None),
            ("zip", f"Zip 2.{n}", None),
        ]
        for n in range(1, 14)
    }


# Schedule H: page 1 rows 1-3, page 2 rows 4-11.
def h_slots():
    return {
        n: [
            ("name", f"Codebtor Name 3.{n}", None),
            ("street_joined", f"Codebtor Street 3.{n}", None),
            ("city", f"Codebtor City 3.{n}", None),
            ("state", f"Codebtor State 3.{n}", None),
            ("zip", f"Codebtor Zip 3.{n}", None),
            ("on_d", f"check schedule line D 3.{n}", None),
            ("d_lines", f"Schedule line D 3.{n}", None),
            ("on_ef", f"check schedule line E/F 3.{n}", None),
            ("ef_lines", f"Schedule line E/F 3.{n}", None),
            ("on_g", f"check schedule line G 3.{n}", None),
            ("g_lines", f"Schedule line G 3.{n}", None),
        ]
        for n in range(1, 12)
    }


# Schedule D Part 1: page 1 rows 1-2, page 2 rows 3-5 (appendix: row maps). Slot 3's stacked
# pairs take untagged bindings: the index lists both widgets of each pair with one on-state and
# the second is never drawn, so the startup check counts one drawn widget.
def d_part_1_slots():
    def common(n, amounts, other_text, last_4):
        sfx = "" if n == 1 else f"_{n}"
        a, b, c = amounts
        return [
            ("amount", a, None),
            ("value", b, None),
            ("unsecured", c, None),
            ("name", f"Creditors Name{sfx}", None),
            ("street", f"Street{sfx}", None),
            ("street_2", f"1{sfx}", None),
            ("city", f"2{sfx}", None),
            ("state", f"3{sfx}", None),
            ("zip", f"4{sfx}", None),
            ("property", f"As of the date you file the claim is Check all that apply{sfx}", None),
            ("contingent", f"Contingent{sfx}", None),
            ("unliquidated", f"Unliquidated{sfx}", None),
            ("disputed", f"Disputed{sfx}", None),
            ("lien_agreement", f"An agreement you made such as mortgage or secured{sfx}", None),
            ("lien_statutory", f"Statutory lien such as tax lien mechanics lien{sfx}", None),
            ("lien_judgment", f"Judgment lien from a lawsuit{sfx}", None),
            ("lien_other", f"Other including a right to offset{sfx}", None),
            ("lien_other_text", other_text, None),
            ("community", f"Check if this claim relates to a{sfx}", None),
            ("date", f"Date debt was incurred{sfx}", None),
            last_4,
        ]

    def last_4(n):
        return (
            "last_4",
            "account number" if n == 1 else f"account number {n}",
            "T32" if n == 1 else None,
        )

    return {
        1: common(1, ("undefined", "undefined_2", "undefined_3"), "undefined_4", last_4(1))
        + [("who", "check 2", None)],
        2: common(2, ("undefined_5", "undefined_6", "undefined_7"), "undefined_8", last_4(2))
        + [("who", "check 3", None)],
        3: common(3, ("undefined_10", "undefined_13", "undefined_15"), "undefined_11", last_4(3))
        + [("who", "check 4", None)],
        4: common(4, ("undefined_14", "undefined_17", "undefined_18"), "undefined_16", last_4(4))
        + [("who_debtor_1", "check 5", "T51"), ("who_another", "check 5", "T56")],
        5: common(5, ("undefined_20", "undefined_22", "undefined_25"), "undefined_21", last_4(5))
        + [
            ("who_debtor_1", "Debtor 1 only_5", None),
            ("who_another", "At least one of the debtors and another_5", None),
        ],
    }


# Part 2 (page 3): six entries.
def d_part_2_slots():
    lines = {
        1: "On which line in Part 1 did you enter the creditor",
        2: "undefined_26",
        3: "undefined_27",
        4: "On which line in Part 1 did you enter the creditor_4",
        5: "On which line in Part 1 did you enter the creditor_5",
        6: "On which line in Part 1 did you enter the creditor_6",
    }
    out = {}
    for n in range(1, 7):
        sfx = "" if n == 1 else f"_{n}"
        last_4 = (
            ("last_4", "account number", "T33")
            if n == 4
            else ("last_4", f"account number {n + 5}", None)
        )
        out[n] = [
            ("name", f"Name{sfx}", None),
            ("street", f"Number_{n + 5}", None),
            ("street_2", f"Street 1{sfx}", None),
            ("city", f"Street 2{sfx}", None),
            ("state", f"Street 3{sfx}", None),
            ("zip", f"Street 4{sfx}", None),
            ("line", lines[n], None),
            last_4,
        ]
    return out


GROUPS = {
    "schedule_d": [
        ("d_part_1", "secured", d_part_1_slots),
        ("d_part_2", "secured_notices", d_part_2_slots),
    ],
    "schedule_g": [("g", "contracts", g_slots)],
    "schedule_h": [("h", "codebtors", h_slots)],
}

DECLARATIONS = {
    "d_part_1": {
        "extra_page": 2,
        "number": "2.{n}",
        "number_boxes": {"3": "undefined_12", "4": "undefined_19@2:T37", "5": "undefined_19@2:T63"},
        "totals": {
            "column": "claims.secured[].amount",
            "page_boxes": {"1": "undefined_9", "2": "undefined_23"},
            "last_page_box": "undefined_24",
        },
    },
    "d_part_2": {"extra_page": 3},
    "g": {
        "extra_page": 2,
        "number": "{n}",
        "number_boxes": {str(n): f"fill 2.{n}" for n in range(6, 14)},
    },
    "h": {
        "extra_page": 2,
        "number": "{n}",
        "number_boxes": {str(n): f"fill 3.{n}" for n in range(4, 12)},
    },
}

TWO_PAGE_NUMBERS = [
    {"page": 1, "this": None, "of": "fill_27.0"},
    {"page": 2, "this": "fill_27.1.0", "of": "fill_27.1.1"},
]
PAGE_NUMBERS = {
    "schedule_d": [
        {"page": 1, "this": None, "of": "fill_27.0"},
        {"page": 2, "this": "fill_27.1.0", "of": "fill_27.1.1"},
        {"page": 3, "this": "fill_28.1.1", "of": "fill_28.1.2"},
    ],
    "schedule_g": TWO_PAGE_NUMBERS,
    "schedule_h": TWO_PAGE_NUMBERS,
}


def header(form_type):
    """The bindings today's schema holds, in its order."""
    name = field("Debtor 1", "text", 1, "Debtor 1", rule="full_name")
    district = field(*DISTRICT, rule="district_name")
    if form_type == "schedule_d":
        # Production D's own bindings, less undefined_24: its group's total prints there (R8).
        return [
            name,
            field(
                "check1",
                "checkbox",
                1,
                "Do any creditors have claims secured by your property?",
                rule="has_secured_debts",
                choices=YES_NO,
            ),
            district,
        ]
    question = {
        "schedule_g": (
            "Do you have any executory contracts or unexpired leases?",
            "has_executory_contracts",
        ),
        "schedule_h": ("Do you have any codebtors?", "has_codebtors"),
    }[form_type]
    return [
        name,
        field("check1", "checkbox", 1, question[0], rule=question[1], choices=YES_NO),
        district,
    ]


# H line 2 (§9.3): check2 and check3 take yes, no or blank from their rules; the six text
# rules take no choices.
H_LINE_2 = [
    ("check2", "schedule_h_community_lived", "Line 2: Lived in a community property state", YES_NO),
    ("check3", "schedule_h_spouse_lived_with", "Line 2: Spouse lived with you", YES_NO),
    ("Community state", "schedule_h_community_state", "Line 2: Community property state", None),
    ("Spouse Name", "schedule_h_spouse_name", "Line 2: Spouse's name", None),
    ("Spouse Street", "schedule_h_spouse_street", "Line 2: Spouse's street", None),
    ("Spouse City", "schedule_h_spouse_city", "Line 2: Spouse's city", None),
    ("Spouse State", "schedule_h_spouse_state", "Line 2: Spouse's state", None),
    ("Spouse Zip", "schedule_h_spouse_zip", "Line 2: Spouse's ZIP code", None),
]

TESTS = {
    "schedule_d": "test_schedules_d_e_f_schema.py",
    "schedule_g": "test_schedules_g_h_schema.py",
    "schedule_h": "test_schedules_g_h_schema.py",
}


# The spec section and rulings that place each cell (T4-2, T4-5). Task 6 adds E/F's cells here;
# a cell not listed raises, so none falls through to a default unnoticed.
CELL_RULINGS = {
    **dict.fromkeys(
        (
            "name",
            "street",
            "street_joined",
            "street_2",
            "city",
            "purpose",
            "amount",
            "property",
            "contingent",
            "unliquidated",
            "disputed",
            "lien_agreement",
            "lien_statutory",
            "lien_judgment",
            "lien_other",
            "lien_other_text",
            "line",
        ),
        "3c spec §9.3, R2",
    ),
    **dict.fromkeys(
        ("on_d", "d_lines", "on_ef", "ef_lines", "on_g", "g_lines"), "3c spec §9.3, R6, B40"
    ),
    **dict.fromkeys(("who", "who_debtor_1", "who_another"), "3c spec §9.3, R3"),
    "value": "3c spec §9.4, R5",
    "unsecured": "3c spec §9.4, R5",
    **dict.fromkeys(("student_loans", "other_type", "other_type_words"), "3c spec §9.3, R10, B14"),
    **dict.fromkeys(("state", "zip"), "3c spec §9.3, R4, B49"),
    "community": "3c spec §9.3, R4, B33",
    **dict.fromkeys(("date", "last_4"), "3c spec §9.3, R4, B32"),
}


def cell_ruling(spec):
    attr = spec["binding"].rsplit(".", 1)[-1]
    if attr not in CELL_RULINGS:
        raise KeyError(f"no ruling listed for cell {attr!r}: add it to CELL_RULINGS")
    return CELL_RULINGS[attr]


def evidence(form_type, spec, widgets):
    """The box's index label and basis, the spec section and ruling that place it, and the
    tests that read it."""
    words = "; ".join(
        f"p{w['page']} {w['tag']} line {w['line']}, {w['option_text'] or w['label']!r} "
        f"({w['basis']})"
        for w in widgets
    )
    cite = f"Field index: {spec['pdf_field']} {words}."
    if spec["rule"]:
        basis = (
            f"{spec['rule']} prints H line 2 as the filer answered it, only where the gap table "
            "asks it (3c spec §9.3, R4)."
        )
    else:
        basis = (
            f"Row {spec['row']} of group {spec['repeat']} prints {spec['binding']} here "
            f"({cell_ruling(spec)})."
        )
    return f"{cite} {basis} Read by {TESTS[form_type]} and tier 1."


def addendum_row(form_type, spec, widgets):
    producer = f"derived:{spec['rule']}" if spec["rule"] else f"asked:{spec['binding']}"
    return {
        "schema": form_type,
        "pdf_field": spec["pdf_field"],
        "producer": producer,
        "original_verdicts": [],
        "final_verdicts": ["correct"],
        "status": "confirmed",
        "correct_target": spec["pdf_field"],
        "evidence": evidence(form_type, spec, widgets),
    }


def owned(row):
    return row["producer"].startswith(("asked:claims.", "derived:schedule_h_"))


def build():
    """(schema by form type, the addendum rows it owns), reading only the repo."""
    schemas, rows = {}, []
    for form_type in SCHEDULES:
        template = TEMPLATES[form_type]
        index = Index(template)
        placed = []
        if form_type == "schedule_h":
            for name, rule, words, choices in H_LINE_2:
                placed.append(rule_field(index, name, rule, words, choices))
        groups = {}
        for group, list_name, table in GROUPS[form_type]:
            slots = table()
            for row, cells in slots.items():
                for attr, name, tag in cells:
                    placed.append(slot(index, group, len(slots), row, list_name, attr, name, tag))
            groups[group] = DECLARATIONS[group]
        version = hashlib.sha256((PDFS / template).read_bytes()).hexdigest()
        schemas[form_type] = {
            "form_type": form_type,
            "template_filename": template,
            "template_version": version,
            "groups": groups,
            "page_numbers": PAGE_NUMBERS[form_type],
            "fields": [*header(form_type), *(spec for spec, _ in placed)],
        }
        rows += [addendum_row(form_type, spec, widgets) for spec, widgets in placed]
    return schemas, rows


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
    """existing with our rows taken out, and ours put back just after each schema's last row."""
    kept = [r for r in existing if not owned(r)]
    out = []
    by_schema = {}
    for r in ours:
        by_schema.setdefault(r["schema"], []).append(r)
    last = {r["schema"]: i for i, r in enumerate(kept)}
    for i, r in enumerate(kept):
        out.append(r)
        for schema, at in last.items():
            if at == i and schema in by_schema:
                out += by_schema.pop(schema)
    for schema_rows in by_schema.values():
        out += schema_rows
    return out


def merged_text(existing_text, rows):
    """The addendum file's text once our rows are merged into it."""
    return dumps(merged(json.loads(existing_text), rows))


def main():
    schemas, rows = build()
    for form_type, schema in schemas.items():
        (SCHEMAS_DIR / f"{form_type}.json").write_text(dumps(schema))
    ADDENDUM.write_text(merged_text(ADDENDUM.read_text(), rows))
    counts = {f: sum(1 for r in rows if r["schema"] == f) for f in schemas}
    print(f"addendum rows by schema: {counts}; total {len(rows)}")


if __name__ == "__main__":
    main()
