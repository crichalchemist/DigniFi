"""
Schedule A/B: each part's total prints on its own line and again on the summary, and each
property question answers Yes only for the kind of property the filer listed.

Business intent: the totals are what the trustee reads first, and 106Sum copies lines 55,
62 and 63. Until step 3 asks for each item's row, the boxes that need a row stay blank
(step 2 spec §6.1 B5, Appendix A.9, owner Q8 and Q9).
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import AssetInfo, IncomeInfo, IntakeSession

User = get_user_model()

# One or two rows of each kind, each a distinct power of two, so a total that reads the
# wrong kind, or misses a row, prints a different figure.
ASSETS = [
    ("real_property", "1.00"),
    ("vehicle", "2.00"),
    ("vehicle", "4.00"),
    ("bank_account", "8.00"),
    ("retirement_account", "16.00"),
    ("personal_property", "32.00"),
    ("personal_property", "64.00"),
    ("other", "128.00"),
]
# Box → what it prints with ASSETS.
TOTALS = {
    "undefined_13": "1.00",  # line 2, Part 1: real estate
    "undefined_159": "1.00",  # line 55, copies line 2
    "undefined_26": "6.00",  # line 5, Part 2: vehicles
    "undefined_160": "6.00",  # line 56, copies line 5
    "15 amount": "96.00",  # line 15, Part 3: personal and household items
    "undefined_161": "96.00",  # line 57, copies line 15
    "undefined_124": "24.00",  # line 36, Part 4: deposits (17) and retirement accounts (21)
    "undefined_162": "24.00",  # line 58, copies line 36
    "undefined_158": "128.00",  # line 54, Part 7: other property
    "undefined_165": "128.00",  # line 61, copies line 54
    "undefined_166": "254.00",  # line 62, lines 56 through 61
    "undefined_167": "255.00",  # line 63, line 55 + line 62
}
# Kind of property → (its question's box, the state its "Yes" exports, its "No"), each
# state from the field index. The template is irregular: line 1's "No. Go to Part 2."
# exports On, and so does line 53's "Yes. Give specific information."
QUESTIONS = {
    "real_property": ("Check 2", "/yes", "/On"),  # line 1
    "vehicle": ("Check 3", "/yes", "/no"),  # line 3
    "bank_account": ("Check 17", "/yes", "/no"),  # line 17
    "retirement_account": ("check 21", "/yes", "/no"),  # line 21
    "other": ("check 53", "/On", "/no"),  # line 53
}
OTHER_PROPERTY = "53 Examples Season tickets country club membership"
LINE_4_QUESTION = (
    "Examples Boats trailers motors personal watercraft fishing vessels snowmobiles "
    "motorcycle accessories"
)
# Boxes that need a row, or a figure, the intake never asks for (step 3).
LEFT_BLANK = {
    "12",  # line 1.2, a second property's street address
    "16 Cash amount",  # line 16, cash
    "Check 16",  # line 16's question
    LINE_4_QUESTION,  # boats and other recreational vehicles (spec §10)
    "6 check",  # line 6's question, household goods
    "undefined_155",  # line 53's amounts
    "undefined_156",
    "undefined_157",
    "undefined_163",  # line 59, Part 5: business property
    "undefined_164",  # line 60, Part 6: farm and fishing property
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemaab", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def _asset(session, asset_type, value, description="Item"):
    AssetInfo.objects.create(
        session=session,
        asset_type=asset_type,
        description=description,
        current_value=Decimal(value),
    )


def _filled(session):
    """Box → what the drawn form prints in it: the ticked states, or the text."""
    values = resolve(load_schema("schedule_a_b"), session)
    shows = {}
    for widget in read_drawn("schedule_a_b", PDFFormFiller().fill("schedule_a_b", values)):
        seen = shows.setdefault(widget.full_name, set())
        if widget.state:
            if widget.state != "/Off":
                seen.add(widget.state)
        elif widget.value:
            seen.add(widget.value)
    return shows


def test_each_part_total_prints_on_its_own_line_and_again_on_the_summary(session):
    for asset_type, value in ASSETS:
        _asset(session, asset_type, value)

    printed = resolve(load_schema("schedule_a_b"), session)

    assert {box: printed.get(box) for box in TOTALS} == TOTALS


def test_the_summary_adds_up_the_way_the_form_says(session):
    # Line 62 adds lines 56 through 61, and line 63 adds line 55 and line 62. Lines 59
    # and 60 (business and farm property) are never asked, so they count as zero.
    for asset_type, value in ASSETS:
        _asset(session, asset_type, value)

    printed = resolve(load_schema("schedule_a_b"), session)

    def line(box):
        return Decimal(printed[box])

    assert "undefined_163" not in printed and "undefined_164" not in printed
    lines_56_to_61 = ("undefined_160", "undefined_161", "undefined_162", "undefined_165")
    assert line("undefined_166") == sum(line(box) for box in lines_56_to_61)
    assert line("undefined_167") == line("undefined_159") + line("undefined_166")


def test_the_summary_form_copies_the_property_totals_schedule_a_b_prints(session):
    # 106Sum lines 1a, 1b and 1c say "Copy line 55", "Copy line 62" and "Copy line 63
    # from Schedule A/B": the two forms must never disagree.
    for asset_type, value in ASSETS:
        _asset(session, asset_type, value)
    # 106Sum line 8 prints current monthly income, which needs income by source.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))

    schedule = resolve(load_schema("schedule_a_b"), session)
    summary = resolve(load_schema("form_106sum"), session)

    assert {line: summary[line] for line in ("1a", "1b", "1c")} == {
        "1a": schedule["undefined_159"],
        "1b": schedule["undefined_166"],
        "1c": schedule["undefined_167"],
    }


def test_a_filer_with_no_property_gets_zero_totals_and_no_on_every_question(session):
    # The filer finished the intake with an empty list, which is "none" (Ruling T0-e,
    # owner Q8), so the totals print 0.00 and every question says No.
    filled = _filled(session)

    assert {box: filled.get(box) for box in TOTALS} == {box: {"0.00"} for box in TOTALS}
    assert {box: filled.get(box) for box, _, _ in QUESTIONS.values()} == {
        box: {no} for box, _, no in QUESTIONS.values()
    }
    assert filled.get(OTHER_PROPERTY) == set()


@pytest.mark.parametrize("asset_type", [kind for kind, _ in AssetInfo.ASSET_TYPE_CHOICES])
def test_each_property_question_answers_yes_only_for_the_kind_listed(session, asset_type):
    # Household goods have no question bound yet (lines 6-14 need rows, step 3), so a
    # filer who lists only those answers No to all five.
    _asset(session, asset_type, "1.00")

    filled = _filled(session)

    assert {kind: filled.get(box) for kind, (box, _, _) in QUESTIONS.items()} == {
        kind: {yes if kind == asset_type else no} for kind, (_, yes, no) in QUESTIONS.items()
    }


def test_other_property_is_described_in_the_order_the_filer_listed_it(session):
    # The values run against the order listed, so an order by value can't pass, and the
    # stored order follows the encrypted value (DIG-164): only the id is the filer's order.
    _asset(session, "other", "50.00", "Season tickets")
    _asset(session, "vehicle", "4000.00", "2015 Honda Civic")
    _asset(session, "other", "900.00", "Club membership")
    _asset(session, "other", "10.00", "Coin collection")
    _asset(session, "other", "300.00", "Timeshare points")

    printed = resolve(load_schema("schedule_a_b"), session)

    assert printed.get(OTHER_PROPERTY) == (
        "Season tickets; Club membership; Coin collection; Timeshare points"
    )


def test_lines_the_intake_never_asks_print_nothing(session):
    # Every kind of property is listed, so a box still bound to a total, or to an
    # answer about one, would print. The account totals once filled the second
    # property's street address (line 1.2) and the cash line (16).
    for asset_type, value in ASSETS:
        _asset(session, asset_type, value)

    filled = _filled(session)

    assert {box: filled.get(box) for box in LEFT_BLANK} == {box: set() for box in LEFT_BLANK}
