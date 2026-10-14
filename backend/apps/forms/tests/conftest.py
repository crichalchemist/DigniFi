"""Shared test fixtures for the forms app."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.models import GeneratedForm
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def api_client_authed(db):
    user = User.objects.create_user(username="testuser", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def generated_form_factory(db, api_client_authed):
    def _make(status="generated"):
        user = User.objects.filter(username="testuser").first()
        district = District.objects.filter(code="ilnd").first()
        if not district:
            # The real ILND data: preparing a form works the means test out against its median.
            call_command("loaddata", "ilnd_2025_data", verbosity=0)
            district = District.objects.get(code="ilnd")
        session = IntakeSession.objects.create(
            user=user, district=district, status="completed", current_step=6
        )
        DebtorInfo.objects.create(
            session=session,
            first_name="Maria",
            last_name="Torres",
            ssn="900-11-0001",  # IRS-reserved range: synthetic
            date_of_birth=date(1988, 6, 15),
            street_address="2145 W Division St",
            city="Chicago",
            state="IL",
            zip_code="60622",
        )
        IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("2800.00"))
        return GeneratedForm.objects.create(
            session=session,
            form_type="form_121",
            status=status,
            generated_by=user,
        )

    return _make
