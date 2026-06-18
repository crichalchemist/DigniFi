"""Tests for DischargeabilityClassifier."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.services.dischargeability_classifier import (
    DischargeabilityClassifier,
    classify_debt,
)
from apps.intake.models import DebtInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session_with_debts(db):
    user = User.objects.create_user(username="discharge", password="pass")
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
        is_dischargeable=False,
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="Chase",
        amount_owed=Decimal("5000"),
        is_secured=False,
        is_priority=False,
        debt_type="credit_card",
        is_dischargeable=True,
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="IRS",
        amount_owed=Decimal("3000"),
        is_secured=False,
        is_priority=True,
        debt_type="taxes",
        is_dischargeable=False,
    )
    return session


@pytest.mark.django_db
class TestClassifyDebt:
    def test_student_loan_non_dischargeable(self):
        debt = type("D", (), {"debt_type": "student_loan"})()
        result = classify_debt(debt)
        assert result["dischargeable"] is False
        assert "523" in result["reason"]

    def test_credit_card_dischargeable(self):
        debt = type("D", (), {"debt_type": "credit_card"})()
        result = classify_debt(debt)
        assert result["dischargeable"] is True

    def test_child_support_non_dischargeable(self):
        debt = type("D", (), {"debt_type": "child_support"})()
        result = classify_debt(debt)
        assert result["dischargeable"] is False

    def test_unknown_type_dischargeable(self):
        debt = type("D", (), {"debt_type": "medical"})()
        result = classify_debt(debt)
        assert result["dischargeable"] is True


@pytest.mark.django_db
class TestDischargeabilityClassifier:
    def test_evaluate_flags_student_loan(self, session_with_debts):
        classifier = DischargeabilityClassifier(session_with_debts)
        results = classifier.evaluate()
        student = [r for r in results if r["debt_type"] == "student_loan"][0]
        assert student["dischargeable"] is False
        assert student["proceeding_needed"] is True

    def test_evaluate_counts_dischargeable(self, session_with_debts):
        classifier = DischargeabilityClassifier(session_with_debts)
        results = classifier.evaluate()
        dischargeable = sum(1 for r in results if r["dischargeable"])
        assert dischargeable == 1
