"""
Writes Form 108 (Statement of Intention for Individuals Filing Under Chapter 7)'s schema, its 47
addendum rows in `step2_verification.json` and `form_108.limits.json`, the caps on the texts it
and the claims schedules print (forms step 4e, R-SHAPE, 4e-R4, 4e-R9).

Run it with the backend's Python, the one with the backend's requirements installed, since the
caps are measured with the filler's own text_fit. From the repo root:

    python data/forms/field_index/tools/build_form_108.py

It puts `backend/` on the path and sets up Django itself (`config.settings.test` unless
DJANGO_SETTINGS_MODULE names another), so it needs no database. It does need the backend's
environment (the secret key and the field encryption key the test settings read, as for pytest).

Never hand-edit `form_108.json`, `form_108.limits.json` or its rows: change this tool and run it
again. test_form_108_generator.py fails on any difference.

The boxes are found in the committed index (`form_b108.index.json`) by full name, and each box's
on-states by its index label, so a choice maps to the box the form prints its words beside. Part 1
prints `claims.secured[]` (four rows, then an attached sheet) and Part 2 `claims.leases[]` (seven
rows, then a sheet). Debtor 2, the case number, the amended-filing box, both signatures and both
dates stay unbound: DigniFi ticks nothing the filer didn't choose and nothing they sign in ink.

The caps (4e-R4) are one per box, keyed "<form>:<binding>", each measured on every slot of the
box's column and the narrowest kept: a one-line box by `build_form_101a.py`'s formula, a multi-line
box by half its lines' worth (the venue reason's rule, `build_schedule_i_limits.py`), chosen by the
widget's own multiline flag (F5). "form_108:explain" is Explain1's cap plus Explain2's (R-EXPLAIN).

Like the other schema tools it copies `export_state()`, `field()` and `dumps()`
(`build_claims_schedules.py`) rather than importing them: the tools folder isn't a package.
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

FORM_TYPE = "form_108"
TEMPLATE = "form_b108.pdf"

PART_1_ROWS = "abcd"
PART_2_ROWS = "abcdefg"

# Part 1's four choices in the form's order: the answer, the end of its box's index label.
INTENTIONS = {
    "surrender": "intention, surrender",
    "retain_redeem": "intention, retain and redeem",
    "retain_reaffirm": "intention, retain and reaffirm",
    "retain_explain": "intention, retain and explain",
}
YES_NO = {"no": ", No", "yes": ", Yes"}

# attr -> (the box's full name with {row} for its letter, its words in the schema)
PART_1_CELLS = {
    "name": ("Creditors Name 1{row}", "Creditor's name"),
    "property": ("PropertyDescription 1{row}", "Description of property securing debt"),
    "intention": ("check1 1{row}", "What do you intend to do with the property?"),
    "exempt": ("check2 1{row}", "Did you claim the property as exempt on Schedule C?"),
    "explain_1": ("Explain1 1{row}", "Retain the property and [explain], first box"),
    "explain_2": ("Explain2 1{row}", "Retain the property and [explain], second box"),
}
PART_2_CELLS = {
    "name": ("Lessors Name 2{row}", "Lessor's name"),
    "purpose": ("PropertyDescription 2{row}", "Description of leased property"),
    "assumed": ("check2{row}", "Will the lease be assumed?"),
}

TITLE = "Official Form 108, Statement of Intention for Individuals Filing Under Chapter 7"
# 4e-R9: each label is the form's own words; the explanation prints beside the choice it explains.
GROUPS = {
    "f108_part_1": {
        "number": "1.{n}",
        "sheet": {
            "title": f"{TITLE}, Part 1",
            "line_width": 40,
            "columns": [
                {"label": "Creditor’s name:", "binding": "claims.secured[].name", "width": 96},
                {
                    "label": "Description of property securing debt:",
                    "binding": "claims.secured[].property",
                    "width": 104,
                },
                {
                    "label": "What do you intend to do with the property that secures a debt?",
                    "binding": "claims.secured[].intention",
                    "width": 110,
                },
                {
                    "label": "[explain]",
                    "binding": "claims.secured[].explain",
                    "width": 96,
                    "covers": ["claims.secured[].explain_1", "claims.secured[].explain_2"],
                },
                {
                    "label": "Did you claim the property as exempt on Schedule C?",
                    "binding": "claims.secured[].exempt",
                    "width": 58,
                },
            ],
        },
    },
    "f108_part_2": {
        "number": "2.{n}",
        "sheet": {
            "title": f"{TITLE}, Part 2",
            "line_width": 40,
            "columns": [
                {"label": "Lessor’s name:", "binding": "claims.leases[].name", "width": 170},
                {
                    "label": "Description of leased property:",
                    "binding": "claims.leases[].purpose",
                    "width": 194,
                },
                {
                    "label": "Will the lease be assumed?",
                    "binding": "claims.leases[].assumed",
                    "width": 100,
                },
            ],
        },
    },
}

# The texts the filer types that Form 108 and the claims schedules print (4e-R4), each box by
# (form, binding); the schema each binding is read from is that form's committed one.
CAPPED = [
    ("form_108", "claims.secured[].name"),
    ("schedule_d", "claims.secured[].name"),
    ("schedule_e_f", "claims.priority[].name"),
    ("schedule_e_f", "claims.unsecured[].name"),
    ("form_108", "claims.secured[].property"),
    ("schedule_d", "claims.secured[].property"),
    ("schedule_g", "claims.contracts[].name"),
    ("form_108", "claims.leases[].name"),
    ("schedule_g", "claims.contracts[].purpose"),
    ("form_108", "claims.leases[].purpose"),
]
EXPLAIN_BINDINGS = ("claims.secured[].explain_1", "claims.secured[].explain_2")

# The too-long detail's words for each text (E7, E8).
LABELS = {
    # DRAFT: counsel C-37
    "creditor_name": "the creditor's name",
    # DRAFT: counsel C-37
    "collateral_description": "the description of the property",
    # DRAFT: counsel C-37
    "counterparty_name": "the lessor's name",
    # DRAFT: counsel C-37
    "description": "the description of the leased property",
    # DRAFT: counsel C-37
    "explain": "the explanation of your plan",
}

# Measuring letters, as build_form_101a.py: digits for every text.
TEXT_LETTERS = "0123456789"


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


KIND = {"Text": "text", "CheckBox": "checkbox", "RadioButton": "radio", "ComboBox": "choice"}


def _named(index, name):
    found = [row for row in index if row["full_name"] == name]
    if not found:
        sys.exit(f"no index row named {name!r}")
    return found


def _choices(widgets, answers):
    """Each answer's export state, read off the box whose index label ends in its words, so a
    choice ticks the box the form prints its words beside."""
    choices = {}
    for answer, words in answers.items():
        (box,) = [w for w in widgets if w["label"].endswith(words)] or [None]
        if box is None:
            sys.exit(f"no box of {widgets[0]['full_name']!r} labelled …{words!r}")
        choices[answer] = export_state(box["on_state"])
    states = {export_state(w["on_state"]) for w in widgets}
    if set(choices.values()) != states or len(states) != len(choices):
        sys.exit(f"{widgets[0]['full_name']!r}'s states {sorted(states)} aren't one an answer")
    return choices


def _slot(index, group, capacity, row, list_name, attr, name, words):
    widgets = _named(index, name)
    kinds = {w["type"] for w in widgets}
    pages = {w["page"] for w in widgets}
    if len(kinds) != 1 or len(pages) != 1:
        sys.exit(f"{name!r} is on {sorted(pages)} as {sorted(kinds)}")
    kind = KIND[kinds.pop()]
    choices = None
    if attr == "intention":
        choices = _choices(widgets, INTENTIONS)
    elif kind == "checkbox":
        choices = _choices(widgets, YES_NO)
    spec = field(
        name,
        kind,
        pages.pop(),
        f"Part {group[-1]}, row {row}: {words}",
        binding=f"claims.{list_name}[].{attr}",
        choices=choices,
        group=(group, capacity, row),
    )
    return spec, widgets


def _header(index):
    """The filer's name on both pages (one untagged binding fills each widget of the name) and
    the court."""
    placed = []
    for name, kind, rule, words in (
        ("Debtor 1", "text", "full_name", "Debtor 1"),
        ("Bankruptcy District Information", "choice", "district_name", "District Information"),
    ):
        widgets = _named(index, name)
        placed.append((field(name, kind, widgets[0]["page"], words, rule=rule), widgets))
    return placed


def _placed(index):
    """(field, its index rows) for every binding, in the schema's order."""
    placed = _header(index)
    for number, letter in enumerate(PART_1_ROWS, start=1):
        for attr, (name, words) in PART_1_CELLS.items():
            placed.append(
                _slot(
                    index, "f108_part_1", 4, number, "secured", attr, name.format(row=letter), words
                )
            )
    for number, letter in enumerate(PART_2_ROWS, start=1):
        for attr, (name, words) in PART_2_CELLS.items():
            placed.append(
                _slot(
                    index, "f108_part_2", 7, number, "leases", attr, name.format(row=letter), words
                )
            )
    return placed


