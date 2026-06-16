"""Tests for the form-schema loader and validator."""

import json

import pytest

from apps.forms.schema import FieldSpec, FormSchema, load_schema

SAMPLE = {
    "form_type": "form_test",
    "template_filename": "b_107_0425-form.pdf",
    "template_version": "abc123",
    "fields": [
        {
            "pdf_field": "Debtor 1",
            "type": "text",
            "source": "derived",
            "on_states": [],
            "page": 1,
            "label": "Debtor name",
            "required": True,
            "conditional_on": None,
            "value": None,
            "rule": "full_name",
            "ingest_key": None,
            "binding": None,
            "repeat": None,
            "repeat_capacity": None,
            "row": None,
            "legal_review": False,
        }
    ],
}


def test_load_schema_returns_dataclass(tmp_path, settings):
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    (tmp_path / "form_test.json").write_text(json.dumps(SAMPLE))

    schema = load_schema("form_test")

    assert isinstance(schema, FormSchema)
    assert schema.template_version == "abc123"
    assert len(schema.fields) == 1
    assert isinstance(schema.fields[0], FieldSpec)
    assert schema.fields[0].rule == "full_name"


def test_load_schema_missing_file_raises(tmp_path, settings):
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    with pytest.raises(FileNotFoundError):
        load_schema("does_not_exist")
