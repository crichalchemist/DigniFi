"""
The claims schedules are written by a tool, never by hand (3c5 R7).

Business intent: a hand edit to a schedule the tool owns would be undone by the next run,
or worse, kept while the row maps it came from changed. This test fails on any difference
between what the tool writes and what is committed.
"""

import importlib.util
import json

from django.conf import settings

TOOL = settings.BASE_DIR.parent / "data/forms/field_index/tools/build_claims_schedules.py"


def _tool():
    spec = importlib.util.spec_from_file_location("build_claims_schedules", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_claims_schedules_are_what_the_generator_writes():
    tool = _tool()

    schemas, rows = tool.build()

    assert set(schemas) == set(tool.SCHEDULES)
    for form_type, schema in schemas.items():
        path = settings.BASE_DIR.parent / f"data/forms/schemas/{form_type}.json"
        assert json.loads(path.read_text()) == schema
    committed = json.loads(
        (
            settings.BASE_DIR.parent / "data/forms/field_index/audit/step2_verification.json"
        ).read_text()
    )
    assert [r for r in committed if tool.owned(r)] == rows
