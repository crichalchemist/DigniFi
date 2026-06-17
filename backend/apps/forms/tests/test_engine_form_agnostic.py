"""
Engine-is-not-Form-107-special-cased — the SP2 contract.

These tests prove the schema-driven engine operates on a second, uncurated
form's metadata, not just Form 107. If they pass, SP2 is "curate the next
schema", not "rebuild the engine".
"""

import pytest

from apps.districts.models import District
from apps.forms.management.commands.ingest_form_schema import build_draft_schema
from apps.forms.schema import FormSchema, FieldSpec, validate_schema
from apps.forms.services.derivations import DERIVATIONS, PREDICATES
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import IntakeSession


def test_ingest_runs_on_a_second_form():
    """build_draft_schema works on any AO template, not just form_107."""
    draft = build_draft_schema("schedule_j")
    assert len(draft["fields"]) > 0
    assert all(f["source"] == "TBD" for f in draft["fields"])


def test_validate_flags_uncurated_draft():
    """An uncurated draft has TBD sources, which validate_schema flags."""
    draft = build_draft_schema("schedule_j")
    schema = FormSchema(
        **{**draft, "fields": [FieldSpec(**f) for f in draft["fields"]]}
    )
    errors = validate_schema(schema, set(DERIVATIONS), set(PREDICATES))
    assert any("TBD" in e for e in errors), "uncurated draft should be flagged"


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
    s = IntakeSession.objects.create(
        district=d, user=user, status="in_progress", current_step=1
    )
    empty = FormSchema("form_x", "b_107_0425-form.pdf", "v1", [])
    assert resolve(empty, s) == {}
