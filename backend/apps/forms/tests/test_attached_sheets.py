"""
Rows past a repeat group's last slot print on an attached sheet when the form has no page
to copy (3a2 spec §5.3): plain US Letter pages after the form, headed by the filer's name,
the form's title and the case number, each row under the form's columns and labelled with
the line it continues. 3a2 proves it on a synthetic Schedule A/B group (§5.4; conftest's
schedule_a_b_with_sheet): line 3's four vehicles, 3.1 and 3.2 on page 2, 3.3 and 3.4 on
page 3.
"""

import json
import re
import unicodedata
from io import BytesIO, StringIO
from pathlib import Path

import pymupdf
import pypdf
import pytest
from django.conf import settings

from apps.forms.registry import build_parts, get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services import sheets
from apps.forms.services.derivations import DERIVATIONS
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong
from apps.forms.services.sheets import draw_sheet, plan_sheet, sheet_spec
from apps.forms.services.text_fit import font_for
from apps.forms.tests.pdf_readback import read_drawn, read_sheets

MAKES = ["Honda", "Toyota", "Subaru", "Mazda", "Volvo", "Kia", "Saab", "Fiat"]
SLOTS = {  # line 3's boxes: (make, value), 3.1 to 3.4
    "3.1": ("3 1", "undefined_15"),
    "3.2": ("If you own or have more than one describe here", "undefined_17"),
    "3.3": ("1_3", "undefined_19"),
    "3.4": ("1_4", "undefined_21"),
}
HEADER = (
    "Maria Torres",
    "Official Form 106A/B, Schedule A/B: Property (attached sheet)",
    "Case number (if known)",
)
LABELS = ("", "Make", "Current value of the portion you own")
TITLE = "Official Form 106A/B, Schedule A/B: Property"
COLUMNS = [
    {"label": "Make", "width": 300.0},
    {"label": "Current value of the portion you own", "width": 168.0},
]


@pytest.fixture
def session(generated_form_factory, schedule_a_b_with_sheet):
    """Maria Torres's completed intake in the Northern District of Illinois."""
    return generated_form_factory().session


def _spec():
    return load_schema("schedule_a_b").groups["ab_line_3"].sheet


def _sheet_part(rows):
    """A/B's sheet part with these rows, as resolve_parts() stores one."""
    return {
        "kind": "sheet",
        "group": "ab_line_3",
        "title": TITLE,
        "columns": COLUMNS,
        "name": "Maria Torres",
        "rows": rows,
    }


def _drawn(session):
    """Schedule A/B's parts for the session, and its drawn PDF."""
    document = build_parts("schedule_a_b", session)
    return document["parts"], PDFFormFiller().fill("schedule_a_b", document)


def test_extra_rows_print_on_an_attached_sheet(session, creditor_payments):
    creditor_payments(session, 5, MAKES)

    parts, pdf = _drawn(session)

    # One sheet part carries the rows past the slots, the name its header prints (R23), and
    # the title and columns it is drawn with (R63).
    assert parts[1:] == [
        {
            "kind": "sheet",
            "group": "ab_line_3",
            "title": TITLE,
            "columns": COLUMNS,
            "name": "Maria Torres",
            "rows": [{"line": "3.5", "cells": ["Volvo", "500.00"]}],
        }
    ]
    pages = pymupdf.open("pdf", pdf)
    assert len(pages) == 11  # A/B's ten pages, then the sheet
    assert len(pypdf.PdfReader(BytesIO(pdf)).pages) == 11  # pypdf opens it the same
    # Rows 1 to 4 fill line 3's slots on pages 2 and 3; the fifth prints on the sheet.
    printed = {w.full_name: w.value for w in read_drawn("schedule_a_b", pdf, parts)}
    assert {line: (printed[make], printed[value]) for line, (make, value) in SLOTS.items()} == {
        "3.1": ("Honda", "100.00"),
        "3.2": ("Toyota", "200.00"),
        "3.3": ("Subaru", "300.00"),
        "3.4": ("Mazda", "400.00"),
    }
    (sheet,) = read_sheets(pdf, _spec())
    assert (sheet.header, sheet.labels, sheet.rows) == (
        HEADER,
        LABELS,
        (("3.5", "Volvo", "500.00"),),
    )
    assert "Volvo" not in "".join(page.get_text() for page in pages[:10])
    # Each character stays in its column, and no line runs into the next.
    assert (sheet.crossing, sheet.overlapping) == ((), ())
    # Every line is Helvetica at 10 pt (spec §5.3).
    spans = [
        span
        for block in pages[10].get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
    ]
    assert {(span["font"], span["size"]) for span in spans} == {("Helvetica", 10.0)}
    # The case number's blank line runs on from its label.
    label = pages[10].search_for("Case number (if known)")[0]
    blanks = [
        item
        for drawing in pages[10].get_drawings()
        for item in drawing["items"]
        if item[0] == "l" and item[1].x >= label.x1 and label.y0 <= item[1].y <= label.y1 + 2
    ]
    assert len(blanks) == 1 and blanks[0][2].x - blanks[0][1].x >= 144  # 2 in at least


