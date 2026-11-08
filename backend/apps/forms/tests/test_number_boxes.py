"""
A group's number box takes every row the form can reach (3c spec §5.4). /MaxLen stops typing, and
nothing can type in a baked page; and a number that still can't fit is refused in plain words. A
text read-back can't see a clipped digit (3a2's lesson), so these tests also judge pixels.
"""

import pymupdf
import pytest

from apps.forms.field_index import load_index
from apps.forms.registry import build_parts
from apps.forms.schema import FieldSpec, FormSchema, load_schema
from apps.forms.services.pdf_filler import (
    PDFFormFiller,
    Planned,
    ValueTooLong,
    _baked,
    _clone,
)
from apps.forms.services.text_fit import fit
from apps.forms.services.widgets import template_widgets
from apps.forms.tests.pdf_readback import read_drawn
from apps.forms.views import _failure


def _widget(form_type, name, tag=None):
    template = load_schema(form_type).template_filename
    return next(
        w
        for w in template_widgets(template)
        if w.full_name == name and (tag is None or w.tag == tag)
    )


def _clear_of_the_clip(page, empty, widget) -> float:
    """
    Points between the drawn value's last ink and the right edge of the clip pypdf declares
    (x0 + 2 x margin + field width). Below zero, the ink runs past it.
    """
    edge = widget.rect[2] - 2 * widget.margin
    rect = pymupdf.Rect(widget.rect)
    drawn = page.get_pixmap(dpi=1440, clip=rect, colorspace=pymupdf.csGRAY)
    blank = empty.get_pixmap(dpi=1440, clip=rect, colorspace=pymupdf.csGRAY)
    rightmost = None
    for y in range(drawn.height):
        for x in range(drawn.width):
            at = y * drawn.stride + x
            if blank.samples[at] - drawn.samples[at] > 64 and (rightmost is None or x > rightmost):
                rightmost = x
    assert rightmost is not None, "the box printed nothing"
    return edge - (drawn.x + rightmost + 1) * 72 / 1440


def _drawn_alone(form_type, widget, value, size):
    """The widget drawn at `size` whatever fit() says, on its one page, and that page blank."""
    template = load_schema(form_type).template_filename
    planned = (Planned(widget, value, size),)
    page = widget.page
    return (
        _baked(_clone(form_type, template), template, planned, page)[0],
        _baked(_clone(form_type, template), template, (), page)[0],
    )


@pytest.mark.slow
def test_the_clip_check_sees_a_clipped_number(schedule_d_with_copies):
    # So the checks below mean what they say: "2.100" at 6 pt runs past undefined_12's clip.
    widget = _widget("schedule_d", "undefined_12")
    page, empty = _drawn_alone("schedule_d", widget, "2.100", 6.0)
    assert _clear_of_the_clip(page, empty, widget) < 0


@pytest.mark.slow
@pytest.mark.parametrize(
    "form_type, name, tag, number",
    [
        # R4's slack, for the font that actually draws: every last digit in the narrowest box.
        *(("schedule_d", "undefined_12", None, f"2.1{digit}") for digit in range(10)),
        ("schedule_d", "undefined_12", None, "2.99"),
        ("schedule_d", "undefined_12", None, "2.9"),
        # Every other number box (3c spec §5.4), each with a last digit that leaves the least clear
        # at the widest number it takes. H's "999" draws larger than "1000", so it takes both.
        *(("schedule_d", "undefined_19", tag, "2.17") for tag in ("T37", "T63")),
        ("schedule_e_f", "undefined_12", None, "2.17"),
        *(("schedule_e_f", "undefined_19", tag, "2.17") for tag in ("T30", "T57")),
        *(("schedule_e_f", f"undefined_4.{n}", None, "4.17") for n in (4, 5, 6)),
        *(("schedule_g", f"fill 2.{n}", None, "999") for n in range(6, 14)),
        *(("schedule_h", f"fill 3.{n}", None, "999") for n in range(4, 12)),
        *(("schedule_h", f"fill 3.{n}", None, "1000") for n in range(4, 12)),
        ("schedule_g", "fill 2.10", None, "10"),
        ("schedule_d", "fill_27.1.0", None, "100"),
    ],
)
def test_a_number_that_fits_is_not_clipped(form_type, name, tag, number):
    widget = _widget(form_type, name, tag)
    template = load_schema(form_type).template_filename
    value, size = fit(widget, template, number, number_box=True)
    page, empty = _drawn_alone(form_type, widget, value, size)
    assert _clear_of_the_clip(page, empty, widget) > 0


def test_no_box_but_a_number_box_takes_the_slack():
    # "2.12" is 0.076 pt over undefined_12's field at 6 pt: any other box's value that far over
    # would run into the box's edge, so it stays refused (R4).
    widget = _widget("schedule_d", "undefined_12")
    template = load_schema("schedule_d").template_filename
    assert fit(widget, template, "2.12") is None
    assert fit(widget, template, "2.12", number_box=True) == ("2.12", 6.0)


