"""Tests for the form-schema loader and validator."""

import json

import pytest

from apps.forms.schema import FieldSpec, FormSchema, load_schema, validate_schema
from apps.forms.services.derivations import DERIVATIONS, PREDICATES

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


def _schema(**field_overrides):
    base = dict(SAMPLE["fields"][0])
    base.update(field_overrides)
    return FormSchema("form_test", "b_107_0425-form.pdf", "v1", [FieldSpec(**base)])


def test_validate_flags_unknown_pdf_field():
    schema = _schema(pdf_field="NOT_A_REAL_FIELD_xyz", source="constant", value="x", rule=None)
    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
    assert any("NOT_A_REAL_FIELD_xyz" in e for e in errors)


def test_validate_flags_tbd_source():
    schema = _schema(pdf_field="Debtor 1", source="TBD", rule=None)
    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
    assert any("TBD" in e for e in errors)


def test_validate_flags_unknown_rule():
    schema = _schema(pdf_field="Debtor 1", source="derived", rule="no_such_rule")
    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
    assert any("no_such_rule" in e for e in errors)


def test_validate_clean_schema_returns_empty():
    schema = _schema(pdf_field="Debtor 1", source="derived", rule="full_name")
    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
    assert errors == []


@pytest.mark.django_db
def test_form_107_schema_is_valid(db):
    schema = load_schema("form_107")
    errors = validate_schema(schema, derivations=set(DERIVATIONS), predicates=set(PREDICATES))
    assert errors == [], "form_107 schema invalid:\n" + "\n".join(errors)


@pytest.mark.django_db
def test_form_107_schema_has_no_tbd(db):
    schema = load_schema("form_107")
    assert all(f.source != "TBD" for f in schema.fields), "form_107 has fields with source=TBD"


def test_form_101_schema_is_valid(db):
    schema = load_schema("form_101")
    errors = validate_schema(schema, derivations=set(DERIVATIONS), predicates=set(PREDICATES))
    assert not errors


def test_form_101_schema_has_no_tbd(db):
    schema = load_schema("form_101")
    for f in schema.fields:
        if f.source != "skip":
            assert "TBD" not in f.pdf_field
            assert "TBD" not in str(f.rule)
            assert "TBD" not in str(f.binding)
