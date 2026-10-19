"""
check() plans what each box prints, and at what size, without drawing (3a2 spec §4.3).

Today a letter the form's font lacks prints as "?" and a value wider than its box is cut
off at the edge, both silently. check() shrinks a long value in 0.5 pt steps down to
6 pt and refuses what still doesn't fit, or can't be printed, naming the box and where
the filer fixes it.

Widths here are measured with PyMuPDF's Helvetica, a second source of the same font's
metrics, so "the first size that fits" isn't checked against check()'s own arithmetic.
"""

import dataclasses
import re
from pathlib import Path

import pymupdf
import pypdf
import pytest
from django.conf import settings
from pypdf.generic import NameObject, TextStringObject
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import _emit, _key
from apps.forms.services.pdf_filler import (
    InvalidFieldValue,
    PDFFormFiller,
    UnknownField,
    UnprintableLetter,
    ValueTooLong,
)
from apps.forms.services.text_fit import MIN_SIZE, fit
from apps.forms.services.widgets import field_of, template_widgets, widget_for

LAST_NAME = "Debtor1.Last name"  # Form 101 page 1: derived last_name, label "Last name"
EMAIL = "Debtor1.Email address_2"  # Form 101 page 9: derived email, label "Email address"
SSN = "Debtor1a.SSNum"  # Form 121: an 11-cell comb box, derived ssn_formatted
OTHER_PROPERTY = "53 Examples Season tickets country club membership"  # A/B line 53, multi-line
ASSISTANCE = "3 type"  # Form 103B line 3, multi-line, from the fee-waiver page
DISTRICT = "Bankruptcy District Information"  # a combo box on every form


def _plan(form_type, values):
    (part,) = PDFFormFiller().check(form_type, values)
    assert part.part == {"kind": "form", "values": values}
    return part.widgets


def _widgets(form_type, full_name):
    template = load_schema(form_type).template_filename
    return [w for w in template_widgets(template) if w.full_name == full_name and w.drawn]


def _room(widget):
    """The width pypdf's clip leaves for text: the box less its padding on each side."""
    return widget.width - 4 * widget.margin


def _helvetica(text, size):
    return pymupdf.get_text_length(text, fontname="helv", fontsize=size)


# Helvetica's FontBBox (its AFM), per 1000 em: pypdf spaces lines by its height.
_HELVETICA_BOTTOM, _HELVETICA_TOP = -225, 931
_LEADING = (_HELVETICA_TOP - _HELVETICA_BOTTOM) / 1000


def _pypdf_stream(form_type, widget, value, size=-1):
    """The appearance pypdf builds for one widget holding value, at size or its own."""
    template = load_schema(form_type).template_filename
    writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
    page = writer.pages[widget.page - 1]
    annotation = next(
        a.get_object()
        for a in page["/Annots"]
        if a.get_object().get("/Subtype") == "/Widget"
        and widget_for(template, widget.page, a.get_object(), float(page.mediabox.top)) == widget
    )
    field = field_of(annotation)
    field[NameObject("/V")] = TextStringObject(value)
    appearance = TextStreamAppearance.from_text_annotation(
        writer, page, False, writer.root_object["/AcroForm"], field, annotation, user_font_size=size
    )
    return appearance.get_data()


# ── Letters ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "last_name,letter",
    [
        ("Varée", None),
        ("Peñalta", None),
        ("Grünholt", None),
        ("Łazar", None),
        ("Wąsowicz", "ą"),
        ("Dvořák", "ř"),
        ("Nguyễn", "ễ"),
        # pypdf reads the template's /.notdef, at code 173, as □: drawn, it prints that code,
        # a soft hyphen.
        ("Nowak□", "□"),
    ],
)
def test_a_letter_the_form_cannot_print_is_refused(last_name, letter):
    if letter is None:
        (planned,) = _plan("form_101", {LAST_NAME: last_name})
        assert (planned.value, planned.size) == (last_name, 10.0)
        return
    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("form_101", {LAST_NAME: last_name})
    assert refused.value.letter == letter
    assert (refused.value.label, refused.value.step, refused.value.page) == (
        "Last name",
        "debtor_info",
        None,
    )
    assert str(refused.value) == (
        f"The court form can't print the letter “{letter}” in “Last name”. "
        "Change it to a letter without the mark."
    )