def test_a_cell_filled_to_its_padding_stays_in_its_column(session, creditor_payments):
    # The Make column runs from 90 to 390 pt, and a cell's text starts 2 pt in, at 92, and
    # wraps within 296 pt, ending by 388. Row 3.5: thirty W's and two i's, 293.2 pt at 10 pt,
    # end at 385.2; a third i would end at 390.2, so it starts the next line. Row 3.6:
    # thirty-one W's and an i, 297.64 pt, would end at 389.64, inside the column but past
    # its right padding, so the i starts the next line.
    make = "W" * 30 + " i" * 4
    creditor_payments(session, 6, [*MAKES[:4], make, "W" * 31 + " i"])

    _, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.lines == (
        (("3.5",), ("W" * 30 + " i i", "i i"), ("500.00",)),
        (("3.6",), ("W" * 31, "i"), ("600.00",)),
    )
    assert sheet.crossing == ()
    (first_line,) = pymupdf.open("pdf", pdf)[10].search_for("W" * 30 + " i i")
    assert (round(first_line.x0, 2), round(first_line.x1, 2)) == (92.0, 385.2)


def _long_make(n):
    """A make that wraps to three lines in its column."""
    return (
        f"Vehicle {n}: Honda Civic LX sedan, silver, bought used in 2019 with the dealer’s "
        "extended service contract, roof rack, winter tyres and a tow hitch"
    )


def test_a_long_sheet_runs_to_a_second_page(session, creditor_payments):
    # Twenty rows on the sheet: three of one line, then three-line rows. Page 1 takes
    # fourteen, and has room left for the first line of the fifteenth but not the whole row.
    makes = {n: _long_make(n) if n >= 8 else MAKES[n - 1] for n in range(1, 25)}
    creditor_payments(session, 24, list(makes.values()))

    _, pdf = _drawn(session)

    assert len(pymupdf.open("pdf", pdf)) == 12
    first, second = read_sheets(pdf, _spec())
    for page in (first, second):
        assert (page.header, page.labels) == (HEADER, LABELS)  # on every page of the sheet
        # Nothing is cut off: every character inside the margins and its column, and no
        # line running into the next.
        x0, y0, x1, y1 = page.ink
        assert 54 <= x0 and 54 <= y0 and x1 <= 612 - 54 and y1 <= 792 - 54
        assert (page.crossing, page.overlapping) == ((), ())
    # Every row prints once, whole and in order: none is split across the pages.
    assert [*first.rows, *second.rows] == [(f"3.{n}", makes[n], f"{n}00.00") for n in range(5, 25)]
    assert (len(first.rows), len(second.rows)) == (14, 6)
    assert 792 - 54 - first.ink[3] > 6 + 14  # a row gap and a line: the fifteenth's first line


