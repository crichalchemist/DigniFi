"""
The court's Form 101 (11/26) template and its index (forms step 4b, B55, 4b-R5).

Business intent: the petition a filer prints is the court's own current file, so the template
is the court's bytes, and every one of its 279 boxes is indexed under the court's own name, by a
tool that reads a hand table checked against the tagged render, never by hand-editing the index.
A box the index misses, or names a little differently, is a box the forms engine can't fill.
"""

import hashlib
import importlib.util
import json
import re
from collections import Counter

from django.conf import settings
from pypdf import PdfReader

from apps.forms.services.widgets import parse_key, template_widgets
from apps.forms.tests.oracle import case_param

ROOT = settings.BASE_DIR.parent
TOOL = ROOT / "data/forms/field_index/tools/build_form_101_index.py"
INDEX_DIR = ROOT / "data/forms/field_index"
PDF_DIR = ROOT / "data/forms/pdfs"
TEMPLATE = "form_b101.pdf"


def _tool():
    spec = importlib.util.spec_from_file_location("build_form_101_index", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _tool()


def _rows():
    return json.loads((INDEX_DIR / "form_b101.index.json").read_text())


def test_the_index_is_what_the_tool_reads_off_the_template():
    # 4b-R5: the index is never hand-edited; the tool reads it off the committed template.
    committed = (INDEX_DIR / "form_b101.index.json").read_text()
    assert committed == tool.dumps(tool.index_rows(PDF_DIR / TEMPLATE))


def test_the_template_is_the_courts_file():
    # §8.1: the file downloaded from the court, byte for byte; its hash is the schema's version.
    data = (PDF_DIR / TEMPLATE).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == tool.TEMPLATE_SHA256
    assert digest == "f9b8f6b2d11540fce286914c153003aa058ca125b6171e78f3bb440f810c5950"
    assert len(PdfReader(PDF_DIR / TEMPLATE).pages) == 8


def test_every_widget_is_indexed_with_its_own_tag():
    rows = _rows()
    assert len(rows) == 279
    assert Counter(r["type"] for r in rows) == {
        "Text": 177,
        "CheckBox": 85,
        "RadioButton": 14,
        "Signature": 3,
    }
    assert len({r["full_name"] for r in rows}) == 271
    assert len({(r["page"], r["tag"]) for r in rows}) == 279
    assert {r["basis"] for r in rows} == {"adjudicated"}


def test_the_seven_radio_groups_carry_their_own_state_names():
    # §5.3: each yes/no pair is one radio group whose states are suffixed; a binding copies them.
    groups = {}
    for r in _rows():
        if r["type"] == "RadioButton":
            groups.setdefault(r["full_name"], set()).add(r["on_state"])
    assert groups == {
        "bankruptcy within the": {"No", "Yes"},
        "filed by a spouse who is": {"No_2", "Yes_2"},
        "Go to line 12": {"No_3", "Yes_3"},
        "property that poses or is": {"No_6", "Yes_4"},
        "administrative expenses are paid that funds will be available to distribute to "
        "unsecured creditors": {"No_7", "Yes_5"},
        "consequences": {"No_8", "Yes_6"},
        "inaccurate or incomplete you could be fined or imprisoned": {"No_9", "Yes_7"},
    }


def test_the_district_twin_is_two_rows_on_two_pages():
    # §5.5: one name fills the court on page 1 and line 9's first district on page 3.
    district = [r for r in _rows() if r["full_name"] == "District"]
    assert {r["page"] for r in district} == {1, 3}
    assert len({r["tag"] for r in district}) == 2


def test_every_name_survives_the_engine():
    # Leading and double spaces, digits alone: every name must pass the key syntax, JSON, an
    # oracle case id and the template matcher unchanged. The three /Sig rows take neither the
    # text nor the box branch of widgets._template_widget, and still match (E-14).
    rows = _rows()
    for r in rows:
        key = f"{r['full_name']}@{r['page']}:{r['tag']}"
        assert parse_key(key) == (r["full_name"], r["page"], r["tag"])
        assert json.loads(json.dumps({key: "x"})) == {key: "x"}
        case_param("form_101", r["full_name"], "1", "")
    widgets = template_widgets(TEMPLATE)
    assert len(widgets) == 279
    assert {(w.full_name, w.page, w.tag) for w in widgets} == {
        (r["full_name"], r["page"], r["tag"]) for r in rows
    }
    assert [w.kind for w in widgets].count("Signature") == 3


def test_the_hard_names_are_in_the_index_verbatim():
    # H6: the court's generated names keep their leading and doubled spaces.
    names = {r["full_name"] for r in _rows()}
    assert {
        " YYYY",
        "MM  DD",
        "See 28 USC  1408 1",
        "1",
        "149",
        "undefined_14",
        "9 xx  xx",
    } <= names


_SILENT = re.compile(r"^(undefined(_\d+)?|xx(_2)?|9 xx  xx|fill_28)$")
# Boxes on one debtor's side: the SSN and ITIN digits, the EIN halves, the home's second line.
_ONE_DEBTORS = re.compile(r"^(undefined(_([1-9]|1[0-9]))?|xx(_2)?|9 xx  xx)$")


def test_labels_are_unique_and_every_silent_box_has_one():
    # The schema tool finds a box by its label (4b-R5), so no two rows share one; a box whose
    # name and tooltip say nothing ("undefined") is labelled with what the render shows.
    rows = _rows()
    assert len({r["label"] for r in rows}) == 279
    silent = [r for r in rows if _SILENT.match(r["full_name"])]
    assert len(silent) == 28
    for r in silent:
        assert r["label"] and "undefined" not in r["label"], r
    sided = [r for r in silent if _ONE_DEBTORS.match(r["full_name"])]
    assert len(sided) == 22
    for r in sided:
        assert re.search(r"\bDebtor [12]\b", r["label"]), r
        assert f"line {r['line']}" in r["label"], r
        assert re.search(r"\bdigit [1-4] of 4\b|\b(first|last|second)\b", r["label"]), r
