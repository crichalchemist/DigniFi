"""Prototype field index: each widget in an AO template with its page, rect,
tooltip and the printed text on the same row. Read-only.

usage: field_index.py <template.pdf> <out.json>
"""

import json
import logging
import sys

import pypdf

logging.disable(logging.CRITICAL)


def text_runs(page):
    runs = []

    def visit(text, cm, tm, font_dict, font_size):
        if not text.strip():
            return
        # pypdf gives the text matrix; combine with the CTM for page coordinates
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        runs.append({"x": round(x, 1), "y": round(y, 1), "text": text.strip()})

    page.extract_text(visitor_text=visit)
    return runs


def widgets(page):
    annots = page.get("/Annots")
    annots = annots.get_object() if annots is not None else []
    for a in annots:
        a = a.get_object()
        if a.get("/Subtype") != "/Widget":
            continue
        # the field is the widget itself when it carries /T, else its parent
        field = a if "/T" in a else a["/Parent"].get_object()
        parts, node = [], field
        while node is not None:
            if "/T" in node:
                parts.append(str(node["/T"]))
            node = node["/Parent"].get_object() if node.get("/Parent") is not None else None
        qualified = ".".join(reversed(parts))
        tu = a.get("/TU") or field.get("/TU")
        ft = a.get("/FT") or field.get("/FT")
        rect = [round(float(v), 1) for v in a["/Rect"]]
        yield qualified, str(field["/T"]), str(tu or "").strip(), str(ft or ""), rect


def build(path):
    reader = pypdf.PdfReader(path)
    out = []
    for pi, page in enumerate(reader.pages, start=1):
        runs = text_runs(page)
        for name, partial, tu, ft, (x0, y0, x1, y1) in widgets(page):
            lo, hi = min(y0, y1) - 3, max(y0, y1) + 3
            row = sorted((r for r in runs if lo <= r["y"] <= hi), key=lambda r: r["x"])
            out.append(
                {
                    "page": pi,
                    "name": name,
                    "partial": partial,
                    "type": ft,
                    "rect": [x0, y0, x1, y1],
                    "tooltip": tu,
                    "row_text": " | ".join(r["text"] for r in row)[:300],
                }
            )
    return out


if __name__ == "__main__":
    data = build(sys.argv[1])
    with open(sys.argv[2], "w") as fh:
        json.dump(data, fh, indent=1)
    print(len(data), "widgets ->", sys.argv[2])