@pytest.mark.parametrize(
    "fixture, form_type, total, printed",
    [
        ("schedule_d_with_copies", "schedule_d", "undefined_24", {(None, "2100.00"), (1, "")}),
        ("schedule_a_b_with_sheet", "schedule_a_b", "undefined_26", {(None, "2100.00")}),
    ],
    ids=["copies", "a sheet"],
)
def test_totals_count_rows_printed_on_copies_and_sheets(
    request,
    monkeypatch,
    generated_form_factory,
    creditor_payments,
    fixture,
    form_type,
    total,
    printed,
):
    # Six rows of 100.00 to 600.00: Schedule D's five slots and one copy, A/B's four slots and
    # its sheet. A total adds up every row, not the slots (spec §5.1); page 2's total of
    # Schedule D prints once, on the form, not on its copy (R24).
    schemas = request.getfixturevalue(fixture)
    path = schemas / f"{form_type}.json"
    data = json.loads(path.read_text())
    box = next(f for f in data["fields"] if f["pdf_field"] == total)
    box.update(source="derived", rule="every_row_total")
    path.write_text(json.dumps(data))
    load_schema.cache_clear()
    monkeypatch.setitem(
        DERIVATIONS,
        "every_row_total",
        lambda s: str(sum(row.total_paid for row in s.sofa_report.creditor_payments.all())),
    )
    session = generated_form_factory().session
    creditor_payments(session, 6, MAKES)

    document = build_parts(form_type, session)
    pdf = PDFFormFiller().fill(form_type, document)

    assert [part["kind"] for part in document["parts"]][1:] == (
        ["copy"] if form_type == "schedule_d" else ["sheet"]
    )
    drawn = read_drawn(form_type, pdf, document["parts"])
    assert {(w.copy, w.value) for w in drawn if w.full_name == total} == printed


def test_a_letter_the_sheet_cannot_print_is_refused(session, creditor_payments):
    # The fifth vehicle prints only on the sheet; its make comes from the SOFA.
    rows = creditor_payments(session, 5, MAKES)
    rows[4].creditor_name = "Wąsowicz Motors"
    rows[4].save()
    document = build_parts("schedule_a_b", session)
    assert document["parts"][1]["rows"][0]["cells"][0] == "Wąsowicz Motors"

    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("schedule_a_b", document)

    assert str(refused.value) == (
        "The court form can't print the letter “ą” in “Make”. "
        "Change it to a letter without the mark."
    )
    # Fixed where the column's slots' binding is changed (fix_for): a SOFA list's, the SOFA page.
    assert (refused.value.step, refused.value.page) == (None, "/sofa")


def test_the_sheet_prints_every_letter_the_form_prints(session, creditor_payments):
    # The sheet prints in the templates' own encoding (R62), so Ł, ł and ı, which WinAnsi
    # lacks, print as themselves in its header and in a cell, as on the form.
    debtor = session.debtor_info
    debtor.first_name, debtor.last_name = "Łucja", "Kıłıç"
    debtor.save()
    creditor_payments(session, 5, [*MAKES[:4], "Łada Niva ł ı"])
    pymupdf.TOOLS.mupdf_warnings()  # clears them

    _, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert (sheet.header[0], sheet.rows) == (
        "Łucja Kıłıç",
        (("3.5", "Łada Niva ł ı", "500.00"),),
    )
    assert pymupdf.TOOLS.mupdf_warnings() == ""
    text = pypdf.PdfReader(BytesIO(pdf)).pages[10].extract_text()
    assert "Łucja Kıłıç" in text and "Łada Niva ł ı" in text


def test_letters_typed_with_their_marks_apart_print_whole_on_the_form_and_the_sheet(
    session, creditor_payments
):
    # é typed as e and U+0301 (pasted from a file name, say) is checked, measured and drawn
    # as é, the one letter the font prints, on the form's boxes and on its sheet alike.
    debtor = session.debtor_info
    debtor.first_name = unicodedata.normalize("NFD", "José")
    debtor.last_name = unicodedata.normalize("NFD", "Muñoz")
    debtor.save()
    creditor_payments(session, 5, [*MAKES[:4], unicodedata.normalize("NFD", "Citroën Müller")])

    parts, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert (sheet.header[0], sheet.rows) == (
        "José Muñoz",
        (("3.5", "Citroën Müller", "500.00"),),
    )
    name_boxes = {f.pdf_field for f in load_schema("schedule_a_b").fields if f.rule == "full_name"}
    printed = [w.value for w in read_drawn("schedule_a_b", pdf, parts) if w.full_name in name_boxes]
    assert printed and set(printed) == {"José Muñoz"}


