"""
Writes the court's List of Creditors template and its field index (forms step 3c6, R1 and R2).
Run it from the repo root:

    python -I data/forms/field_index/tools/build_list_of_creditors.py extract <bundle.pdf>
    python -I data/forms/field_index/tools/build_list_of_creditors.py index
    python -I data/forms/field_index/tools/build_list_of_creditors.py schema

The template is pages 12-13 of the Northern District of Illinois's pro se bundle, "Required
Documents for a Chapter 7 filing" (page 1: "Last Updated: January 3, 2025"), whose source URL is
https://www.ilnb.uscourts.gov/sites/ilnb/files/RequiredDocsCh72025January3.pdf
The court's site turns scripts away, so the bundle is the owner's accepted copy; `extract` refuses
any file whose sha256 is not BUNDLE_SHA256. The bundle is never committed.

`extract` appends the two pages with pypdf (which keeps every field's full name; PyMuPDF's
`insert_pdf` renames them), prunes /AcroForm /Fields to the nodes with a widget on those pages and
saves through PyMuPDF with `no_new_id=True`, so two runs write the same bytes. The committed
PDF's sha256 is its `template_version`.

`index` reads one row per widget off the committed PDF. Every box was read against the bundle and
rendered by hand, so each row's `basis` is "adjudicated" (the tool writes that as a constant, and
`test_list_of_creditors_template.py` fails on any difference between the committed index and
what this tool reads). Never hand-edit the index: change this tool and run it again.

Like `build_claims_schedules.py`, it reads only the repo and copies `dumps()` rather than importing
it: the tools folder isn't a package.
"""

import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

import fitz
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject

ROOT = Path(__file__).resolve().parents[4]
PDFS = ROOT / "data" / "forms" / "pdfs"
INDEX_DIR = ROOT / "data" / "forms" / "field_index"

TEMPLATE = "ilnb_list_of_creditors.pdf"
BUNDLE_SHA256 = "24edcd3bfd03af96f9d07662205ce91315fb0c3d640c3a47e5965da5de72167e"
PAGES = (11, 13)  # pypdf's half-open range: bundle pages 12 and 13

# R2: the label each box's printed words give it (full name -> index label).
LABELS = {
    "Debtor1.Name": "Debtor 1's name",
    "Debtor2.Name": "Debtor 2's name",
    "Case number1": "Case number",
    "chapter": "Chapter",
    "Debtor1andDebtor2": "Debtor 1 (label)",
}
CREDITOR_LABEL = "Creditor's name and address"


def _label(full_name):
    if full_name in LABELS:
        return LABELS[full_name]
    if full_name.startswith("creditor"):
        return CREDITOR_LABEL
    raise SystemExit(f"no label for the box {full_name!r}")


def extract(bundle, out):
    """Write bundle pages 12-13 to `out`, their fields pruned to the widgets on them (R1)."""
    digest = hashlib.sha256(Path(bundle).read_bytes()).hexdigest()
    if digest != BUNDLE_SHA256:
        raise SystemExit(f"the bundle's sha256 is {digest}, not {BUNDLE_SHA256}")

    writer = PdfWriter()
    writer.append(str(bundle), pages=PAGES)
    on_pages = set()
    for page in writer.pages:
        for annot in page.get("/Annots", []) or []:
            on_pages.add(annot.idnum)

    def keep(ref):
        """Prune a field node to the widgets on these pages; False when none remain."""
        node = ref.get_object()
        kids = node.get("/Kids")
        if kids is None:
            return ref.idnum in on_pages
        survivors = ArrayObject(k for k in kids if keep(k))
        if not survivors:
            return False
        node[NameObject("/Kids")] = survivors
        return True

    acro = writer._root_object["/AcroForm"].get_object()
    acro[NameObject("/Fields")] = ArrayObject(f for f in acro["/Fields"] if keep(f))
    writer.compress_identical_objects(remove_identicals=False, remove_orphans=True)

    with tempfile.TemporaryDirectory() as scratch:
        pruned = Path(scratch) / "pruned.pdf"
        writer.write(pruned)
        doc = fitz.open(pruned)
        doc.save(out, garbage=4, deflate=True, clean=False, no_new_id=True)
        doc.close()


def index_rows(template):
    """One index row per widget of the template, tagged in reading order on each page (R2)."""
    reader = PdfReader(template)
    tooltips = {}
    for number, page in enumerate(reader.pages, start=1):
        for annot in page.get("/Annots") or []:
            annotation = annot.get_object()
            node = annotation
            while "/TU" not in node and "/Parent" in node:
                node = node["/Parent"].get_object()
            tooltips[(number, annot.idnum)] = str(node.get("/TU", ""))

    rows = []
    with fitz.open(template) as doc:
        for number, page in enumerate(doc, start=1):
            found = []
            for w in page.widgets():
                kind = {"Text": "text", "ComboBox": "choice"}.get(w.field_type_string)
                if kind is None:
                    raise SystemExit(
                        f"unexpected {w.field_type_string} box {w.field_name!r}"
                    )
                found.append(
                    {
                        "full_name": w.field_name,
                        "page": number,
                        "rect": [round(v, 1) for v in w.rect],
                        "type": w.field_type_string,
                        "tooltip": tooltips.get((number, w.xref), "").strip(),
                        "kind": kind,
                    }
                )
            found.sort(key=lambda d: (round(d["rect"][1] / 4), d["rect"][0]))
            for i, d in enumerate(found, start=1):
                rows.append(
                    {
                        "full_name": d["full_name"],
                        "page": d["page"],
                        "tag": f"T{i}",
                        "rect": d["rect"],
                        "type": d["type"],
                        "on_state": None,
                        "tooltip": d["tooltip"],
                        "line": "",
                        "label": _label(d["full_name"]),
                        "column": "",
                        "kind": d["kind"],
                        "option_text": "",
                        "basis": "adjudicated",
                    }
                )
    return rows


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
    return (
        _SCALAR_ARRAY.sub(_on_one_line, json.dumps(data, indent=2, ensure_ascii=False))
        + "\n"
    )