@pytest.mark.parametrize(
    "space", ["\t", "\N{NO-BREAK SPACE}", "\N{THIN SPACE}", "\N{NARROW NO-BREAK SPACE}"]
)
def test_a_tab_or_any_other_space_prints_as_a_space(space):
    # The template's font draws U+00A0 as "€" (R34) and has no glyph for the rest (R36).
    (planned,) = _plan("form_101", {LAST_NAME: f"Varée{space}Peñalta"})
    assert planned.value == "Varée Peñalta"


@pytest.mark.parametrize("invisible", ["\N{SOFT HYPHEN}", "\N{ZERO WIDTH SPACE}"])
def test_a_character_that_prints_nothing_is_left_out(invisible):
    # Format characters, pasted along with text, print nothing anyway (R36).
    (planned,) = _plan("form_101", {LAST_NAME: f"Varée{invisible}Peñalta"})
    assert planned.value == "VaréePeñalta"


def test_a_control_character_is_refused():
    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("form_101", {LAST_NAME: "Varée\x07"})
    assert refused.value.letter == "\x07"


@pytest.mark.parametrize("letter", ["(", ")", "\\"])
def test_a_comb_box_refuses_a_character_that_breaks_its_cells(letter):
    # pypdf draws each cell's character as its own string, which these break (R33).
    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("form_121", {SSN: f"900-12-345{letter}"})
    assert (refused.value.letter, refused.value.label, refused.value.step) == (
        letter,
        "Debtor 1 SSN",
        "debtor_info",
    )


def test_a_refusal_names_the_box_as_its_binding_does():
    # Bound: the schema's label and fix. The index calls the same box "Running header: …".
    with pytest.raises(UnprintableLetter) as bound:
        PDFFormFiller().check("form_101", {"Debtor1.Name": "Ana Wąsowicz"})
    assert (bound.value.label, bound.value.step) == ("Debtor name", "debtor_info")
    # A key no binding produced, such as one widget of a name bound as a whole, or an
    # unbound box, is named by its index row and links nowhere.
    page_2 = next(w for w in _widgets("form_101", "Debtor1.Name") if w.page == 2)
    for key, label in [
        (page_2.key, "Running header: Debtor 1 (First Name Middle Name Last Name)"),
        ("Suffix Sr Jr II III_2", "Suffix (Sr., Jr., II, III)"),
    ]:
        with pytest.raises(UnprintableLetter) as unbound:
            PDFFormFiller().check("form_101", {key: "Wąsowicz"})
        assert (unbound.value.label, unbound.value.step, unbound.value.page) == (label, None, None)


# ── Fit ───────────────────────────────────────────────────────────────


def test_a_long_value_shrinks_before_it_is_refused():
    (box,) = _widgets("form_101", EMAIL)
    email = "kestrel.wanamaker.okonkwo@example.org"
    assert _helvetica(email, box.size) > _room(box)  # too wide at the box's own 10 pt

    (planned,) = _plan("form_101", {EMAIL: email})
    assert planned.value == email
    assert MIN_SIZE <= planned.size < box.size
    assert planned.size % 0.5 == 0
    # The first size that fits: half a point larger doesn't.
    assert _helvetica(email, planned.size) <= _room(box)
    assert _helvetica(email, planned.size + 0.5) > _room(box)

    too_long = "kestrel.wanamaker.okonkwo.marchetti-oyel@example.org"
    # Too wide at 6 pt, the smallest size the check prints, though it would fit at 5.5.
    assert _helvetica(too_long, 6.0) > _room(box)
    assert _helvetica(too_long, 5.5) <= _room(box)
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("form_101", {EMAIL: too_long})
    assert (refused.value.label, refused.value.step, refused.value.page) == (
        "Email address",
        "debtor_info",
        None,
    )
    assert str(refused.value) == (
        "“Email address” is too long to fit on the court form, even in small print. Shorten it."
    )


def test_a_word_too_wide_for_a_multi_line_box_is_refused():
    (box,) = _widgets("form_103b", ASSISTANCE)
    word = "W" * 60
    assert _helvetica(word, MIN_SIZE) > _room(box)  # too wide even at 6 pt, on one line
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("form_103b", {ASSISTANCE: f"SNAP {word}"})
    assert (refused.value.label, refused.value.page) == ("Type of assistance", "/fee-waiver")


def test_a_comb_value_longer_than_its_cells_is_refused_not_shrunk():
    (box,) = _widgets("form_121", SSN)
    assert (box.comb, box.max_len) == (True, 11)
    (planned,) = _plan("form_121", {SSN: "900-12-3456"})
    assert (planned.value, planned.size) == ("900-12-3456", box.size)
    with pytest.raises(ValueTooLong):
        PDFFormFiller().check("form_121", {SSN: "900-12-34567"})


