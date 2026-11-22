"""
Writes Form 101A (12/15)'s schema and the caps on the landlord's text (forms step 4b2, R1).
Form 101A is the court's older fillable template, `form_b101a_fillable.pdf`, whose index is
`form_b101a_fillable.index.json`. Run it with the backend's Python, the one with
the backend's requirements installed, since the caps are measured with the filler's own text_fit.
From the repo root:

    python data/forms/field_index/tools/build_form_101a.py

It puts `backend/` on the path and sets up Django itself (`config.settings.test` unless
DJANGO_SETTINGS_MODULE names another), so it needs no database and no other setup. In this repo
run it through the backend settings (`py.sh ../data/forms/field_index/tools/build_form_101a.py`),
because the backend imports `form_101a.limits.json` at start-up: a missing or overlapping
`form_101a.limits.json` is restored from git, never rebuilt by hand (PF-4b2-8).

Never hand-edit `form_101a.json` or `form_101a.limits.json`: change this tool and run it again.
`test_the_schema_and_its_caps_are_what_the_tool_writes` fails on any difference.

The table is keyed by the index label: the tool looks the box's full name and page up in the
committed index by that label, exiting on zero or two matches. Seven boxes are bound. The
certification boxes, the signatures, the dates, Debtor 2 and the case number stay unbound: DigniFi
prints no No the filer didn't give and ticks nothing sworn.

Like the other schema tools it copies `dumps()` and the cap formula (`build_form_101.py`'s
`limits()`) rather than importing them: the tools folder isn't a package. One line is added: a
box's own /MaxLen caps the formula (a two-capital state box 27 pt wide measures 4, but refuses a
third character).
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

FORM_TYPE = "form_101a"
TEMPLATE = "form_b101a_fillable.pdf"

# label -> (type, source, rule or binding)
BINDINGS = {
    "Caption: Debtor 1's name": ("text", "derived", "full_name"),
    "Caption: the court (district)": ("choice", "derived", "district_name"),
    "Landlord's name": ("text", "asked", "petition.landlord_name"),
    "Landlord's address: number and street": ("text", "asked", "petition.landlord_street"),
    "Landlord's address: city": ("text", "asked", "petition.landlord_city"),
    "Landlord's address: state": ("text", "asked", "petition.landlord_state"),
    "Landlord's address: ZIP code": ("text", "asked", "petition.landlord_zip"),
}

# The filer's landlord texts: key, the box's index label, the box in plain words for
# DETAIL_TOO_LONG_101A.
LIMITED = [
    ("landlord_name", "Landlord's name", "the landlord's name"),
    ("landlord_street", "Landlord's address: number and street", "the landlord's street"),
    ("landlord_city", "Landlord's address: city", "the landlord's city"),
    ("landlord_state", "Landlord's address: state", "the landlord's state"),
    ("landlord_zip", "Landlord's address: ZIP code", "the landlord's ZIP code"),
]

# Measuring letters, as build_form_101.py: a ZIP's digits and hyphen, a state's capitals, digits
# for every other text.
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


def _by_label(index, label):
    found = [row for row in index if row["label"] == label]
    if len(found) != 1:
        sys.exit(f"{len(found)} index rows labelled {label!r}")
    return found[0]


def _field(pdf_field, kind, source, page, label, **over):
    """A schema field with every key Schedule G's fields have, in their order."""
    field = {
        "pdf_field": pdf_field,
        "type": kind,
        "source": source,
        "page": page,
        "label": label,
        "required": False,
        "conditional_on": None,
        "value": None,
        "rule": None,
        "ingest_key": None,
        "binding": None,
        "repeat": None,
        "repeat_capacity": None,
        "row": None,
        "legal_review": False,
    }
    return field | over


def schema(index, template_sha256):
    """Form 101A's schema: seven bindings, no groups (the packet gates the whole form)."""
    fields = []
    for label, (kind, source, target) in BINDINGS.items():
        row = _by_label(index, label)
        over = {"rule": target} if source == "derived" else {"binding": target}
        fields.append(_field(row["full_name"], kind, source, row["page"], label, **over))
    return {
        "form_type": FORM_TYPE,
        "template_filename": TEMPLATE,
        "template_version": template_sha256,
        "groups": {},
        "fields": fields,
    }


ADDENDUM = INDEX_DIR / "audit" / "step2_verification.json"


def _producer(label):
    kind, source, target = BINDINGS[label]
    return f"{source}:{target}"


def addendum_rows(index):
    """One confirmed addendum row a binding, keyed by (box, the whole binding key)."""
    rows = []
    for label in BINDINGS:
        row = _by_label(index, label)
        rows.append(
            {
                "schema": FORM_TYPE,
                "pdf_field": row["full_name"],
                "producer": _producer(label),
                "original_verdicts": [],
                "final_verdicts": ["correct"],
                "status": "confirmed",
                "correct_target": row["full_name"],
                "evidence": (
                    f"Field index: {row['full_name']} p{row['page']} {row['tag']}, "
                    f"{label!r} ({row['basis']}). Printed from the filer's own answer; "
                    "Form 101A's certification boxes stay unbound. "
                    "Read by test_form_101a_schema.py and tier 1."
                ),
            }
        )
    return rows


def owned(row):
    return row["schema"] == FORM_TYPE


def merged(existing, ours):
    """existing with our rows put at the first Form 101A row's place; with none, just before
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


def limits(index):
    """
    Each landlord text key → as many of the widest of its measuring letters as fit its box's
    inner width at 6 pt, and never more than the box's own /MaxLen.
    """
    _setup_django()
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
        cap = math.floor((box.width - 4 * box.margin) / widest)
        if box.max_len:
            cap = min(cap, box.max_len)
        caps[key] = cap
        labels[key] = words
    return {"limits": caps, "labels": labels}


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


def _setup_django():
    import django
    from django.conf import settings

    if not settings.configured:
        sys.path.insert(0, str(ROOT / "backend"))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
        django.setup()


def main():
    index = json.loads((INDEX_DIR / f"{Path(TEMPLATE).stem}.index.json").read_text())
    sha256 = hashlib.sha256((PDFS / TEMPLATE).read_bytes()).hexdigest()
    built = schema(index, sha256)
    (SCHEMAS_DIR / f"{FORM_TYPE}.json").write_text(dumps(built))
    (SCHEMAS_DIR / f"{FORM_TYPE}.limits.json").write_text(dumps(limits(index)))
    rows = addendum_rows(index)
    ADDENDUM.write_text(merged_text(ADDENDUM.read_text(), rows))
    print(f"bindings for {FORM_TYPE}: {len(built['fields'])}; addendum rows: {len(rows)}")


if __name__ == "__main__":
    main()
