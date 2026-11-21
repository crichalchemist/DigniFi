"""A loaded step 1 knows the server holds the filer's SSN without the SSN coming back.

Business intent (owner ruling Q3, forms step 4b): the SSN is write-only, so before this a filer
returning to step 1 had to type it again before Continue. The read now says only whether a valid
one is saved (`ssn_saved`, judged by the predicate Form 101's and Complete's `_needs_ssn` uses),
and a save that leaves `ssn` out keeps the stored one.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import DebtorInfo, IntakeSession
from apps.users.models import User

SSN = "900701234"


@pytest.fixture
def session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    return IntakeSession.objects.create(user=user, district=district)


def _debtor(session, ssn: str) -> DebtorInfo:
    return DebtorInfo.objects.create(
        session=session,
        first_name="Demo",
        last_name="Filer",
        ssn=ssn,
        date_of_birth=date(1985, 6, 15),
        phone="312-555-0100",
        email="demo@example.com",
        street_address="1 Demo Street",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )


def _client(session) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=session.user)
    return client


def test_a_stored_nine_digit_ssn_reads_as_saved_and_never_comes_back(session):
    _debtor(session, SSN)

    response = _client(session).get(f"/api/intake/sessions/{session.pk}/")

    assert response.status_code == 200
    assert response.data["debtor_info"]["ssn_saved"] is True
    assert "ssn" not in response.data["debtor_info"]
    assert SSN.encode() not in response.content
    assert SSN[-4:].encode() not in response.content


@pytest.mark.parametrize("stored", ["", "90070123", "9007012345"])
def test_a_missing_or_wrong_length_ssn_reads_as_not_saved(session, stored):
    # Form 101 and Complete refuse these (`_needs_ssn`), so step 1 must ask for it again
    _debtor(session, stored)

    response = _client(session).get(f"/api/intake/sessions/{session.pk}/")

    assert response.data["debtor_info"]["ssn_saved"] is False


def test_a_step_1_save_without_the_ssn_keeps_the_stored_one(session):
    _debtor(session, SSN)
    client = _client(session)

    response = client.patch(
        f"/api/intake/sessions/{session.pk}/",
        {"debtor_info": {"first_name": "Demo", "last_name": "Renamed", "ssn_saved": False}},
        format="json",
    )

    assert response.status_code == 200
    stored = DebtorInfo.objects.get(session=session)
    assert stored.ssn == SSN
    assert stored.last_name == "Renamed"
    assert response.data["debtor_info"]["ssn_saved"] is True
