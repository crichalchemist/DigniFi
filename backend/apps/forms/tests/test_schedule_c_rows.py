"""
Schedule C draws each claim in its own row and column, the filer's answers on lines 1, 3 and
3-1, and the claims past its 15 rows on numbered copies of page 2 (3g2 §6).

Business intent: Schedule C is signed under oath, so a claim's law, amount and tick must land
in the boxes the form labels for that claim, never beside another claim's, and a line the
filer didn't answer ticks nothing. ROWS is written out here, not imported from the tool that
writes the schema, so a tool that swaps two boxes fails these tests.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.districts.models import District
from apps.forms.registry import build_parts
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import UnmappedChoice, resolve_parts
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import (
    AssetInfo,
    DebtorInfo,
    ExemptionClaim,
    IncomeInfo,
    IntakeSession,
)
from apps.intake.tests.builders import answer_asset_lines, answer_exemptions, answer_household

User = get_user_model()

# ROWS: each claim row's six boxes, read from the template's row labels and written out here
# rather than imported from build_schedule_c.py.
_TABLE = [
    (1, "description", "Schedule AB", "undefined", "check 2.1", "undefined_2", "2.1"),
    (2, "description_2", "Schedule AB_2", "undefined_6", "check 2.2", "undefined_7", "2.2"),
    (3, "description_3", "Schedule AB_3", "undefined_8", "check 2.3", "undefined_9", "2.3"),
    (4, "description_4", "Line from", "undefined_11", "check 4", "undefined_12", "3"),
    (5, "description_5", "Schedule AB_4", "undefined_13", "check 5", "undefined_26", "4"),
    (6, "description_6", "Schedule AB_5", "undefined_27", "check 6", "undefined_28", "5"),
    (7, "description_7", "Line from_2", "undefined_29", "check 7", "undefined_30", "6"),
    (8, "description_8", "Schedule AB_6", "undefined_31", "check 8", "undefined_32", "7"),
    (9, "description_9", "Schedule AB_7", "undefined_34", "check 9", "undefined_35", "8"),
    (10, "description_10", "Line from_3", "undefined_36", "check 10", "undefined_37", "9"),
    (11, "description_11", "Schedule AB_8", "undefined_38", "check 11", "undefined_39", "10"),
    (12, "description_12", "Schedule AB_9", "undefined_40", "check 12", "undefined_41", "11"),
    (13, "description_13", "Line from_4", "undefined_42", "check 13", "undefined_43", "12"),
    (14, "description_14", "Schedule AB_10", "undefined_44", "check 14", "undefined_45", "13"),
    (15, "description_15", "Schedule AB_11", "undefined_47", "check 15", "undefined_48", "14"),
]
_COLUMNS = ("description", "line", "value", "amount_kind", "amount", "law")
ROWS = {row[0]: dict(zip(_COLUMNS, row[1:], strict=False)) for row in _TABLE}
ALL_BOXES = [name for boxes in ROWS.values() for name in boxes.values()]


@pytest.fixture
def session(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    user = User.objects.create_user(username="schedulecrows", password="pw")
    district = District.objects.get(code="ilnd")
    session = IntakeSession.objects.create(user=user, district=district, status="completed")
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("2000.00")
    )
    answer_household(session, payroll_tax=Decimal("250.00"), exemptions=None)
    return session


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


def _claim_items(session, count, kind_of=lambda n: "dollars", **answers):
    """count line 6 items, each with one claim of its own: item n is worth n * 10 dollars, its
    law is "Demo Law n" and, under dollars, its amount is n dollars."""
    for n in range(1, count + 1):
        item = AssetInfo(
            session=session,
            ab_line="6",
            description=f"Demo item {n}",
            current_value=Decimal(n * 10),
        )
        item.set_details({})
        item.save()
        ExemptionClaim.objects.create(
            session=session,
            asset=item,
            other_law=f"Demo Law {n}",
            amount_kind=kind_of(n),
            amount=Decimal(n) if kind_of(n) == "dollars" else None,
        )
    answer_asset_lines(session, ["6"])
    answer_exemptions(session, **answers)  # after the claims, so its no_claims default is False
    return _fresh(session)


def _parts_drawn(session, form_type):
    """(the parts, what the drawn form and its copies print), the copies read as their pages."""
    document = build_parts(form_type, session)
    pdf = PDFFormFiller().fill(form_type, document)
    return document["parts"], read_drawn(form_type, pdf, document["parts"])


def _at(drawn, name, copy=None, page=None):
    """What one box prints, on the form's own page (copy None) or on a copy."""
    values = [
        w.value
        for w in drawn
        if w.full_name == name and w.copy == copy and (page is None or w.page == page)
    ]
    assert len(values) == 1, (name, copy, values)
    return values[0]


def _tick(drawn, name, copy=None):
    """The state of the one box of this name that is ticked, else "/Off"."""
    states = {w.state for w in drawn if w.full_name == name and w.copy == copy} - {"/Off"}
    assert len(states) <= 1, (name, states)
    return states.pop() if states else "/Off"


@pytest.mark.parametrize("odd_kind", ["dollars", "fair_market_value"])
def test_each_claim_prints_in_its_own_row_and_column(session, odd_kind):
    # 15 claims, one per item; odd rows odd_kind, even rows the other, so across both cases
    # every row ticks both boxes.
    even_kind = {"dollars": "fair_market_value", "fair_market_value": "dollars"}[odd_kind]

    def kind_of(n):
        return odd_kind if n % 2 else even_kind

    fresh = _claim_items(session, 15, kind_of=kind_of, no_claims=False)
    parts, drawn = _parts_drawn(fresh, "schedule_c")

    assert [p["kind"] for p in parts] == ["form"]
    for n, boxes in ROWS.items():
        assert _at(drawn, boxes["description"]) == f"Demo item {n}"
        assert _at(drawn, boxes["line"]) == ("6" if n == 1 else f"6.{n}")
        assert _at(drawn, boxes["value"]) == f"{n * 10}.00"
        assert _at(drawn, boxes["law"]) == f"Demo Law {n}"
        kind = kind_of(n)
        assert _tick(drawn, boxes["amount_kind"]) == (
            "/On" if kind == "dollars" else "/fair market"
        )
        assert _at(drawn, boxes["amount"]) == (f"{n}.00" if kind == "dollars" else "")