def test_a_name_neither_the_form_nor_the_sheet_can_print_is_refused_on_the_form(
    session, creditor_payments
):
    # The form's Debtor 1 box refuses the letter first, with or without a sheet: the box
    # named is one that can't print it.
    debtor = session.debtor_info
    debtor.last_name = "Wąsowicz"
    debtor.save()

    def refusal():
        with pytest.raises(UnprintableLetter) as refused:
            PDFFormFiller().check("schedule_a_b", build_parts("schedule_a_b", session))
        return str(refused.value), refused.value.step, refused.value.page

    the_form_s = (
        "The court form can't print the letter “ą” in “Debtor 1”. "
        "Change it to a letter without the mark.",
        "debtor_info",
        None,
    )
    payments = creditor_payments(session, 5, MAKES)
    assert refusal() == the_form_s  # a fifth vehicle, on a sheet
    payments[4].delete()
    assert refusal() == the_form_s  # no sheet


def test_a_name_the_sheet_cannot_print_is_refused_where_the_name_is_entered(
    schedule_a_b_with_sheet,
):
    # check() refuses such a name on the form first; plan_sheet() still refuses it alone,
    # named as the form's name box, and fixed where the name is entered (R23).
    part = {**_sheet_part([{"line": "3.5", "cells": ["Volvo", "500.00"]}]), "name": "Maria Wąs"}

    with pytest.raises(UnprintableLetter) as refused:
        plan_sheet("schedule_a_b", _spec(), part)

    assert (refused.value.letter, refused.value.label) == ("ą", "Debtor 1")
    assert (refused.value.step, refused.value.page) == ("debtor_info", None)


def test_the_sheet_prints_in_the_templates_own_encoding(schedule_a_b_with_sheet):
    # Every template's /Helv is the base-14 Helvetica with one /Encoding (R62). The sheet
    # encodes each letter by it, as pypdf encodes a form's, and gives every page's font it.
    for form_type in get_all_form_types():
        template = load_schema(form_type).template_filename
        reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template)
        helv = reader.root_object["/AcroForm"]["/DR"]["/Font"]["/Helv"].get_object()
        encoding = helv["/Encoding"].get_object()
        assert (helv["/BaseFont"], helv["/Subtype"], "/BaseEncoding" in encoding) == (
            "/Helvetica",
            "/Type1",
            False,
        )
        assert [str(entry) for entry in encoding["/Differences"]] == sheets._DIFFERENCES.split()
        assert sheets._font().encoding == font_for(template, "/Helv").encoding
    # A sheet of two pages: each page's Helvetica has the encoding.
    rows = [{"line": f"3.{n}", "cells": ["\n".join(["Volvo"] * 40), ""]} for n in (5, 6)]
    part = _sheet_part(rows)
    document = pymupdf.open("pdf", draw_sheet(sheet_spec(part), part))
    fonts = [xref for page in document for xref, *_ in page.get_fonts()]
    assert (len(document), len(fonts)) == (2, 2)
    for xref in fonts:
        _, differences = document.xref_get_key(xref, "Encoding/Differences")
        assert re.findall(r"\d+|/[^\s/\[\]]+", differences) == sheets._DIFFERENCES.split()


def test_a_word_wider_than_its_cell_is_refused(session, creditor_payments):
    rows = creditor_payments(session, 5, MAKES)
    rows[4].creditor_name = "Volvo " + "YV1MS382X42" * 6  # one word, wider than the column
    rows[4].save()

    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_a_b", build_parts("schedule_a_b", session))

    assert str(refused.value) == (
        "“Make” is too long to fit on the court form, even in small print. Shorten it."
    )
    assert (refused.value.step, refused.value.page) == (None, "/sofa")


