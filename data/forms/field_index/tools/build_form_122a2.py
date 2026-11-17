"""
Writes Form 122A-2's schema whole, and the step 2 addendum rows for Form 122A-2 (3h3 plan R14).
Run it from anywhere:

    python data/forms/field_index/tools/build_form_122a2.py

Never hand-edit `form_122a2.json` or Form 122A-2's addendum rows: change this tool and run it
again. `test_form_122a2_is_what_the_tool_writes` fails on any difference. It owns every
form_122a2 row of `step2_verification.json`, the header rules' included, and replaces them in
place.

Like `build_schedule_c.py`, it reads only the repo (the field index and the template) and
copies `field()`, `Index`, `export_state` and `dumps()` rather than importing them: the tools
folder isn't a package. Every `means.` field is `source: asked` and carries no rule (R1):
`legal_review` marks the filer's own answers, the row cells the page typed included, and
nothing else. A name drawn on several pages binds once, on its first page (R25). Every widget
the table leaves out is blank on purpose (R15): `test_form_122a2_schema.py` lists them.
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

FORM_TYPE = "form_122a2"
TEMPLATE = "b_122a-2_0425-form.pdf"
TITLE = "Official Form 122A-2, Chapter 7 Means Test Calculation, line {line}"
# The line column of every sheet: "13b.9999" is 41.70 pt wide at 10 pt, more than the 36 pt
# default's inner width (spec §9.2). The columns of each group add up to 504 pt with it.
LINE_WIDTH = 46
SHEET_WIDTH = 504

# R2: the reader's keys → the index's export states. CheckBox5, CheckBox7 and CheckBox10 tick
# their Yes as /On; CheckBox6's "2 or more" and CheckBox14's middle band are /On too.
YES_NO = {"no": "/No", "yes": "/Yes"}
YES_ON = {"no": "/No", "yes": "/On"}
PAGE_1 = {"no_presumption": "/No Abuse", "presumption": "/Presumption of abuse applies"}
LINE_11 = {"0": "/0", "1": "/1", "2_or_more": "/On"}
LINE_40 = {"1": "/1", "2": "/2", "between": "/On"}

# The header rules, as on every form: (full name, kind, page, words, rule).
RULES = [
    ("Debtor1.Name", "text", 1, "Debtor's name (first, middle, last)", "full_name"),
    ("Bankruptcy District Information", "choice", 1, "District Information", "district_name"),
    ("Quest1", "text", 1, "Total monthly income", "cmi"),
]

# Every LINE_KEYS entry with a box of its own, in the form's order (R2): (full name, key,
# legal_review, choices, words). legal_review marks the filer's own answers (R1): §10's asked
# units (3, 9b, 11, 13b, 13e, 15-23, 25-31, 33d, 34, 36, 43), their totals and line 36's figures.
SCALARS = [
    ("CheckBox1", "page_1", False, PAGE_1, "Page 1: the result box at the top of the form"),
    ("CheckBox3", "2", False, YES_NO, "Line 2: Did you fill out Column B in Part 1 of Form 122A-1?"),
    ("CheckBox4", "2_filing", False, YES_NO, "Line 2: Is your spouse filing with you?"),
    ("CheckBox5", "3_answer", True, YES_ON, "Line 3: Is part of your spouse's income not used?"),
    ("Quest3", "3", True, None, "Line 3: Total of the amounts subtracted from your spouse's income"),
    ("Quest4", "4", False, None, "Line 4: Adjusted current monthly income"),
    ("Quest5", "5", False, None, "Line 5: The number of people used in determining your deductions"),
    ("Quest6", "6", False, None, "Line 6: Food, clothing, and other items"),
    ("Quest7A", "7a", False, None, "Line 7a: Out-of-pocket health care allowance per person under 65"),
    ("Quest7B", "7b", False, None, "Line 7b: Number of people who are under 65"),
    ("Quest7C", "7c", False, None, "Line 7c: Subtotal, line 7a times line 7b"),
    ("Quest7D", "7d", False, None, "Line 7d: Out-of-pocket health care allowance per person 65 or older"),
    ("Quest7E", "7e", False, None, "Line 7e: Number of people who are 65 or older"),
    ("Quest7F", "7f", False, None, "Line 7f: Subtotal, line 7d times line 7e"),
    ("Quest7G", "7g", False, None, "Line 7g: Total, lines 7c and 7f"),
    ("Quest8", "8", False, None, "Line 8: Housing and utilities: insurance and operating expenses"),
    ("Quest9", "9a", False, None, "Line 9a: Housing and utilities: mortgage or rent expenses"),
    ("Quest9B total amount", "9b", True, None, "Line 9b: Total average monthly payment, debts secured by your home"),
    ("Quest9C", "9c", False, None, "Line 9c: Net mortgage or rent expense"),
    ("CheckBox6", "11", True, LINE_11, "Line 11: The number of vehicles you claim an expense for"),
    ("Quest12", "12", False, None, "Line 12: Vehicle operation expense"),
    ("Describe Vehicle 1 1", "13_vehicle_1", False, None, "Line 13: Describe Vehicle 1"),
    ("Describe Vehicle 2 1", "13_vehicle_2", False, None, "Line 13: Describe Vehicle 2"),
    ("Quest13A", "13a", False, None, "Line 13a: Ownership or leasing costs for Vehicle 1"),
    ("Quest13B Total amount for vehicle 1", "13b", True, None, "Line 13b: Total average monthly payment, debts secured by Vehicle 1"),
    ("Quest13C", "13c", False, None, "Line 13c: Net Vehicle 1 ownership or lease expense"),
    ("Quest13D", "13d", False, None, "Line 13d: Ownership or leasing costs for Vehicle 2"),
    ("Quest13E.TotalMonthly", "13e", True, None, "Line 13e: Total average monthly payment, debts secured by Vehicle 2"),
    ("Quest13F", "13f", False, None, "Line 13f: Net Vehicle 2 ownership or lease expense"),
    ("Quest14", "14", False, None, "Line 14: Public transportation expense"),
    ("Quest15", "15", True, None, "Line 15: Additional public transportation expense"),
    ("undefined_48", "16", True, None, "Line 16: Taxes"),
    ("undefined_49", "17", True, None, "Line 17: Involuntary deductions"),
    ("undefined_50", "18", True, None, "Line 18: Life insurance"),
    ("undefined_51", "19", True, None, "Line 19: Court-ordered payments"),
    ("undefined_52", "20", True, None, "Line 20: Education"),
    ("undefined_53", "21", True, None, "Line 21: Childcare"),
    ("undefined_54", "22", True, None, "Line 22: Additional health care expenses"),
    ("undefined_55", "23", True, None, "Line 23: Optional telephones and telephone services"),
    ("undefined_56", "24", False, None, "Line 24: Total of the expenses allowed under the IRS standards"),
    ("undefined_57", "25_health", True, None, "Line 25: Health insurance"),
    ("undefined_58", "25_disability", True, None, "Line 25: Disability insurance"),
    ("1_2", "25_hsa", True, None, "Line 25: Health savings account"),
    ("2_2", "25", True, None, "Line 25: Total of health insurance, disability insurance and health savings account"),
    ("CheckBox7", "25_spends", True, YES_ON, "Line 25: Do you actually spend this total amount?"),
    ("undefined_59", "25_actual", True, None, "Line 25: How much do you actually spend?"),
    ("undefined_61", "26", True, None, "Line 26: Continuing contributions to the care of household or family members"),
    ("undefined_62", "27", True, None, "Line 27: Protection against family violence"),
    ("undefined_63", "28", True, None, "Line 28: Additional home energy costs"),
    ("undefined_64", "29", True, None, "Line 29: Education expenses for dependent children who are younger than 18"),
    ("undefined_65", "30", True, None, "Line 30: Additional food and clothing expense"),
    ("undefined_66", "31", True, None, "Line 31: Continuing charitable contributions"),
    ("undefined_67", "32", False, None, "Line 32: Total of the additional expense deductions"),
    ("undefined_80", "33e", False, None, "Line 33e: Total average monthly payment for all secured debts"),
    ("CheckBox11", "34_answer", True, YES_NO, "Line 34: Are any debts on line 33 secured by property you need for support?"),
    ("undefined_92", "34", True, None, "Line 34: Total monthly cure amount"),
    ("CheckBox12", "35_answer", False, YES_NO, "Line 35: Do you owe any priority claims that are past due?"),
    ("undefined_93", "35_total", False, None, "Line 35: Total amount of all past-due priority claims"),
    ("undefined_93-1", "35", False, None, "Line 35: Past-due priority claims divided by 60"),
    ("CheckBox13", "36_answer", True, YES_NO, "Line 36: Can you file a case under Chapter 13 of the Bankruptcy Code?"),
    ("undefined_97", "36_payment", True, None, "Line 36: Projected monthly plan payment if you were filing under Chapter 13"),
    ("x", "36_multiplier", True, None, "Line 36: Current multiplier for your district"),
    ("undefined_98", "36", True, None, "Line 36: Average monthly administrative expense if you were filing under Chapter 13"),
    ("undefined_100", "37", False, None, "Line 37: Total of the deductions for debt payment"),
    ("undefined_104", "38", False, None, "Line 38: Total deductions"),
    ("undefined_107", "39c", False, None, "Line 39c: Monthly disposable income under 11 U.S.C. § 707(b)(2)"),
    ("undefined_108", "39d", False, None, "Line 39d: Line 39c multiplied by 60"),
    ("CheckBox14", "40", False, LINE_40, "Line 40: How does line 39d compare to the two figures?"),
    ("undefined_110", "41a", False, None, "Line 41a: Total nonpriority unsecured debt"),
    ("undefined_111", "41b", False, None, "Line 41b: 25% of your total nonpriority unsecured debt"),
    ("CheckBox15", "42", False, YES_NO, "Line 42: How does line 39d compare to line 41b?"),
    ("CheckBox16", "43", True, YES_NO, "Line 43: Do you have any special circumstances?"),
]  # fmt: skip

# Line 38's three copy boxes: a second field each on lines 24, 32 and 37 (R2).
COPIES = [
    ("undefined_101", "24", "Line 38: Copy line 24"),
    ("undefined_102", "32", "Line 38: Copy line 32"),
    ("undefined_103", "37", "Line 38: Copy line 37"),
]

# Line 43's four form rows: circumstance n's pointer box and amount box (H49).
LINE_43_ROWS = [
    ("undefined_113", "undefined_114"),
    ("undefined_115", "undefined_116"),
    ("undefined_117", "undefined_118"),
    ("undefined_119", "undefined_120"),
]
LINE_43_WORDS = {
    "pointer": "Give a detailed explanation of the special circumstances",
    "amount": "Average monthly expense or income adjustment",
}

# The slot groups (R14): each cell's attribute, its sheet column's width and its words, the
# words being the form's own for the column, and the slot boxes row by row. The words also
# label each slot, "Line 34, row 1: Name of the creditor", for a refusal to quote.
CREDITOR = "Name of the creditor"
PROPERTY = "Identify property that secures the debt"
AVERAGE = "Average monthly payment"
GROUPS = {
    "3": {
        "columns": (
            ("purpose", 378, "Purpose for which your spouse's income was used", True),
            ("amount", 80, "Amount subtracted", True),
        ),
        "slots": (("Quest3A", "Quest3A1"), ("Quest3B", "Quest3B1"), ("Quest3C", "Quest3C1")),
    },
    "9b": {
        "columns": (("creditor", 378, CREDITOR, False), ("amount", 80, AVERAGE, True)),
        "slots": (
            ("Quest9B creditor name1", "Quest9B creditor amount1"),
            ("Quest9B creditor name2", "Quest9B creditor amount2"),
            ("Quest9B creditor name3", "Quest9B creditor amount3"),
        ),
    },
    "13b": {
        "columns": (("creditor", 378, CREDITOR, False), ("amount", 80, AVERAGE, True)),
        "slots": (
            ("Quest13B Creditor for vehicle 1-1", "Quest13B amount for vehicle 1-1"),
            ("Quest13B Creditor for vehicle 1-2", "Quest13B amount for vehicle 1-2"),
        ),
    },
    "13e": {
        "columns": (("creditor", 378, CREDITOR, False), ("amount", 80, AVERAGE, True)),
        "slots": (
            ("Quest13E.Creditor1", "Quest13E.Monthly1"),
            ("Quest13E.Creditor2", "Quest13E.Monthly2"),
        ),
    },
    "33d": {
        "columns": (
            ("creditor", 170, CREDITOR, False),
            ("property", 150, PROPERTY, False),
            ("taxes_or_insurance", 58, "Does payment include taxes or insurance?", True),
            ("amount", 80, AVERAGE, True),
        ),
        "slots": (
            ("undefined_71", "undefined_72", "CheckBox8", "undefined_73"),
            ("undefined_74", "undefined_75", "CheckBox9", "undefined_76"),
            ("undefined_77", "undefined_78", "CheckBox10", "undefined_79"),
        ),
    },
    "34": {
        "columns": (
            ("creditor", 150, CREDITOR, False),
            ("property", 150, PROPERTY, False),
            ("cure", 78, "Total cure amount", True),
            ("amount", 80, "Monthly cure amount", True),
        ),
        "slots": (
            ("undefined_81", "secures the debt", "undefined_82", "undefined_83"),
            ("undefined_84", "undefined_85", "undefined_86", "undefined_87"),
            ("undefined_88", "undefined_89", "undefined_90", "undefined_91"),
        ),
    },
}
# Each 33d slot keeps its own map: row 3's Yes is /On where rows 1 and 2 tick /Yes (R14).
BOX_CHOICES = {"CheckBox8": YES_NO, "CheckBox9": YES_NO, "CheckBox10": YES_ON}
# The statement group (H49): a sheet and no slots, its explanation column as wide as the PUT
# measures (`means_fit.LINE_43_EXPLANATION_WIDTH`).
LINE_43_COLUMNS = (
    ("explanation", 362, LINE_43_WORDS["pointer"]),
    ("amount", 96, LINE_43_WORDS["amount"]),
)

KIND = {"Text": "text", "CheckBox": "checkbox", "RadioButton": "radio"}


def export_state(on_state):
    """The index's on-state as the PDF's export state: the name escapes decoded."""
    return "/" + re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), on_state)


def field(
    pdf_field,
    kind,
    page,
    label,
    *,
    rule=None,
    binding=None,
    choices=None,
    group=None,
    tag=None,
    legal_review=False,
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
        "legal_review": legal_review,
    }
    return out


class Index:
    """One template's field index, by full name."""

    def __init__(self, template):
        self.rows = json.loads((INDEX_DIR / f"{Path(template).stem}.index.json").read_text())
        self.by_name = {}
        for row in self.rows:
            self.by_name.setdefault(row["full_name"], []).append(row)

    def widgets(self, name):
        found = self.by_name.get(name)
        if not found:
            raise KeyError(f"no index row named {name!r}")
        return found


