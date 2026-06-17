"""Tests for the fill resolver: binding resolution."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import FieldSpec, FormSchema
from apps.forms.services.fill_resolver import RepeatOverflow, resolve, resolve_binding
from apps.intake.models import (
    DebtorInfo,
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


# ── Task 8: resolve() dispatch, conditionals, repeats, UPL ────────────


def _field(**kw):
    base = {
        "pdf_field": "F",
        "type": "text",
        "source": "constant",
        "on_states": [],
        "page": 1,
        "label": "",
        "required": False,
        "conditional_on": None,
        "value": None,
        "rule": None,
        "ingest_key": None,
        "binding": None,
        "repeat": None,
        "repeat_capacity": None,
        "row": None,
        "legal_review": False,
    }
    base.update(kw)
    return FieldSpec(**base)


def _schema(fields):
    return FormSchema("form_107", "b_107_0425-form.pdf", "v1", fields)


def test_constant_and_derived_dispatch(session):
    from datetime import date

    DebtorInfo.objects.create(
        session=session,
        first_name="Maria",
        middle_name="",
        last_name="Torres",
        ssn="000-00-0000",
        date_of_birth=date(1985, 6, 1),
        phone="555-0100",
        email="maria@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
        household_size=2,
    )
    schema = _schema(
        [
            _field(pdf_field="Chapter", source="constant", value="7"),
            _field(pdf_field="Debtor 1", source="derived", rule="full_name"),
        ]
    )
    out = resolve(schema, session)
    assert out["Chapter"] == "7"
    assert out["Debtor 1"] == "Maria Torres"


def test_conditional_section_skipped_when_predicate_false(session):
    schema = _schema(
        [
            _field(
                pdf_field="BizName", source="constant", value="X", conditional_on="has_business"
            ),
        ]
    )
    # no SOFAReport → has_business False → field skipped
    assert "BizName" not in resolve(schema, session)


def test_none_value_dropped(session):
    schema = _schema(
        [
            _field(pdf_field="Inert", source="ingested", ingest_key="x"),
        ]
    )
    assert "Inert" not in resolve(schema, session)


def test_checkbox_emits_on_state(session):
    FormAnswer.objects.create(
        session=session,
        form_type="form_107",
        field_key="q1",
        value="yes",
    )
    schema = _schema(
        [
            _field(
                pdf_field="Box",
                type="checkbox",
                source="asked",
                on_states=["/Yes"],
                binding="answer:form_107.q1",
            ),
        ]
    )
    assert resolve(schema, session)["Box"] == "/Yes"


def test_repeat_group_expands_rows(session):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    for name, amt in [("Acme", "100.00"), ("Beta", "200.00")]:
        SOFACreditorPayment.objects.create(
            report=report,
            creditor_name=name,
            total_paid=Decimal(amt),
        )
    schema = _schema(
        [
            _field(
                pdf_field="Cred1",
                source="asked",
                repeat="cp",
                repeat_capacity=3,
                row=1,
                binding="sofa.creditor_payments[].creditor_name",
            ),
            _field(
                pdf_field="Cred2",
                source="asked",
                repeat="cp",
                repeat_capacity=3,
                row=2,
                binding="sofa.creditor_payments[].creditor_name",
            ),
            _field(
                pdf_field="Cred3",
                source="asked",
                repeat="cp",
                repeat_capacity=3,
                row=3,
                binding="sofa.creditor_payments[].creditor_name",
            ),
        ]
    )
    out = resolve(schema, session)
    assert out["Cred1"] == "Acme"
    assert out["Cred2"] == "Beta"
    assert "Cred3" not in out  # only two rows of data


def test_repeat_overflow_raises(session):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    for i in range(4):
        SOFACreditorPayment.objects.create(
            report=report,
            creditor_name=f"C{i}",
            total_paid=Decimal("1.00"),
        )
    schema = _schema(
        [
            _field(
                pdf_field="Cred1",
                source="asked",
                repeat="cp",
                repeat_capacity=3,
                row=1,
                binding="sofa.creditor_payments[].creditor_name",
            ),
        ]
    )
    with pytest.raises(RepeatOverflow):
        resolve(schema, session)


def test_legal_review_field_not_filled_without_answer(session):
    # derived legal_review field must NOT be silently filled
    schema = _schema(
        [
            _field(pdf_field="Exemption", source="derived", rule="chapter", legal_review=True),
        ]
    )
    assert "Exemption" not in resolve(schema, session)
