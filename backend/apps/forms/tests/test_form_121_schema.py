"""Round-trip tests for Form 121 schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import DebtorInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema121", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_ssn(session):
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        middle_name="Marie",
        last_name="Doe",
        ssn="123-45-6789",
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


@pytest.mark.django_db
class TestForm121Schema:
    def test_schema_loads(self):
        schema = load_schema("form_121")
        assert schema.form_type == "form_121"

    def test_all_fields_have_valid_source(self):
        schema = load_schema("form_121")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, session_with_ssn):
        field_map = resolve(load_schema("form_121"), session_with_ssn)
        assert "Debtor1.First name" in field_map
        assert field_map["Debtor1.First name"] == "Jane"
        assert field_map["Debtor1.Last name"] == "Doe"
        assert "Debtor1a.SSNum" in field_map
        assert field_map["Debtor1a.SSNum"] == "123-45-6789"

    def test_district_name(self, session_with_ssn):
        field_map = resolve(load_schema("form_121"), session_with_ssn)
        assert field_map["Bankruptcy District Information"] == "Northern District of Illinois"

    def test_without_debtor(self, session):
        field_map = resolve(load_schema("form_121"), session)
        assert "Bankruptcy District Information" in field_map

    def test_a_filer_with_a_social_security_number_is_never_marked_as_having_none(
        self, session_with_ssn
    ):
        # Line 2's Debtor 1 box says "You do not have a Social Security number". The old
        # rule would have ticked it for exactly the filers who have one (DIG-68).
        field_map = resolve(load_schema("form_121"), session_with_ssn)
        assert "Check Box1" not in field_map

    def test_a_filer_without_a_social_security_number_is_marked_as_having_none(self, session):
        # Only resolve() reaches this: the packet refuses Form 121 without a 9-digit
        # number (registry._needs_ssn), so a generated packet never ticks the box.
        DebtorInfo.objects.create(
            session=session,
            first_name="Jane",
            middle_name="Marie",
            last_name="Doe",
            ssn="",
            date_of_birth=date(1990, 1, 15),
            phone="312-555-0100",
            email="jane@example.com",
            street_address="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
        )
        field_map = resolve(load_schema("form_121"), session)
        assert field_map.get("Check Box1") == "/On"
