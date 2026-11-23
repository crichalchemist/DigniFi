"""
Writes the caps on the filer's Schedule I and Schedule J texts, `schedule_i.limits.json` (forms
step 4c, Ruling 4c-R8). Run it with the backend's Python, the one with the backend's
requirements installed, since the caps are measured with the filler's own text_fit. From the
repo root:

    python data/forms/field_index/tools/build_schedule_i_limits.py

It puts `backend/` on the path and sets up Django itself (`config.settings.test` unless
DJANGO_SETTINGS_MODULE names another), so it needs no database. It does need the backend's
environment (the secret key and the field encryption key the test settings read, as for
pytest) set before it runs. The backend imports `schedule_i.limits.json` at start-up, so the
tool can't bootstrap its own output: a missing or broken `schedule_i.limits.json` is restored
from git, never rebuilt by hand.

Never hand-edit `schedule_i.limits.json`: change this tool and run it again.
`test_the_caps_are_measured_on_schedule_i_and_j_boxes` fails on any difference.

Each text is measured on its narrowest box. Line 1's boxes come in two columns, Debtor 1's and
Debtor 2's, so each of its texts is measured on both and takes the narrower; the filer's key and
the spouse's twin share that cap. A box is named by its page and index tag (the two columns'
boxes share their index labels, and the two tenure boxes share a full name too), and the tool
checks the index's full name for it, exiting on zero or two rows.

- A single-line box takes as many of the widest of the key's measuring letters as fit its inner
  width at 6 pt, and never more than its own /MaxLen (`build_form_101a.py`'s `limits()`).
- A multi-line box (line 13's explanation, Schedule J line 24's) takes half its lines' worth:
  floor(lines / 2 × inner width / widest), the venue reason's rule (`build_form_101.py`), with
  lines = floor((height − 2 × margin) / (6 pt × the font's leading)), the line count `fit()`
  allows, so the tool counts what `check()` refuses. Words break at spaces, so any two lines
  together are wider than one line; half the lines' worth keeps every capped text inside the
  box however its words break, while no single word is wider than a line.

Like the other schema tools it copies `dumps()`, `_setup_django()` and the measuring letters
(`build_form_101a.py`) rather than importing them: the tools folder isn't a package.
"""

import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INDEX_DIR = ROOT / "data" / "forms" / "field_index"
SCHEMAS_DIR = ROOT / "data" / "forms" / "schemas"

SCHEDULE_I = "form_b106i.pdf"
SCHEDULE_J = "form_b106j.pdf"

# The boxes a text prints in, each (template, page, index tag, full name): the narrowest
# sets the cap.
OCCUPATION = [
    (SCHEDULE_I, 1, "T12", "Occupation Debtor 1"),
    (SCHEDULE_I, 1, "T13", "Occupation Debtor 2"),
]
EMPLOYER_NAME = [
    (SCHEDULE_I, 1, "T14", "Employers Name Debtor 1"),
    (SCHEDULE_I, 1, "T15", "Employers Name Debtor 2"),
]
EMPLOYER_STREET = [
    (SCHEDULE_I, 1, "T16", "Employers Street1 Debtor 1"),
    (SCHEDULE_I, 1, "T17", "Employers Street1 Debtor 2"),
]
EMPLOYER_STREET_2 = [
    (SCHEDULE_I, 1, "T18", "Employers Street2 Debtor 1"),
    (SCHEDULE_I, 1, "T19", "Employers Street2 Debtor 2"),
]
EMPLOYER_CITY = [
    (SCHEDULE_I, 1, "T22", "Employers City Debtor 1"),
    (SCHEDULE_I, 1, "T25", "Employers City Debtor 2"),
]
EMPLOYER_STATE = [
    (SCHEDULE_I, 1, "T23", "Employers State Debtor 1"),
    (SCHEDULE_I, 1, "T26", "Employers State Debtor 2"),
]
EMPLOYER_ZIP = [
    (SCHEDULE_I, 1, "T24", "Employers Zip debtor 1"),
    (SCHEDULE_I, 1, "T27", "Employers Zip debtor 2"),
]
TIME_EMPLOYED = [
    (SCHEDULE_I, 1, "T28", "Time employed Debtor 1"),
    (SCHEDULE_I, 1, "T29", "Time employed Debtor 1"),
]