def schema(index, template_sha256):
    """Form 108's schema: the header, then Part 1's four rows and Part 2's seven."""
    return {
        "form_type": FORM_TYPE,
        "template_filename": TEMPLATE,
        "template_version": template_sha256,
        "groups": GROUPS,
        "fields": [spec for spec, _ in _placed(index)],
    }


# Why each cell prints where it does.
RULINGS = {
    "name": "R-SHAPE, 4e-R22",
    "property": "R-SHAPE, 4e-R22",
    "intention": "R-SHAPE, R-BLANK-EXPLAIN, 4e-R22: the filer's own choice, blank while open",
    "exempt": "R-EXEMPT, 4e-R6: Yes or No from Schedule C's own answers, else blank",
    "explain_1": "R-EXPLAIN, 4e-R5: the words only under the filer's retain-and-explain",
    "explain_2": "R-EXPLAIN, 4e-R5: the words only under the filer's retain-and-explain",
    "purpose": "R-SHAPE, R-LEASE-GATE, 4e-R22",
    "assumed": "R-SHAPE, 4e-R22: the filer's own answer, blank while open",
}


def _evidence(spec, widgets):
    words = "; ".join(
        f"p{w['page']} {w['tag']}, {w['label']!r}"
        + (f" ({w['option_text']!r})" if w["option_text"] else "")
        + f" ({w['basis']})"
        for w in widgets
    )
    cite = f"Field index: {spec['pdf_field']} {words}."
    if spec["rule"] == "full_name":
        basis = "Printed from the filer's name in their debtor information, on both pages."
    elif spec["rule"] == "district_name":
        basis = "Printed from the session's district, not the filer's answer."
    else:
        attr = spec["binding"].rsplit(".", 1)[-1]
        basis = (
            f"Row {spec['row']} of group {spec['repeat']} prints {spec['binding']} here "
            f"({RULINGS[attr]})."
        )
    return (
        f"{cite} {basis} Debtor 2, the case number, the amended-filing box, the signatures and "
        "the dates stay unbound. Read by test_form_108_schema.py, test_form_108_prints.py and "
        "tier 1."
    )