def test_a_word_as_wide_as_its_cell_prints_and_a_wider_one_is_refused(session, creditor_payments):
    # The Make column is 300 pt, 296 pt inside its padding. Thirty-one W's and an i are
    # 294.86 pt at 10 pt and print whole; with a second i, 297.08 pt, Generate refuses them
    # rather than Download failing.
    payments = creditor_payments(session, 5, [*MAKES[:4], "W" * 31 + "i"])

    _, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.rows == (("3.5", "W" * 31 + "i", "500.00"),)
    assert sheet.crossing == ()
    payments[4].creditor_name = "W" * 31 + "ii"
    payments[4].save()
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_a_b", build_parts("schedule_a_b", session))
    assert refused.value.label == "Make"


def test_a_row_as_tall_as_a_page_prints_and_a_taller_one_is_refused(schedule_a_b_with_sheet):
    # Below the header's three lines, a blank line, the labels' one and a 6 pt gap, a page
    # has 792 - 54 - 128.70 = 609.30 pt for its rows: 44 lines of 13.74 pt.
    def parts(lines):
        make = "\n".join(["Volvo"] * lines)
        row = {"line": "3.5", "cells": [make, "500.00"]}
        return {"version": 2, "parts": [{"kind": "form", "values": {}}, _sheet_part([row])]}

    pdf = PDFFormFiller().fill("schedule_a_b", parts(44))

    assert len(pymupdf.open("pdf", pdf)) == 11
    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.lines == ((("3.5",), ("Volvo",) * 44, ("500.00",)),)
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_a_b", parts(45))
    assert refused.value.label == "Make"


def test_a_row_taller_than_a_page_is_refused_naming_its_tallest_cell(schedule_a_b_with_sheet):
    part = _sheet_part([{"line": "3.5", "cells": ["Volvo", "worth " * 600]}])

    with pytest.raises(ValueTooLong) as refused:
        plan_sheet("schedule_a_b", _spec(), part)

    assert refused.value.label == "Current value of the portion you own"


def test_a_sheet_page_is_never_read_as_a_page_of_the_form(session, creditor_payments):
    creditor_payments(session, 5, MAKES)
    parts, pdf = _drawn(session)
    with pytest.raises(ValueError, match="11 pages, but its parts print 10$"):
        read_drawn("schedule_a_b", pdf)
    # A drawing with no sheet, read with parts that have one.
    session.sofa_report.creditor_payments.order_by("pk").last().delete()
    _, unsheeted = _drawn(session)
    with pytest.raises(ValueError, match="10 pages, but its parts print 10 and 1 attached sheet"):
        read_drawn("schedule_a_b", unsheeted, parts)


def test_a_guarded_column_prints_blank_on_the_sheet(
    schedule_a_b_with_sheet, session, creditor_payments, monkeypatch
):
    # UPL guard: the value slots print only an asked answer, so they print nothing here,
    # on the form's pages or on the sheet. The guard decides which cells print, never
    # which rows exist: the fifth row and its make still print.
    path = schedule_a_b_with_sheet / "schedule_a_b.json"
    data = json.loads(path.read_text())
    for f in data["fields"]:
        if f["repeat"] == "ab_line_3" and f["binding"].endswith("total_paid"):
            f.update(source="derived", rule="full_name", legal_review=True)
    path.write_text(json.dumps(data))
    load_schema.cache_clear()
    creditor_payments(session, 5, MAKES)
    # PyMuPDF's own log, where it writes an error it swallows; stdout by default.
    log = StringIO()
    monkeypatch.setattr(pymupdf, "_g_out_log", log)

    parts, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.rows == (("3.5", "Volvo", ""),)
    text = "".join(page.get_text() for page in pymupdf.open("pdf", pdf))
    assert [amount for amount in ("100.00", "400.00", "500.00") if amount in text] == []
    # The blank cell draws no line, so PyMuPDF logs no error for an empty one.
    assert log.getvalue() == ""


