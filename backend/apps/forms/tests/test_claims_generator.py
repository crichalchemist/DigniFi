"""
The claims schedules are written by a tool, never by hand (3c5 R7).

Business intent: a hand edit to a schedule the tool owns would be undone by the next run,
or worse, kept while the row maps it came from changed. This test fails on any difference
between what the tool writes and what is committed.
"""

import importlib.util
import json

import pytest
from django.conf import settings

TOOL = settings.BASE_DIR.parent / "data/forms/field_index/tools/build_claims_schedules.py"


def _tool():
    spec = importlib.util.spec_from_file_location("build_claims_schedules", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ADDENDUM = "data/forms/field_index/audit/step2_verification.json"


def _committed_texts():
    root = settings.BASE_DIR.parent
    schemas = {
        form_type: (root / f"data/forms/schemas/{form_type}.json").read_text()
        for form_type in _tool().SCHEDULES
    }
    return schemas, (root / ADDENDUM).read_text()


def _byte_differences(tool, schema_texts, addendum_text, schemas, rows):
    """The files whose text is not exactly what the tool writes."""
    differs = [f for f, text in schema_texts.items() if text != tool.dumps(schemas[f])]
    if addendum_text != tool.merged_text(addendum_text, rows):
        differs.append("step2_verification.json")
    return differs


def test_the_claims_schedules_are_what_the_generator_writes():
    tool = _tool()

    schemas, rows = tool.build()

    assert set(schemas) == set(tool.SCHEDULES)
    schema_texts, addendum_text = _committed_texts()
    for form_type, schema in schemas.items():
        assert json.loads(schema_texts[form_type]) == schema
    # Each schema's rows sit just after its own last existing row, so the schemas' blocks follow
    # the file's order, not the tool's: compare schema by schema (the bytes check below holds the
    # whole file).
    committed = [r for r in json.loads(addendum_text) if tool.owned(r)]
    for form_type in schemas:
        assert [r for r in committed if r["schema"] == form_type] == [
            r for r in rows if r["schema"] == form_type
        ]
    assert len(committed) == len(rows)
    # Bytes too: a hand move or reformat would pass the parsed comparison and churn the next run.
    assert _byte_differences(tool, schema_texts, addendum_text, schemas, rows) == []


def test_every_cell_the_tool_places_names_its_ruling():
    # T4-5: a cell with no entry in CELL_RULINGS would fall through to "§9.3, R2" unnoticed.
    tool = _tool()
    schemas, _ = tool.build()

    for schema in schemas.values():
        for spec in schema["fields"]:
            if spec["binding"]:
                assert tool.cell_ruling(spec)

    with pytest.raises(KeyError):
        tool.cell_ruling({"binding": "claims.secured[].no_such_cell"})


def test_each_who_owes_cell_cites_its_ruling():
    tool = _tool()
    schemas, _ = tool.build()

    who = {
        tool.cell_ruling(spec)
        for spec in schemas["schedule_d"]["fields"]
        if (spec["binding"] or "").rsplit(".", 1)[-1] in ("who", "who_debtor_1", "who_another")
    }

    assert who == {"3c spec §9.3, R3"}


def test_a_reformatted_or_moved_generated_file_is_caught_by_its_bytes():
    tool = _tool()
    schemas, rows = tool.build()
    schema_texts, addendum_text = _committed_texts()

    reformatted = {f: json.dumps(json.loads(t), indent=4) for f, t in schema_texts.items()}
    committed = json.loads(addendum_text)
    first = next(i for i, r in enumerate(committed) if tool.owned(r))
    moved = committed[:]
    moved.append(moved.pop(first))
    moved_text = tool.dumps(moved)

    assert _byte_differences(tool, reformatted, addendum_text, schemas, rows) == list(
        tool.SCHEDULES
    )
    assert _byte_differences(tool, schema_texts, moved_text, schemas, rows) == [
        "step2_verification.json"
    ]
