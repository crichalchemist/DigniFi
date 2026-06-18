"""Tests for DischargeabilityService."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.services.dischargeability_service import DischargeabilityService
from apps.intake.models import AdversaryProceeding, DebtInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session_with_student_loan(db):
    user = User.objects.create_user(username="dsvctest", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtInfo.objects.create(
        session=session,
        creditor_name="Navient",
        amount_owed=Decimal("28000"),
        is_secured=False,
        is_priority=False,
        debt_type="student_loan",
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="Chase",
        amount_owed=Decimal("5000"),
        is_secured=False,
        is_priority=False,
        debt_type="credit_card",
    )
    return session


@pytest.mark.django_db
class TestDischargeabilityService:
    def test_flags_student_loan(self, session_with_student_loan):
        svc = DischargeabilityService(session_with_student_loan)
        svc.evaluate()
        debt = DebtInfo.objects.get(creditor_name="Navient")
        assert debt.is_dischargeable is False
        assert debt.adversary_proceeding_needed is True

    def test_creates_adversary_proceeding(self, session_with_student_loan):
        svc = DischargeabilityService(session_with_student_loan)
        svc.evaluate()
        aps = AdversaryProceeding.objects.filter(session=session_with_student_loan)
        assert aps.count() == 1
        assert aps.first().proceeding_type == "student_loan"

    def test_does_not_duplicate_proceedings(self, session_with_student_loan):
        svc = DischargeabilityService(session_with_student_loan)
        svc.evaluate()
        svc.evaluate()
        assert AdversaryProceeding.objects.filter(session=session_with_student_loan).count() == 1


@pytest.mark.django_db
class TestDischargeabilityEndToEnd:
    def test_student_loan_full_flow(self):
        """Student loan -> classify -> flag -> adversary proceeding -> API."""
        session = IntakeSession.objects.create(
            user=User.objects.create_user(username="e2e_disc", password="pass"),
            district=District.objects.create(
                code="ILND",
                name="Northern District of Illinois",
                state="IL",
                court_name="U.S. Bankruptcy Court",
                filing_fee_chapter_7=Decimal("338"),
            ),
        )
        DebtInfo.objects.create(
            session=session,
            creditor_name="Sallie Mae",
            amount_owed=Decimal("35000"),
            is_secured=False,
            is_priority=False,
            debt_type="student_loan",
        )

        svc = DischargeabilityService(session)
        results = svc.evaluate()
        assert len(results) == 1
        assert results[0]["dischargeable"] is False

        debt = DebtInfo.objects.get(creditor_name="Sallie Mae")
        assert debt.is_dischargeable is False
        assert debt.adversary_proceeding_needed is True

        ap = AdversaryProceeding.objects.get(session=session)
        assert ap.proceeding_type == "student_loan"
        assert ap.status == "identified"
