"""
Form 122A-1Supp's schema and its addendum rows are written by a tool, never by hand (forms step 4d,
Task 4).

Business intent: a hand edit to one of the Supp's line 1 or Part 2 bindings would be undone by the
next run of build_form_122a1_supp.py, or kept while the table it came from changed. These tests
fail on any difference between what the tool writes and what is committed. Where each box belongs
is judged by test_form_122a1_supp_schema.py and tier 1, not here.
"""

import importlib.util
import json

from django.conf import settings

ROOT = settings.BASE_DIR.parent
TOOLS = ROOT / "data/forms/field_index/tools"
ADDENDUM = ROOT / "data/forms/field_index/audit/step2_verification.json"
SCHEMA = ROOT / "data/forms/schemas/form_122a1_supp.json"


def _tool():
    spec = importlib.util.spec_from_file_location(
        "build_form_122a1_supp", TOOLS / "build_form_122a1_supp.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_supps_schema_is_what_the_tool_writes():
    tool = _tool()

    schema, _ = tool.build()

    assert json.loads(SCHEMA.read_text()) == schema
    # Bytes too: a hand reformat would pass the parsed comparison and churn the next run.
    assert SCHEMA.read_text() == tool.dumps(schema)


def test_step2_verification_is_what_the_tool_writes():
    tool = _tool()

    _, rows = tool.build()

    addendum_text = ADDENDUM.read_text()
    committed = json.loads(addendum_text)
    assert [r for r in committed if tool.owned(r)] == rows
    # Nine rows, line 1's pair and Part 2's seven; the header's two stay in verification.json.
    assert len(rows) == 9
    assert addendum_text == tool.merged_text(addendum_text, rows)
    # Ruling K: the rows sit right after Form 122A-1's last row, never after the List of Creditors.
    schemas = [r["schema"] for r in committed]
    first = schemas.index("form_122a1_supp")
    assert schemas[first - 1] == "form_122a1"
    assert first < schemas.index("list_of_creditors")
