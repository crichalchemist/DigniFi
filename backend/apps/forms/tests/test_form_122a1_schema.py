"""Round-trip tests for Form 122A-1 schema-driven resolution."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema122a1", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_income(session):
    IncomeInfo.objects.create(
        session=session,
        monthly_income=[2000, 2000, 2000, 2000, 2000, 2000],
        marital_status="single",
        number_of_dependents=0,
    )
    return session


@pytest.mark.django_db
class TestForm122A1Schema:
    def test_schema_loads(self):
        schema = load_schema("form_122a1")
        assert schema.form_type == "form_122a1"

    def test_all_fields_have_valid_source(self):
        schema = load_schema("form_122a1")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, session_with_income):
        field_map = resolve(load_schema("form_122a1"), session_with_income)
        assert "Bankruptcy District Information" in field_map
        assert "12B" in field_map  # annualized CMI

    def test_cmi_calculation(self, session_with_income):
        field_map = resolve(load_schema("form_122a1"), session_with_income)
        # 2000 * 6 / 6 = 2000 CMI, annualized = 24000
        assert field_map["12B"] == "24000.00"

    def test_empty_session(self, session):
        field_map = resolve(load_schema("form_122a1"), session)
        assert "Bankruptcy District Information" in field_map