def _kind_and_page(name, widgets):
    kinds = {w["type"] for w in widgets}
    assert len(kinds) == 1, (name, kinds)
    # R25: a name drawn on several pages binds once, on its first page, one value in every widget
    return KIND[kinds.pop()], min(w["page"] for w in widgets)


def _states(widgets):
    return {export_state(w["on_state"]) for w in widgets}


def _binding(key):
    return "means.page_1" if key == "page_1" else f"means.line_{key}"


def scalar(index, name, key, legal_review, choices, words):
    widgets = index.widgets(name)
    kind, page = _kind_and_page(name, widgets)
    assert (choices is None) == (kind == "text"), (name, kind)
    if choices is not None:
        assert set(choices.values()) == _states(widgets), (name, _states(widgets))
    spec = field(
        name, kind, page, words, binding=_binding(key), choices=choices, legal_review=legal_review
    )
    return spec, widgets


def slot(index, line, row, column, name):
    attr, _, words, legal_review = column
    widgets = index.widgets(name)
    kind, page = _kind_and_page(name, widgets)
    choices = BOX_CHOICES.get(name)
    assert (choices is None) == (kind == "text"), (name, kind)
    if choices is not None:
        assert set(choices.values()) == _states(widgets), (name, _states(widgets))
    spec = field(
        name,
        kind,
        page,
        f"Line {line}, row {row}: {words}",
        binding=f"means.line_{line}[].{attr}",
        choices=choices,
        group=(f"means_line_{line}", len(GROUPS[line]["slots"]), row),
        legal_review=legal_review,
    )
    return spec, widgets


