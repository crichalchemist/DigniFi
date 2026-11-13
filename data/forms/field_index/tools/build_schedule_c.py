"""
Writes Schedule C's schema whole, and the step 2 addendum rows for Schedule C (3g2 R9). Run it
from anywhere:

    python data/forms/field_index/tools/build_schedule_c.py

Never hand-edit `schedule_c.json` or Schedule C's addendum rows: change this tool and run it
again. `test_schedule_c_is_what_the_generator_writes` fails on any difference. It owns every
Schedule C row of `step2_verification.json`, the header rules' included.

Like `build_claims_schedules.py`, it reads only the repo (the field index and the template) and
copies `field()`, `Index`, `export_state` and `dumps()` rather than importing them: the tools
folder isn't a package. `field()` takes a `legal_review` keyword (True on every `exemptions.`
field, which prints a legal answer the filer gave).
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

FORM_TYPE = "schedule_c"
TEMPLATE = "b_106c_0425-form.pdf"
GROUP = "c_part_2"

# Row → column → full name. Rows 1-3 sit on page 1, rows 4-15 on page 2 (the index's row labels:
# page 2's row N is "Part 2 Additional Page row N - 3"; page 2's law boxes are named one less than
# their row's checkbox). Read from the field index's own labels, 2026-11-12.
COLUMNS = ("description", "line", "value", "amount_kind", "amount", "law")
_ROWS = [
    ("description", "Schedule AB", "undefined", "check 2.1", "undefined_2", "2.1"),
    ("description_2", "Schedule AB_2", "undefined_6", "check 2.2", "undefined_7", "2.2"),
    ("description_3", "Schedule AB_3", "undefined_8", "check 2.3", "undefined_9", "2.3"),
    ("description_4", "Line from", "undefined_11", "check 4", "undefined_12", "3"),
    ("description_5", "Schedule AB_4", "undefined_13", "check 5", "undefined_26", "4"),
    ("description_6", "Schedule AB_5", "undefined_27", "check 6", "undefined_28", "5"),
    ("description_7", "Line from_2", "undefined_29", "check 7", "undefined_30", "6"),
    ("description_8", "Schedule AB_6", "undefined_31", "check 8", "undefined_32", "7"),
    ("description_9", "Schedule AB_7", "undefined_34", "check 9", "undefined_35", "8"),
    ("description_10", "Line from_3", "undefined_36", "check 10", "undefined_37", "9"),
    ("description_11", "Schedule AB_8", "undefined_38", "check 11", "undefined_39", "10"),
    ("description_12", "Schedule AB_9", "undefined_40", "check 12", "undefined_41", "11"),
    ("description_13", "Line from_4", "undefined_42", "check 13", "undefined_43", "12"),
    ("description_14", "Schedule AB_10", "undefined_44", "check 14", "undefined_45", "13"),
    ("description_15", "Schedule AB_11", "undefined_47", "check 15", "undefined_48", "14"),
]
SLOTS = {n: dict(zip(COLUMNS, names, strict=True)) for n, names in enumerate(_ROWS, start=1)}

CELL_WORDS = {
    "description": "Brief description",
    "line": "Line from Schedule A/B",
    "value": "Current value of the portion you own",
    "amount_kind": "Amount of the exemption you claim",
    "amount": "Amount of the exemption you claim",
    "law": "Specific laws that allow exemption",
}

# R7 and R6: the answer → the box's export state.
AMOUNT_KIND_CHOICES = {"dollars": "/On", "fair_market_value": "/fair market"}
YES_NO = {"no": "/no", "yes": "/yes"}
LINES = [
    (
        "check 1",
        "exemptions.line_1",
        "Which set of exemptions are you claiming?",
        {"state_and_federal": "/state and federal", "federal": "/federal"},
    ),
    (
        "check 3",
        "exemptions.line_3",
        "Are you claiming a homestead exemption of more than $214,000?",
        YES_NO,
    ),
    (
        "check 3-1",
        "exemptions.line_3_1",
        "Did you acquire the property covered by the exemption within 1,215 days before you "
        "filed this case?",
        YES_NO,
    ),
]
DISTRICT = ("Bankruptcy District Information", "choice", 1, "District Information")

# R12: the tagged keys, since "page" names a widget on each page.
PAGE_NUMBERS = [
    {"page": 1, "this": None, "of": "page@1:T33"},
    {"page": 2, "this": "page 2", "of": "page@2:T88"},
]

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

    def widgets(self, name, tag=None):
        found = self.by_name.get(name)
        if not found:
            raise KeyError(f"no index row named {name!r}")
        if tag is not None:
            found = [w for w in found if w["tag"] == tag]
            if len(found) != 1:
                raise KeyError(f"{name!r} has no one widget tagged {tag!r}")
        return found


def _kind_and_page(name, widgets):
    kinds = {w["type"] for w in widgets}
    assert len(kinds) == 1, (name, kinds)
    pages = {w["page"] for w in widgets}
    assert len(pages) == 1, (name, pages)
    return KIND[kinds.pop()], pages.pop()


def _states(widgets):
    return {export_state(w["on_state"]) for w in widgets}


def slot(index, row, column, name):
    widgets = index.widgets(name)
    kind, page = _kind_and_page(name, widgets)
    choices = None
    if column == "amount_kind":
        choices = AMOUNT_KIND_CHOICES
        assert set(choices.values()) == _states(widgets), (name, _states(widgets))
    spec = field(
        name,
        kind,
        page,
        f"Exemption claim: {CELL_WORDS[column]}",
        binding=f"exemptions.claims[].{column}",
        choices=choices,
        group=(GROUP, len(SLOTS), row),
        legal_review=True,
    )
    return spec, widgets


def line_field(index, name, binding, words, choices):
    widgets = index.widgets(name)
    kind, page = _kind_and_page(name, widgets)
    assert set(choices.values()) == _states(widgets), (name, _states(widgets))
    spec = field(name, kind, page, words, binding=binding, choices=choices, legal_review=True)
    return spec, widgets


def rule_field(index, name, kind, page, words, rule):
    widgets = index.widgets(name)
    return field(name, kind, page, words, rule=rule), widgets


def _line_words(widget):
    return f" line {widget['line']}" if widget["line"] else ""


def evidence(spec, widgets):
    """The box's index label and basis, what prints there, and the tests that read it."""
    words = "; ".join(
        f"p{w['page']} {w['tag']}{_line_words(w)}, "
        f"{w['option_text'] or w['label']!r} ({w['basis']})"
        for w in widgets
    )
    cite = f"Field index: {spec['pdf_field']} {words}."
    readers = "test_schedule_c_rows.py and tier 1"
    if spec["rule"] == "full_name":
        basis = "full_name prints the filer's name as on every schedule (3g2 plan R9)."
        readers = "test_schedule_c_rows.py (on a copy) and tier 1"
    elif spec["rule"] == "district_name":
        basis = "district_name prints the district as on every schedule (3g2 plan R9)."
        readers = "tier 1"
    elif spec["repeat"]:
        basis = (
            f"Row {spec['row']} of group {spec['repeat']} prints {spec['binding']} here "
            "(3g spec §6.2)."
        )
    else:
        basis = f"{spec['binding']} prints the filer's answer (3g spec §6.2)."
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
    placed = [
        rule_field(index, "Debtor 1", "text", 1, "Debtor 1", "full_name"),
        rule_field(index, DISTRICT[0], DISTRICT[1], DISTRICT[2], DISTRICT[3], "district_name"),
    ]
    placed += [line_field(index, *line) for line in LINES]
    for row, cells in SLOTS.items():
        for column in COLUMNS:
            placed.append(slot(index, row, column, cells[column]))
    version = hashlib.sha256((PDFS / TEMPLATE).read_bytes()).hexdigest()
    schema = {
        "form_type": FORM_TYPE,
        "template_filename": TEMPLATE,
        "template_version": version,
        "groups": {GROUP: {"extra_page": 2}},
        "page_numbers": PAGE_NUMBERS,
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
    """existing with our rows put at the first Schedule C row's place; with none, just before
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
