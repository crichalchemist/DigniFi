"""
Schedule C is refused, with a link to the exemptions page, until the filer has answered it
(3g1 §5.5, P4, P5, P22).

Business intent: no exemption, amount or answer is ever chosen for the filer, so a Schedule C
whose page is unfinished is never generated; and a filer who claims nothing is not stopped by a
missing list of laws.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.exemptions import NO_EXEMPTION_CATALOG, NoExemptionCatalog
from apps.districts.models import District, ExemptionCatalog
from apps.forms.registry import PreconditionMissing, build_field_values
from apps.intake.exemptions import EXEMPTION_GAP_DESCRIPTION, EXEMPTION_GAP_LINE_1
from apps.intake.models import (
    AssetInfo,
    DebtorInfo,
    ExemptionClaim,
    IncomeInfo,
    IntakeSession,
)
from apps.intake.tests.builders import answer_asset_lines, answer_exemptions, answer_household

User = get_user_model()


@pytest.fixture
def session(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    user = User.objects.create_user(username="schedulec", password="pw")
    district = District.objects.get(code="ilnd")
    session = IntakeSession.objects.create(user=user, district=district, status="completed")
    DebtorInfo.objects.create(
        session=session,
        first_name="Sarah",
        last_name="Chen",
        ssn="900-55-0005",
        date_of_birth=date(1995, 1, 20),
        street_address="1520 N Damen Ave Apt 2F",
        city="Chicago",
        state="IL",
        zip_code="60622",
    )
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("2000.00")
    )
    answer_household(session, payroll_tax=Decimal("250.00"), exemptions=None)
    return session


@pytest.fixture
def api_client(session):
    client = APIClient()
    client.force_authenticate(session.user)
    return client


def _laptop(session, description="Laptop"):
    row = AssetInfo(
        session=session, ab_line="7", description=description, current_value=Decimal("300.00")
    )
    row.set_details({})
    row.save()
    answer_asset_lines(session, ["7"])
    return row


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


def test_schedule_c_is_refused_with_a_link_to_the_exemptions_page_until_answered(session):
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("schedule_c", _fresh(session))

    assert str(refused.value) == EXEMPTION_GAP_LINE_1
    assert refused.value.page == "/exemptions"

    answer_exemptions(session)
    assert build_field_values("schedule_c", _fresh(session)) is not None


def test_generate_all_lists_schedule_cs_refusal_with_its_page(session, api_client):
    response = api_client.post(
        "/api/forms/generate_all/", {"session_id": session.pk}, format="json"
    )

    assert response.status_code == 200, response.data
    assert {
        "form_type": "schedule_c",
        "error": EXEMPTION_GAP_LINE_1,
        "page": "/exemptions",
    } in response.data["errors"]


def test_not_claiming_passes_schedule_c_on_a_day_with_no_list_of_laws(session):
    ExemptionCatalog.objects.all().delete()
    answer_exemptions(session)

    assert build_field_values("schedule_c", _fresh(session)) is not None


def test_a_chosen_law_on_a_day_with_no_list_refuses_in_the_exemption_sentence(session, api_client):
    row = _laptop(session)
    answer_exemptions(session, no_claims=False)
    ExemptionClaim.objects.create(
        session=session,
        asset=row,
        law="il_735_5_12_1001_b",
        amount_kind="dollars",
        amount=Decimal("100.00"),
    )
    ExemptionCatalog.objects.all().delete()

    with pytest.raises(NoExemptionCatalog):
        build_field_values("schedule_c", _fresh(session))

    response = api_client.post(
        "/api/forms/generate/",
        {"session_id": session.pk, "form_type": "schedule_c"},
        format="json",
    )
    assert response.status_code == 422, response.data
    assert response.data["form_type"] == "schedule_c"
    assert response.data["error"] == NO_EXEMPTION_CATALOG
    assert "page" not in response.data


def test_a_typed_law_passes_on_a_day_with_no_list_of_laws(session):
    row = _laptop(session)
    answer_exemptions(session, no_claims=False)
    ExemptionClaim.objects.create(
        session=session,
        asset=row,
        law=None,
        other_law="Demo Statute 1",
        amount_kind="dollars",
        amount=Decimal("100.00"),
    )
    ExemptionCatalog.objects.all().delete()

    assert build_field_values("schedule_c", _fresh(session)) is not None


def test_a_name_changed_after_the_claim_no_longer_fitting_raises_the_description_gap(session):
    row = _laptop(session)
    answer_exemptions(session, no_claims=False)
    ExemptionClaim.objects.create(
        session=session,
        asset=row,
        law="il_735_5_12_1001_b",
        amount_kind="dollars",
        amount=Decimal("100.00"),
    )
    assert build_field_values("schedule_c", _fresh(session)) is not None

    name = "Bed, couch, table, kitchenware (secondhand)"
    row.description = name
    row.save()

    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("schedule_c", _fresh(session))
    assert str(refused.value) == EXEMPTION_GAP_DESCRIPTION.format(name=name)
