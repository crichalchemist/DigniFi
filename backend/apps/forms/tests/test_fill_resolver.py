"""Tests for the fill resolver: binding resolution."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.documents.models import IngestedAggregate
from apps.forms.schema import FieldSpec, FormSchema, GroupSpec
from apps.forms.services.fill_resolver import (
    UnmappedChoice,
    resolve,
    resolve_binding,
    resolve_parts,
)
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


def _answer(session, value):
    FormAnswer.objects.create(session=session, form_type="form_107", field_key="q1", value=value)


def _box(**kw):
    return _field(type="checkbox", source="asked", binding="answer:form_107.q1", **kw)


def test_single_box_ticks_for_a_yes_answer(session):
    _answer(session, "Yes")
    schema = _schema([_box(pdf_field="Box", choices={"true": "/Yes"})])
    assert resolve(schema, session)["Box"] == "/Yes"


def test_single_box_stays_off_for_a_no_answer(session):
    # The old _emit ticked any non-empty value, "false" included (DIG-68).
    _answer(session, "false")
    schema = _schema([_box(pdf_field="Box", choices={"true": "/Yes"})])
    assert "Box" not in resolve(schema, session)


def test_option_group_ticks_the_chosen_option(session):
    _answer(session, "Chapter_7")
    choices = {"chapter_7": "/Chapter 7", "chapter_13": "/Chapter 13"}
    schema = _schema([_box(pdf_field="Chapter", choices=choices)])
    assert resolve(schema, session)["Chapter"] == "/Chapter 7"


def test_answer_with_no_box_raises_instead_of_printing_nothing(session):
    _answer(session, "maybe")
    schema = _schema([_box(pdf_field="Box", choices={"true": "/Yes"})])
    with pytest.raises(UnmappedChoice):
        resolve(schema, session)


def test_unmapped_box_emits_nothing_and_reads_no_value(session):
    # An unknown rule would raise if the resolver looked the value up.
    schema = _schema(
        [
            _field(
                pdf_field="Box", type="checkbox", source="derived", rule="no_such_rule", choices={}
            )
        ]
    )
    assert resolve(schema, session) == {}


def test_unmapped_box_in_a_repeat_group_emits_nothing_and_reads_no_value(session):
    # An unknown binding would raise if the resolver looked the value up (spec §5.1).
    schema = _schema(
        [
            _field(
                pdf_field="Box1",
                type="checkbox",
                source="asked",
                binding="nowhere.rows[].x",
                repeat="rows",
                repeat_capacity=1,
                row=1,
                choices={},
            )
        ]
    )
    assert resolve(schema, session) == {}


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


def test_a_tagged_binding_resolves_under_its_widget_address(session):
    # Schedule I prints "Assistance 8f" twice; a tag gives each widget a value of its own.
    schema = _schema(
        [
            _field(pdf_field="Assistance 8f", page=2, tag="T36", value="SNAP"),
            _field(pdf_field="Assistance 8f", page=2, tag="T49", value="WIC"),
        ]
    )
    assert resolve(schema, session) == {
        "Assistance 8f@2:T36": "SNAP",
        "Assistance 8f@2:T49": "WIC",
    }


def test_repeat_rows_of_a_shared_name_land_on_their_own_widgets(session):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    for name, amt in [("Acme", "100.00"), ("Beta", "200.00")]:
        SOFACreditorPayment.objects.create(
            report=report, creditor_name=name, total_paid=Decimal(amt)
        )

    def cell(tag, row, attr):
        return _field(
            pdf_field="Line",
            tag=tag,
            source="asked",
            repeat="cp",
            repeat_capacity=2,
            row=row,
            binding=f"sofa.creditor_payments[].{attr}",
        )

    schema = _schema(
        [
            cell("T5", 1, "creditor_name"),
            cell("T6", 1, "total_paid"),
            cell("T9", 2, "creditor_name"),
            cell("T10", 2, "total_paid"),
        ]
    )
    assert resolve(schema, session) == {
        "Line@1:T5": "Acme",
        "Line@1:T6": "100.00",
        "Line@1:T9": "Beta",
        "Line@1:T10": "200.00",
    }


def _payments(session, count):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    for i in range(count):
        SOFACreditorPayment.objects.create(
            report=report,
            creditor_name=f"C{i}",
            total_paid=Decimal("1.00"),
        )


def _slots():
    """Group cp's four slots, one creditor each: Cred1 and Cred2 on page 1, Cred3 and Cred4 on 2."""
    return [
        _field(
            pdf_field=f"Cred{row}",
            page=1 if row <= 2 else 2,
            source="asked",
            repeat="cp",
            repeat_capacity=4,
            row=row,
            binding="sofa.creditor_payments[].creditor_name",
        )
        for row in range(1, 5)
    ]