def test_a_column_with_one_guarded_slot_prints_blank_on_the_sheet(
    schedule_a_b_with_sheet, session, creditor_payments
):
    # One guarded slot is enough (R59(a)): with only row 1's value slot guarded, the
    # column's sheet cells print nothing, while rows 2 to 4 print their values.
    path = schedule_a_b_with_sheet / "schedule_a_b.json"
    data = json.loads(path.read_text())
    for f in data["fields"]:
        if f["repeat"] == "ab_line_3" and f["binding"].endswith("total_paid") and f["row"] == 1:
            f.update(source="derived", rule="full_name", legal_review=True)
    path.write_text(json.dumps(data))
    load_schema.cache_clear()
    creditor_payments(session, 5, MAKES)

    _, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.rows == (("3.5", "Volvo", ""),)
    text = "".join(page.get_text() for page in pymupdf.open("pdf", pdf))
    printed = [a for a in ("100.00", "200.00", "300.00", "400.00", "500.00") if a in text]
    assert printed == ["200.00", "300.00", "400.00"]


def test_a_refused_sheet_cell_names_where_its_columns_slot_is_fixed(
    schedule_a_b_with_sheet, session, creditor_payments
):
    # The Make slots are declared derived (rule full_name) but keep their SOFA binding, so
    # they still print the creditor's name, a state no production schema has. A refusal in
    # their column takes the slot's own fix (fix_for), that rule's step, not the SOFA page:
    # a cell's fix comes from its column's slot, not from the value it prints.
    path = schedule_a_b_with_sheet / "schedule_a_b.json"
    data = json.loads(path.read_text())
    for f in data["fields"]:
        if f["repeat"] == "ab_line_3" and f["binding"].endswith("creditor_name"):
            f.update(source="derived", rule="full_name")
    path.write_text(json.dumps(data))
    load_schema.cache_clear()
    rows = creditor_payments(session, 5, MAKES)
    rows[4].creditor_name = "Wąsowicz Motors"
    rows[4].save()

    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("schedule_a_b", build_parts("schedule_a_b", session))

    assert (refused.value.label, refused.value.step, refused.value.page) == (
        "Make",
        "debtor_info",
        None,
    )


def test_a_cell_written_like_a_pdf_operand_prints_as_typed(session, creditor_payments):
    # PyMuPDF takes a line written "[<…>]" as a ready-made text operand: "[<4F4B>]" would
    # print "OK", and a longer one could draw anything on the page.
    creditor_payments(session, 5, [*MAKES[:4], "[<4F4B>]"])

    _, pdf = _drawn(session)

    (sheet,) = read_sheets(pdf, _spec())
    assert sheet.rows == (("3.5", "[<4F4B>]", "500.00"),)


def test_a_form_with_a_copy_and_a_sheet_prints_the_sheet_last(
    session, schedule_d_with_a_copy_and_a_sheet, creditor_payments
):
    # Seven payments: Part 1 prints five rows and its sixth and seventh on a sheet; Part 2
    # prints six entries on page 3, the template's last, and its seventh on a copy of it.
    # The pages are the form's, then the copy, then the sheet (spec §6, printing order).
    creditor_payments(session, 7, MAKES)

    document = build_parts("schedule_d", session)
    pdf = PDFFormFiller().fill("schedule_d", document)

    assert [part["kind"] for part in document["parts"]] == ["form", "copy", "sheet"]
    pages = pymupdf.open("pdf", pdf)
    headed = ["(attached sheet)" in " ".join(page.get_text().split()) for page in pages]
    assert headed == [False] * 4 + [True]
    drawn = read_drawn("schedule_d", pdf, document["parts"])
    assert {(w.copy, w.value) for w in drawn if w.full_name == "Name"} == {
        (None, "Honda"),
        (1, "Saab"),
    }
    (sheet,) = read_sheets(pdf, sheet_spec(document["parts"][2]))
    assert sheet.rows == (("2.6", "Kia", "600.00"), ("2.7", "Saab", "700.00"))
    # Headed with Schedule D's own title, not another form's
    assert sheet.header == (
        "Maria Torres",
        "Official Form 106D, Schedule D: Creditors Who Have Claims Secured by Property "
        "(attached sheet)",
        "Case number (if known)",
    )
