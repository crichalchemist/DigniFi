"""Tests for ingest_form_schema management command."""

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from apps.forms.management.commands.ingest_form_schema import (
    build_draft_schema,
    template_version_hash,
)


class TestTemplateVersionHash(TestCase):
    """Tests for template_version_hash()."""

    def test_returns_64_char_hex_string(self):
        """SHA-256 digest is 64 hex characters."""
        template_path = Path(settings.PDF_FORMS_DIRECTORY) / "b_107_0425-form.pdf"
        result = template_version_hash(template_path)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        """Same file produces same hash on repeated calls."""
        template_path = Path(settings.PDF_FORMS_DIRECTORY) / "b_107_0425-form.pdf"
        assert template_version_hash(template_path) == template_version_hash(template_path)

    def test_different_files_different_hash(self):
        """Different template files yield different hashes."""
        path_a = Path(settings.PDF_FORMS_DIRECTORY) / "b_107_0425-form.pdf"
        path_b = Path(settings.PDF_FORMS_DIRECTORY) / "form_b106ab.pdf"
        if path_a.exists() and path_b.exists():
            assert template_version_hash(path_a) != template_version_hash(path_b)


class TestBuildDraftSchema(TestCase):
    """Tests for build_draft_schema()."""

    def test_returns_dict_with_required_keys(self):
        """Draft schema must have form_type, template_filename, template_version, fields."""
        draft = build_draft_schema("form_107")
        assert "form_type" in draft
        assert "template_filename" in draft
        assert "template_version" in draft
        assert "fields" in draft

    def test_form_type_matches_argument(self):
        """form_type in draft matches the argument passed."""
        draft = build_draft_schema("form_107")
        assert draft["form_type"] == "form_107"

    def test_template_version_is_64_chars(self):
        """template_version is a 64-char SHA-256 hex digest."""
        draft = build_draft_schema("form_107")
        assert len(draft["template_version"]) == 64
        assert all(c in "0123456789abcdef" for c in draft["template_version"])

    def test_fields_has_more_than_100_entries(self):
        """Form 107 has many fields; draft must discover >100."""
        draft = build_draft_schema("form_107")
        assert len(draft["fields"]) > 100

    def test_all_fields_source_is_tbd(self):
        """All draft fields must have source='TBD' (unfilled)."""
        draft = build_draft_schema("form_107")
        for field in draft["fields"]:
            assert field["source"] == "TBD", f"Expected TBD for {field['pdf_field']}"

    def test_all_fieldspec_keys_present(self):
        """Every field record must contain all FieldSpec keys so load_schema can parse it."""
        required_keys = {
            "pdf_field",
            "type",
            "source",
            "on_states",
            "page",
            "label",
            "required",
            "conditional_on",
            "value",
            "rule",
            "ingest_key",
            "binding",
            "repeat",
            "repeat_capacity",
            "row",
            "legal_review",
        }
        draft = build_draft_schema("form_107")
        for field in draft["fields"]:
            missing = required_keys - set(field.keys())
            assert not missing, f"Field {field['pdf_field']!r} missing keys: {missing}"

    def test_raises_for_unknown_form_type(self):
        """CommandError raised for form types not in FORM_TEMPLATES."""
        from django.core.management.base import CommandError

        with pytest.raises(CommandError, match="unknown form_type"):
            build_draft_schema("form_999")

    def test_page_numbers_are_positive_integers(self):
        """Page numbers must be positive integers."""
        draft = build_draft_schema("form_107")
        for field in draft["fields"]:
            assert isinstance(field["page"], int)
            assert field["page"] >= 1

    def test_required_is_bool(self):
        """required field is always a bool."""
        draft = build_draft_schema("form_107")
        for field in draft["fields"]:
            assert isinstance(field["required"], bool)

    def test_legal_review_is_bool(self):
        """legal_review field is always a bool."""
        draft = build_draft_schema("form_107")
        for field in draft["fields"]:
            assert isinstance(field["legal_review"], bool)


class TestIngestFormSchemaCommand(TestCase):
    """Tests for the ingest_form_schema management command."""

    def test_command_writes_json_file(self):
        """Command writes a JSON schema file to FORM_SCHEMAS_DIRECTORY."""
        with tempfile.TemporaryDirectory() as schemas_dir:
            with patch.object(settings, "FORM_SCHEMAS_DIRECTORY", Path(schemas_dir)):
                out = StringIO()
                call_command("ingest_form_schema", "form_107", stdout=out)

            schema_file = Path(schemas_dir) / "form_107.json"
            assert schema_file.exists(), "Expected form_107.json to be written"
            with open(schema_file) as f:
                data = json.load(f)
            assert data["form_type"] == "form_107"
            assert len(data["fields"]) > 100

    def test_command_reports_drift_on_existing_schema(self):
        """Command reports version drift when template hash has changed."""
        with tempfile.TemporaryDirectory() as schemas_dir:
            # Write a stale schema with a fake template_version
            stale = {
                "form_type": "form_107",
                "template_filename": "b_107_0425-form.pdf",
                "template_version": "a" * 64,
                "fields": [],
            }
            schema_file = Path(schemas_dir) / "form_107.json"
            schema_file.write_text(json.dumps(stale))

            with patch.object(settings, "FORM_SCHEMAS_DIRECTORY", Path(schemas_dir)):
                out = StringIO()
                call_command("ingest_form_schema", "form_107", stdout=out)

            output = out.getvalue()
            assert (
                "drift" in output.lower()
                or "changed" in output.lower()
                or "updated" in output.lower()
            )

    def test_command_no_drift_when_hash_matches(self):
        """Command reports no drift when existing schema template_version matches."""
        with tempfile.TemporaryDirectory() as schemas_dir:
            # First run: write the schema
            with patch.object(settings, "FORM_SCHEMAS_DIRECTORY", Path(schemas_dir)):
                call_command("ingest_form_schema", "form_107", stdout=StringIO())

            # Second run with same hash: no drift
            with patch.object(settings, "FORM_SCHEMAS_DIRECTORY", Path(schemas_dir)):
                out = StringIO()
                call_command("ingest_form_schema", "form_107", stdout=out)

            output = out.getvalue()
            assert (
                "no drift" in output.lower()
                or "up to date" in output.lower()
                or "unchanged" in output.lower()
            )

    def test_command_invalid_form_type_raises(self):
        """Command raises CommandError for unknown form types."""
        from django.core.management.base import CommandError

        with pytest.raises((CommandError, SystemExit)):
            call_command("ingest_form_schema", "form_999")

    def test_command_preserves_existing_field_metadata(self):
        """Command retains source/binding/rule on existing fields when drift is detected."""
        with tempfile.TemporaryDirectory() as schemas_dir:
            stale = {
                "form_type": "form_107",
                "template_filename": "b_107_0425-form.pdf",
                "template_version": "a" * 64,
                "fields": [
                    {
                        "pdf_field": "Debtor 2",
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
                        "on_states": [],
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

            # Find Debtor 2 in the updated fields
            field = next(f for f in updated["fields"] if f["pdf_field"] == "Debtor 2")

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
