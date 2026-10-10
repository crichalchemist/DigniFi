"""Cross-check the vision index against the PDF text layer.

For each widget, derive a line number from the text layer alone:
  1. the nearest line-number token on the same row, left of the box
     (Schedule J style "4a. $____"); else
  2. the last line-number token in the left margin above the box.
Compare it with the vision answer. Checkboxes are also checked against
their own on-state (yes/no) where the template names it.

usage: ocr_crosscheck.py <ocr_dir> <pdf_dir> <out.json>
"""

import json
import pathlib
import re
import sys

import fitz

LINE_TOKEN = re.compile(r"^(\d{1,2}(?:[a-hA-H]|\.\d{1,2})?)(\.?)$")


def norm_line(s):
    s = (s or "").strip().lower()
    s = re.sub(r"^(line|item|part \d+,? line)\s*", "", s)
    s = s.strip(" .:")
    return s


GENERIC_TIPS = {"", "amount", "check", "total amount", "total", "date", "name", "text", "number", "dollar amount",
                "select appropriate", "district information", "check if this is"}
FORM_CONTROLS = ("Button.", "attach", "Print", "SaveAs", "Reset")


def sub_item(a, b):
    """True when one line is a sub-item of the other: 13 vs 13b, 2 vs 2.1."""
    short, long_ = sorted((a, b), key=len)
    return bool(short) and long_.startswith(short) and bool(re.fullmatch(r"([a-h]|\.\d{1,2})", long_[len(short):]))


def words(s):
    return {w for w in re.findall(r"[a-z]{3,}", (s or "").lower())}


def column_conflict(full_name, v):
    """Debtor-1/2 prefixed fields must not be read as the other debtor's column."""
    head = full_name.split(".")[0].lower()
    seen = f"{v.get('column', '')} {v.get('label', '')}".lower()
    if head in ("debtor1", "debto1"):
        return any(k in seen for k in ("debtor 2", "column b", "spouse"))
    if head in ("debtor2", "debto2"):
        return any(k in seen for k in ("debtor 1", "column a", "for you")) and "spouse" not in seen
    return False


def margin_tokens(page):
    toks = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        m = LINE_TOKEN.match(word)
        if m:
            toks.append((x0, y0, x1, y1, m.group(1).lower(), bool(m.group(2))))
    return toks


def text_line(widget_rect, toks):
    x0, y0, x1, y1 = widget_rect
    mid = (y0 + y1) / 2
    # on the box's own row only a "N." marker counts; prose numbers lack the period
    same_row = [t for t in toks if t[5] and t[1] - 3 <= mid <= t[3] + 3 and t[2] <= x0 + 2]
    if same_row:
        return min(same_row, key=lambda t: t[0])[4]
    above = [t for t in toks if t[0] < 90 and t[1] <= y1]
    if above:
        return max(above, key=lambda t: (t[1], t[0]))[4]
    return ""


def main():
    ocr_dir, pdf_dir, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
    report = {}
    for idx_path in sorted(ocr_dir.glob("*/index.json")):
        stem = idx_path.parent.name
        doc = fitz.open(pdf_dir / f"{stem}.pdf")
        toks_by_page = {i + 1: margin_tokens(doc[i]) for i in range(len(doc))}
        rows = json.loads(idx_path.read_text())
        summary = {"widgets": len(rows), "agree": 0, "partial": 0, "disagree": 0, "header": 0, "text_unknown": 0,
                   "no_vision": 0, "checkbox_mismatch": 0}
        flagged = []
        for w in rows:
            v = w.get("vision")
            if w["full_name"].startswith(FORM_CONTROLS):
                summary["form_controls"] = summary.get("form_controls", 0) + 1
                continue
            if not v:
                summary["no_vision"] += 1
                flagged.append({"tag": w["tag"], "page": w["page"], "full_name": w["full_name"], "why": "no_vision"})
                continue
            tl = text_line(w["rect"], toks_by_page[w["page"]])
            vl = norm_line(v["line"])
            w["text_line"] = tl
            if not vl:
                verdict = "header"  # vision read a page header box; no line number to compare
            elif not tl:
                verdict = "text_unknown"
            elif vl == tl:
                verdict = "agree"
            elif sub_item(vl, tl):
                verdict = "partial"
            else:
                verdict = "disagree"
            summary[verdict] += 1
            cb = None
            on = (w.get("on_state") or "")
            on = on.lower() if isinstance(on, str) else ""
            opt = (v.get("option_text") or "").strip().lower()
            if w["type"] == "CheckBox" and on in ("yes", "no") and opt[:3].strip(" .") in ("yes", "no"):
                if not opt.startswith(on):
                    cb = f"on_state={on} option={opt[:30]}"
                    summary["checkbox_mismatch"] += 1
            tip = (w.get("tooltip") or "").strip()
            tip_flag = None
            if tip.lower().strip(" .:") not in GENERIC_TIPS and len(words(tip)) >= 2:
                if not (words(tip) & words(f"{v['label']} {v.get('option_text', '')} {v.get('column', '')}")):
                    tip_flag = f"tooltip={tip[:60]!r}"
                    summary["tooltip_mismatch"] = summary.get("tooltip_mismatch", 0) + 1
            col_flag = "column_conflict" if column_conflict(w["full_name"], v) else None
            if col_flag:
                summary["column_conflict"] = summary.get("column_conflict", 0) + 1
            if verdict == "disagree" or cb or tip_flag or col_flag:
                flagged.append(
                    {
                        "tag": w["tag"], "page": w["page"], "full_name": w["full_name"], "type": w["type"],
                        "vision_line": v["line"], "text_line": tl, "vision_label": v["label"],
                        "option_text": v.get("option_text", ""), "checkbox": cb, "tooltip_flag": tip_flag,
                        "column_flag": col_flag, "vision_column": v.get("column", ""), "line_verdict": verdict,
                        "text_row": w["text_row"][:160],
                    }
                )
        report[stem] = {"summary": summary, "flagged": flagged}
        print(stem, json.dumps(summary))
    pathlib.Path(out).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
