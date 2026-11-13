"""
Schedule C's schema and addendum rows are written by a tool, never by hand (3g2 R9).

Business intent: a hand edit to Schedule C's boxes would be undone by the next run, or worse,
kept while the row table it came from changed. This test fails on any difference between what
the tool writes and what is committed. Where each box belongs is judged by
`test_schedule_c_schema.py` from the form's own labels, not here: a tool that places a box
wrongly writes files that agree with it.
"""

import importlib.util
import json

from django.conf import settings

ROOT = settings.BASE_DIR.parent
TOOLS = ROOT / "data/forms/field_index/tools"
ADDENDUM = ROOT / "data/forms/field_index/audit/step2_verification.json"
SCHEMA = ROOT / "data/forms/schemas/schedule_c.json"


def _load(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], TOOLS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tool():
    return _load("build_schedule_c.py")


def test_schedule_c_is_what_the_generator_writes():
    tool = _tool()

    schema, rows = tool.build()

    assert json.loads(SCHEMA.read_text()) == schema
    addendum_text = ADDENDUM.read_text()
    assert [r for r in json.loads(addendum_text) if tool.owned(r)] == rows
    # Bytes too: a hand move or reformat would pass the parsed comparison and churn the next run.
    assert SCHEMA.read_text() == tool.dumps(schema)
    assert addendum_text == tool.merged_text(addendum_text, rows)


def test_a_reformatted_or_moved_schedule_c_file_is_caught_by_its_bytes():
    tool = _tool()
    schema, rows = tool.build()
    schema_text, addendum_text = SCHEMA.read_text(), ADDENDUM.read_text()

    reformatted = json.dumps(json.loads(schema_text), indent=4)
    committed = json.loads(addendum_text)
    first = next(i for i, r in enumerate(committed) if tool.owned(r))
    moved = committed[:]
    moved.append(moved.pop(first))

    assert reformatted != tool.dumps(schema)
    assert tool.dumps(moved) != tool.merged_text(addendum_text, rows)


def test_each_addendum_writer_leaves_the_others_rows_where_they_are():
    # The claims tool puts its rows after each schedule's last row and the List of Creditors'
    # tool rewrites its own at the end of the file: Schedule C's rows sit before them (R9), so
    # no tool's run moves another's.
    schedule_c = _tool()
    claims = _load("build_claims_schedules.py")
    text = ADDENDUM.read_text()
    committed = json.loads(text)
    _, schedule_c_rows = schedule_c.build()
    _, claims_rows = claims.build()

    list_rows = [r for r in committed if r["schema"] == "list_of_creditors"]
    others = [r for r in committed if r["schema"] != "list_of_creditors"]

    assert claims.merged_text(text, claims_rows) == text
    assert schedule_c.merged_text(text, schedule_c_rows) == text
    assert schedule_c.dumps([*others, *list_rows]) == text
