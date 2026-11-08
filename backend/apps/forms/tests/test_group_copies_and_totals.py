"""
A form with several groups continued on copies (3c spec §5.1, §5.2) and a group's total boxes
(§5.3), proven on synthetic schemas with the real templates' names, read off the printed page.
"""

import pymupdf
import pytest

from apps.forms.registry import build_parts
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn

EF_THIS = ("fill_27.1.0", "fill_27.1.2", "fill_27.1.4", "fill_27.1.6", "fill_27.1.8")
EF_OF = ("fill_27.0", "fill_27.1.1", "fill_27.1.3", "fill_27.1.5", "fill_27.1.7")
D_THIS = ("fill_27.1.0", "fill_28.1.1")
D_OF = ("fill_27.0", "fill_27.1.1", "fill_28.1.2")


def _drawn(form_type, session):
    document = build_parts(form_type, session)
    pdf = PDFFormFiller().fill(form_type, document)
    return document["parts"], pdf, read_drawn(form_type, pdf, document["parts"])


def _page_numbers(drawn, this, of):
    """In printing order, each page's (template page, copy, its position, the form's count)."""
    pages = {}
    for w in drawn:
        if w.full_name in this:
            pages.setdefault((w.page, w.copy), ["", ""])[0] = w.value
        elif w.full_name in of:
            pages.setdefault((w.page, w.copy), ["", ""])[1] = w.value
    return [(*place, *numbers) for place, numbers in pages.items()]


def _printed(drawn, names):
    return {(w.page, w.copy, w.full_name): w.value for w in drawn if w.full_name in names}


@pytest.mark.slow
def test_page_numbers_count_every_groups_copies(
    schedule_e_f_with_copies, generated_form_factory, creditor_payments
):
    # The sworn form's own "page 3 of 9": each group's rows past its slots take a copy, so
    # every later page moves down and every page counts all three copies (3c spec §5.2's table).
    schedule_e_f_with_copies()
    session = generated_form_factory().session
    creditor_payments(session, 4)

    parts, pdf, drawn = _drawn("schedule_e_f", session)

    assert [(p["page"], p["number"]) for p in parts if p["kind"] == "copy"] == [
        (2, 1),
        (4, 1),
        (5, 1),
    ]
    assert len(pymupdf.open("pdf", pdf)) == 9
    assert _page_numbers(drawn, EF_THIS, EF_OF) == [
        (1, None, "", "9"),
        (2, None, "2", "9"),
        (2, 1, "3", "9"),
        (3, None, "4", "9"),
        (4, None, "5", "9"),
        (4, 1, "6", "9"),
        (5, None, "7", "9"),
        (5, 1, "8", "9"),
        (6, None, "9", "9"),
    ]


@pytest.mark.slow
def test_page_numbers_count_the_copies_of_a_group_that_doesnt_come_first(
    schedule_e_f_with_copies, generated_form_factory, creditor_payments
):
    # Only Part 2 overflows: a declaration on Part 1's group would have numbered nothing.
    schedule_e_f_with_copies((3, 2, 3))
    session = generated_form_factory().session
    creditor_payments(session, 3)

    parts, _, drawn = _drawn("schedule_e_f", session)

    assert [(p["page"], p["number"]) for p in parts if p["kind"] == "copy"] == [(4, 1)]
    assert _page_numbers(drawn, EF_THIS, EF_OF) == [
        (1, None, "", "7"),
        (2, None, "2", "7"),
        (3, None, "3", "7"),
        (4, None, "4", "7"),
        (4, 1, "5", "7"),
        (5, None, "6", "7"),
        (6, None, "7", "7"),
    ]


def test_page_numbers_follow_the_pages_not_the_order_the_schema_declares(
    schedule_e_f_with_copies, generated_form_factory, creditor_payments
):
    schedule_e_f_with_copies(reverse=True)
    session = generated_form_factory().session
    creditor_payments(session, 4)

    form, *copies = build_parts("schedule_e_f", session)["parts"]

    # The parts document stays in printing order, as field_values promises.
    assert [copy["page"] for copy in copies] == [2, 4, 5]
    assert [
        copy["values"][this]
        for copy, this in zip(copies, ("fill_27.1.0", "fill_27.1.4", "fill_27.1.6"), strict=True)
    ] == ["3", "6", "8"]
    assert [form["values"][box] for box in EF_THIS] == ["2", "4", "5", "7", "9"]


def test_rows_that_fit_their_slots_print_no_page_number(
    schedule_e_f_with_copies, generated_form_factory, creditor_payments
):
    # The blank form's own numbering stands until a copy changes it.
    schedule_e_f_with_copies()
    session = generated_form_factory().session
    creditor_payments(session, 3)

    (form,) = build_parts("schedule_e_f", session)["parts"]

    assert not set(form["values"]) & {*EF_THIS, *EF_OF}


@pytest.mark.slow
def test_each_group_continues_its_own_rows_after_its_own_page(
    schedule_d_with_two_groups, generated_form_factory, creditor_payments
):
    session = generated_form_factory().session
    rows = creditor_payments(session, 7)
    names = [row.creditor_name for row in rows]

    _, pdf, drawn = _drawn("schedule_d", session)

    # Part 1 has five slots and Part 2 six, so rows 6 and 7 and row 7 go on copies of their pages.
    pages = pymupdf.open("pdf", pdf)
    assert ["Part 2:" in page.get_text() for page in pages] == [False, False, False, True, True]
    assert _printed(drawn, ["Creditors Name_3", "Creditors Name_4", "Name"]) == {
        (2, None, "Creditors Name_3"): names[2],
        (2, None, "Creditors Name_4"): names[3],
        (2, 1, "Creditors Name_3"): names[5],
        (2, 1, "Creditors Name_4"): names[6],
        (3, None, "Name"): names[0],
        (3, 1, "Name"): names[6],
    }
    assert _page_numbers(drawn, D_THIS, D_OF) == [
        (1, None, "", "5"),
        (2, None, "2", "5"),
        (2, 1, "3", "5"),
        (3, None, "4", "5"),
        (3, 1, "5", "5"),
    ]