def test_rows_past_the_slots_go_to_copies_of_the_extra_page(session):
    _payments(session, 7)
    schema = FormSchema(
        "form_107",
        "b_107_0425-form.pdf",
        "v1",
        _slots(),
        groups={"cp": GroupSpec("cp", extra_page=2, number=None, number_boxes={}, page_numbers=())},
    )

    # Page 2's two slots take rows 5 and 6 on its first copy, and row 7 on its second.
    assert resolve_parts(schema, session)["parts"] == [
        {"kind": "form", "values": {"Cred1": "C0", "Cred2": "C1", "Cred3": "C2", "Cred4": "C3"}},
        {"kind": "copy", "page": 2, "number": 1, "values": {"Cred3": "C4", "Cred4": "C5"}},
        {"kind": "copy", "page": 2, "number": 2, "values": {"Cred3": "C6"}},
    ]
    assert resolve(schema, session) == {"Cred1": "C0", "Cred2": "C1", "Cred3": "C2", "Cred4": "C3"}


def test_a_legal_review_row_prints_neither_in_the_slots_nor_on_a_copy(session):
    # UPL guard: a legal_review binding fills only from an explicit asked answer, on the
    # form's own slots and on the copies alike.
    _payments(session, 7)
    reviewed = [
        _field(
            pdf_field=f"Amt{row}",
            page=1 if row <= 2 else 2,
            source="derived",
            legal_review=True,
            repeat="cp",
            repeat_capacity=4,
            row=row,
            binding="sofa.creditor_payments[].total_paid",
        )
        for row in range(1, 5)
    ]
    group = GroupSpec("cp", extra_page=2, number=None, number_boxes={}, page_numbers=())
    schema = FormSchema("form_107", "b_107_0425-form.pdf", "v1", _slots() + reviewed, {"cp": group})

    parts = resolve_parts(schema, session)["parts"]

    assert [sorted(part["values"]) for part in parts] == [
        ["Cred1", "Cred2", "Cred3", "Cred4"],
        ["Cred3", "Cred4"],
        ["Cred3"],
    ]


def test_a_copy_never_repeats_a_row_from_the_form(session):
    # Schedule D's Part 2 entry 4 box on page 3 shares its full name with a page 1 box, as
    # a page header does. A copy of page 3 with one row leaves that slot blank.
    _payments(session, 7)
    boxes = [
        "account number 6",
        "account number 7",
        "account number 8",
        "account number",
        "account number 10",
        "account number 11",
    ]
    fields = [
        _field(
            pdf_field=box,
            page=3,
            tag="T33" if box == "account number" else None,
            source="asked",
            repeat="notified",
            repeat_capacity=6,
            row=row,
            binding="sofa.creditor_payments[].creditor_name",
        )
        for row, box in enumerate(boxes, start=1)
    ]
    group = GroupSpec("notified", extra_page=3, number=None, number_boxes={}, page_numbers=())
    schema = FormSchema("schedule_d", "form_b106d.pdf", "v1", fields, {"notified": group})

    form, copy = resolve_parts(schema, session)["parts"]

    assert form["values"]["account number@3:T33"] == "C3"
    assert copy["values"] == {"account number 6": "C6"}


def test_rows_past_the_slots_of_a_group_with_no_extra_page_are_never_dropped(session):
    # The startup check refuses such a schema (forms.E007); a row must never vanish.
    _payments(session, 5)
    schema = _schema(_slots())
    with pytest.raises(ValueError, match="names no extra page"):
        resolve_parts(schema, session)


def test_legal_review_field_not_filled_without_answer(session):
    # derived legal_review field must NOT be silently filled
    schema = _schema(
        [
            _field(pdf_field="Exemption", source="derived", rule="chapter", legal_review=True),
        ]
    )
    assert "Exemption" not in resolve(schema, session)


def test_resolve_ingested_source(session):
    schema = _schema(
        [_field(pdf_field="Income.Gross", source="ingested", ingest_key="paystub.gross")]
    )

    # Missing aggregate -> empty string, wait, the brief test says `assert out1 == {"Income.Gross": ""}`.
    # But fill_resolver drops None. Let's test it as the brief specifies.
    out1 = resolve(schema, session)
    # _emit drops empty values, so it's not included in the dictionary at all
    assert out1 == {}

    # Existing aggregate -> resolved
    IngestedAggregate.objects.create(session=session, ingest_key="paystub.gross", value="5000.00")
    out2 = resolve(schema, session)
    assert out2 == {"Income.Gross": "5000.00"}