def _producer(spec):
    return f"derived:{spec['rule']}" if spec["rule"] else f"asked:{spec['binding']}"


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


def _index():
    return json.loads((INDEX_DIR / f"{Path(TEMPLATE).stem}.index.json").read_text())


def build():
    """(the schema, the addendum rows it owns), reading only the repo."""
    index = _index()
    sha256 = hashlib.sha256((PDFS / TEMPLATE).read_bytes()).hexdigest()
    return schema(index, sha256), addendum_rows(index)


def owned(row):
    return row["schema"] == FORM_TYPE


def merged(existing, ours):
    """existing with our rows put at the first Form 108 row's place; with none, just before
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


def _cap(template, box):
    """As many of the widest digits as fit the box at 6 pt: a line's worth in a one-line box
    (never more than its /MaxLen), half its lines' worth in a multi-line box."""
    from apps.forms.services.text_fit import MIN_SIZE, _leading, _width, font_for, reverse_cmap_for

    font = font_for(template, box.font)
    cmap = reverse_cmap_for(template, box.font)
    widest = max(_width(font, cmap, c, MIN_SIZE) for c in TEXT_LETTERS)
    room = box.width - 4 * box.margin
    if box.multiline:
        lines = math.floor((box.height - 2 * box.margin) / (MIN_SIZE * _leading(font)))
        return math.floor(lines / 2 * room / widest)
    cap = math.floor(room / widest)
    if box.max_len:
        cap = min(cap, box.max_len)
    return cap


