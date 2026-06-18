import sys

f = 'backend/apps/forms/tests/test_ingest_command.py'
with open(f) as file:
    content = file.read()
if 'test_command_preserves_existing_field_metadata' not in content:
    new_test = """
    def test_command_preserves_existing_field_metadata(self):
        \"\"\"Command retains source/binding/rule on existing fields when drift is detected.\"\"\"
        with tempfile.TemporaryDirectory() as schemas_dir:
            stale = {
                "form_type": "form_107",
                "template_filename": "b_107_0425-form.pdf",
                "template_version": "a" * 64,
                "fields": [
                    {
                        "pdf_field": "Part1_Line1",
                        "type": "text",
                        "source": "asked",
                        "binding": "first_name",
                        "rule": "custom_rule",
                        "conditional_on": "some_gate",
                        "repeat": "some_repeat",
                        "legal_review": True,
                        "repeat_capacity": 5,
                        "row": 1,
                        "value": "constant_value",
                        "ingest_key": "custom_key",
                        "required": True,
                        "on_states": []
                    }
                ],
            }
            schema_file = Path(schemas_dir) / "form_107.json"
            schema_file.write_text(json.dumps(stale))

            with patch.object(settings, "FORM_SCHEMAS_DIRECTORY", Path(schemas_dir)):
                out = StringIO()
                call_command("ingest_form_schema", "form_107", stdout=out)

            with open(schema_file) as f:
                updated = json.load(f)

            # Find Part1_Line1 in the updated fields
            field = next(f for f in updated["fields"] if f["pdf_field"] == "Part1_Line1")

            assert field["source"] == "asked"
            assert field["binding"] == "first_name"
            assert field["rule"] == "custom_rule"
            assert field["conditional_on"] == "some_gate"
            assert field["repeat"] == "some_repeat"
            assert field["legal_review"] is True
            assert field["repeat_capacity"] == 5
            assert field["row"] == 1
            assert field["value"] == "constant_value"
            assert field["ingest_key"] == "custom_key"
            assert field["required"] is True
"""
    content += new_test
    with open(f, 'w') as file:
        file.write(content)