# The filer's line 1 texts: key, boxes, the box in plain words for the too-long line (W18).
LINE_1 = [
    ("occupation", OCCUPATION, "Occupation"),
    ("employer_name", EMPLOYER_NAME, "Employer's name"),
    ("employer_street", EMPLOYER_STREET, "Employer's address"),
    ("employer_street_2", EMPLOYER_STREET_2, "Employer's address, line 2"),
    ("employer_city", EMPLOYER_CITY, "Employer's city"),
    ("employer_state", EMPLOYER_STATE, "Employer's state"),
    ("employer_zip", EMPLOYER_ZIP, "Employer's ZIP Code"),
    ("time_employed", TIME_EMPLOYED, "How long employed there"),
]

# The spouse's tenure label isn't the prefix rule's (Ruling PF-4c-E).
SPOUSE_LABELS = {"time_employed": "How long your spouse has been employed there"}

LINES = [
    (
        "line_11_text",
        [(SCHEDULE_I, 2, "T49", "Assistance 8f")],
        "Line 11, Specify",
    ),
    (
        "line_13_text",
        [(SCHEDULE_I, 2, "T53", "Increase/Decrease 13")],
        "Line 13, Explain",
    ),
    (
        "schedule_j_line_24_text",
        [(SCHEDULE_J, 3, "T12", "Other 24")],
        "Line 24, Explain",
    ),
]


def spouse_label(key, label):
    """The spouse's twin of a line 1 label: "Your spouse's " and the label, first letter small."""
    return SPOUSE_LABELS.get(key, f"Your spouse's {label[0].lower()}{label[1:]}")


def limited():
    """Every text key with its boxes and its label, in the record's order."""
    return [
        *LINE_1,
        *[(f"spouse_{key}", boxes, spouse_label(key, label)) for key, boxes, label in LINE_1],
        *LINES,
    ]


# Measuring letters, as build_form_101a.py: a ZIP's digits and hyphen, a state's capitals,
# digits for every other text.
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


def _row(index, page, tag, full_name):
    """The index row at page and tag, which must carry full_name."""
    found = [row for row in index if (row["page"], row["tag"]) == (page, tag)]
    if len(found) != 1 or found[0]["full_name"] != full_name:
        sys.exit(f"{len(found)} index rows at page {page} {tag} named {full_name!r}")
    return found[0]


def _cap(key, template, box):
    from apps.forms.services.text_fit import MIN_SIZE, _leading, _width, font_for, reverse_cmap_for

    font = font_for(template, box.font)
    cmap = reverse_cmap_for(template, box.font)
    widest = max(_width(font, cmap, c, MIN_SIZE) for c in measuring_letters(key))
    room = box.width - 4 * box.margin
    if box.multiline:
        lines = math.floor((box.height - 2 * box.margin) / (MIN_SIZE * _leading(font)))
        return math.floor(lines / 2 * room / widest)
    cap = math.floor(room / widest)
    if box.max_len:
        cap = min(cap, box.max_len)
    return cap


def limits():
    """Each of the filer's Schedule I and J text keys → its cap on its narrowest box, and its
    words for the too-long line."""
    _setup_django()
    from apps.forms.services.widgets import template_widgets

    indexes = {
        template: json.loads((INDEX_DIR / f"{Path(template).stem}.index.json").read_text())
        for template in (SCHEDULE_I, SCHEDULE_J)
    }
    caps, labels = {}, {}
    for key, boxes, label in limited():
        measured = []
        for template, page, tag, full_name in boxes:
            row = _row(indexes[template], page, tag, full_name)
            widgets = template_widgets(template)
            (box,) = [w for w in widgets if (w.page, w.tag) == (row["page"], row["tag"])]
            measured.append(_cap(key, template, box))
        caps[key] = min(measured)
        labels[key] = label
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
    built = limits()
    (SCHEMAS_DIR / "schedule_i.limits.json").write_text(dumps(built))
    print(f"caps for {len(built['limits'])} Schedule I and J texts")


if __name__ == "__main__":
    main()
