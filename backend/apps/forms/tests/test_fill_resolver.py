"""Tests for the fill resolver: binding resolution."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.services.fill_resolver import resolve_binding
from apps.intake.models import (
    FormAnswer,
    IntakeSession,
    SOFACreditorPayment,
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


def test_resolve_answer_binding(session):
    FormAnswer.objects.create(session=session, form_type="form_107", field_key="q9", value="No")
    assert resolve_binding("answer:form_107.q9", session) == "No"


def test_resolve_answer_binding_missing_returns_empty(session):
    assert resolve_binding("answer:form_107.q9", session) == ""


def test_resolve_collection_binding_returns_list(session):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    SOFACreditorPayment.objects.create(
        report=report, creditor_name="Acme", total_paid=Decimal("100.00")
    )
    SOFACreditorPayment.objects.create(
        report=report, creditor_name="Beta", total_paid=Decimal("200.00")
    )
    vals = resolve_binding("sofa.creditor_payments[].creditor_name", session)
    assert vals == ["Acme", "Beta"]


def test_resolve_collection_binding_no_report_returns_empty_list(session):
    assert resolve_binding("sofa.creditor_payments[].creditor_name", session) == []


def test_resolve_scalar_binding_returns_str(session):
    SOFAReport.objects.create(session=session, has_creditor_payments=True, has_business=True)
    assert resolve_binding("sofa.has_business", session) == "True"


def test_resolve_scalar_binding_no_report_returns_empty(session):
    assert resolve_binding("sofa.has_business", session) == ""
