"""
Writes the field index of the court's Form 108, Statement of Intention for Individuals Filing
Under Chapter 7 (12/15) (forms step 4e). Run it from the repo root:

    python -I data/forms/field_index/tools/build_form_108_index.py index
    python -I data/forms/field_index/tools/build_form_108_index.py render <dir>

The template is the court's own file, `form_b108.pdf`, read on 2026-11-24 from SOURCE_URL; its
sha256 is TEMPLATE_SHA256. It has 83 widgets on 2 pages, and every one has a tooltip.

`render` writes one PNG per page with every widget outlined and tagged as `index` tags it; the
PNGs are scratch and never committed. `index` reads one row per widget off the committed PDF and
takes each row's line, label, column, kind and option text from ROWS, a hand table keyed by page
and rectangle (top-left points, rounded to 1 pt) as PyMuPDF reports it, never the raw PDF /Rect
or the widget order. Several widgets share a full name (the form's Yes/No pairs and its four
intention boxes are kids of one field), so a rectangle is the only thing that names a kid. Every
widget was read by eye on the tagged render, so each row's `basis` is "adjudicated" (no vision
run), and the four push buttons are `form_control` rows. The tool exits on a widget with no row, a
row with no widget, two rows with one label, or a widget type outside TYPES, and
`test_form_108_template.py` fails on any difference between the committed index and what this
tool reads. Never hand-edit the index: change this tool and run it again.

Like `build_form_101a_index.py`, it reads only the repo and copies its helpers rather than
importing them: the tools folder isn't a package.
"""

import json
import re
import sys
from pathlib import Path

import fitz
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[4]
PDFS = ROOT / "data" / "forms" / "pdfs"
INDEX_DIR = ROOT / "data" / "forms" / "field_index"

TEMPLATE = "form_b108.pdf"
SOURCE_URL = "https://www.uscourts.gov/sites/default/files/form_b108.pdf"
TEMPLATE_SHA256 = "fe51d222d87f461b8695e3d9b7a061e768b2a75824511d167cfba736ca35e8fe"

# The index's widget types, shared with the court's other hand-adjudicated forms: each type's
# `basis`. A push button is a `form_control` row.
TYPES = {
    "Text": "adjudicated",
    "ComboBox": "adjudicated",
    "CheckBox": "adjudicated",
    "RadioButton": "adjudicated",
    "Signature": "adjudicated",
    "Button": "form_control",
}

INTENTION = {
    "surrender": ("surrender", "Surrender the property."),
    "redeem": ("retain and redeem", "Retain the property and redeem it."),
    "reaffirm": (
        "retain and reaffirm",
        "Retain the property and enter into a Reaffirmation Agreement.",
    ),
    "explain": ("retain and explain", "Retain the property and [explain]:"),
}

# Part 1's four creditor rows (line 1), a to d. Each row's boxes as PyMuPDF reports them, read on
# the tagged render. In row d the Yes box sits above the redeem box, the other way round in rows
# a to c, so the rectangles, never the order, say which is which.
PART_1 = {
    "a": {
        "surrender": (298, 413, 310, 425),
        "no": (492, 412, 504, 425),
        "name": (96, 417, 292, 431),
        "yes": (492, 426, 504, 438),
        "redeem": (298, 427, 310, 439),
        "description": (107, 436, 292, 487),
        "reaffirm": (298, 440, 310, 452),
        "explain": (298, 464, 310, 476),
        "explain_1": (430, 464, 480, 478),
        "explain_2": (311, 476, 480, 490),
    },
    "b": {
        "surrender": (298, 505, 310, 517),
        "no": (492, 504, 504, 517),
        "name": (96, 509, 292, 523),
        "yes": (492, 518, 504, 530),
        "redeem": (298, 519, 310, 531),
        "description": (107, 528, 292, 579),
        "reaffirm": (298, 532, 310, 544),
        "explain": (298, 556, 310, 568),
        "explain_1": (430, 556, 480, 570),
        "explain_2": (311, 568, 480, 582),
    },
    "c": {
        "surrender": (298, 593, 310, 605),
        "no": (492, 592, 504, 605),
        "name": (96, 597, 292, 611),
        "yes": (492, 606, 504, 618),
        "redeem": (298, 607, 310, 619),
        "description": (107, 616, 292, 667),
        "reaffirm": (298, 620, 310, 632),
        "explain": (298, 644, 310, 656),
        "explain_1": (430, 644, 480, 658),
        "explain_2": (311, 656, 480, 670),
    },
    "d": {
        "surrender": (298, 680, 310, 692),
        "no": (492, 679, 504, 692),
        "name": (96, 684, 292, 698),
        "redeem": (298, 694, 310, 706),
        "yes": (492, 693, 504, 705),
        "description": (107, 703, 292, 754),
        "reaffirm": (298, 707, 310, 719),
        "explain": (298, 731, 310, 743),
        "explain_1": (430, 731, 480, 745),
        "explain_2": (311, 743, 480, 757),
    },
}

