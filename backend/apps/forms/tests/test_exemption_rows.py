"""
Schedule C prints only the filer's own answers, and copies the rest from Schedule A/B.

Business intent: a sworn form must never show a law, an amount or an answer the filer didn't give,
and its property, line and value must be the ones Schedule A/B prints, so the two forms agree.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District, ExemptionCatalog
from apps.forms.schema import FieldSpec, FormSchema, GroupSpec
from apps.forms.services import exemption_items
from apps.forms.services.exemption_items import (
    ExemptionRow,
    exemption_rows,
    one_read_of_exemptions,
)
from apps.forms.services.fill_resolver import EXEMPTION_CELLS, resolve_binding, resolve_parts
from apps.intake.models import AssetInfo, ExemptionAnswers, ExemptionClaim, IntakeSession
from apps.intake.tests.builders import answer_exemptions

User = get_user_model()


def _district():
    return District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="exemptionrows", password="pw")
    district = _district()
    session = IntakeSession.objects.create(user=user, district=district, status="completed")
    answer_exemptions(session, no_claims=False)
    return session


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


def _row(session, line, description, value, kind=None):
    row = AssetInfo(session=session, ab_line=line, description=description, current_value=value)
    row.set_details({"kind": kind} if kind else {})
    row.save()
    return row


def _claim(session, asset, **fields):
    return ExemptionClaim.objects.create(session=session, asset=asset, **fields)


def test_a_claim_prints_its_items_name_line_and_value_and_its_own_law_and_amount(session):
    laptop = _row(session, "7", "Laptop", Decimal("300.00"))
    _claim(session, laptop, law="il_735_5_12_1001_b", amount_kind="dollars", amount=Decimal("100"))

    assert exemption_rows(_fresh(session)) == [
        ExemptionRow("Laptop", "7", "300.00", "dollars", "100.00", "735 ILCS 5/12-1001(b)")
    ]


def test_a_claim_whose_property_is_gone_never_prints(session):
    gone = _row(session, "7", "Demo Gone", Decimal("10"))
    _claim(session, gone, law="il_735_5_12_1001_b", amount_kind="dollars", amount=Decimal("1"))
    gone.delete()
    other = IntakeSession.objects.create(user=session.user, district=session.district)
    moved = _row(other, "7", "Demo Moved", Decimal("10"))
    _claim(session, moved, law="il_735_5_12_1001_b", amount_kind="dollars", amount=Decimal("1"))

    assert exemption_rows(_fresh(session)) == []


def test_claims_print_in_schedule_ab_order_and_an_items_claims_in_the_order_added(session):
    laptop = _row(session, "7", "Laptop", Decimal("300"))
    car = _row(session, "3", "Demo Car", Decimal("2000"))
    b, c = "il_735_5_12_1001_b", "il_735_5_12_1001_c"
    _claim(session, laptop, law=b, amount_kind="fair_market_value")
    _claim(session, car, law=c, amount_kind="fair_market_value")
    _claim(session, car, law=b, amount_kind="fair_market_value")

    rows = exemption_rows(_fresh(session))

    assert [(r.description, r.law) for r in rows] == [
        ("Demo Car", "735 ILCS 5/12-1001(c)"),
        ("Demo Car", "735 ILCS 5/12-1001(b)"),
        ("Laptop", "735 ILCS 5/12-1001(b)"),
    ]


def test_claims_follow_their_items_saved_order_across_kinds_of_one_line(session):
    savings = _row(session, "17", "Demo Savings", Decimal("50"), kind="savings")
    checking = _row(session, "17", "Demo Checking", Decimal("20"), kind="checking")
    law = "il_735_5_12_1001_b"
    _claim(session, checking, law=law, amount_kind="fair_market_value")
    _claim(session, savings, law=law, amount_kind="fair_market_value")

    rows = exemption_rows(_fresh(session))

    assert [r.line for r in rows] == ["17.3", "17.1"]


def test_a_short_description_prints_only_while_the_items_name_does_not_fit(session):
    long_name = "Bed, couch, table, kitchenware (secondhand)"  # fits no size (3g1 P2)
    item = _row(session, "6", long_name, Decimal("500"))
    _claim(
        session,
        item,
        law="il_735_5_12_1001_b",
        amount_kind="fair_market_value",
        short_description="  Bed, couch, table  ",
    )

    assert exemption_rows(_fresh(session))[0].description == "Bed, couch, table"

    item.description = "Beds"
    item.save()

    assert exemption_rows(_fresh(session))[0].description == "Beds"


def test_a_typed_law_prints_as_typed_and_needs_no_list_of_laws(session):
    ExemptionCatalog.objects.all().delete()
    item = _row(session, "7", "Laptop", Decimal("300"))
    _claim(
        session,
        item,
        law=None,
        other_law="  Demo Statute 1 ",
        amount_kind="dollars",
        amount=Decimal("5"),
    )

    assert exemption_rows(_fresh(session))[0].law == "Demo Statute 1"


def test_a_law_no_longer_listed_prints_nothing_and_a_law_beats_a_typed_law(session):
    item = _row(session, "7", "Laptop", Decimal("300"))
    _claim(session, item, law="no_such_law", amount_kind="fair_market_value")
    _claim(
        session, item, law="il_735_5_12_1001_c", other_law="Demo", amount_kind="fair_market_value"
    )

    rows = exemption_rows(_fresh(session))

    assert [r.law for r in rows] == ["", "735 ILCS 5/12-1001(c)"]


def test_an_amount_prints_only_under_a_dollar_amount(session):
    item = _row(session, "7", "Laptop", Decimal("300"))
    _claim(
        session,
        item,
        law="il_735_5_12_1001_b",
        amount_kind="fair_market_value",
        amount=Decimal("9"),
    )

    rows = exemption_rows(_fresh(session))

    assert (rows[0].amount_kind, rows[0].amount) == ("fair_market_value", "")


def test_a_zero_dollar_claim_and_a_zero_value_print_0_00(session):
    item = _row(session, "7", "Laptop", Decimal("0"))
    _claim(session, item, law="il_735_5_12_1001_b", amount_kind="dollars", amount=Decimal("0"))

    rows = exemption_rows(_fresh(session))

    assert (rows[0].value, rows[0].amount) == ("0.00", "0.00")


def test_a_value_schedule_ab_leaves_blank_prints_blank(session):
    item = _row(session, "7", "Laptop", None)
    _claim(session, item, law="il_735_5_12_1001_b", amount_kind="fair_market_value")

    assert exemption_rows(_fresh(session))[0].value == ""


def test_a_tax_refund_claim_prints_its_line_and_no_value(session):
    refund = _row(session, "28", "Demo refund", Decimal("400"), kind="federal")
    _claim(session, refund, law="il_735_5_12_1001_b", amount_kind="fair_market_value")

    rows = exemption_rows(_fresh(session))

    assert (rows[0].line, rows[0].value) == ("28", "")  # 3g1 P7


def test_the_rows_are_read_once_a_resolve(session):
    item = _row(session, "7", "Laptop", Decimal("300"))
    claim = _claim(
        session, item, law="il_735_5_12_1001_b", amount_kind="dollars", amount=Decimal("1")
    )
    fresh = _fresh(session)

    with one_read_of_exemptions():
        first = exemption_rows(fresh)
        claim.amount = Decimal("2")
        claim.save()
        assert exemption_rows(fresh) is first

    assert exemption_rows(fresh) != first  # outside, a save shows


def test_line_3_1_prints_only_under_line_3_yes(session):
    answers = ExemptionAnswers.objects.get(session=session)
    answers.line_1 = "state_and_federal"
    answers.line_3 = "yes"
    answers.line_3_1 = "no"
    answers.save()

    assert resolve_binding("exemptions.line_3_1", _fresh(session)) == "no"
    assert resolve_binding("exemptions.line_1", _fresh(session)) == "state_and_federal"
    assert resolve_binding("exemptions.line_3", _fresh(session)) == "yes"

    answers.line_3 = "no"
    answers.line_3_1 = "yes"  # stored under No, as an earlier Yes left it
    answers.save()

    assert resolve_binding("exemptions.line_3_1", _fresh(session)) == ""


def test_an_unanswered_page_prints_no_answer(db):
    user = User.objects.create_user(username="exemptionrows2", password="pw")
    district = _district()
    bare = IntakeSession.objects.create(user=user, district=district)

    for key in ("line_1", "line_3", "line_3_1"):
        assert resolve_binding(f"exemptions.{key}", _fresh(bare)) == ""


def test_each_column_binding_reads_its_cell_of_every_row(session):
    laptop = _row(session, "7", "Laptop", Decimal("300"))
    car = _row(session, "3", "Demo Car", Decimal("2000"))
    _claim(session, laptop, law="il_735_5_12_1001_b", amount_kind="dollars", amount=Decimal("100"))
    _claim(session, car, law="il_735_5_12_1001_c", amount_kind="fair_market_value")
    fresh = _fresh(session)
    rows = exemption_rows(fresh)

    assert set(EXEMPTION_CELLS) == {
        "description",
        "line",
        "value",
        "amount_kind",
        "amount",
        "law",
    }
    for attr in EXEMPTION_CELLS:
        assert resolve_binding(f"exemptions.claims[].{attr}", fresh) == [
            getattr(r, attr) for r in rows
        ]


def test_a_resolve_reads_the_rows_once_for_every_box_that_asks(session, monkeypatch):
    columns = ("description", "line", "law")
    fields = []
    for column in columns:
        for row in (1, 2):
            fields.append(
                FieldSpec(
                    pdf_field=f"{column}{row}",
                    type="text",
                    source="asked",
                    page=1,
                    label=column,
                    required=False,
                    conditional_on=None,
                    value=None,
                    rule=None,
                    ingest_key=None,
                    binding=f"exemptions.claims[].{column}",
                    repeat="c",
                    repeat_capacity=2,
                    row=row,
                    legal_review=False,
                )
            )
    schema = FormSchema(
        "form_107",
        "b_107_0425-form.pdf",
        "v1",
        fields,
        groups={"c": GroupSpec("c", extra_page=1, number=None, number_boxes={})},
    )
    item = _row(session, "7", "Laptop", Decimal("300"))
    _claim(session, item, law="il_735_5_12_1001_b", amount_kind="fair_market_value")
    reads = []
    real = exemption_items.exemption_items

    def spy(s):
        reads.append(s.pk)
        return real(s)

    monkeypatch.setattr(exemption_items, "exemption_items", spy)

    parts = resolve_parts(schema, _fresh(session))["parts"]

    assert parts[0]["values"]["description1"] == "Laptop"
    assert len(reads) == 1
