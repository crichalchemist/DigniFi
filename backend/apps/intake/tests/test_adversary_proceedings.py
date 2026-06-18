"""Tests for AdversaryProceeding model and DebtInfo dischargeability fields."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import AdversaryProceeding, DebtInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session_with_student_loan(db):
    user = User.objects.create_user(username="adversary", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    debt = DebtInfo.objects.create(
        session=session,
        creditor_name="Navient",
        amount_owed=Decimal("28000"),
        is_secured=False,
        is_priority=False,
        debt_type="student_loan",
    )
    return session, debt


@pytest.mark.django_db
class TestAdversaryProceeding:
    def test_create_proceeding(self, session_with_student_loan):
        session, debt = session_with_student_loan
        ap = AdversaryProceeding.objects.create(
            session=session,
            debt=debt,
            proceeding_type="student_loan",
            lender_name="Navient",
            loan_amount=Decimal("28000"),
        )
        assert ap.status == "identified"
        assert ap.proceeding_type == "student_loan"

    def test_debt_flagged_non_dischargeable(self, session_with_student_loan):
        session, debt = session_with_student_loan
        debt.is_dischargeable = False
        debt.adversary_proceeding_needed = True
        debt.save()
        debt.refresh_from_db()
        assert debt.is_dischargeable is False
        assert debt.adversary_proceeding_needed is True
