"""
Writes Form 122A-1Supp's schema and its nine addendum rows in `step2_verification.json` (forms step
4d, Task 4). From the repo root:

    python data/forms/field_index/tools/build_form_122a1_supp.py

It reads only the repo (the template, its committed index and the addendum file), so it needs no
Django and no database.

Never hand-edit `form_122a1_supp.json` or its rows: change this tool and run it again.
`test_form_122a1_supp_generator.py` fails on any difference.

The table is keyed by the box's full name and, for a name drawn twice as two boxes, its tag: line
1's `CheckBox2` is one name with a Yes widget (T7) and a No widget (T6), each its own tagged
binding (R-D6, 4d-R7). Never by label: five names share theirs across two widgets.

The header's two bindings (the filer's name and the district) are written as they stood, and their
rows stay in `verification.json` (E13): this tool owns only the nine rows of line 1 and Part 2.
The amended-filing box, Debtor 2's name and the case number stay unbound: DigniFi prints no No the
filer didn't give and nothing the filer didn't answer.

Like the other schema tools it copies `dumps()` rather than importing it: the tools folder isn't a
package.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INDEX_DIR = ROOT / "data" / "forms" / "field_index"
SCHEMAS_DIR = ROOT / "data" / "forms" / "schemas"
PDFS = ROOT / "data" / "forms" / "pdfs"
ADDENDUM = INDEX_DIR / "audit" / "step2_verification.json"

FORM_TYPE = "form_122a1_supp"
TEMPLATE = "form_b122a-1supp.pdf"

YES_NO = {"yes": "/Yes", "no": "/no"}
CATEGORIES = {"1": "/1", "2": "/2", "3": "/3", "4": "/4"}

# The header, written as it stood before 4d, its labels the boxes' tooltips. No addendum row:
# verification.json's rows assert them (E13).
HEADER = (
    ("Debtor1.Name", "text", "Debtor;s name (first, middle, last)", "full_name"),
    ("Bankruptcy District Information", "choice", "District Information", "district_name"),
)

# (full name, tag or None, type, rule or binding, choices, label, conditional_on, legal_review,
# why). A rule is written "derived:<rule>", a binding "asked:<binding>".
BINDINGS = (
    (
        "CheckBox2",
        "T7",
        "checkbox",
        "derived:debt_nature_consumer",
        {"true": "/Yes"},
        "Line 1: debts are primarily consumer debts",
        None,
        True,
        "Step 4 spec §5.3: line 1 prints Form 101 line 16's answer (debt_nature). Ruling R-D6 and "
        "4d-R7: the name is drawn twice, each widget its own box, so each answer has its own "
        "tagged binding through the line 16a rules' aliases. The Yes box prints only for the "
        "filer's own `consumer`, marked for legal review, its rule in ANSWER_BOX_RULES; an "
        "unanswered line 16 ticks neither box.",
    ),
    (
        "CheckBox2",
        "T6",
        "checkbox",
        "derived:debt_nature_not_consumer",
        {"true": "/no"},
        "Line 1: debts are not primarily consumer debts",
        None,
        False,
        "Step 4 spec §5.3: line 1 prints Form 101 line 16's answer (debt_nature). Ruling R-D6 and "
        "4d-R7: the name is drawn twice, each widget its own box, so each answer has its own "
        "tagged binding through the line 16a rules' aliases. The No box prints only for the "
        "filer's own `business` or `neither`, not marked for legal review; an unanswered line 16 "
        "ticks neither box.",
    ),
    (
        "CheckBox3",
        None,
        "checkbox",
        "asked:petition.disabled_veteran",
        YES_NO,
        "Line 2: disabled veteran",
        "petition_debt_nature_consumer",
        True,
        "4d-R8: line 2 prints the filer's own answer, only under consumer debts (line 1's No "
        "goes to Form 122A-1 instead).",
    ),
    (
        "CheckBox4",
        None,
        "checkbox",
        "asked:petition.debts_on_duty",
        YES_NO,
        "Line 2: debts incurred mostly on active duty or in a homeland defense activity",
        "supp_line_2_follow_up",
        True,
        "4d-R8: line 2's follow-up prints the filer's own answer, only under consumer debts and "
        "line 2's Yes.",
    ),
    (
        "CheckBox5",
        None,
        "checkbox",
        "asked:petition.reservist",
        YES_NO,
        "Line 3: Reservist or member of the National Guard",
        "supp_line_3",
        True,
        "4d-R8 and R-D2: line 3 prints the filer's own answer only where the form reaches it, "
        "under consumer debts unless line 2 is Yes to both questions (supp_line_3_reached).",
    ),
    (
        "CheckBox6",
        None,
        "checkbox",
        "asked:petition.called_to_duty",
        YES_NO,
        "Line 3: called to active duty or performed a homeland defense activity",
        "supp_line_3_follow_up",
        True,
        "4d-R8: line 3's follow-up prints the filer's own answer where line 3 is reached and its "
        "answer is Yes.",
    ),
    (
        "CheckBox7",
        None,
        "checkbox",
        "derived:supp_duty_category",
        CATEGORIES,
        "Line 3: the active duty or homeland defense category",
        "supp_categories",
        True,
        "4d-R8 and 4d-R26: the category prints through the rule supp_duty_category, which "
        "returns the filer's own stored category 1 to 4 and blank otherwise, so 'none applies' "
        "(D9) ticks no box; marked for legal review, its rule in ANSWER_BOX_RULES. It prints only "
        "under the follow-up's Yes.",
    ),
    (
        "Date1",
        None,
        "text",
        "asked:petition.duty_released_on",
        None,
        "Line 3: date released from active duty (category 2)",
        "supp_date_1",
        False,
        "4d-R8 and 4d-R9: the filer's own date, only under category 2's whole chain, and only "
        "as MM/DD/YYYY (record_value blanks any other).",
    ),
    (
        "Date2",
        None,
        "text",
        "asked:petition.duty_ended_on",
        None,
        "Line 3: date the homeland defense activity ended (category 4)",
        "supp_date_2",
        False,
        "4d-R8 and 4d-R9: the filer's own date, only under category 4's whole chain, and only "
        "as MM/DD/YYYY (record_value blanks any other).",
    ),
)


def export_state(on_state):
    """The index's on-state as the PDF's export state: the name escapes decoded."""
    return "/" + re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), on_state)


def _widgets(index, name, tag):
    """The index rows a binding fills: every widget of the name, or only the tagged one."""
    found = [r for r in index if r["full_name"] == name and tag in (None, r["tag"])]
    if not found or (tag is not None and len(found) != 1):
        sys.exit(f"{len(found)} index rows named {name!r} with tag {tag!r}")
    return found


def field(pdf_field, kind, page, label, *, rule=None, binding=None, **over):
    """A schema field in build_form_122a2.py's key order: tag after the name, choices after the
    source."""
    out = {"pdf_field": pdf_field}
    if over.get("tag") is not None:
        out["tag"] = over["tag"]
    out |= {"type": kind, "source": "derived" if rule else "asked"}
    if over.get("choices") is not None:
        out["choices"] = over["choices"]
    return out | {
        "page": page,
        "label": label,
        "required": False,
        "conditional_on": over.get("conditional_on"),
        "value": None,
        "rule": rule,
        "ingest_key": None,
        "binding": binding,
        "repeat": None,
        "repeat_capacity": None,
        "row": None,
        "legal_review": over.get("legal_review", False),
    }


def _placed(index):
    """(spec, widgets, why) for each of the nine bindings, checked against the index."""
    placed = []
    for name, tag, kind, target, choices, label, conditional_on, legal_review, why in BINDINGS:
        widgets = _widgets(index, name, tag)
        if kind == "text":
            assert choices is None and {w["type"] for w in widgets} == {"Text"}, name
        else:
            states = {export_state(w["on_state"]) for w in widgets}
            assert set(choices.values()) == states, (name, tag, states)
        source, _, producer = target.partition(":")
        spec = field(
            name,
            kind,
            widgets[0]["page"],
            label,
            rule=producer if source == "derived" else None,
            binding=producer if source == "asked" else None,
            tag=tag,
            choices=choices,
            conditional_on=conditional_on,
            legal_review=legal_review,
        )
        placed.append((spec, widgets, why))
    return placed


def schema(index, template_sha256):
    """The Supp's schema: the header as it stood, then line 1 and Part 2. No groups."""
    fields = []
    for name, kind, label, rule in HEADER:
        (row,) = _widgets(index, name, None)
        fields.append(field(name, kind, row["page"], label, rule=rule))
    fields += [spec for spec, _, _ in _placed(index)]
    return {
        "form_type": FORM_TYPE,
        "template_filename": TEMPLATE,
        "template_version": template_sha256,
        "groups": {},
        "fields": fields,
    }


