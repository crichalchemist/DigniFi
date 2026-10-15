"""Headline proof: the resolver fills a filer's forms from every kind of source they bind."""

import pytest
from django.core.management import call_command

from apps.districts.models import District
from apps.forms.registry import packet
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import FormAnswer, IntakeSession


@pytest.fixture
def ilnd_fixture(db):
    """Ensure ILND district data exists before seeding personas."""
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data")


@pytest.mark.django_db
def test_resolved_fields_come_from_multiple_sources(ilnd_fixture):
    """Resolver pulls from derivations, constants and the filer's answers — not just one source."""
    call_command("seed_demo_data", "--reset", persona="maria")
    session = IntakeSession.objects.filter(user__username="demo_maria").first()
    # The seeds store no answers, so Maria gives one, as step 4 will ask her to.
    FormAnswer.objects.create(
        session=session, form_type="form_101", field_key="primarily_consumer_debts", value="yes"
    )

    # The kind of source behind every box Maria's packet prints.
    sources = set()
    for form_type in packet(session):
        schema = load_schema(form_type)
        out = resolve(schema, session)
        sources |= {f.source for f in schema.fields if out.get(f.pdf_field)}
    #   - constants: Chapter 7, the 106Sum and 103B ticks
    #   - derivations: name, address, district, totals, income
    #   - answers: whether her debts are primarily consumer debts
    assert {"constant", "derived", "asked"} <= sources
