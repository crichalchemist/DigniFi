from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import IntakeSession
from apps.users.models import User


@pytest.fixture
def district(db):
    return District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def filer(district):
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


@pytest.fixture
def filer_session(filer):
    return filer


@pytest.fixture
def other_session(district):
    other = User.objects.create_user(username="other", password="pw")
    return IntakeSession.objects.create(user=other, district=district)
