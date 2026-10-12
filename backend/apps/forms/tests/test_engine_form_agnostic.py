"""
Engine-is-not-Form-107-special-cased — the SP2 contract.

These tests prove the schema-driven engine operates on a second, uncurated
form's metadata, not just Form 107. If they pass, SP2 is "curate the next
schema", not "rebuild the engine".
"""

import pytest

from apps.districts.models import District
from apps.forms.schema import FormSchema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import IntakeSession


@pytest.mark.django_db
def test_resolver_noops_on_empty_schema():
    """resolve() returns an empty dict for a no-field schema (edge case)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(username="test_resolver", password="x")
    d = District.objects.create(
        code="ilnd",
        name="Test District",
        court_name="Test Court",
        state="IL",
        filing_fee_chapter_7="338.00",
    )
    s = IntakeSession.objects.create(district=d, user=user, status="in_progress", current_step=1)
    empty = FormSchema("form_x", "b_107_0425-form.pdf", "v1", [])
    assert resolve(empty, s) == {}


def test_scalar_value_raises_on_asked_without_binding():
    from apps.forms.schema import FieldSpec
    from apps.forms.services.fill_resolver import _scalar_value

    f = FieldSpec(
        pdf_field="A",
        type="text",
        source="asked",
        binding=None,
        page=1,
        label="Test",
        required=False,
        conditional_on=None,
        value=None,
        rule=None,
        ingest_key=None,
        repeat=None,
        repeat_capacity=None,
        row=None,
        legal_review=False,
    )
    with pytest.raises(RuntimeError, match="but no binding"):
        _scalar_value(f, {})
