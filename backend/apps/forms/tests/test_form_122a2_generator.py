"""
Form 122A-2's schema and addendum rows are written by a tool, never by hand (3h3 plan R14).

Business intent: a hand edit to one of 122A-2's 130 bindings would be undone by the next run, or
worse, kept while the table it came from changed. This test fails on any difference between what
the tool writes and what is committed. Where each box belongs is judged by
`test_form_122a2_schema.py` and the row tests, not here: a tool that places a box wrongly writes
files that agree with it.
"""

import importlib.util
import json

from django.conf import settings

from apps.forms.schema import load_schema
from apps.forms.services import means_fit
from apps.forms.services.sheets import WIDTH

ROOT = settings.BASE_DIR.parent
TOOLS = ROOT / "data/forms/field_index/tools"
ADDENDUM = ROOT / "data/forms/field_index/audit/step2_verification.json"
SCHEMA = ROOT / "data/forms/schemas/form_122a2.json"


def _tool():
    spec = importlib.util.spec_from_file_location("build_form_122a2", TOOLS / "build_form_122a2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_form_122a2_is_what_the_tool_writes():
    tool = _tool()

    schema, rows = tool.build()

    assert json.loads(SCHEMA.read_text()) == schema
    addendum_text = ADDENDUM.read_text()
    assert [r for r in json.loads(addendum_text) if tool.owned(r)] == rows
    # Bytes too: a hand move or reformat would pass the parsed comparison and churn the next run.
    assert SCHEMA.read_text() == tool.dumps(schema)
    assert addendum_text == tool.merged_text(addendum_text, rows)


def test_the_schema_shares_the_puts_explanation_width():
    # The PUT measures a line 43 explanation against the sheet's explanation column (spec §9.2,
    # H49): the two figures are one constant, or a saved explanation could fail at Generate.
    sheet = load_schema("form_122a2").groups["means_line_43"].sheet

    explanation, amount = sheet.columns
    assert explanation.width == means_fit.LINE_43_EXPLANATION_WIDTH
    assert sheet.line_width + amount.width == WIDTH - means_fit.LINE_43_EXPLANATION_WIDTH
