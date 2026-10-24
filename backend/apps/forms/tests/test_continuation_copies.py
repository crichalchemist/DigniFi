"""
Rows past a repeat group's last slot continue on copies of the page its schema names (3a2
spec §5.2): each copy is drawn alone and goes in right after that page, numbered as the
form asks. 3a2 proves it on a synthetic Schedule D group (§5.4; conftest's
schedule_d_with_copies): Part 1's rows 2.1 and 2.2 on page 1, then three rows on page 2.
"""

import pymupdf
import pytest

from apps.forms.registry import build_parts
from apps.forms.services.pdf_filler import PDFFormFiller, UnknownField, UnprintableLetter
from apps.forms.tests.pdf_readback import read_drawn

NAMES = [
    "Creditors Name",
    "Creditors Name_2",
    "Creditors Name_3",
    "Creditors Name_4",
    "Creditors Name_5",
]
AMOUNTS = ["undefined", "undefined_5", "undefined_10", "undefined_14", "undefined_20"]
ENTRY_NUMBERS = ("undefined_12", "undefined_19")  # page 2's three "2.__" boxes
PAGE_NUMBERS = {
    "fill_27.0": "of",  # page 1 prints "page 1 of ___"
    "fill_27.1.0": "this",
    "fill_27.1.1": "of",
    "fill_28.1.1": "this",
    "fill_28.1.2": "of",
}


@pytest.fixture
def session(generated_form_factory, schedule_d_with_copies):
    """Maria Torres's completed intake in the Northern District of Illinois."""
    return generated_form_factory().session


def _drawn(session):
    """Schedule D's parts for the session, its drawn PDF, and what each widget prints."""
    document = build_parts("schedule_d", session)
    pdf = PDFFormFiller().fill("schedule_d", document)
    return document["parts"], pdf, read_drawn("schedule_d", pdf, document["parts"])


def _printed(drawn, names):
    """(full name, copy) → what it prints, for boxes with one widget on their page."""
    return {(w.full_name, w.copy): w.value for w in drawn if w.full_name in names}


def _entries(drawn):
    """The entry-number boxes, in the order they print."""
    return [w.value for w in drawn if w.full_name in ENTRY_NUMBERS]


def _page_numbers(drawn):
    """Each printed page's page-number boxes, {"this": …, "of": …}, in the order they print."""
    pages = {}
    for w in drawn:
        if w.full_name in PAGE_NUMBERS:
            pages.setdefault((w.page, w.copy), {})[PAGE_NUMBERS[w.full_name]] = w.value
    return list(pages.values())


def test_extra_rows_print_on_copies_of_the_extra_page(session, creditor_payments):
    rows = creditor_payments(session, 6)

    parts, pdf, drawn = _drawn(session)

    assert [(part["kind"], part.get("page"), part.get("number")) for part in parts] == [
        ("form", None, None),
        ("copy", 2, 1),
    ]
    # Read from the pages themselves: the sixth row is on the third of four pages, right
    # after page 2, and Part 2's page comes last.
    pages = pymupdf.open("pdf", pdf)
    assert len(pages) == 4
    assert rows[5].creditor_name in pages[2].get_text()
    assert "Part 2:" in pages[3].get_text()
    assert "Part 2:" not in pages[2].get_text()
    # Rows 1-5 fill the form's own slots, page 2's included; row 6 fills the copy's first.
    names = [row.creditor_name for row in rows]
    assert _printed(drawn, NAMES) == {
        **{(box, None): names[n] for n, box in enumerate(NAMES)},
        ("Creditors Name_3", 1): names[5],
        ("Creditors Name_4", 1): "",
        ("Creditors Name_5", 1): "",
    }
    assert _printed(drawn, AMOUNTS) == {
        **{(box, None): f"{n}00.00" for n, box in enumerate(AMOUNTS, start=1)},
        ("undefined_10", 1): "600.00",
        ("undefined_14", 1): "",
        ("undefined_20", 1): "",
    }


def test_a_copy_repeats_the_page_header_but_not_the_page_total(session, creditor_payments):
    # The filer's name heads every page; page 2's total prints once (R24).
    creditor_payments(session, 6)

    _, _, drawn = _drawn(session)

    assert {(w.page, w.copy, w.value) for w in drawn if w.full_name == "Debtor 1"} == {
        (1, None, "Maria Torres"),
        (2, None, "Maria Torres"),
        (2, 1, "Maria Torres"),
        (3, None, "Maria Torres"),
    }
    assert _printed(drawn, ["undefined_24"]) == {
        ("undefined_24", None): "0.00",
        ("undefined_24", 1): "",
    }


