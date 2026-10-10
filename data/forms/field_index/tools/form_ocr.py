"""Vision index of AO court-form templates.

Render each page with every widget outlined and tagged, ask an OpenAI vision
model which printed line and label each tag belongs to, and keep the
text-layer row beside each widget for cross-checking.

Blank public court forms only -- no filer data is sent.

usage: form_ocr.py <out_dir> <template.pdf>[:<pages>] ...   (pages e.g. 1,2)
env:   OCR_INDEX_MODEL (default gpt-4o), OCR_INDEX_BANDS (default 2)
"""

import base64
import concurrent.futures as cf
import json
import os
import pathlib
import sys
import time

import fitz  # pymupdf
from openai import OpenAI

MODEL = os.environ.get("OCR_INDEX_MODEL", "gpt-4o")
BANDS = int(os.environ.get("OCR_INDEX_BANDS", "2"))
ZOOM = 2.5  # 180 dpi


def load_key():
    for line in open("/Volumes/Containers/DigniFi/.env"):
        if line.startswith("OPENAI_API_KEY="):
            return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("OPENAI_API_KEY missing from .env")


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["boxes"],
    "properties": {
        "boxes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tag", "line", "label", "column", "kind", "option_text", "confidence"],
                "properties": {
                    "tag": {"type": "string"},
                    "line": {"type": "string"},
                    "label": {"type": "string"},
                    "column": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["amount", "text", "date", "count", "checkbox", "signature", "other"],
                    },
                    "option_text": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        }
    },
}

PROMPT = """This image is part of page {page} of the official U.S. Bankruptcy form "{form}".
Each fillable box is outlined in red and tagged in red with an id like T12. Tags in this image: {tags}.

For EVERY tag listed, report:
- line: the printed line or item number the box belongs to, exactly as printed (e.g. "4", "6d", "13B", "14a", "Part 2 line 3"). Use "" for header boxes such as the debtor name or case number.
- label: the printed words that say what belongs in that box, copied verbatim and kept short. For a header box, the printed caption (e.g. "Debtor 1", "Case number").
- column: the column heading the box sits under, exactly as printed (e.g. "Debtor 1", "Debtor 2", "Column A", "Column B", "For you", "Total"), or "".
- kind: amount, text, date, count (a number of people, vehicles and the like), checkbox, signature, or other.
- option_text: for a checkbox, the printed words beside it; otherwise "".
- confidence: high, medium or low.

Read the printed form, not the red tags, for line and label. If a tag is cut off at the edge of this image, still report it with confidence low."""


def widgets(page):
    out = []
    for w in page.widgets():
        out.append(
            {
                "full_name": w.field_name,
                "type": w.field_type_string,
                "tooltip": (w.field_label or "").strip(),
                "on_state": w.on_state() if w.field_type_string in ("CheckBox", "RadioButton") else None,
                "rect": [round(v, 1) for v in w.rect],
            }
        )
    # reading order: top to bottom, then left to right
    out.sort(key=lambda d: (round(d["rect"][1] / 4), d["rect"][0]))
    for i, d in enumerate(out, start=1):
        d["tag"] = f"T{i}"
    return out


def text_rows(page, ws):
    words = page.get_text("words")  # x0,y0,x1,y1,word,block,line,wordno
    for d in ws:
        x0, y0, x1, y1 = d["rect"]
        mid = (y0 + y1) / 2
        row = [w for w in words if w[1] - 2 <= mid <= w[3] + 2 and not (w[0] >= x0 and w[2] <= x1)]
        row.sort(key=lambda w: w[0])
        d["text_row"] = " ".join(w[4] for w in row)[:300]


def annotate(page, ws):
    for d in ws:
        r = fitz.Rect(d["rect"])
        page.draw_rect(r, color=(1, 0, 0), width=0.8)
        page.insert_text(
            fitz.Point(r.x0 + 1, r.y0 + min(7, r.height - 1) if r.height > 7 else r.y0 - 1),
            d["tag"],
            fontsize=6.5,
            color=(0.85, 0, 0),
            fontname="hebo",
        )