def rule_field(index, name, kind, page, words, rule):
    widgets = index.widgets(name)
    return field(name, kind, page, words, rule=rule), widgets


def sheet(line, columns):
    """A group's sheet (R14): its title, the 46 pt line column and its columns, 504 pt in all."""
    assert LINE_WIDTH + sum(column[1] for column in columns) == SHEET_WIDTH, line
    return {
        "title": TITLE.format(line=line),
        "line_width": LINE_WIDTH,
        "columns": [
            {"label": column[2], "binding": f"means.line_{line}[].{column[0]}", "width": column[1]}
            for column in columns
        ],
    }


def _line_words(widget):
    return f" line {widget['line']}" if widget["line"] else ""


def evidence(spec, widgets):
    """The box's index label and basis, every widget of the name, what prints there, and the
    tests that read it."""
    words = "; ".join(
        f"p{w['page']} {w['tag']}{_line_words(w)}, "
        f"{w['option_text'] or w['label']!r} ({w['basis']})"
        for w in widgets
    )
    cite = f"Field index: {spec['pdf_field']} {words}."
    readers = "tier 1 and tier 3 (Priya)"
    binding = spec["binding"] or ""
    if spec["rule"] == "full_name":
        basis = "full_name prints the filer's name as on every form (3h3 plan R14)."
        readers = "tier 1"
    elif spec["rule"] == "district_name":
        basis = "district_name prints the district as on every form (3h3 plan R14)."
        readers = "tier 1"
    elif spec["rule"] == "cmi":
        basis = (
            "cmi prints 122A-1 line 11's current monthly income, which line 1 copies "
            "(3h spec §10; step 2 spec §6.1, C1)."
        )
    elif spec["repeat"]:
        basis = (
            f"Row {spec['row']} of group {spec['repeat']} prints {binding} here, the "
            "calculator's row (3h spec §9.2, H30)."
        )
        readers = "test_form_122a2_rows.py and tier 1"
    elif binding.startswith("means.line_43_"):
        kind, n = binding.rsplit("_", 2)[1:]
        what = "the pointer to its sheet row" if kind == "pointer" else "the amount"
        basis = f"{binding} prints {what} for circumstance {n} of line 43 (3h spec §9.2, H49)."
        readers = "test_form_122a2_rows.py and tier 1"
    else:
        key = binding.removeprefix("means.").removeprefix("line_")
        basis = f"{binding} prints the calculator's line {key} (3h spec §10, 3h3 plan R2)."
    return f"{cite} {basis} Read by {readers}."


