"""
Form 108's schema, its addendum rows and its caps are written by a tool, never by hand (forms step
4e, Task 4).

Business intent: a hand edit to one of Form 108's bindings, or to a cap that decides whether a
long creditor name is flagged, would be undone by the next run of build_form_108.py, or kept while
the table it came from changed. These tests fail on any difference between what the tool writes
and what is committed. Where each box belongs is judged by test_form_108_schema.py and tier 1.
"""

import importlib.util
import json

from django.conf import settings

ROOT = settings.BASE_DIR.parent
TOOLS = ROOT / "data/forms/field_index/tools"
ADDENDUM = ROOT / "data/forms/field_index/audit/step2_verification.json"
SCHEMAS = ROOT / "data/forms/schemas"


def _tool():
    spec = importlib.util.spec_from_file_location("build_form_108", TOOLS / "build_form_108.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_form_108s_schema_is_what_the_tool_writes():
    tool = _tool()

    schema, _ = tool.build()

    committed = (SCHEMAS / "form_108.json").read_text()
    assert json.loads(committed) == schema
    # Bytes too: a hand reformat would pass the parsed comparison and churn the next run.
    assert committed == tool.dumps(schema)


def test_step2_verification_is_what_the_tool_writes():
    tool = _tool()

    _, rows = tool.build()

    addendum_text = ADDENDUM.read_text()
    committed = json.loads(addendum_text)
    assert [r for r in committed if tool.owned(r)] == rows
    # The header's two, Part 1's 4 rows of 6 and Part 2's 7 rows of 3.
    assert len(rows) == 47
    assert addendum_text == tool.merged_text(addendum_text, rows)
    # The run sits right after Form 101A's rows and before the List of Creditors' (its tool
    # rewrites its own rows at the end).
    schemas = [r["schema"] for r in committed]
    first = schemas.index("form_108")
    assert schemas[first - 1] == "form_101a"
    assert schemas[first + len(rows)] == "list_of_creditors"


def test_the_caps_are_what_the_tool_measures():
    tool = _tool()

    committed = (SCHEMAS / "form_108.limits.json").read_text()

    assert committed == tool.dumps(tool.limits())