# Part 2's seven lease rows (the page prints no line number), a to g, on page 2: lessor's name, No, Yes, description.
PART_2 = {
    "a": ((111, 154, 446, 168), (452, 155, 464, 168), (452, 169, 464, 181), (133, 173, 446, 202)),
    "b": ((111, 215, 446, 230), (452, 217, 464, 229), (452, 230, 464, 243), (133, 235, 446, 263)),
    "c": ((111, 277, 446, 291), (452, 278, 464, 291), (452, 292, 464, 304), (133, 296, 446, 325)),
    "d": ((111, 336, 446, 351), (452, 338, 464, 350), (452, 351, 464, 364), (133, 363, 446, 391)),
    "e": ((111, 405, 446, 420), (452, 407, 464, 419), (452, 420, 464, 432), (133, 428, 446, 457)),
    "f": ((111, 466, 446, 481), (452, 468, 464, 480), (452, 483, 464, 495), (133, 490, 446, 518)),
    "g": ((111, 532, 446, 547), (452, 534, 464, 546), (452, 547, 464, 559), (133, 553, 446, 582)),
}


def _build_rows():
    """ROWS, (page, rect) -> (line, label, column, kind, option_text), from the tables above."""
    rows = {
        (1, (76, 62, 333, 77)): ("", "Caption: Debtor 1's name (page 1)", "", "text", ""),
        (1, (80, 83, 329, 97)): ("", "Caption: Debtor 2's name", "", "text", ""),
        (1, (154, 107, 316, 124)): ("", "Caption: the court (district)", "", "choice", ""),
        (1, (506, 120, 518, 132)): (
            "",
            "Caption: amended filing",
            "",
            "checkbox",
            "Check if this is an amended filing",
        ),
        (1, (80, 123, 248, 138)): ("", "Caption: case number (page 1)", "", "text", ""),
        (2, (85, 34, 342, 49)): ("", "Caption: Debtor 1's name (page 2)", "", "text", ""),
        (2, (436, 34, 592, 49)): ("", "Caption: case number (page 2)", "", "text", ""),
        (2, (56, 683, 243, 697)): ("", "Part 3: Debtor 1's signature", "", "signature", ""),
        (2, (263, 683, 450, 697)): ("", "Part 3: Debtor 2's signature", "", "signature", ""),
        (2, (71, 714, 146, 729)): ("", "Part 3: Debtor 1's signing date", "", "text", ""),
        (2, (283, 714, 358, 729)): ("", "Part 3: Debtor 2's signing date", "", "text", ""),
        (2, (31, 774, 133, 791)): ("", "Print", "", "other", ""),
        (2, (143, 774, 244, 791)): ("", "Save As...", "", "other", ""),
        (2, (252, 774, 354, 791)): ("", "Add Attachment", "", "other", ""),
        (2, (479, 774, 580, 791)): ("", "Reset", "", "other", ""),
    }
    for letter, boxes in PART_1.items():
        row = f"Part 1, row {letter}: "
        rows[(1, boxes["name"])] = ("1", row + "creditor's name", "", "text", "")
        rows[(1, boxes["description"])] = (
            "1",
            row + "description of property securing the debt",
            "",
            "text",
            "",
        )
        for key, (words, option) in INTENTION.items():
            rows[(1, boxes[key])] = ("1", row + f"intention, {words}", "", "checkbox", option)
        rows[(1, boxes["explain_1"])] = ("1", row + "explanation, first box", "", "text", "")
        rows[(1, boxes["explain_2"])] = ("1", row + "explanation, second box", "", "text", "")
        for key, answer in (("no", "No"), ("yes", "Yes")):
            rows[(1, boxes[key])] = (
                "1",
                row + f"claimed as exempt on Schedule C, {answer}",
                "",
                "checkbox",
                answer,
            )
    for letter, (name, no, yes, description) in PART_2.items():
        row = f"Part 2, row {letter}: "
        rows[(2, name)] = ("", row + "lessor's name", "", "text", "")
        rows[(2, no)] = ("", row + "will the lease be assumed, No", "", "checkbox", "No")
        rows[(2, yes)] = ("", row + "will the lease be assumed, Yes", "", "checkbox", "Yes")
        rows[(2, description)] = ("", row + "description of leased property", "", "text", "")
    return rows