def _evidence(spec, widgets, why, index):
    name = spec["pdf_field"]
    first = widgets[0]
    tags = ", ".join(w["tag"] for w in widgets)
    if first["type"] == "Text":
        drawn = f"a text box ({first['tooltip']})"
    else:
        drawn = "; ".join(
            f"state {export_state(w['on_state'])} ({w['option_text']!r})" for w in widgets
        )
    cite = (
        f"Field index: {name} p{first['page']} {tags} line {first['line']} {first['label']!r}, "
        f"{drawn} ({first['basis']})."
    )
    if spec.get("tag"):
        others = [r["tag"] for r in index if r["full_name"] == name and r["tag"] != spec["tag"]]
        cite += f" Bound @{first['page']}:{spec['tag']}; {', '.join(others)} is the other box."
    return (
        f"{cite} {why} Written by build_form_122a1_supp.py; read by "
        "test_form_122a1_supp_schema.py and tier 1."
    )


def addendum_rows(index):
    """One confirmed addendum row a binding of line 1 and Part 2, keyed by (box, binding key)."""
    rows = []
    for spec, widgets, why in _placed(index):
        producer = f"derived:{spec['rule']}" if spec["rule"] else f"asked:{spec['binding']}"
        rows.append(
            {
                "schema": FORM_TYPE,
                "pdf_field": spec["pdf_field"],
                "producer": producer,
                "original_verdicts": [],
                "final_verdicts": ["correct"],
                "status": "confirmed",
                "correct_target": spec["pdf_field"],
                "evidence": _evidence(spec, widgets, why, index),
            }
        )
    return rows