def _narrowest(form_schema, binding):
    """The cap of the narrowest drawn box a binding fills on a form, over every slot."""
    from apps.forms.services.widgets import template_widgets

    template = form_schema["template_filename"]
    widgets = template_widgets(template)
    caps = []
    for spec in form_schema["fields"]:
        if spec["binding"] != binding:
            continue
        boxes = [
            w
            for w in widgets
            if w.drawn
            and (w.full_name, w.page) == (spec["pdf_field"], spec["page"])
            and spec.get("tag") in (None, w.tag)
        ]
        if not boxes:
            sys.exit(f"no drawn box for {binding!r} at {spec['pdf_field']!r}")
        caps += [_cap(template, box) for box in boxes]
    if not caps:
        sys.exit(f"{form_schema['form_type']} binds no box to {binding!r}")
    return min(caps)


def limits():
    """Each capped box's cap, keyed "<form>:<binding>", and each text's too-long words."""
    _setup_django()
    built, _ = build()
    schemas = {FORM_TYPE: built}
    boxes = {}
    for form_type, binding in CAPPED:
        if form_type not in schemas:
            schemas[form_type] = json.loads((SCHEMAS_DIR / f"{form_type}.json").read_text())
        boxes[f"{form_type}:{binding}"] = _narrowest(schemas[form_type], binding)
    boxes[f"{FORM_TYPE}:explain"] = sum(_narrowest(built, b) for b in EXPLAIN_BINDINGS)
    return {"boxes": boxes, "labels": LABELS}


_SCALAR_ARRAY = re.compile(
    r'^( *(?:"[^"\n]*": )?)\[\n((?: *(?:"(?:[^"\\\n]|\\.)*"|-?\d+(?:\.\d+)?),?\n)+) *\](,?)$', re.M
)


def _on_one_line(match):
    items = [item.strip().rstrip(",") for item in match[2].splitlines()]
    line = f"{match[1]}[{', '.join(items)}]{match[3]}"
    # The repo's prettier joins a list that fits its printWidth, 100 (.prettierrc.json). The
    # other tools' 80 never meets a list between the two; the explain column's covers is 82.
    return line if len(line) <= 100 else match[0]


def dumps(data):
    """json.dumps as prettier writes it: a list of scalars that fits a line on one line."""
    return _SCALAR_ARRAY.sub(_on_one_line, json.dumps(data, indent=2, ensure_ascii=False)) + "\n"


def _setup_django():
    import django
    from django.conf import settings

    if not settings.configured:
        sys.path.insert(0, str(ROOT / "backend"))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
        django.setup()


def main():
    built, rows = build()
    (SCHEMAS_DIR / f"{FORM_TYPE}.json").write_text(dumps(built))
    (SCHEMAS_DIR / f"{FORM_TYPE}.limits.json").write_text(dumps(limits()))
    ADDENDUM.write_text(merged_text(ADDENDUM.read_text(), rows))
    print(f"bindings for {FORM_TYPE}: {len(built['fields'])}; addendum rows: {len(rows)}")


if __name__ == "__main__":
    main()
