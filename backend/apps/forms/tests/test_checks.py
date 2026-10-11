"""
A schema that disagrees with its template or field index stops the app from starting.

pytest-django runs no system checks, so these tests call the same
validate_form() the check uses (spec §5.4), on every registered form and on
deliberately broken copies of real schemas.
"""

import json
import shutil

import pypdf
import pytest
from django.conf import settings as django_settings
from django.core.management import call_command
from django.core.management.base import SystemCheckError

from apps.forms.checks import validate_form
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema


@pytest.fixture
def schema_copy(tmp_path, settings):
    """A writable copy of the real schemas; edit one, then validate it."""
    shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, tmp_path / "schemas")
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path / "schemas"
    load_schema.cache_clear()
    yield tmp_path / "schemas"
    load_schema.cache_clear()


def _edit(schemas, form_type, change):
    path = schemas / f"{form_type}.json"
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))


def _field(data, pdf_field):
    return next(f for f in data["fields"] if f["pdf_field"] == pdf_field)


def _ids(form_type):
    return [e.id for e in validate_form(form_type)]


def _errors(form_type):
    return [(e.id, e.msg) for e in validate_form(form_type)]


@pytest.mark.parametrize("form_type", get_all_form_types())
def test_every_registered_form_passes(form_type):
    assert validate_form(form_type) == []


def test_missing_schema_is_reported(schema_copy):
    (schema_copy / "form_121.json").unlink()
    assert _ids("form_121") == ["forms.E001"]


def test_changed_template_is_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: d.update(template_version="0" * 64))
    assert _ids("form_121") == ["forms.E002"]


def test_short_name_is_reported(schema_copy):
    # A short name is what put the filer's name in Debtor 2 boxes (DIG-63).
    _edit(schema_copy, "form_122a1", lambda d: _field(d, "Debtor1.Name").update(pdf_field="Name"))
    assert _ids("form_122a1") == ["forms.E003"]


def test_checkbox_bound_as_text_is_reported(schema_copy):
    def change(d):
        box = _field(d, "Check Box1")
        box.update(type="text")
        del box["choices"]

    _edit(schema_copy, "form_121", change)
    assert _ids("form_121") == ["forms.E004"]


def test_push_button_binding_is_reported(schema_copy):
    print_button = {
        "pdf_field": "Button.Print1",
        "type": "text",
        "source": "constant",
        "page": 9,
        "label": "",
        "required": False,
        "conditional_on": None,
        "value": "x",
        "rule": None,
        "ingest_key": None,
        "binding": None,
        "repeat": None,
        "repeat_capacity": None,
        "row": None,
        "legal_review": False,
    }
    _edit(schema_copy, "form_101", lambda d: d["fields"].append(print_button))
    assert _ids("form_101") == ["forms.E004"]


def test_checkbox_without_choices_is_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: _field(d, "Check Box1").pop("choices"))
    assert _errors("form_121") == [
        ("forms.E004", "form_121: 'Check Box1': a checkbox binding needs choices")
    ]


def test_choices_on_a_text_binding_are_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: _field(d, "Debtor1.First name").update(choices={}))
    assert _errors("form_121") == [
        (
            "forms.E004",
            "form_121: 'Debtor1.First name': choices go on checkbox and radio only, not on text",
        )
    ]


def test_choices_key_that_isnt_lower_case_is_reported(schema_copy):
    # The filler lower-cases the answer before the lookup, so "True" could never match.
    _edit(schema_copy, "form_107", lambda d: _field(d, "check5").update(choices={"True": "/no"}))
    assert _errors("form_107") == [
        (
            "forms.E004",
            "form_107: 'check5': choices key 'True' isn't lower-case, so no answer can match it",
        )
    ]


def test_state_the_template_lacks_is_reported(schema_copy):
    # The old schema wrote /Yes; the template's state is /On, so nothing ticked.
    _edit(
        schema_copy, "form_121", lambda d: _field(d, "Check Box1").update(choices={"true": "/Yes"})
    )
    assert _ids("form_121") == ["forms.E005"]


def test_district_constant_outside_the_options_is_reported(schema_copy):
    district = "Bankruptcy District Information"
    _edit(
        schema_copy,
        "form_121",
        lambda d: _field(d, district).update(source="constant", rule=None, value="Nowhere"),
    )
    assert _ids("form_121") == ["forms.E005"]


def test_constant_option_on_a_box_the_template_lacks_is_reported(schema_copy, monkeypatch):
    # The index still names the box, but the template has drifted: an error, not a crash.
    district = "Bankruptcy District Information"
    _edit(
        schema_copy,
        "form_121",
        lambda d: _field(d, district).update(
            source="constant", rule=None, value="Northern District of Illinois"
        ),
    )
    assert _ids("form_121") == []
    monkeypatch.setattr(pypdf.PdfReader, "get_fields", lambda self, *args, **kwargs: {})
    assert _ids("form_121") == ["forms.E005"]


def test_box_bound_twice_is_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: d["fields"].append(_field(d, "Debtor1.First name")))
    assert _ids("form_121") == ["forms.E006"]


@pytest.mark.parametrize(
    "change",
    [
        {"source": "TBD"},
        {"source": "derived", "rule": "no_such_rule"},
        {"conditional_on": "no_such_predicate"},
        {"source": "asked", "rule": None, "binding": "intake.first_name"},
    ],
)
def test_unresolvable_source_is_reported(schema_copy, change):
    _edit(schema_copy, "form_121", lambda d: _field(d, "Debtor1.First name").update(change))
    assert _ids("form_121") == ["forms.E007"]


def test_manage_py_check_fails_on_a_bad_schema(schema_copy):
    """migrate runs the same checks, so this is what fails a Heroku release."""
    _edit(schema_copy, "form_121", lambda d: d.update(template_version="0" * 64))
    with pytest.raises(SystemCheckError, match="forms.E002"):
        call_command("check")
