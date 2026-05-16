from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import FeeWaiverApplication, IntakeSession
from apps.users.models import User


@pytest.fixture
def setup(db):
    user = User.objects.create_user(username="fwtest", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session, user


def test_create_fee_waiver(setup):
    """POST /intake/fee-waiver/ creates a FeeWaiverApplication linked to user's session."""
    client, session, _ = setup
    payload = {
        "session": session.id,
        "household_size": 2,
        "monthly_income": "1800.00",
        "monthly_expenses": "1600.00",
        "receives_public_benefits": False,
        "benefit_types": [],
        "cannot_pay_full": True,
        "cannot_pay_installments": True,
    }
    resp = client.post("/api/intake/fee-waiver/", payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["session"] == session.id
    assert data["household_size"] == 2
    assert data["id"] is not None
    fw = FeeWaiverApplication.objects.get(session=session)
    assert data["id"] == fw.id
    assert FeeWaiverApplication.objects.filter(session=session).exists()


def test_create_fee_waiver_unauthenticated(db):
    """POST /intake/fee-waiver/ without auth returns 401."""
    client = APIClient()
    resp = client.post("/api/intake/fee-waiver/", {}, format="json")
    assert resp.status_code == 401


def test_get_fee_waiver(setup):
    """GET /intake/fee-waiver/{id}/ returns record owned by user."""
    client, session, _ = setup
    fw = FeeWaiverApplication.objects.create(
        session=session,
        household_size=1,
        monthly_income=Decimal("1200.00"),
        monthly_expenses=Decimal("1000.00"),
    )
    resp = client.get(f"/api/intake/fee-waiver/{fw.id}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == fw.id


def test_other_user_cannot_access_fee_waiver(db):
    """GET /intake/fee-waiver/{id}/ for another user's record returns 404."""
    owner = User.objects.create_user(username="owner", password="pass")
    other = User.objects.create_user(username="other", password="pass")
    district = District.objects.create(
        code="ILND2",
        name="Illinois Northern 2",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=owner, district=district)
    fw = FeeWaiverApplication.objects.create(
        session=session,
        household_size=1,
        monthly_income=Decimal("1200.00"),
        monthly_expenses=Decimal("1000.00"),
    )
    client = APIClient()
    client.force_authenticate(user=other)
    resp = client.get(f"/api/intake/fee-waiver/{fw.id}/")
    assert resp.status_code == 404


def test_cross_user_post_is_forbidden(db):
    """POST /intake/fee-waiver/ with another user's session returns 403."""
    owner = User.objects.create_user(username="fw_owner2", password="pass")
    attacker = User.objects.create_user(username="fw_attacker", password="pass")
    district = District.objects.create(
        code="ILND3",
        name="Illinois Northern 3",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=owner, district=district)
    client = APIClient()
    client.force_authenticate(user=attacker)
    payload = {
        "session": session.id,
        "household_size": 99,
        "monthly_income": "100.00",
        "monthly_expenses": "100.00",
        "receives_public_benefits": False,
        "benefit_types": [],
        "cannot_pay_full": True,
        "cannot_pay_installments": True,
    }
    resp = client.post("/api/intake/fee-waiver/", payload, format="json")
    assert resp.status_code == 403
    assert not FeeWaiverApplication.objects.filter(session=session).exists()


def test_create_fee_waiver_is_idempotent(setup):
    """Second POST to /intake/fee-waiver/ for same session updates, not duplicates."""
    client, session, _ = setup
    payload = {
        "session": session.id,
        "household_size": 1,
        "monthly_income": "1000.00",
        "monthly_expenses": "800.00",
        "receives_public_benefits": False,
        "benefit_types": [],
        "cannot_pay_full": True,
        "cannot_pay_installments": True,
    }
    client.post("/api/intake/fee-waiver/", payload, format="json")
    updated_payload = {**payload, "household_size": 3}
    resp = client.post("/api/intake/fee-waiver/", updated_payload, format="json")
    assert resp.status_code == 201
    assert FeeWaiverApplication.objects.filter(session=session).count() == 1
    assert FeeWaiverApplication.objects.get(session=session).household_size == 3
