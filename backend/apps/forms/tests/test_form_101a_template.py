"""
The court's older fillable Form 101A (12/15) template and its index (forms step 4b2, B57).

Business intent: the eviction statement a filer prints is the court's own fillable file, so the
template is the court's bytes, every one of its 18 boxes is indexed under the court's own name by
a tool that reads a hand table checked against the tagged render, and the file says what the
current publication (`form_b101a_0.pdf`, which the eviction quotes are pinned to) says. A box the
index misses, or a page whose words drifted from the current form, is a form that can't be filled
or can't be trusted.
"""

import hashlib
import importlib.util
import json
import re
from collections import Counter

from django.conf import settings
from pypdf import PdfReader

ROOT = settings.BASE_DIR.parent
TOOL = ROOT / "data/forms/field_index/tools/build_form_101a_index.py"
INDEX_DIR = ROOT / "data/forms/field_index"
PDF_DIR = ROOT / "data/forms/pdfs"
TEMPLATE = "form_b101a_fillable.pdf"
CURRENT = "form_b101a_0.pdf"


def _tool():
    spec = importlib.util.spec_from_file_location("build_form_101a_index", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _tool()


def _rows():
    return json.loads((INDEX_DIR / "form_b101a_fillable.index.json").read_text())


def _by_name():
    return {row["full_name"]: row for row in _rows()}


def test_the_index_is_what_the_tool_reads_off_the_template():
    # The index is never hand-edited; the tool reads it off the committed template.
    committed = (INDEX_DIR / "form_b101a_fillable.index.json").read_text()
    assert committed == tool.dumps(tool.index_rows(PDF_DIR / TEMPLATE))


def test_the_template_is_the_courts_fillable_file():
    # The file downloaded from the court, byte for byte; its hash is the schema's version.
    data = (PDF_DIR / TEMPLATE).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == tool.TEMPLATE_SHA256
    assert digest == "4c79ea2730408b7bbc28a22a86e3698187f960eb5d97d11be4b671cdf62c327b"
    assert len(data) == 75274
    assert len(PdfReader(PDF_DIR / TEMPLATE).pages) == 1


def test_the_index_has_eighteen_rows_of_four_types():
    rows = _rows()
    assert Counter(row["type"] for row in rows) == {
        "Text": 12,
        "ComboBox": 1,
        "CheckBox": 2,
        "Button": 3,
    }
    assert len({row["tag"] for row in rows}) == 18
    assert len({row["label"] for row in rows}) == 18


def test_the_buttons_are_form_controls_and_every_other_row_adjudicated():
    for row in _rows():
        expected = "form_control" if row["type"] == "Button" else "adjudicated"
        assert row["basis"] == expected, row["full_name"]


def test_check_box_12_is_on_at_no_and_says_which_box_it_is():
    # A trap: the first certification box's on-state is literally "No", so a reader who takes it
    # for a yes/no answer would print a No the filer never gave. Its label says which box it is.
    by_name = _by_name()
    first, second = by_name["Check Box12"], by_name["Check Box13"]
    assert first["on_state"] == "No"
    assert first["label"].startswith("Certification box 1")
    assert second["on_state"] == "Yes"
    assert second["label"].startswith("Certification box 2")


def _words(path):
    text = "".join(PdfReader(path).pages[0].extract_text().split())
    return re.sub(r"_+", "_", text)


def test_the_fillable_page_says_what_the_current_form_says():
    # Owner B57 chose the fillable copy; counsel C-46 sees the choice. It is only the same form if
    # its words are the current publication's, so every difference is named: the footer URLs
    # (the court moved its pages), the lengths of the underscore blanks, and "(State)".
    fillable = _words(PDF_DIR / TEMPLATE)
    current = _words(PDF_DIR / CURRENT)
    for text, part in (
        (current, "http://www.uscourts.gov/rules-policies/current-rules-practice-procedure"),
        (current, "http://www.uscourts.gov/court-locator"),
        (current, "(State)"),
        (fillable, "www.uscourts.gov/rulesandpolicies/rules.aspx"),
        (fillable, "www.uscourts.gov/Court_Locator.aspx"),
    ):
        assert text.count(part) == 1, part
    current = (
        current.replace(
            "http://www.uscourts.gov/rules-policies/current-rules-practice-procedure", ""
        )
        .replace("http://www.uscourts.gov/court-locator", "")
        .replace("(State)", "")
    )
    fillable = fillable.replace("www.uscourts.gov/rulesandpolicies/rules.aspx", "").replace(
        "www.uscourts.gov/Court_Locator.aspx", ""
    )
    assert fillable == current