def bands(page, ws):
    """Split the page into horizontal bands with overlap; return (clip, tags)."""
    h = page.rect.height
    step = h / BANDS
    out = []
    for b in range(BANDS):
        top = max(0, b * step - 30)
        bot = min(h, (b + 1) * step + 30)
        clip = fitz.Rect(0, top, page.rect.width, bot)
        # a tag belongs to the band containing its centre; overlap is context only
        tags = [d["tag"] for d in ws if b * step <= (d["rect"][1] + d["rect"][3]) / 2 < (b + 1) * step]
        if tags:
            out.append((clip, tags))
    return out


def ask(client, png, form, page_no, tags):
    b64 = base64.b64encode(png).decode()
    for attempt in range(3):
        extra = {"temperature": 0} if MODEL.startswith("gpt-4") else {}
        resp = client.chat.completions.create(
            model=MODEL,
            **extra,
            response_format={"type": "json_schema", "json_schema": {"name": "boxes", "strict": True, "schema": SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT.format(page=page_no, form=form, tags=", ".join(tags))},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}},
                    ],
                }
            ],
        )
        choice = resp.choices[0]
        content = (choice.message.content or "").strip()
        if content:
            return json.loads(content)["boxes"], resp.usage
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"empty reply ({choice.finish_reason}, refusal={choice.message.refusal!r})")


def do_page(client, path, page_no, out_dir):
    doc = fitz.open(path)
    page = doc[page_no - 1]
    ws = widgets(page)
    if not ws:
        return page_no, [], (0, 0)
    text_rows(page, ws)
    annotate(page, ws)
    by_tag = {d["tag"]: d for d in ws}
    tok_in = tok_out = 0
    for i, (clip, tags) in enumerate(bands(page, ws)):
        png = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip).tobytes("png")
        (out_dir / f"p{page_no}_b{i}.png").write_bytes(png)
        boxes, usage = ask(client, png, pathlib.Path(path).stem, page_no, tags)
        tok_in += usage.prompt_tokens
        tok_out += usage.completion_tokens
        for box in boxes:
            if box["tag"] in by_tag and box["tag"] in tags:
                by_tag[box["tag"]]["vision"] = {k: v for k, v in box.items() if k != "tag"}
    for d in ws:
        d["page"] = page_no
    return page_no, ws, (tok_in, tok_out)


def main():
    out_root = pathlib.Path(sys.argv[1])
    client = OpenAI(api_key=load_key())
    jobs = []
    for arg in sys.argv[2:]:
        path, _, pages = arg.partition(":")
        n = len(fitz.open(path))
        page_list = [int(p) for p in pages.split(",")] if pages else range(1, n + 1)
        out_dir = out_root / pathlib.Path(path).stem
        out_dir.mkdir(parents=True, exist_ok=True)
        jobs += [(path, p, out_dir) for p in page_list]
    results = {}
    tok = [0, 0]
    with cf.ThreadPoolExecutor(max_workers=int(os.environ.get("OCR_INDEX_WORKERS", "6"))) as pool:
        futs = {pool.submit(do_page, client, *j): j for j in jobs}
        for f in cf.as_completed(futs):
            path, p, out_dir = futs[f]
            try:
                page_no, ws, (ti, to) = f.result()
            except Exception as e:  # report and keep going; the page is retried by rerunning
                print(f"FAIL {pathlib.Path(path).stem} p{p}: {e!r}", flush=True)
                continue
            tok[0] += ti
            tok[1] += to
            results.setdefault(out_dir, []).extend(ws)
            missing = sum(1 for d in ws if "vision" not in d)
            print(f"ok {pathlib.Path(path).stem} p{page_no}: {len(ws)} boxes, {missing} unanswered", flush=True)
    for out_dir, ws in results.items():
        ws.sort(key=lambda d: (d["page"], int(d["tag"][1:])))
        fn = out_dir / "index.json"
        prev = json.loads(fn.read_text()) if fn.exists() else []
        done_pages = {d["page"] for d in ws}
        merged = [d for d in prev if d["page"] not in done_pages] + ws
        merged.sort(key=lambda d: (d["page"], int(d["tag"][1:])))
        fn.write_text(json.dumps(merged, indent=1))
    print(f"tokens in={tok[0]} out={tok[1]} model={MODEL}")


if __name__ == "__main__":
    main()