def addendum_row(spec, widgets):
    producer = f"derived:{spec['rule']}" if spec["rule"] else f"asked:{spec['binding']}"
    return {
        "schema": FORM_TYPE,
        "pdf_field": spec["pdf_field"],
        "producer": producer,
        "original_verdicts": [],
        "final_verdicts": ["correct"],
        "status": "confirmed",
        "correct_target": spec["pdf_field"],
        "evidence": evidence(spec, widgets),
    }


def owned(row):
    return row["schema"] == FORM_TYPE


def build():
    """(the schema, the addendum rows it owns), reading only the repo."""
    index = Index(TEMPLATE)
    # The rules first: Quest1's cmi raises IncomeNotSplit for a filer with no income by source
    # before any means. field reads the session.
    placed = [rule_field(index, *rule) for rule in RULES]
    placed += [scalar(index, *entry) for entry in SCALARS]
    placed += [scalar(index, name, key, False, None, words) for name, key, words in COPIES]
    for n, (pointer, amount) in enumerate(LINE_43_ROWS, start=1):
        for name, kind in ((pointer, "pointer"), (amount, "amount")):
            widgets = index.widgets(name)
            spec = field(
                name,
                "text",
                9,
                f"Line 43, row {n}: {LINE_43_WORDS[kind]}",
                binding=f"means.line_43_{kind}_{n}",
                legal_review=True,
            )
            placed.append((spec, widgets))
    groups = {}
    for line, group in GROUPS.items():
        for row, names in enumerate(group["slots"], start=1):
            for column, name in zip(group["columns"], names, strict=True):
                placed.append(slot(index, line, row, column, name))
        groups[f"means_line_{line}"] = {
            "number": f"{line}.{{n}}",
            "sheet": sheet(line, group["columns"]),
        }
    groups["means_line_43"] = {"number": "43.{n}", "sheet": sheet("43", LINE_43_COLUMNS)}
    version = hashlib.sha256((PDFS / TEMPLATE).read_bytes()).hexdigest()
    schema = {
        "form_type": FORM_TYPE,
        "template_filename": TEMPLATE,
        "template_version": version,
        "groups": groups,
        "fields": [spec for spec, _ in placed],
    }
    return schema, [addendum_row(spec, widgets) for spec, widgets in placed]


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
    """existing with our rows put at the first Form 122A-2 row's place; with none, just before
    the first List of Creditors row (its tool rewrites its rows at the end), else at the end."""
    at = next((i for i, r in enumerate(existing) if owned(r)), None)
    if at is None:
        at = next(
            (i for i, r in enumerate(existing) if r["schema"] == "list_of_creditors"),
            len(existing),
        )
    before = [r for r in existing[:at] if not owned(r)]
    after = [r for r in existing[at:] if not owned(r)]
    return [*before, *ours, *after]


def merged_text(existing_text, rows):
    """The addendum file's text once our rows are merged into it."""
    return dumps(merged(json.loads(existing_text), rows))


def main():
    schema, rows = build()
    (SCHEMAS_DIR / f"{FORM_TYPE}.json").write_text(dumps(schema))
    ADDENDUM.write_text(merged_text(ADDENDUM.read_text(), rows))
    print(f"addendum rows for {FORM_TYPE}: {len(rows)}")


if __name__ == "__main__":
    main()