@pytest.mark.parametrize(
    "count, copies, entries, page_numbers",
    [
        (
            6,
            [1],
            ["2.3", "2.4", "2.5", "2.6", "", ""],
            [
                {"of": "4"},
                {"this": "2", "of": "4"},
                {"this": "3", "of": "4"},
                {"this": "4", "of": "4"},
            ],
        ),
        (
            9,
            [1, 2],
            ["2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "", ""],
            [
                {"of": "5"},
                {"this": "2", "of": "5"},
                {"this": "3", "of": "5"},
                {"this": "4", "of": "5"},
                {"this": "5", "of": "5"},
            ],
        ),
    ],
    ids=["one copy", "two copies"],
)
def test_entry_and_page_numbers_continue_on_each_copy(
    session, creditor_payments, count, copies, entries, page_numbers
):
    creditor_payments(session, count)

    parts, _, drawn = _drawn(session)

    assert [part["number"] for part in parts if part["kind"] == "copy"] == copies
    assert _entries(drawn) == entries
    assert _page_numbers(drawn) == page_numbers


@pytest.mark.parametrize(
    "count, entries",
    [(3, ["2.3", "", ""]), (5, ["2.3", "2.4", "2.5"])],
    ids=["a row on page 2", "every slot"],
)
def test_rows_that_fit_the_slots_print_no_copy_and_no_page_number(
    session, creditor_payments, count, entries
):
    creditor_payments(session, count)

    parts, pdf, drawn = _drawn(session)

    assert [part["kind"] for part in parts] == ["form"]
    assert len(pymupdf.open("pdf", pdf)) == 3
    assert _entries(drawn) == entries  # only a slot that holds a row is numbered
    assert _page_numbers(drawn) == [{"of": ""}, {"this": "", "of": ""}, {"this": "", "of": ""}]


def test_a_copy_is_never_read_as_another_page(session, creditor_payments):
    # Read without its parts, the copy would pass for page 3, and page 3 would go unread.
    creditor_payments(session, 6)
    _, pdf, _ = _drawn(session)
    with pytest.raises(ValueError, match="4 pages, but its parts print 3"):
        read_drawn("schedule_d", pdf)


def test_a_copy_of_the_last_page_goes_after_it(
    schedule_d_part_2_with_copies, generated_form_factory, creditor_payments
):
    # C, G and H continue on their last page; here D's Part 2 page, page 3 of 3.
    session = generated_form_factory().session
    rows = creditor_payments(session, 7)

    parts, pdf, drawn = _drawn(session)

    assert [(part["kind"], part.get("page"), part.get("number")) for part in parts] == [
        ("form", None, None),
        ("copy", 3, 1),
    ]
    pages = pymupdf.open("pdf", pdf)
    assert len(pages) == 4
    assert ["Part 2:" in page.get_text() for page in pages] == [False, False, True, True]
    assert rows[6].creditor_name in pages[3].get_text()
    assert _printed(drawn, ["Name"]) == {
        ("Name", None): rows[0].creditor_name,
        ("Name", 1): rows[6].creditor_name,
    }
    # Pages 1 and 2 come before the copied page, so they keep their numbers.
    assert _page_numbers(drawn) == [
        {"of": "4"},
        {"this": "2", "of": "4"},
        {"this": "3", "of": "4"},
        {"this": "4", "of": "4"},
    ]


def test_a_letter_refused_on_a_copy_names_where_to_fix_it(session, creditor_payments):
    # Row 6 prints only on the copy of page 2; its creditor's name comes from the SOFA.
    rows = creditor_payments(session, 6)
    rows[5].creditor_name = "Wąsowicz Credit"
    rows[5].save()
    document = build_parts("schedule_d", session)
    assert "Wąsowicz Credit" not in document["parts"][0]["values"].values()

    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("schedule_d", document)

    assert str(refused.value) == (
        "The court form can't print the letter “ą” in “Creditor's name”. "
        "Change it to a letter without the mark."
    )
    assert (refused.value.step, refused.value.page) == (None, "/sofa")


def test_a_copy_fills_only_the_widgets_on_its_page(schedule_d_with_copies):
    # "Debtor 1" heads pages 1 to 3; on a copy of page 2 it fills page 2's widget alone.
    (_, copy) = PDFFormFiller().check(
        "schedule_d",
        {
            "version": 2,
            "parts": [
                {"kind": "form", "values": {}},
                {"kind": "copy", "page": 2, "number": 1, "values": {"Debtor 1": "Maria Torres"}},
            ],
        },
    )
    assert [(p.widget.page, p.widget.tag) for p in copy.widgets] == [(2, "T1")]

    # Page 1's first creditor box isn't on page 2.
    with pytest.raises(UnknownField):
        PDFFormFiller().check(
            "schedule_d",
            {
                "version": 2,
                "parts": [{"kind": "copy", "page": 2, "number": 1, "values": {NAMES[0]: "x"}}],
            },
        )


def test_a_part_of_a_kind_check_does_not_know_is_refused(schedule_d_with_copies):
    with pytest.raises(ValueError, match="poster"):
        PDFFormFiller().check(
            "schedule_d",
            {"version": 2, "parts": [{"kind": "poster", "values": {"Debtor 1": "Maria Torres"}}]},
        )
