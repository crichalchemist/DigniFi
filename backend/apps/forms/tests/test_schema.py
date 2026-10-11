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


def test_load_schema_with_ui_metadata(tmp_path, settings):
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    schema_data = {
        "form_type": "test_form",
        "template_filename": "test.pdf",
        "template_version": "v1",
        "fields": [
            {
                "pdf_field": "street",
                "type": "text",
                "source": "asked",
                "page": 1,
                "label": "Street",
                "required": True,
                "conditional_on": None,
                "value": None,
                "rule": None,
                "ingest_key": None,
                "binding": "answer:form.street",
                "repeat": None,
                "repeat_capacity": None,
                "row": None,
                "legal_review": False,
                "ui": {
                    "step": "Address",
                    "prompt": "What is your street address?",
                    "widget": "text",
                    "help_text": "No PO Boxes",
                },
            }
        ],
    }
    schema_file = tmp_path / "test_form.json"
    schema_file.write_text(json.dumps(schema_data))

    schema = load_schema("test_form")
    field = schema.fields[0]

    assert field.ui is not None
    assert field.ui.step == "Address"
    assert field.ui.prompt == "What is your street address?"
    assert field.ui.widget == "text"
    assert field.ui.help_text == "No PO Boxes"