def test_a_box_with_a_maximum_length_refuses_a_longer_value():
    # Form 101's State box takes 2 characters (MaxLen), though 3 would fit its width.
    (planned,) = _plan("form_101", {"Debtor1.State": "IL"})
    assert planned.value == "IL"
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("form_101", {"Debtor1.State": "ILL"})
    assert (refused.value.label, refused.value.step) == ("State", "debtor_info")


def test_parentheses_take_the_room_pypdf_gives_them():
    # pypdf measures "(" as "\(" when it places text, so a value that fits only without
    # the backslashes would start left of a right-aligned box's clip (R33).
    (box,) = _widgets("form_101", LAST_NAME)
    count = 1  # as many narrow letters as fit between the parentheses at the box's size
    while _helvetica(f"({'i' * (count + 1)})", box.size) <= _room(box):
        count += 1
    value = f"({'i' * count})"
    assert _helvetica(value, box.size) <= _room(box) < _helvetica(rf"\({'i' * count}\)", box.size)

    (planned,) = _plan("form_101", {LAST_NAME: value})
    assert planned.value == value  # pypdf escapes /V itself
    assert planned.size < box.size


def test_a_multi_line_value_wraps_at_spaces_into_lines_that_fit():
    (box,) = _widgets("schedule_a_b", OTHER_PROPERTY)
    description = (
        "Season tickets to a minor league ballpark, a canoe and two paddles, "
        "and a set of carpentry tools kept in a rented storage unit"
    )
    (planned,) = _plan("schedule_a_b", {OTHER_PROPERTY: description})
    lines = planned.value.split("\n")
    assert len(lines) > 1
    assert " ".join(lines) == description
    assert all(_helvetica(line, planned.size) <= _room(box) for line in lines)


def test_a_multi_line_value_shrinks_to_the_largest_size_its_lines_fit():
    (box,) = _widgets("schedule_a_b", OTHER_PROPERTY)
    items = ["A canoe", "A bicycle", "A tent", "A saddle", "A kiln"]
    assert all(_helvetica(item, 10) <= _room(box) for item in items)  # none wraps at any size
    # T3 lowers line 1 by 2 × margin (R35), so the lines get the box's height less that.
    height = box.height - 2 * box.margin
    sizes = [10 - 0.5 * step for step in range(9)]  # 10, 9.5, …, 6
    expected = max(size for size in sizes if len(items) * size * _LEADING <= height)
    assert len(items) * (expected + 0.5) * _LEADING > height

    (planned,) = _plan("schedule_a_b", {OTHER_PROPERTY: "\n".join(items)})
    assert planned.value.split("\n") == items
    assert planned.size == expected

    # pypdf's own layout: the last line's lowest point, lowered with line 1, stays above the
    # clip's bottom at the planned size and falls below it 0.5 pt larger.
    for size, fits in [(planned.size, True), (planned.size + 0.5, False)]:
        stream = _pypdf_stream("schedule_a_b", box, planned.value, size)
        baseline = sum(float(y) for y in re.findall(rb"-?[0-9.]+ (-?[0-9.]+) Td", stream))
        lowest = baseline + _HELVETICA_BOTTOM * size / 1000 - 2 * box.margin
        assert (lowest >= box.margin) is fits, size


@pytest.mark.parametrize("line_break", ["\r\n", "\r", "\N{LINE SEPARATOR}"])
def test_a_line_break_starts_a_new_line_only_in_a_multi_line_box(line_break):
    (multi_line,) = _plan("schedule_a_b", {OTHER_PROPERTY: f"A canoe{line_break}A bicycle"})
    assert multi_line.value == "A canoe\nA bicycle"
    (single_line,) = _plan("form_101", {LAST_NAME: f"Varée{line_break}Peñalta"})
    assert single_line.value == "Varée Peñalta"


@pytest.mark.parametrize(
    "form_type,name,page,value,limit",
    [
        ("form_101", "Case number1", 1, "24-10001", "height"),
        ("form_107", "Email 16a", 7, "rosalind.oyelaran.synthetic@example.org", "width"),
    ],
)
def test_an_auto_size_box_starts_where_pypdf_would_size_it(form_type, name, page, value, limit):
    # These boxes have no size of their own: pypdf picks one per value, as large as the
    # box's height allows, or its width when the value is long.
    box = next(w for w in _widgets(form_type, name) if w.page == page)
    assert box.size == 0
    stream = _pypdf_stream(form_type, box, value)
    pypdf_size = float(re.search(rb"/Helv ([0-9.]+) Tf", stream)[1])
    by_height = round((box.height - 2 * box.margin) / _LEADING, 1)
    assert (pypdf_size == by_height) is (limit == "height")

    (planned,) = _plan(form_type, {box.key: value})
    assert planned.size == pypdf_size


