"""
Form 101A's schema and the landlord caps (forms step 4b2, R1, R10).

Business intent: Form 101A prints the filer's own landlord answer and nothing sworn, and each
landlord text stops at the width of the box that prints it on this form.
"""

import hashlib
import importlib.util
import json

from django.conf import settings

from apps.forms.services.widgets import template_widgets

ROOT = settings.BASE_DIR.parent
TOOL = ROOT / "data/forms/field_index/tools/build_form_101a.py"
INDEX_DIR = ROOT / "data/forms/field_index"
SCHEMAS = ROOT / "data/forms/schemas"
PDF_DIR = ROOT / "data/forms/pdfs"
TEMPLATE = "form_b101a_fillable.pdf"


def _tool():
    spec = importlib.util.spec_from_file_location("build_form_101a", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _tool()


def _index():
    return json.loads((INDEX_DIR / "form_b101a_fillable.index.json").read_text())


def test_the_schema_its_rows_and_its_caps_are_what_the_tool_writes():
    index = _index()
    digest = hashlib.sha256((PDF_DIR / TEMPLATE).read_bytes()).hexdigest()
    assert (SCHEMAS / "form_101a.json").read_text() == tool.dumps(tool.schema(index, digest))
    assert (SCHEMAS / "form_101a.limits.json").read_text() == tool.dumps(tool.limits(index))
    rows = tool.addendum_rows(index)
    assert len(rows) == 7
    assert tool.ADDENDUM.read_text() == tool.merged_text(tool.ADDENDUM.read_text(), rows)


def test_form_101a_binds_seven_boxes_and_nothing_sworn():
    # Never a No the filer didn't give, and nothing sworn (spec 5.3, B58).
    fields = json.loads((SCHEMAS / "form_101a.json").read_text())["fields"]
    names = {f["pdf_field"] for f in fields}
    assert names == {
        "Debtor 1",
        "Bankruptcy District Information",
        "Name of landlord",
        "Landlord Street address",
        "Landlord City",
        "Landlord State",
        "Landlord ZIP Code_5",
    }
    assert len(fields) == 7
    never = {
        "Check Box12",
        "Check Box13",
        "undefined_38",
        "undefined_39",
        "Date",
        "Date_2",
        "Debtor 2",
        "Case number",
    }
    assert not names & never


def test_the_landlord_caps_are_measured_on_form_101as_boxes():
    limits = json.loads((SCHEMAS / "form_101a.limits.json").read_text())
    assert limits["limits"] == {
        "landlord_name": 65,
        "landlord_street": 65,
        "landlord_city": 35,
        "landlord_state": 2,
        "landlord_zip": 13,
    }
    assert set(limits["labels"]) == set(limits["limits"])
    assert "cell_labels" not in limits


def test_the_state_cap_is_the_boxs_max_len():
    # The width formula gives 4 for two capitals in this box, but the box refuses a third
    # character (/MaxLen 2), so the cap is the smaller.
    (box,) = [w for w in template_widgets(TEMPLATE) if w.full_name == "Landlord State"]
    cap = json.loads((SCHEMAS / "form_101a.limits.json").read_text())["limits"]["landlord_state"]
    assert box.max_len == 2 == cap