@pytest.mark.slow
def test_schedule_d_prints_its_twelfth_secured_debt(
    schedule_d_with_copies, generated_form_factory, creditor_payments
):
    # Row 12 lands in undefined_12, the narrow box, on the third copy of page 2.
    session = generated_form_factory().session
    rows = creditor_payments(session, 12)

    document = build_parts("schedule_d", session)
    pdf = PDFFormFiller().fill("schedule_d", document)
    drawn = read_drawn("schedule_d", pdf, document["parts"])

    printed = {(w.copy, w.full_name): w.value for w in drawn}
    assert printed[(3, "undefined_12")] == "2.12"
    assert printed[(3, "Creditors Name_3")] == rows[11].creditor_name


@pytest.mark.slow
def test_schedule_g_prints_its_tenth_contract(
    schedule_g_numbered, generated_form_factory, creditor_payments
):
    # The blank form's "fill 2.10" holds one letter: a filer with ten contracts was refused.
    session = generated_form_factory().session
    creditor_payments(session, 14)

    document = build_parts("schedule_g", session)
    pdf = PDFFormFiller().fill("schedule_g", document)
    drawn = read_drawn("schedule_g", pdf, document["parts"])

    printed = {(w.copy, w.full_name): w.value for w in drawn}
    assert printed[(None, "fill 2.9")] == "9"
    assert printed[(None, "fill 2.10")] == "10"
    assert printed[(None, "fill 2.13")] == "13"
    assert printed[(1, "fill 2.6")] == "14"


@pytest.mark.parametrize("number, size", [("10", 10.0), ("100", 7.0), ("999", 7.0)])
def test_a_number_box_takes_more_than_its_max_length(schedule_g_numbered, number, size):
    (part,) = PDFFormFiller().check("schedule_g", {"fill 2.10": number})
    assert [(p.value, p.size) for p in part.widgets] == [(number, size)]


@pytest.mark.parametrize("position, size", [("9", 10.0), ("10", 10.0), ("100", 7.0)])
def test_a_page_number_prints_whole_in_its_small_box(schedule_d_with_copies, position, size):
    # The page-number boxes are 16.3 pt wide: a long form reaches two and three digits.
    (part,) = PDFFormFiller().check("schedule_d", {"fill_27.1.0": position})
    assert [(p.value, p.size) for p in part.widgets] == [(position, size)]


def test_a_box_no_group_numbers_keeps_its_max_length():
    # Form 101's state box holds two letters: only a group's number box skips /MaxLen.
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("form_101", {"Debtor1.State": "ILL"})
    assert str(refused.value).endswith("Shorten it.")


def _refused_copy(form_type, key, value, page=2):
    document = {
        "version": 2,
        "parts": [{"kind": "copy", "page": page, "number": 1, "values": {key: value}}],
    }
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check(form_type, document)
    return refused.value


@pytest.mark.parametrize(
    "key, value, words",
    [
        ("undefined_19@2:T37", "2.100", "The entry number"),
        ("fill_27.1.0", "1000", "The page number"),
    ],
)
def test_a_number_that_cant_fit_is_refused_in_plain_words(
    schedule_d_with_copies, key, value, words
):
    refused = _refused_copy("schedule_d", key, value)

    assert str(refused) == (
        f"“{words}” is too long to fit on the court form, even in small print. "
        "This form has more entries than its boxes can hold."
    )
    # The fix is where the group's rows come from, and no index label reaches the filer.
    assert (refused.step, refused.page) == (None, "/sofa")
    index_labels = {row.label for rows in load_index("form_b106d.pdf").values() for row in rows}
    assert refused.label not in index_labels
    assert not any(label and label in str(refused) for label in index_labels)


def test_a_total_too_wide_for_its_box_is_refused_in_plain_words(schedule_d_with_totals):
    refused = _refused_copy("schedule_d", "undefined_23", "9" * 40 + ".00")

    assert refused.label == "The total"
    assert (refused.step, refused.page) == (None, "/sofa")


def test_the_dashboard_gets_a_number_refusals_sentence_and_its_fix(schedule_d_with_copies):
    refused = _refused_copy("schedule_d", "undefined_19@2:T37", "2.100")

    body, code = _failure("schedule_d", refused)

    assert code == 422
    assert body["page"] == "/sofa"
    assert "entry number" in body["error"]


def test_a_groups_fix_is_where_its_rows_are_answered():
    from apps.forms.services.fill_resolver import group_fix

    slot = FieldSpec(
        pdf_field="x",
        type="text",
        source="asked",
        page=1,
        label="x",
        required=False,
        conditional_on=None,
        value=None,
        rule=None,
        ingest_key=None,
        binding="household.dependents[].age",
        repeat="g",
        repeat_capacity=1,
        row=1,
        legal_review=False,
    )
    schema = FormSchema("schedule_j", "form_b106j.pdf", "v1", [slot])

    assert group_fix(schema, "g") == {"step": "income_info"}
    assert group_fix(schema, "another") == {}
