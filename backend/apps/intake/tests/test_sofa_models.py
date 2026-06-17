"""Tests for the SOFA hybrid data model + FormAnswer store."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.districts.models import District
from apps.intake.models import (
    FormAnswer,
    IntakeSession,
    SOFACreditorPayment,
    SOFAPriorIncome,
    SOFAReport,
)

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="testuser", password="pw")
    d = District.objects.create(
        code="ilnd",
        name="N.D. Ill.",
        court_name="x",
        state="IL",
        filing_fee_chapter_7="338.00",
    )
    return IntakeSession.objects.create(user=user, district=d, status="in_progress", current_step=1)


def test_sofa_report_children_and_encrypted_amounts(session):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    SOFAPriorIncome.objects.create(
        report=report,
        year=2025,
        source="Wages",
        gross_amount=Decimal("42000.00"),
    )
    SOFACreditorPayment.objects.create(
        report=report,
        creditor_name="Acme Card",
        total_paid=Decimal("1200.50"),
    )

    report.refresh_from_db()
    assert session.sofa_report.has_creditor_payments is True
    assert report.prior_income.first().gross_amount == Decimal("42000.00")
    assert report.creditor_payments.first().total_paid == Decimal("1200.50")


def test_form_answer_unique_per_session_form_key(session):
    FormAnswer.objects.create(session=session, form_type="form_107", field_key="q9", value="No")
    with pytest.raises(IntegrityError):
        FormAnswer.objects.create(
            session=session, form_type="form_107", field_key="q9", value="Yes"
        )
