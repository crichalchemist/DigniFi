"""Regression tests for BIZ-57: cross-session write IDOR on Asset/Debt.

Business intent: a user must never attach (or re-parent) an asset or debt row
onto another user's intake session, even though the ``session`` PK is
client-supplied and enumerable. ``get_queryset`` scopes reads; these guard writes.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import AssetInfo, DebtInfo, IntakeSession
from apps.users.models import User


def _district(code="ILND"):
    return District.objects.create(
        code=code,
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def attacker_and_victim_session(db):
    district = _district()
    victim = User.objects.create_user(username="victim", password="pw")
    attacker = User.objects.create_user(username="attacker", password="pw")
    victim_session = IntakeSession.objects.create(user=victim, district=district)
    client = APIClient()
    client.force_authenticate(user=attacker)
    return client, victim_session


@pytest.mark.django_db
class TestCrossSessionWriteIDOR:
    def test_reject_asset_write_to_foreign_session(self, attacker_and_victim_session):
        client, victim_session = attacker_and_victim_session
        resp = client.post(
            "/api/intake/assets/",
            {
                "session": victim_session.pk,
                "asset_type": "vehicle",
                "description": "Injected car",
                "current_value": "5000.00",
                "amount_owed": "0",
            },
            format="json",
        )
        assert resp.status_code == 403
        assert AssetInfo.objects.filter(session=victim_session).count() == 0

    def test_reject_debt_write_to_foreign_session(self, attacker_and_victim_session):
        client, victim_session = attacker_and_victim_session
        resp = client.post(
            "/api/intake/debts/",
            {
                "session": victim_session.pk,
                "creditor_name": "Injected Creditor",
                "debt_type": "credit_card",
                "priority_classification": "unsecured",
                "amount_owed": "1000.00",
                "monthly_payment": "50.00",
            },
            format="json",
        )
        assert resp.status_code == 403
        assert DebtInfo.objects.filter(session=victim_session).count() == 0

    def test_owner_can_still_write_to_own_session(self, db):
        """The guard must not block the legitimate session owner."""
        district = _district(code="ILND2")
        owner = User.objects.create_user(username="owner", password="pw")
        own_session = IntakeSession.objects.create(user=owner, district=district)
        client = APIClient()
        client.force_authenticate(user=owner)
        resp = client.post(
            "/api/intake/assets/",
            {
                "session": own_session.pk,
                "asset_type": "vehicle",
                "description": "My car",
                "current_value": "5000.00",
                "amount_owed": "0",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert AssetInfo.objects.filter(session=own_session).count() == 1
