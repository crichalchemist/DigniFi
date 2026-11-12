"""What Schedule C copies from Schedule A/B (3g1 B6, B12, B13, B16)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.exemption_items import (
    _groups,
    ab_line_label,
    ab_value,
    exemption_items,
    fits_description,
    fits_law,
)
from apps.forms.services.fill_resolver import _key, resolve_parts
from apps.intake.asset_lines import LINES, exemption_item_name, ordered_assets
from apps.intake.models import AssetInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="exemptionitems", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def _row(session, line, description="", value=None, entire=None, **details):
    row = AssetInfo.objects.create(
        session=session,
        ab_line=line,
        description=description,
        current_value=None if value is None else Decimal(value),
        entire_value=None if entire is None else Decimal(entire),
    )
    row.set_details(details)
    row.save()
    return row


def _label(session, row):
    return ab_line_label(ordered_assets(IntakeSession.objects.get(pk=session.pk)), row)


def test_a_car_is_named_by_make_model_and_year(session):
    full = _row(session, "3", make="Honda", model="CR-V EX", year="2021")
    no_model = _row(session, "3", make="Honda", year="2021")

    assert exemption_item_name(full) == "Honda CR-V EX 2021"
    assert exemption_item_name(no_model) == "Honda 2021"


def test_cash_is_named_cash_and_never_one_item(session):
    assert exemption_item_name(_row(session, "16", value="40")) == "Cash"


def test_a_home_is_named_by_its_street(session):
    row = _row(session, "1", street="7823 S Sangamon St")

    assert exemption_item_name(row) == "7823 S Sangamon St"


def test_a_described_row_is_named_by_its_description(session):
    row = _row(session, "17", description="  JPMorgan Chase ", kind="checking")

    assert exemption_item_name(row) == "JPMorgan Chase"


def test_customer_lists_with_no_description_are_named_in_the_forms_words(session):
    row = _row(session, "43", has_personal_info=False)

    assert exemption_item_name(row) == "Customer lists"


def test_each_row_gets_the_line_schedule_ab_prints_for_it(session):
    car = _row(session, "3", make="Honda", year="2015", value="4000")
    clothes = _row(session, "11", description="Clothes", value="300")
    checking = _row(session, "17", description="JPMorgan Chase", kind="checking", value="900")
    savings = _row(session, "17", description="JPMorgan Chase", kind="savings", value="500")
    k401 = _row(session, "21", description="Vanguard", kind="401k", value="9000")
    home = _row(session, "1", street="7823 S Sangamon St", value="90000")

    labels = [_label(session, r) for r in (car, clothes, checking, savings, k401, home)]

    assert labels == ["3.1", "11", "17.1", "17.3", "21", "1.1"]
    assert not any(label.endswith(".") for label in labels)


def test_a_row_past_ab_boxes_gets_its_sheet_number(session):
    cars = [_row(session, "3", make="Car", year=str(2000 + n)) for n in range(5)]
    checking = [
        _row(session, "17", description=f"Bank {n}", kind="checking", value="1") for n in range(3)
    ]
    clothes = [_row(session, "11", description=f"Clothes {n}", value="1") for n in range(2)]

    assert _label(session, cars[4]) == "3.5"
    assert _label(session, checking[2]) == "17c.3"
    assert _label(session, clothes[1]) == "11.2"


def test_a_sheet_label_is_the_number_ab_itself_prints(session):
    checking = [
        _row(session, "17", description=f"Bank {n}", kind="checking", value="1") for n in range(3)
    ]

    parts = resolve_parts(load_schema("schedule_a_b"), IntakeSession.objects.get(pk=session.pk))
    sheet = next(
        p for p in parts["parts"] if p["kind"] == "sheet" and p["group"] == "ab_17_checking"
    )

    assert _label(session, checking[2]) == sheet["rows"][0]["line"]


def test_a_tax_refund_row_is_labelled_by_its_line_and_has_no_value(session):
    row = _row(session, "28", description="Federal refund", kind="federal", value="900")

    assert (_label(session, row), ab_value(row)) == ("28", None)


def test_every_catalog_line_and_kind_gets_a_label(session):
    assert len(_groups()) == 59
    for line in LINES:
        if line.shape == "gate":
            continue
        for kind, _ in line.kinds or ((None, 0),):
            details = {"kind": kind} if kind else {}
            row = _row(session, line.key, description="Demo item", value="1", **details)
            label = _label(session, row)
            assert label and not label.endswith(".")
            row.delete()


def test_the_value_is_what_ab_prints_in_the_portion_box(session):
    fit_row = _row(session, "3", make="Fit", year="2019", value="4300", entire="8600")
    unknown = _row(session, "16")
    zero = _row(session, "16", value="0")
    schema = load_schema("schedule_a_b")
    parts = resolve_parts(schema, IntakeSession.objects.get(pk=session.pk))
    box = next(f for f in schema.fields if f.binding == "assets.line_3[].value" and f.row == 1)

    assert ab_value(fit_row) == "4300.00"
    assert ab_value(fit_row) == parts["parts"][0]["values"][_key(box)]
    assert ab_value(unknown) is None
    assert ab_value(zero) == "0.00"


def test_a_description_fits_until_the_box_is_full():
    for text in ("Honda Civic 2015", "Bed, couch, table, kitchenware", "M" * 18):
        assert fits_description(text)
    for text in (
        "Bed, couch, table, kitchenware (secondhand)",
        "Driving payouts already earned, not yet paid by the apps",
        "M" * 19,
    ):
        assert not fits_description(text)


def test_a_law_fits_until_its_box_is_full():
    assert fits_law("word " * 40)
    assert not fits_law("word " * 60)


def test_a_letter_the_form_cannot_print_never_fits():
    assert not fits_description("Demo ☃")
    assert not fits_law("Demo ☃")


def test_the_items_are_the_rows_with_a_line_in_ab_order(session):
    AssetInfo.objects.create(session=session, ab_line=None, description="Old row")
    long = _row(
        session, "6", description="Bed, couch, table, kitchenware (secondhand)", value="500"
    )
    car = _row(session, "3", make="Honda", model="Civic", year="2015", value="4000")

    items = exemption_items(IntakeSession.objects.get(pk=session.pk))

    assert [(i.id, i.name, i.line_label, i.value, i.description_fits) for i in items] == [
        (car.pk, "Honda Civic 2015", "3.1", "4000.00", True),
        (long.pk, "Bed, couch, table, kitchenware (secondhand)", "6", "500.00", False),
    ]
