"""
Schedule A/B: each part's total prints on its own line and again on the summary, and each
property question answers Yes only for the kind of property the filer listed.

Business intent: the totals are what the trustee reads first, and 106Sum copies lines 55,
62 and 63 (step 2 spec §6.1 B5, Appendix A.9, owner Q8 and Q9; 3b spec §8).
"""

import json
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.districts.models import District
from apps.forms.field_index import export_state
from apps.forms.schema import load_schema
from apps.forms.services.derivations import RULE_FIXES
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.asset_lines import LINE_BY_KEY
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
# Boxes no row of ASSETS feeds.
LEFT_BLANK = {
    "12",  # line 1.2: ASSETS holds one property
    "16 Cash amount",  # line 16: ASSETS holds no cash
    "undefined_156",  # line 53's second amount: ASSETS holds one row there
    "undefined_157",
}
# Lines ASSETS has nothing on, which say so rather than print nothing (3b spec §8.1).
SAYS_NOTHING_THERE = {
    "Check 16": {"/no"},  # line 16's question
    LINE_4_QUESTION: {"/No_2"},  # boats and other recreational vehicles
    "undefined_163": {"0.00"},  # line 59, Part 5: business property
    "undefined_164": {"0.00"},  # line 60, Part 6: farm and fishing property
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


# The A/B line a row of each kind sits on (3b): the kinds name the sections of the old step.
LINE_OF_KIND = {
    "real_property": "1",
    "vehicle": "3",
    "bank_account": "17",
    "retirement_account": "21",
    "personal_property": "6",
    "other": "53",
}


def _asset(session, asset_type, value, description="Item"):
    AssetInfo.objects.create(
        session=session,
        ab_line=LINE_OF_KIND[asset_type],
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


@pytest.mark.slow
def test_a_filer_with_no_property_gets_zero_totals_and_no_on_every_question(session):
    # The filer finished the intake with an empty list, which is "none" (Ruling T0-e,
    # owner Q8), so the totals print 0.00 and every question says No. Line 1's No skips
    # line 2, the one total the form tells such a filer to leave (3b spec §8.1).
    filled = _filled(session)

    assert {box: filled.get(box) for box in TOTALS} == {
        box: set() if box == "undefined_13" else {"0.00"} for box in TOTALS
    }
    assert {box: filled.get(box) for box, _, _ in QUESTIONS.values()} == {
        box: {no} for box, _, no in QUESTIONS.values()
    }
    assert filled.get(OTHER_PROPERTY) == set()


@pytest.mark.slow
@pytest.mark.parametrize("asset_type", list(LINE_OF_KIND))
def test_each_property_question_answers_yes_only_for_the_kind_listed(session, asset_type):
    # Household goods have no question bound yet (lines 6-14 need rows, step 3), so a
    # filer who lists only those answers No to all five.
    _asset(session, asset_type, "1.00")

    filled = _filled(session)

    assert {kind: filled.get(box) for kind, (box, _, _) in QUESTIONS.items()} == {
        kind: {yes if kind == asset_type else no} for kind, (_, yes, no) in QUESTIONS.items()
    }


def test_a_boat_on_line_4_does_not_answer_yes_to_the_cars_question_on_line_3(session):
    # Line 3 asks about cars, vans and motorcycles; a filer whose only vehicle is a
    # line 4 boat must not swear to owning one.
    AssetInfo.objects.create(
        session=session, ab_line="4", description="Fishing boat", current_value=Decimal("1.00")
    )

    printed = resolve(load_schema("schedule_a_b"), session)

    assert printed["Check 3"] == "/no"


def test_other_property_is_described_in_the_order_the_filer_listed_it(session):
    # The values run against the order listed, so an order by value can't pass, and the
    # stored order follows the encrypted value (DIG-164): only the id is the filer's order.
    _asset(session, "other", "50.00", "Season tickets")
    _asset(session, "vehicle", "4000.00", "2015 Honda Civic")
    _asset(session, "other", "900.00", "Club membership")
    _asset(session, "other", "10.00", "Coin collection")
    _asset(session, "other", "300.00", "Timeshare points")

    printed = resolve(load_schema("schedule_a_b"), session)

    # The box holds the three rows beside the form's three amounts; the fourth goes on a sheet.
    assert printed.get(OTHER_PROPERTY) == "Season tickets; Club membership; Coin collection"


def _index():
    return json.loads((settings.FORM_INDEX_DIRECTORY / "form_b106ab.index.json").read_text())


def test_every_catalog_line_has_its_boxes():
    # A line with a box left unbound prints blank on a sworn form. Only Debtor 2's boxes, which
    # 3b never ticks, stay out.
    bound = set()
    for f in load_schema("schedule_a_b").fields:
        for row in _index():
            if row["full_name"] == f.pdf_field and f.tag in (None, row["tag"]):
                bound.add((row["page"], row["tag"]))
    unbound = [
        (row["line"], row["full_name"], row["option_text"])
        for row in _index()
        if row["line"].rstrip(".").partition(".")[0] in LINE_BY_KEY
        and (row["page"], row["tag"]) not in bound
    ]
    assert unbound == []


def test_no_debtor_2_box_is_bound():
    # Joint filing isn't in 3b: "only you" and "you and someone else" tick Debtor 1's two boxes,
    # and a Debtor 2 tick would swear to a co-filer who doesn't exist.
    never = [
        row
        for row in _index()
        if row["option_text"].startswith(("Debtor 2", "Debtor 1 and Debtor 2"))
    ]
    assert never
    choices = {f.pdf_field: f.choices for f in load_schema("schedule_a_b").fields if f.choices}
    ticked = [
        (row["full_name"], row["on_state"])
        for row in never
        if export_state(row["on_state"]) in (choices.get(row["full_name"]) or {}).values()
    ]
    assert ticked == []
    assert not {f.pdf_field for f in load_schema("schedule_a_b").fields} & {"Debtor 2"}


@pytest.mark.slow
def test_a_box_no_row_feeds_prints_nothing(session):
    # Every kind of property is listed, so a box still bound to a total, or to an
    # answer about one, would print. The account totals once filled the second
    # property's street address (line 1.2) and the cash line (16).
    for asset_type, value in ASSETS:
        _asset(session, asset_type, value)

    filled = _filled(session)

    assert {box: filled.get(box) for box in LEFT_BLANK} == {box: set() for box in LEFT_BLANK}
    assert {box: filled.get(box) for box in SAYS_NOTHING_THERE} == SAYS_NOTHING_THERE
    assert filled.get("6 check") == {"/yes"}  # household goods, which ASSETS does list
    assert filled.get("undefined_155") == {"128.00"}  # line 53's first amount, its one row


def test_a_form_reads_the_asset_rows_once_however_many_rules_ask(session):
    # Each rule reads through ordered_assets, and each row decrypts on every read: a read per
    # rule cost 0.62 s more with 20 rows on Generate, which holds a sync worker.
    _asset(session, "vehicle", "2.00")

    with CaptureQueriesContext(connection) as queries:
        resolve(load_schema("schedule_a_b"), session)

    assert len([q for q in queries if "asset_info" in q["sql"]]) == 1


def test_a_form_drawn_after_a_save_prints_what_the_save_stored(session):
    # The one read lasts one resolve: nothing outlives it on a session held across a save.
    _asset(session, "vehicle", "2.00")
    resolve(load_schema("schedule_a_b"), session)

    _asset(session, "vehicle", "4.00")

    assert resolve(load_schema("schedule_a_b"), session)["undefined_26"] == "6.00"


def test_the_business_and_farm_totals_print_on_their_own_lines_and_the_summary(session):
    # Lines 59 and 60 had no binding before 3b, so a filer's business property reached line 63
    # with no line of the summary adding up to it. A wrong figure links to the Assets step.
    AssetInfo.objects.create(session=session, ab_line="38", current_value=Decimal("7.00"))
    AssetInfo.objects.create(session=session, ab_line="47", current_value=Decimal("11.00"))

    printed = resolve(load_schema("schedule_a_b"), session)

    assert printed["undefined_143"] == printed["undefined_163"] == "7.00"
    assert printed["undefined_154"] == printed["undefined_164"] == "11.00"
    assert printed["undefined_166"] == printed["undefined_167"] == "18.00"
    assert RULE_FIXES["total_business_property"] == {"step": "assets"}
    assert RULE_FIXES["total_farm_property"] == {"step": "assets"}
