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


# The label table of 3c5 R9, written out here on purpose: a word the tool gets wrong fails.
PART = {
    "d_part_1": "Part 1",
    "d_part_2": "Part 2",
    "ef_part_1": "Part 1",
    "ef_part_2": "Part 2",
    "ef_part_3": "Part 3",
    "g": "Contract or lease",
    "h": "Codebtor",
}
CELL = {
    "name": "Name",
    "street": "Street",
    "street_joined": "Street",
    "street_2": "Second street line",
    "city": "City",
    "state": "State",
    "zip": "ZIP code",
    "who": "Who owes the debt",
    "who_debtor_1": "Who owes the debt",
    "who_another": "Who owes the debt",
    "community": "Community debt",
    "date": "Date debt was incurred",
    "property": "Describe the property",
    "contingent": "Contingent",
    "unliquidated": "Unliquidated",
    "disputed": "Disputed",
    "lien_agreement": "An agreement you made",
    "lien_statutory": "Statutory lien",
    "lien_judgment": "Judgment lien",
    "lien_other": "Other lien",
    "lien_other_text": "Other lien",
    "last_4": "Last 4 digits of account number",
    "amount": "Column A: Amount of claim",
    "value": "Column B: Value of collateral",
    "unsecured": "Column C: Unsecured portion",
    "student_loans": "Type of claim",
    "other_type": "Type of claim",
    "other_type_words": "Type of claim",
    "offset": "Subject to offset",
    "priority_amount": "Priority amount",
    "nonpriority_amount": "Nonpriority amount",
    "type_domestic_support": "Domestic support obligations",
    "type_taxes": "Taxes and certain other debts you owe the government",
    "type_intoxicated": "Claims for death or personal injury while you were intoxicated",
    "type_other": "Other. Specify",
    "other_specify": "Other. Specify",
    "line": "Line in Part 1",
    "part": "Part of the original creditor",
    "purpose": "What the contract or lease is for",
    "on_d": "Schedule D, line",
    "d_lines": "Schedule D, line",
    "on_ef": "Schedule E/F, line",
    "ef_lines": "Schedule E/F, line",
    "on_g": "Schedule G, line",
    "g_lines": "Schedule G, line",
}


def _expected_label(group, attr):
    if attr == "name" and group in ("d_part_1", "ef_part_1", "ef_part_2"):
        words = "Creditor's name"
    elif attr == "amount" and group.startswith("ef_"):
        words = "Total claim"
    elif attr == "line" and group.startswith("ef_"):
        words = "Line of the original creditor"
    else:
        words = CELL[attr]
    return f"{PART[group]}: {words}"


def test_every_claims_slot_is_labelled_from_the_table():
    schema_texts, _ = _committed_texts()
    checked = 0

    for text in schema_texts.values():
        for spec in json.loads(text)["fields"]:
            if (spec["binding"] or "").startswith("claims."):
                attr = spec["binding"].rsplit(".", 1)[-1]
                assert spec["label"] == _expected_label(spec["repeat"], attr), spec["pdf_field"]
                checked += 1

    # E/F's 275 is Part 1's 110 (3d2) + Part 2's 102 + Part 3's 63.
    assert checked == 112 + 48 + 275 + 78 + 121  # D, E/F, G, H (line 2's 8 are rules)


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