ROWS = _build_rows()


def _key(page, rect):
    return (page, tuple(round(v) for v in rect))


def _in_reading_order(page):
    """The page's widgets in reading order, the order their tags T1, T2, ... count."""
    return sorted(page.widgets(), key=lambda w: (round(w.rect.y0 / 4), w.rect.x0))


def index_rows(template):
    """One index row per widget of the template, tagged in reading order on each page."""
    reader = PdfReader(template)
    tooltips = {}
    for number, page in enumerate(reader.pages, start=1):
        for annot in page.get("/Annots") or []:
            node = annot.get_object()
            while "/TU" not in node and "/Parent" in node:
                node = node["/Parent"].get_object()
            tooltips[(number, annot.idnum)] = str(node.get("/TU", ""))

    rows, seen = [], set()
    with fitz.open(template) as doc:
        for number, page in enumerate(doc, start=1):
            for i, w in enumerate(_in_reading_order(page), start=1):
                kind_of_widget = w.field_type_string
                if kind_of_widget not in TYPES:
                    raise SystemExit(f"unexpected {kind_of_widget} box {w.field_name!r}")
                key = _key(number, w.rect)
                if key not in ROWS:
                    raise SystemExit(f"no row for the widget {w.field_name!r} at {key}")
                seen.add(key)
                line, label, column, kind, option = ROWS[key]
                boxed = kind_of_widget in ("CheckBox", "RadioButton")
                rows.append(
                    {
                        "full_name": w.field_name,
                        "page": number,
                        "tag": f"T{i}",
                        "rect": [round(v, 1) for v in w.rect],
                        "type": kind_of_widget,
                        "on_state": w.on_state() if boxed else None,
                        "tooltip": tooltips.get((number, w.xref), "").strip(),
                        "line": line,
                        "label": label,
                        "column": column,
                        "kind": kind,
                        "option_text": option,
                        "basis": TYPES[kind_of_widget],
                    }
                )
    unused = sorted(set(ROWS) - seen)
    if unused:
        raise SystemExit(f"rows with no widget: {unused}")
    labels = [row["label"] for row in rows]
    repeated = sorted({label for label in labels if labels.count(label) > 1})
    if repeated:
        raise SystemExit(f"labels on more than one row: {repeated}")
    return rows


def render_tagged(template, out_dir):
    """One PNG per page, every widget outlined in red and tagged as `index_rows` tags it."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with fitz.open(template) as doc:
        for number, page in enumerate(doc, start=1):
            tagged = [(f"T{i}", w.rect) for i, w in enumerate(_in_reading_order(page), start=1)]
            for tag, rect in tagged:
                page.draw_rect(rect, color=(1, 0, 0), width=0.6)
                page.insert_text((rect.x0 + 0.5, rect.y0 + 5), tag, fontsize=5, color=(0, 0, 1))
            path = out_dir / f"page-{number}.png"
            page.get_pixmap(dpi=144).save(path)
            written.append(path)
    return written


_SCALAR_ARRAY = re.compile(
    r'^( *(?:"[^"\n]*": )?)\[\n((?: *(?:"(?:[^"\\\n]|\\.)*"|-?\d+(?:\.\d+)?),?\n)+) *\](,?)$',
    re.M,
)


def _on_one_line(match):
    items = [item.strip().rstrip(",") for item in match[2].splitlines()]
    line = f"{match[1]}[{', '.join(items)}]{match[3]}"
    return line if len(line) <= 80 else match[0]


def dumps(data):
    """json.dumps as prettier writes it: a short list of scalars on one line."""
    return _SCALAR_ARRAY.sub(_on_one_line, json.dumps(data, indent=2, ensure_ascii=False)) + "\n"


def main(argv):
    usage = "usage: build_form_108_index.py index | render <dir>"
    if argv == ["index"]:
        rows = index_rows(PDFS / TEMPLATE)
        path = INDEX_DIR / f"{Path(TEMPLATE).stem}.index.json"
        path.write_text(dumps(rows))
        print(f"wrote {path}: {len(rows)} rows")
    elif argv[:1] == ["render"] and len(argv) == 2:
        for path in render_tagged(PDFS / TEMPLATE, argv[1]):
            print(f"wrote {path}")
    else:
        raise SystemExit(usage)


if __name__ == "__main__":
    main(sys.argv[1:])