def owned(row):
    return row["schema"] == FORM_TYPE


def merged(existing, ours):
    """existing with our rows put at the first Supp row's place; with none, just after the last
    Form 122A-1 row (Ruling K), found by schema; with neither, before the first List of Creditors
    row (its tool rewrites its rows at the end), else at the end."""
    at = next((i for i, r in enumerate(existing) if owned(r)), None)
    if at is None:
        last_122a1 = [i for i, r in enumerate(existing) if r["schema"] == "form_122a1"]
        if last_122a1:
            at = last_122a1[-1] + 1
        else:
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


def load_index():
    return json.loads((INDEX_DIR / f"{Path(TEMPLATE).stem}.index.json").read_text())


def build():
    """(the schema, the addendum rows it owns), reading only the repo."""
    index = load_index()
    sha256 = hashlib.sha256((PDFS / TEMPLATE).read_bytes()).hexdigest()
    return schema(index, sha256), addendum_rows(index)


def main():
    built, rows = build()
    (SCHEMAS_DIR / f"{FORM_TYPE}.json").write_text(dumps(built))
    ADDENDUM.write_text(merged_text(ADDENDUM.read_text(), rows))
    print(f"bindings for {FORM_TYPE}: {len(built['fields'])}; addendum rows: {len(rows)}")


if __name__ == "__main__":
    main()