def test_a_value_pypdf_would_print_below_6_pt_is_refused():
    # pypdf's auto size goes down to 4 pt; the check stops at 6.
    box = next(w for w in _widgets("form_101", "Case number1") if w.page == 1)
    assert box.size == 0  # auto size
    value = "24-10001 and 24-10002 and 24-10003 and 24-10004"
    pypdf_size = float(re.search(rb"/Helv ([0-9.]+) Tf", _pypdf_stream("form_101", box, value))[1])
    # pypdf would print it below 6 pt, where it fits, so only the floor refuses it.
    assert pypdf_size < 6.0
    assert _helvetica(value, pypdf_size) <= _room(box)
    with pytest.raises(ValueTooLong):
        PDFFormFiller().check("form_101", {box.key: value})


def test_branches_no_template_has():
    # No template has a multi-line auto-size box or a comb box without a MaxLen.
    (lines,) = _widgets("schedule_a_b", OTHER_PROPERTY)
    template = load_schema("schedule_a_b").template_filename
    assert fit(dataclasses.replace(lines, size=0.0), template, "A canoe") == ("A canoe", 12.0)
    (cells,) = _widgets("form_121", SSN)
    uncounted = dataclasses.replace(cells, max_len=None)
    template = load_schema("form_121").template_filename
    assert fit(uncounted, template, "900-12-3456-78") == ("900-12-3456-78", cells.size)


# ── Which widgets a key fills ─────────────────────────────────────────


def test_a_widgets_own_key_fills_only_that_widget():
    first, second = _widgets("schedule_i", "Assistance 8f")
    planned = _plan("schedule_i", {first.key: "SNAP"})
    assert [(p.widget, p.value) for p in planned] == [(first, "SNAP")]
    # It wins over its full name, which still fills the name's other widget.
    planned = _plan("schedule_i", {"Assistance 8f": "Housing aid", second.key: "SNAP"})
    assert [(p.widget, p.value) for p in planned] == [(first, "Housing aid"), (second, "SNAP")]


def test_a_full_name_fills_every_drawn_widget_but_never_a_stacked_one():
    planned = _plan("schedule_i", {"Time employed Debtor 1": "4 years"})
    assert [p.widget for p in planned] == _widgets("schedule_i", "Time employed Debtor 1")
    assert len(planned) == 2
    # Schedule D page 2 lays a second "4_3" over the first; only the first prints.
    (planned,) = _plan("schedule_d", {"4_3": "2.1"})
    assert (planned.widget.tag, planned.widget.stacked) == ("T13", False)


def test_a_key_that_names_no_drawn_widget_is_refused():
    keys = ["4_3@2:T14", "Debtor9.Name", "4_3@2"]  # stacked; no such name; not a key
    with pytest.raises(UnknownField) as refused:
        PDFFormFiller().check("schedule_d", dict.fromkeys(keys, "1"))
    assert refused.value.names == sorted(keys)


def test_a_box_prints_its_state_on_the_widgets_that_have_it():
    planned = _plan("form_101", {"Check Box1": "/Chapter 7"})
    # Chapter 7 is printed on pages 1 and 3; the other options print empty.
    assert sorted(p.value for p in planned) == ["/Chapter 7"] * 2 + ["/Off"] * (len(planned) - 2)
    assert {p.size for p in planned} == {None}
    with pytest.raises(InvalidFieldValue):
        PDFFormFiller().check("form_101", {"Check Box1": "/Chapter 9"})


def test_a_combo_prints_one_of_its_options():
    (planned,) = _plan("form_121", {DISTRICT: "Northern District of Illinois"})
    assert (planned.value, planned.size) == ("Northern District of Illinois", 8.0)
    with pytest.raises(InvalidFieldValue):
        PDFFormFiller().check("form_121", {DISTRICT: "District of Nowhere"})


def test_every_constant_prints():
    constants = [
        (form_type, field)
        for form_type in get_all_form_types()
        for field in load_schema(form_type).fields
        if field.source == "constant"
    ]
    assert constants  # four checkboxes today
    for form_type, field in constants:
        value = _emit(field, field.value)  # what resolve() emits for it
        assert value is not None
        planned = _plan(form_type, {_key(field): value})
        assert value in [p.value for p in planned], (form_type, field.pdf_field)
