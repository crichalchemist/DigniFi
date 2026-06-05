"""Shared test fixtures for the forms app."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.models import GeneratedForm
from apps.intake.models import IntakeSession

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
            district = District.objects.create(
                code="ilnd",
                name="Northern District of Illinois",
                court_name="U.S. Bankruptcy Court, N.D. Ill.",
                state="IL",
                filing_fee_chapter_7="338.00",
            )
        session = IntakeSession.objects.create(
            user=user, district=district, status="completed", current_step=6
        )
        return GeneratedForm.objects.create(
            session=session,
            form_type="form_121",
            status=status,
            form_data={"debtor_name": "Maria Torres"},
            generated_by=user,
        )

    return _make
