"""
System check: every registered form's schema agrees with its template and field index.

Django runs system checks on manage.py check, runserver and migrate. Heroku's
release phase runs migrate, so a bad schema fails the release before filers
see it. pytest-django runs no system checks, so test_checks.py calls
validate_form() for every form instead (spec §5.4).
"""

from django.core import checks

from apps.forms.field_index import index_path
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema, validate_schema
from apps.forms.services.derivations import DERIVATIONS, PREDICATES


def validate_form(form_type: str) -> list[checks.Error]:
    """Every problem with one form's schema, as forms.E0xx errors naming the form."""
    try:
        schema = load_schema(form_type)
    except FileNotFoundError:
        return [checks.Error(f"{form_type}: no schema file", id="forms.E001")]
    if not index_path(schema.template_filename).exists():
        return [
            checks.Error(
                f"{form_type}: no field index for {schema.template_filename}", id="forms.E001"
            )
        ]
    return [
        checks.Error(f"{form_type}: {message}", id=f"forms.{code}")
        for code, message in validate_schema(schema, set(DERIVATIONS), set(PREDICATES))
    ]


@checks.register()
def form_schemas_match_field_index(app_configs, **kwargs):
    return [error for form_type in get_all_form_types() for error in validate_form(form_type)]