SCHEMA_NAME = "list_of_creditors"
ENTRY_BINDING = "claims.creditor_list[].entry"
# R7: the 30 slots, column by column: rows 1-5 left then 6-10 right on page 1, then 11-20 left
# and 21-30 right on page 2.
SLOT_NAMES = (
    [f"creditor1.0.{i}" for i in range(5)]
    + [f"creditor2.0.{i}" for i in range(5)]
    + [f"creditor1.0.5.{i}" for i in range(10)]
    + [f"creditor2.0.5.{i}" for i in range(10)]
)
SLOT_LABEL = "Name and address"
ADDENDUM = INDEX_DIR / "audit" / "step2_verification.json"
SCHEMAS_DIR = ROOT / "data" / "forms" / "schemas"


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


def schema(rows, template_sha256):
    """The List of Creditors' schema (R4, R7), keys in schedule_g.json's order."""
    page_of = {r["full_name"]: r["page"] for r in rows}
    fields = [
        _field(
            "Debtor1.Name", "text", "derived", 1, "Debtor 1's name", rule="full_name"
        ),
        _field("chapter", "choice", "constant", 1, "Chapter", value="7"),
    ]
    for row, name in enumerate(SLOT_NAMES, start=1):
        fields.append(
            _field(
                name,
                "text",
                "asked",
                page_of[name],
                SLOT_LABEL,
                binding=ENTRY_BINDING,
                repeat="creditors",
                repeat_capacity=len(SLOT_NAMES),
                row=row,
            )
        )
    return {
        "form_type": SCHEMA_NAME,
        "template_filename": TEMPLATE,
        "template_version": template_sha256,
        "groups": {"creditors": {"extra_page": 2}},
        "fields": fields,
    }


def addendum_rows(index):
    """The 32 audit rows that place the form's bindings (R4, R7), shaped as 3c5's rows."""
    where = {r["full_name"]: (r["page"], r["tag"]) for r in index}
    rows = [
        {
            "schema": SCHEMA_NAME,
            "pdf_field": "Debtor1.Name",
            "producer": "derived:full_name",
            "original_verdicts": [],
            "final_verdicts": ["correct"],
            "status": "confirmed",
            "correct_target": "Debtor1.Name",
            "evidence": (
                'Field index: Debtor1.Name p1 T1 and p2 T2, "Debtor 1\'s name" (adjudicated): one '
                "untagged binding prints both pages' boxes. R4: the list's header prints the "
                "filer's full name, as Schedules G and H do."
            ),
        },
        {
            "schema": SCHEMA_NAME,
            "pdf_field": "chapter",
            "producer": "constant:7",
            "original_verdicts": [],
            "final_verdicts": ["correct"],
            "status": "confirmed",
            "correct_target": "chapter",
            "evidence": (
                'Field index: chapter p1 T4, "Chapter" (adjudicated), a combo box whose options '
                "are ' ', '7', '13' and '11'. R4: every DigniFi filer files under chapter 7."
            ),
        },
    ]
    for row, name in enumerate(SLOT_NAMES, start=1):
        page, tag = where[name]
        rows.append(
            {
                "schema": SCHEMA_NAME,
                "pdf_field": name,
                "producer": f"asked:{ENTRY_BINDING}",
                "original_verdicts": [],
                "final_verdicts": ["correct"],
                "status": "confirmed",
                "correct_target": name,
                "evidence": (
                    f'Field index: {name} p{page} {tag}, "{CREDITOR_LABEL}" (adjudicated). '
                    f"R7: row {row} of group creditors prints entry {row} of {ENTRY_BINDING} here, in the "
                    "court's column-by-column order."
                ),
            }
        )
    return rows


def write_schema():
    template = PDFS / TEMPLATE
    index_path = INDEX_DIR / f"{Path(TEMPLATE).stem}.index.json"
    rows = json.loads(index_path.read_text())
    digest = hashlib.sha256(template.read_bytes()).hexdigest()
    path = SCHEMAS_DIR / f"{SCHEMA_NAME}.json"
    path.write_text(dumps(schema(rows, digest)))
    existing = json.loads(ADDENDUM.read_text())
    kept = [r for r in existing if r["schema"] != SCHEMA_NAME]
    new = addendum_rows(rows)
    ADDENDUM.write_text(dumps(kept + new))
    print(f"wrote {path} and {len(new)} rows of {ADDENDUM}")


def main(argv):
    usage = "usage: build_list_of_creditors.py extract <bundle.pdf> | index | schema"
    if argv[:1] == ["extract"] and len(argv) == 2:
        out = PDFS / TEMPLATE
        extract(Path(argv[1]), out)
        print(f"wrote {out}: sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
    elif argv == ["index"]:
        rows = index_rows(PDFS / TEMPLATE)
        path = INDEX_DIR / f"{Path(TEMPLATE).stem}.index.json"
        path.write_text(dumps(rows))
        print(f"wrote {path}: {len(rows)} rows")
    elif argv == ["schema"]:
        write_schema()
    else:
        raise SystemExit(usage)


if __name__ == "__main__":
    main(sys.argv[1:])