def test_line_1_3_and_3_1_print_the_filers_answers(session):
    # federal, line 3 yes, 3-1 yes, "not claiming": the answers no persona gives
    fresh = _claim_items(session, 0, line_1="federal", line_3="yes", line_3_1="yes", no_claims=True)
    parts, drawn = _parts_drawn(fresh, "schedule_c")

    assert [p["kind"] for p in parts] == ["form"]
    assert (_tick(drawn, "check 1"), _tick(drawn, "check 3"), _tick(drawn, "check 3-1")) == (
        "/federal",
        "/yes",
        "/yes",
    )
    # no claim: every row box prints blank, and no row ticks an amount box
    assert [_at(drawn, name) for name in ALL_BOXES if not name.startswith("check")] == [""] * 75
    assert [_tick(drawn, name) for name in ALL_BOXES if name.startswith("check")] == ["/Off"] * 15


def test_line_3_1_stays_blank_under_line_3_no(session):
    # a 3-1 "yes" left stored under line 3 "no" prints nothing
    fresh = _claim_items(
        session, 0, line_1="state_and_federal", line_3="no", line_3_1="yes", no_claims=True
    )
    _, drawn = _parts_drawn(fresh, "schedule_c")

    assert (_tick(drawn, "check 1"), _tick(drawn, "check 3"), _tick(drawn, "check 3-1")) == (
        "/state and federal",
        "/no",
        "/Off",
    )


def test_the_sixteenth_claim_continues_on_a_copy_of_page_2_with_page_numbers(session):
    fresh = _claim_items(session, 16, no_claims=False)
    parts, drawn = _parts_drawn(fresh, "schedule_c")

    assert [p["kind"] for p in parts] == ["form", "copy"]
    # the copy's first row holds claim 16, in the row-4 boxes, and its row 5 is empty
    boxes = ROWS[4]
    assert _at(drawn, boxes["description"], copy=1) == "Demo item 16"
    assert _at(drawn, boxes["line"], copy=1) == "6.16"
    assert _at(drawn, boxes["value"], copy=1) == "160.00"
    assert _at(drawn, boxes["law"], copy=1) == "Demo Law 16"
    assert _tick(drawn, boxes["amount_kind"], copy=1) == "/On"
    assert _at(drawn, boxes["amount"], copy=1) == "16.00"
    assert _at(drawn, "description_5", copy=1) == ""
    assert _at(drawn, "Debtor 1", copy=1) == "Jane Doe"
    form = parts[0]["values"]
    # page 2's own "2" is the template's default, which the read-back shows as blank (R12)
    assert (form["page@1:T33"], form["page 2"], form["page@2:T88"]) == ("3", "2", "3")
    assert (_at(drawn, "page 2", copy=1), _at(drawn, "page", copy=1)) == ("3", "3")


def test_twenty_eight_claims_print_two_copies(session):
    fresh = _claim_items(session, 28, no_claims=False)
    parts, drawn = _parts_drawn(fresh, "schedule_c")

    assert [p["kind"] for p in parts] == ["form", "copy", "copy"]
    assert _at(drawn, "description_15", copy=1) == "Demo item 27"
    assert _at(drawn, "description_4", copy=2) == "Demo item 28"
    assert (_at(drawn, "page 2", copy=2), _at(drawn, "page", copy=2)) == ("4", "4")
    form = parts[0]["values"]
    assert (form["page@1:T33"], form["page@2:T88"]) == ("4", "4")


def test_a_claim_with_no_answers_prints_no_law_no_tick_and_no_amount(session):
    # Ungated: the guard never acts on an asked field; the cells' "" do (§6.1).
    item = AssetInfo(
        session=session, ab_line="6", description="Demo item 1", current_value=Decimal("10")
    )
    item.set_details({})
    item.save()
    ExemptionClaim.objects.create(
        session=session, asset=item, law=None, other_law="  ", amount_kind=None, amount=None
    )
    answer_asset_lines(session, ["6"])
    # 3-1 stored as Yes beside an unanswered line 3 prints nothing: it prints only under line 3 Yes
    answer_exemptions(session, line_1=None, line_3=None, line_3_1="yes", no_claims=False)

    values = resolve_parts(load_schema("schedule_c"), _fresh(session))["parts"][0]["values"]

    assert {"2.1", "check 2.1", "undefined_2", "check 1", "check 3", "check 3-1"}.isdisjoint(values)
    assert values["description"] == "Demo item 1"


def test_an_amount_kind_no_answer_can_have_is_refused_not_printed_blank(session):
    # Stored directly, past the PUT's validation: a sworn form never guesses what was meant.
    item = AssetInfo(
        session=session, ab_line="6", description="Demo item 1", current_value=Decimal("10")
    )
    item.set_details({})
    item.save()
    ExemptionClaim.objects.create(
        session=session, asset=item, other_law="Demo Law", amount_kind="demo", amount=None
    )
    answer_asset_lines(session, ["6"])
    answer_exemptions(session, no_claims=False)

    with pytest.raises(UnmappedChoice):
        resolve_parts(load_schema("schedule_c"), _fresh(session))
