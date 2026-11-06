"""Schedule A/B's line catalog and the records that hold a filer's answers (3b spec §3).

Business intent: the catalog is the one list of the form's lines. A filer who runs no business
and no farm answers 35 lines, and a yes to both gates opens 12 more. What a filer typed on an
asset line is filer data, so it is ciphertext in the table and every ordering happens in Python.
"""

from decimal import Decimal

import pytest
from django.db import connection

from apps.districts.models import District
from apps.intake.asset_lines import (
    LINE_BY_KEY,
    LINES,
    PROPERTY_KINDS,
    WHO,
    ordered_assets,
    rows_on,
    shown_lines,
)
from apps.intake.models import AssetInfo, AssetLineAnswers, IntakeSession
from apps.users.models import User


def test_a_filer_with_no_business_or_farm_answers_35_lines():
    assert len(shown_lines({})) == 35


def test_yes_to_both_gates_shows_47_lines():
    assert len(shown_lines({"37": "yes", "46": "yes"})) == 47


def test_a_no_to_a_gate_keeps_its_lines_hidden():
    assert len(shown_lines({"37": "no", "46": "no"})) == 35
    assert len(shown_lines({"37": "yes"})) == 42


def test_part_four_has_twenty_lines():
    assert sum(1 for line in LINES if line.part == 4) == 20


def test_every_line_is_found_by_its_key_and_keys_are_not_repeated():
    assert len(LINE_BY_KEY) == len(LINES)
    assert LINE_BY_KEY["17"].kinds == (("checking", 2), ("savings", 2), ("cd", 1), ("other", 4))
    assert LINE_BY_KEY["44"].capacity == 6
    assert LINE_BY_KEY["53"].shape == "shared_box" and LINE_BY_KEY["53"].kinds == ()
    assert LINE_BY_KEY["38"].gate == "37" and LINE_BY_KEY["47"].gate == "46"
    assert WHO == ("only_you", "with_someone")
    assert len(PROPERTY_KINDS) == 8


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def _row(session, ab_line, **fields):
    return AssetInfo.objects.create(session=session, ab_line=ab_line, **fields)


def test_rows_order_by_line_then_id_not_by_ciphertext(session):
    # Created out of order, with values whose ciphertext order has nothing to do with the form's.
    late = _row(session, "35", description="zzz")
    first_on_3 = _row(session, "3", description="aaa")
    second_on_3 = _row(session, "3", description="zzz")
    early = _row(session, "1", description="mmm")
    assert [row.pk for row in ordered_assets(session)] == [
        early.pk,
        first_on_3.pk,
        second_on_3.pk,
        late.pk,
    ]


def test_an_old_row_with_no_line_sorts_before_every_line(session):
    on_line = _row(session, "1")
    old = AssetInfo.objects.create(session=session, asset_type="vehicle", description="old")
    assert old.ab_line is None
    assert [row.pk for row in ordered_assets(session)] == [old.pk, on_line.pk]


def test_rows_on_a_line_and_kind_come_back_in_the_order_given(session):
    one = _row(session, "17")
    one.set_details({"kind": "savings"})
    one.save()
    two = _row(session, "17")
    two.set_details({"kind": "checking"})
    two.save()
    other = _row(session, "18")
    rows = [one, two, other]
    assert rows_on(rows, "17") == [one, two]
    assert rows_on(rows, "17", "checking") == [two]
    assert rows_on(rows, "18") == [other]
    assert rows_on(rows, "19") == []


def test_details_start_empty_and_read_back_what_was_stored(session):
    row = _row(session, "1")
    assert row.get_details() == {}
    row.set_details({"kind": "condo", "who": "only_you", "percent": "50"})
    row.save()
    row.refresh_from_db()
    assert row.get_details() == {"kind": "condo", "who": "only_you", "percent": "50"}


def test_a_null_amount_is_stored_as_not_given(session):
    row = _row(session, "1", current_value=None, entire_value=None)
    row.refresh_from_db()
    assert row.current_value is None and row.entire_value is None
    assert row.description == "" and row.financial_institution == ""


def test_line_answers_start_empty_and_a_null_removes_the_key(session):
    record = AssetLineAnswers.objects.create(session=session)
    assert record.get_answers() == {}
    record.merge({"1": "yes", "37": "no"})
    record.merge({"37": None, "46": "yes"})
    record.save()
    record.refresh_from_db()
    assert record.get_answers() == {"1": "yes", "46": "yes"}
    assert session.asset_lines == record


def test_the_asset_columns_and_line_answers_are_ciphertext_in_the_table(session):
    row = _row(
        session,
        "17",
        description="Harborline Savings",
        financial_institution="Harborline Bank",
        current_value=Decimal("4321.50"),
        entire_value=Decimal("8765.25"),
        amount_owed=Decimal("111.11"),
        account_number="9876",
    )
    row.set_details({"kind": "savings", "note": "emergency fund"})
    row.save()
    record = AssetLineAnswers.objects.create(session=session)
    record.merge({"1": "yes"})
    record.save()
    columns = (
        "ab_line",
        "details",
        "description",
        "financial_institution",
        "current_value",
        "entire_value",
        "amount_owed",
        "account_number",
    )
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {', '.join(columns)} FROM asset_info WHERE id = %s", [row.pk])
        stored = dict(zip(columns, cursor.fetchone(), strict=True))
        cursor.execute("SELECT answers FROM asset_line_answers WHERE id = %s", [record.pk])
        (answers,) = cursor.fetchone()
    assert all(value.startswith("gAAAAA") for value in stored.values())
    assert answers.startswith("gAAAAA")
    # Pieces long enough that base64 can't contain them by chance ("." is not a base64 letter).
    plain = ("emergency", "Harborline", "4321.50", "8765.25", "111.11")
    assert not any(piece in value for value in stored.values() for piece in plain)
