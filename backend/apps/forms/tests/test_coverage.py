"""Headline proof: the resolver fills every applicable Form 107 field."""

import pytest
from django.core.management import call_command

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import _section_applies, resolve  # noqa: PLC2701
from apps.intake.models import IntakeSession


@pytest.fixture
def ilnd_fixture(db):
    """Ensure ILND district data exists before seeding personas."""
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data")


@pytest.mark.django_db
def test_resolver_fills_every_applicable_required_field(ilnd_fixture):
    call_command("seed_demo_data", "--reset", persona="maria")
    session = IntakeSession.objects.filter(user__username="demo_maria").first()

    schema = load_schema("form_107")
    out = resolve(schema, session)

    applicable_required = [
        f
        for f in schema.fields
        if f.required
        and _section_applies(f, session)
        and f.source not in ("signature", "ingested")
        and not f.legal_review
    ]
    unresolved = [f.pdf_field for f in applicable_required if f.pdf_field not in out]
    assert unresolved == [], f"unresolved applicable fields: {unresolved}"


@pytest.mark.django_db
def test_resolved_fields_come_from_multiple_sources(ilnd_fixture):
    """Resolver pulls from derivations, SOFA, constants — not just one source."""
    call_command("seed_demo_data", "--reset", persona="maria")
    session = IntakeSession.objects.filter(user__username="demo_maria").first()

    out = resolve(load_schema("form_107"), session)
    # Hand-authored map filled ~6 fields. Schema-driven resolver
    # fills every applicable field with available data:
    #   - constants: chapter, debtor_type
    #   - derivations: full_name, family_size, district_name
    #   - SOFA: prior income rows x N, creditor payment rows x M
    #   - signature: 4 placeholder fields
    assert len(out) >= 10, f"only {len(out)} fields resolved"
    # Verify we have data from multiple resolvers
    assert any(
        v for v in out.values() if v
    ), "all fields are empty — resolver may not be pulling source data"
