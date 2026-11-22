"""
Writes the field index of the court's older fillable Form 101A, Initial Statement About an
Eviction Judgment Against You (12/15) (forms step 4b2, owner choice B57). Run it from the repo
root:

    python -I data/forms/field_index/tools/build_form_101a_index.py index
    python -I data/forms/field_index/tools/build_form_101a_index.py render <dir>

The template is the court's own file, copied byte for byte from the file downloaded on
2026-11-18 from SOURCE_URL; its sha256 is TEMPLATE_SHA256. `form_b101a_0.pdf`, the current
publication, has no fillable boxes and stays beside it.

`render` writes one PNG per page with every widget outlined and tagged as `index` tags it; the
PNGs are scratch and never committed. `index` reads one row per widget off the committed PDF and
takes each row's line, label, column, kind and option text from ROWS, a hand table keyed by page
and rectangle (top-left points, rounded to 1 pt) as PyMuPDF reports it, never the raw PDF /Rect
(`Name of landlord` and `Date` are inverted there). Every widget was read by eye on the tagged
render, so each row's `basis` is "adjudicated" (no vision run), and the three push buttons are
`form_control` rows. The tool exits on a widget with no row, a row with no widget, two rows with
one label, or a widget type outside TYPES, and `test_form_101a_template.py` fails on any
difference between the committed index and what this tool reads. Never hand-edit the index:
change this tool and run it again.

Like `build_form_101_index.py`, it reads only the repo and copies its helpers rather than
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

TEMPLATE = "form_b101a_fillable.pdf"
SOURCE_URL = "https://www.uscourts.gov/sites/default/files/form_b101a.pdf"
TEMPLATE_SHA256 = "4c79ea2730408b7bbc28a22a86e3698187f960eb5d97d11be4b671cdf62c327b"

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

# (page, (x0, y0, x1, y1) from the page's top left, rounded to 1 pt)
#     -> (line, label, column, kind, option_text)
# Each row was read on the tagged render (`render`). The two signature boxes are text widgets in
# this template, so their kind says what they are.
ROWS = {
    (1, (87, 56, 344, 70)): ("", "Caption: Debtor 1's name", "", "text", ""),
    (1, (87, 76, 344, 90)): ("", "Caption: Debtor 2's name", "", "text", ""),
    (1, (166, 102, 328, 119)): ("", "Caption: the court (district)", "", "choice", ""),
    (1, (88, 121, 259, 135)): ("", "Caption: case number", "", "text", ""),
    (1, (131, 281, 354, 295)): ("", "Landlord's name", "", "text", ""),
    (1, (130, 303, 354, 317)): ("", "Landlord's address: number and street", "", "text", ""),
    (1, (131, 326, 254, 340)): ("", "Landlord's address: city", "", "text", ""),
    (1, (264, 326, 291, 340)): ("", "Landlord's address: state", "", "text", ""),
    (1, (307, 326, 356, 340)): ("", "Landlord's address: ZIP code", "", "text", ""),
    (1, (65, 435, 77, 447)): (
        "",
        "Certification box 1: the state-law right to stay by paying the delinquent amount "
        '(on state "No"; its tooltip is copied from Form 101)',
        "",
        "checkbox",
        "",
    ),
    (1, (65, 467, 77, 479)): (
        "",
        "Certification box 2: the rent deposit given to the clerk "
        '(on state "Yes"; its tooltip is copied from Form 101)',
        "",
        "checkbox",
        "",
    ),
    (1, (99, 506, 295, 520)): ("", "Debtor 1's signature", "", "signature", ""),
    (1, (116, 546, 192, 560)): ("", "Debtor 1's signing date", "", "text", ""),
    (1, (360, 506, 556, 520)): ("", "Debtor 2's signature", "", "signature", ""),
    (1, (377, 546, 453, 560)): ("", "Debtor 2's signing date", "", "text", ""),
    (1, (31, 764, 133, 781)): ("", "Print", "", "other", ""),
    (1, (143, 764, 244, 781)): ("", "Save As...", "", "other", ""),
    (1, (479, 764, 580, 781)): ("", "Reset", "", "other", ""),
}


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
    usage = "usage: build_form_101a_index.py index | render <dir>"
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
