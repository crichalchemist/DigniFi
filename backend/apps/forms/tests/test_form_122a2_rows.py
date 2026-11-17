"""
Form 122A-2 draws each row of lines 3, 9b, 13b, 13e, 33d and 34 in the boxes the form gives
that row, the rows past those boxes on each line's attached sheet with the line's number, and
line 43's circumstances as pointers on the form and whole on their sheet (3h3 spec §9.2).

Business intent: Form 122A-2 is signed under oath, so a creditor's payment must land in its
own row, never beside another creditor's, a row the form has no box for must still print and
still count in the line's total, and a circumstance prints only where the form reaches line
43. SLOTS is written out here, not imported from the tool that writes the schema, so a tool
that swaps two boxes fails these tests.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.districts.dated_tables import fill_date
from apps.districts.models import District
from apps.eligibility.means_inputs import page_answers, read_inputs, read_tables
from apps.eligibility.means_lines import NO_PRESUMPTION, work_out
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve_parts
from apps.forms.services.means_cells import LINE_43_POINTER
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.services.sheets import sheet_spec
from apps.forms.tests.means_rows import ROWS, answer_page, overflowing_session, total
from apps.forms.tests.pdf_readback import read_drawn, read_sheet_part, read_sheets
from apps.intake.models import IntakeSession

User = get_user_model()

# Each group's slot boxes, row by row, in the order of the group's cells (R18): read from the
# template's row labels and written out here rather than imported from build_form_122a2.py.
SLOTS = {
    "3": [("Quest3A", "Quest3A1"), ("Quest3B", "Quest3B1"), ("Quest3C", "Quest3C1")],
    "9b": [
        ("Quest9B creditor name1", "Quest9B creditor amount1"),
        ("Quest9B creditor name2", "Quest9B creditor amount2"),
        ("Quest9B creditor name3", "Quest9B creditor amount3"),
    ],
    "13b": [
        ("Quest13B Creditor for vehicle 1-1", "Quest13B amount for vehicle 1-1"),
        ("Quest13B Creditor for vehicle 1-2", "Quest13B amount for vehicle 1-2"),
    ],
    "13e": [
        ("Quest13E.Creditor1", "Quest13E.Monthly1"),
        ("Quest13E.Creditor2", "Quest13E.Monthly2"),
    ],
    "33d": [
        ("undefined_71", "undefined_72", "CheckBox8", "undefined_73"),
        ("undefined_74", "undefined_75", "CheckBox9", "undefined_76"),
        ("undefined_77", "undefined_78", "CheckBox10", "undefined_79"),
    ],
    "34": [
        ("undefined_81", "secures the debt", "undefined_82", "undefined_83"),
        ("undefined_84", "undefined_85", "undefined_86", "undefined_87"),
        ("undefined_88", "undefined_89", "undefined_90", "undefined_91"),
    ],
}
# Line 43's four form rows: the pointer box and the amount box of circumstance n.
LINE_43 = [
    ("undefined_113", "undefined_114"),
    ("undefined_115", "undefined_116"),
    ("undefined_117", "undefined_118"),
    ("undefined_119", "undefined_120"),
]
TOTALS = {
    "3": "Quest3",
    "9b": "Quest9B total amount",
    "13b": "Quest13B Total amount for vehicle 1",
    "13e": "Quest13E.TotalMonthly",
    "34": "undefined_92",
}
GROUPS = {key: f"means_line_{key}" for key in ("3", "9b", "13b", "13e", "33d", "34", "43")}
# The one row past each group's boxes, as its sheet numbers it: the numbering goes on from the
# form's last box (spec §9.2, H30).
OVERFLOW_LINE = {
    "3": "3.4",
    "9b": "9b.4",
    "13b": "13b.3",
    "13e": "13e.3",
    "33d": "33d.4",
    "34": "34.4",
    "43": "43.5",
}
# The 33d sheet prints a box slot's answer in the form's own words beside the box (R14); on the
# page, row 3's Yes is the template's /On where rows 1 and 2 tick /Yes.
TAXES_WORDS = {"yes": "Yes", "no": "No"}
TAXES_STATES = {
    "CheckBox8": {"yes": "/Yes", "no": "/No"},
    "CheckBox9": {"yes": "/Yes", "no": "/No"},
    "CheckBox10": {"yes": "/On", "no": "/No"},
}


@pytest.fixture
def user(db):
    return User.objects.create_user(username="means122a2rows", password="pw")


@pytest.fixture
def district(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


@pytest.fixture
def session(user, district):
    return overflowing_session(user, district)


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


def _document(session):
    # Below the gate; Task 7 moves these tests to build_parts unchanged (R18).
    return resolve_parts(load_schema("form_122a2"), _fresh(session))


def _drawn(session):
    """(the document, its PDF, what the drawn form prints in each widget)."""
    document = _document(session)
    pdf = PDFFormFiller().fill("form_122a2", document)
    return document, pdf, read_drawn("form_122a2", pdf, document["parts"])


def _printed(drawn, name):
    """What every widget of one name prints: one value, since a name prints one value."""
    values = {w.value for w in drawn if w.full_name == name}
    assert len(values) == 1, (name, values)
    return values.pop()


def _tick(drawn, name):
    """The state of the one box of this name that is ticked, else "/Off"."""
    states = {w.state for w in drawn if w.full_name == name} - {"/Off"}
    assert len(states) <= 1, (name, states)
    return states.pop() if states else "/Off"


def _sheet_part(document, key):
    parts = [p for p in document["parts"] if p["kind"] == "sheet" and p["group"] == GROUPS[key]]
    assert len(parts) <= 1, key
    return parts[0] if parts else None


def test_every_row_box_prints_its_own_figure_on_the_page(session):
    _, _, drawn = _drawn(session)

    for key in ("3", "9b", "13b", "13e"):
        for boxes, row in zip(SLOTS[key], ROWS[key], strict=False):
            assert [_printed(drawn, name) for name in boxes] == list(row), (key, boxes)
    for boxes, row in zip(SLOTS["33d"], ROWS["33d"], strict=False):
        creditor, property_, taxes, amount = boxes
        expected_creditor, expected_property, flag, expected_amount = row
        assert _printed(drawn, creditor) == expected_creditor
        assert _printed(drawn, property_) == expected_property
        assert _tick(drawn, taxes) == TAXES_STATES[taxes][flag]
        assert _printed(drawn, amount) == expected_amount
    for boxes, row in zip(SLOTS["34"], ROWS["34"], strict=False):
        assert [_printed(drawn, name) for name in boxes] == list(row), boxes
    for n, ((pointer, amount), (_, expected_amount)) in enumerate(
        zip(LINE_43, ROWS["43"], strict=False), start=1
    ):
        assert _printed(drawn, pointer) == LINE_43_POINTER.format(n=n)
        assert _printed(drawn, amount) == expected_amount
    assert _tick(drawn, "CheckBox16") == "/Yes"
    # as the builder answers them: row 1 Yes, rows 2 and 3 No
    assert [row[2] for row in ROWS["33d"][:3]] == ["yes", "no", "no"]


def test_a_row_past_each_groups_boxes_prints_on_its_sheet_and_counts_in_its_total(session):
    document, pdf, drawn = _drawn(session)
    parts = {key: _sheet_part(document, key) for key in GROUPS}
    assert all(part is not None for part in parts.values()), parts

    # One page per group and seven sheet pages in all, before any row is read: a loose title
    # filter or two groups on one page is caught here, not as a wrong row (design Risks 4).
    pages = {}
    for key, part in parts.items():
        (pages[key],) = read_sheet_part(pdf, part)
    assert len(read_sheets(pdf, sheet_spec(parts["3"]))) == 7

    for key in ("3", "9b", "13b", "13e"):
        assert pages[key].rows == ((OVERFLOW_LINE[key], *ROWS[key][-1]),), key
    creditor, property_, flag, amount = ROWS["33d"][-1]
    assert pages["33d"].rows == (
        (OVERFLOW_LINE["33d"], creditor, property_, TAXES_WORDS[flag], amount),
    )
    assert pages["34"].rows == ((OVERFLOW_LINE["34"], *ROWS["34"][-1]),)
    # line 43's sheet holds every circumstance, the first four included (H49): its fifth row
    assert len(pages["43"].rows) == len(ROWS["43"])
    assert pages["43"].rows[-1] == (OVERFLOW_LINE["43"], *ROWS["43"][-1])
    for page in pages.values():
        assert (page.crossing, page.overlapping) == ((), ())

    # Each total includes the sheet's row: 33d has no total box of its own, so its row is
    # proven through line 33e's, which adds lines 33a through 33d.
    for key, name in TOTALS.items():
        assert _printed(drawn, name) == str(total(key)), key
    thirty_three = sum(total(key) for key in ("9b", "13b", "13e", "33d"))
    assert _printed(drawn, "undefined_80") == str(thirty_three)


@pytest.mark.parametrize(("answer", "printed"), [("no", "No"), ("yes", "Yes")])
def test_a_box_slot_on_the_33d_sheet_prints_no_or_yes(session, answer, printed):
    # The builder answers only row 1 Yes; the sheet's row is debt 4, re-answered here.
    fourth = ROWS["33d"][-1][0]
    session = answer_page(session, debts={fourth: {"taxes_or_insurance": answer}})

    document = _document(session)
    (page,) = read_sheet_part(
        PDFFormFiller().fill("form_122a2", document), _sheet_part(document, "33d")
    )

    assert page.rows[0][0] == OVERFLOW_LINE["33d"]
    assert page.rows[0][1] == fourth
    assert page.rows[0][3] == printed


def test_stored_circumstances_never_print_where_line_43_doesnt(session):
    # Line 16 raised until the result is no presumption: the form then skips line 43 (H44), so
    # the stored circumstances reach no box and no sheet, whatever the filer answered.
    tables, _ = read_tables(fill_date())
    before = work_out(read_inputs(_fresh(session)), tables)
    session = answer_page(session, over={"line_16": str(before.lines["39c"] + 100)})
    after = work_out(read_inputs(_fresh(session)), tables)
    assert after.outcome == NO_PRESUMPTION
    assert len(page_answers(_fresh(session))["line_43_circumstances"]) == len(ROWS["43"])

    document = _document(session)
    values = document["parts"][0]["values"]

    assert "CheckBox16" not in values
    assert not {name for boxes in LINE_43 for name in boxes} & set(values)
    assert _sheet_part(document, "43") is None


def test_a_fifth_circumstance_prints_on_the_sheet_only(session):
    document, pdf, drawn = _drawn(session)

    (page,) = read_sheet_part(pdf, _sheet_part(document, "43"))

    # pointers 1 to 4 and their amounts on the page; every circumstance on the sheet
    for n, ((pointer, amount), (_, expected_amount)) in enumerate(
        zip(LINE_43, ROWS["43"], strict=False), start=1
    ):
        assert _printed(drawn, pointer) == LINE_43_POINTER.format(n=n)
        assert _printed(drawn, amount) == expected_amount
    assert page.rows == tuple((f"43.{n}", *row) for n, row in enumerate(ROWS["43"], start=1))
    assert page.rows[-1] == ("43.5", *ROWS["43"][-1])
    assert not any("43.5" in w.value for w in drawn)
