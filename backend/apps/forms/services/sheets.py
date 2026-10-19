"""
Attached sheets (3a2 spec §5.3): the rows past a repeat group's last slot, when the form has
no page to copy, on plain US Letter pages that PDFFormFiller.fill() appends after the
form's pages and copies.

Every page of a sheet starts with its header: the filer's name, the form's title followed
by " (attached sheet)", and "Case number (if known)" with a blank line. Then come the
column labels and the rows: each row's line, the form line it continues, then its cells
under the group's columns, in Helvetica at 10 pt. A cell's text wraps at its spaces, a row
never splits across pages, and the sheet runs to as many pages as its rows need.

The sheet prints in the templates' own text font (R62): the base-14 Helvetica, with the
/Encoding every template's /Helv has. PyMuPDF draws "helv" in WinAnsiEncoding, so
draw_sheet() writes each letter's code in the templates' encoding and gives every page's
font that /Encoding. The sheet so prints exactly the forms' letters, and plan_sheet()
refuses a letter with the forms' own check, text_fit.printable() on the form's /Helv.

plan_sheet() measures the text with PyMuPDF's Font, without drawing: Generate runs it
through check(). draw_sheet() draws, at Download.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import pymupdf

# pypdf internal, pinned with pypdf==6.13.1 as in text_fit; test_pdf_filler.py fails if it moves.
from pypdf._font import Font
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject

from apps.forms.schema import FormSchema, SheetColumn, SheetSpec, load_schema
from apps.forms.services.derivations import RULE_FIXES
from apps.forms.services.fill_resolver import fix_for
from apps.forms.services.pdf_filler import (
    UnprintableLetter,
    ValueTooLong,
    _as_printed,
    _refused_letter,
)
from apps.forms.services.text_fit import font_for, printable

PAGE = (612.0, 792.0)  # US Letter
MARGIN = 54.0  # 0.75 in on every side
WIDTH = PAGE[0] - 2 * MARGIN  # 504 pt, 7.0 in
LINE_WIDTH = 36.0  # the line column, "3.5"
PAD = 2.0  # a cell's text keeps this far from each side of its column
SIZE = 10.0
_HELVETICA = pymupdf.Font("helv")  # the font insert_text draws "helv" in: its metrics
# A line of text is PyMuPDF's own Helvetica line, ascender to descender (13.74 pt), so
# every character's box lies inside its line, and its baseline is the ascender below its top.
LEADING = (_HELVETICA.ascender - _HELVETICA.descender) * SIZE
_BASELINE = _HELVETICA.ascender * SIZE
_ROW_GAP = 6.0
_BLANK = 180.0  # the line to write the case number on, 2.5 in
_CASE_NUMBER = "Case number (if known)"
_TEXT_FONT = "/Helv"  # the templates' text font, in their /AcroForm /DR

# The /Differences of every template's /Helv /Encoding, which all 17 share
# (test_attached_sheets.py pins it): Helvetica's own encoding, with PDFDocEncoding's
# letters from 128 up, Ł, ł and ı among them, and nothing at 173 (/.notdef).
_DIFFERENCES = (
    "24 /breve /caron /circumflex /dotaccent /hungarumlaut /ogonek /ring /tilde 39 "
    "/quotesingle 96 /grave 128 /bullet /dagger /daggerdbl /ellipsis /emdash "
    "/endash /florin /fraction /guilsinglleft /guilsinglright /minus /perthousand "
    "/quotedblbase /quotedblleft /quotedblright /quoteleft /quoteright "
    "/quotesinglbase /trademark /fi /fl /Lslash /OE /Scaron /Ydieresis /Zcaron "
    "/dotlessi /lslash /oe /scaron /zcaron 160 /Euro 164 /currency 166 /brokenbar "
    "168 /dieresis /copyright /ordfeminine 172 /logicalnot /.notdef /registered "
    "/macron /degree /plusminus /twosuperior /threesuperior /acute /mu 183 "
    "/periodcentered /cedilla /onesuperior /ordmasculine 188 /onequarter /onehalf "
    "/threequarters 192 /Agrave /Aacute /Acircumflex /Atilde /Adieresis /Aring /AE "
    "/Ccedilla /Egrave /Eacute /Ecircumflex /Edieresis /Igrave /Iacute /Icircumflex "
    "/Idieresis /Eth /Ntilde /Ograve /Oacute /Ocircumflex /Otilde /Odieresis "
    "/multiply /Oslash /Ugrave /Uacute /Ucircumflex /Udieresis /Yacute /Thorn "
    "/germandbls /agrave /aacute /acircumflex /atilde /adieresis /aring /ae "
    "/ccedilla /egrave /eacute /ecircumflex /edieresis /igrave /iacute /icircumflex "
    "/idieresis /eth /ntilde /ograve /oacute /ocircumflex /otilde /odieresis "
    "/divide /oslash /ugrave /uacute /ucircumflex /udieresis /yacute /thorn "
    "/ydieresis"
)
_ENCODING = f"<</Type/Encoding/Differences[{_DIFFERENCES}]>>"


def _font() -> Font:
    """The sheet's font as pypdf builds a template's /Helv: Helvetica with _DIFFERENCES."""
    differences = ArrayObject(
        NumberObject(token) if token.isdigit() else NameObject(token)
        for token in _DIFFERENCES.split()
    )
    encoding = {
        NameObject("/Type"): NameObject("/Encoding"),
        NameObject("/Differences"): differences,
    }
    return Font.from_font_resource(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): DictionaryObject(encoding),
            }
        )
    )


# Each letter → its code in that encoding, as a character, the way pypdf encodes a form's.
_CODES, _ = _font()._get_typographic_maps()


def _prints(template: str) -> Callable[[str], bool]:
    """The forms' own letter check, for the form's template (R62)."""
    return partial(printable, font_for(template, _TEXT_FONT))


def _encoded(line: str) -> str:
    """
    The line as insert_text() writes it: one byte per letter, its code in the templates'
    encoding. A letter plan_sheet() refuses prints as "?", as pypdf prints one on a form.
    """
    return "".join(_CODES.get(letter, "?") for letter in line)


def inner_width(width: float) -> float:
    """The width a column's text takes: the column's, less its padding on each side."""
    return width - 2 * PAD


def _lines(text: str, width: float) -> list[str] | None:
    """
    The text as printed (pdf_filler._as_printed), broken at its line breaks, then at spaces
    into lines no wider than width at 10 pt, each taking as many words as fit. Spaces are
    kept as typed, except one at each break. None when a word is wider than width.
    """
    lines = []
    for paragraph in _as_printed(text).splitlines() or [""]:
        line = None
        for word in paragraph.split(" "):
            if _HELVETICA.text_length(word, SIZE) > width:
                return None
            joined = word if line is None else f"{line} {word}"
            if line is None or _HELVETICA.text_length(joined, SIZE) <= width:
                line = joined
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def prints_whole(text: str, width: float, template: str) -> bool:
    """
    Whether the sheet of a form with that template prints every letter of the text, and no
    word of it is wider than width.
    """
    letter = _refused_letter(_as_printed(text), _prints(template))
    return letter is None and _lines(text, width) is not None


def fits_line_column(line: str, template: str) -> bool:
    """Whether a row's line, the group's number for it, prints whole on one line of its column."""
    width = inner_width(LINE_WIDTH)
    return prints_whole(line, width, template) and len(_lines(line, width)) == 1


def sheet_spec(part: dict) -> SheetSpec:
    """
    The sheet a sheet part prints: the title and the columns' labels and widths it stores
    (R63), so a filed sheet draws as it was filed, whatever its schema says later. Its
    columns carry no binding: the part holds their cells.
    """
    return SheetSpec(
        part["title"],
        tuple(SheetColumn(column["label"], "", column["width"]) for column in part["columns"]),
    )


def _header(spec: SheetSpec, name: str) -> list[str]:
    """The lines that start every page of the sheet, the case number's last."""
    return [
        *_lines(name, WIDTH),
        *_lines(f"{spec.title} (attached sheet)", WIDTH),
        _CASE_NUMBER,
    ]


def _labels(spec: SheetSpec) -> list[list[str]]:
    """Each column's label, as the lines it prints in its column."""
    return [_lines(column.label, inner_width(column.width)) for column in spec.columns]


def _rows_top(spec: SheetSpec, header: list[str]) -> float:
    """Where a page's first row starts: below the header, a blank line and the labels."""
    labels = max((len(lines) for lines in _labels(spec)), default=0)
    return MARGIN + (len(header) + 1 + labels) * LEADING + _ROW_GAP


def _room(spec: SheetSpec, header: list[str]) -> float:
    """The height a page of the sheet has for its rows: from the first row to the margin."""
    return PAGE[1] - MARGIN - _rows_top(spec, header)


def _cells(spec: SheetSpec, row: dict) -> list[list[str]]:
    """A row's cells as the lines each prints: its line first, in the line column."""
    widths = [LINE_WIDTH, *(column.width for column in spec.columns)]
    return [
        _lines(text, inner_width(width))
        for text, width in zip([row["line"], *row["cells"]], widths, strict=True)
    ]


def _height(cells: list[list[str]]) -> float:
    return max(len(lines) for lines in cells) * LEADING


def _check(
    form_type: str, template: str, text: str, width: float, label: str, fix: dict[str, str]
) -> list[str]:
    """The text's lines in width, or check()'s refusal for a box with the label and fix."""
    letter = _refused_letter(_as_printed(text), _prints(template))
    if letter is not None:
        raise UnprintableLetter(form_type, letter, label, fix)
    lines = _lines(text, width)
    if lines is None:
        raise ValueTooLong(form_type, label, fix)
    return lines


def _fixes(schema: FormSchema, group: str, spec: SheetSpec) -> list[dict[str, str]]:
    """
    Where the filer changes each column's cells (3a2 spec §4.5): the fix of the group's slot
    that binds what the schema's column of that label prints (fill_resolver.fix_for). A
    column the schema no longer declares, as a filed sheet's may be (R63), has none: a
    filed form's refusal shows none anyway.
    """
    declared = schema.groups.get(group)
    sheet = declared.sheet if declared is not None else None
    bindings = {column.label: column.binding for column in sheet.columns} if sheet else {}
    fixes = []
    for column in spec.columns:
        binding = bindings.get(column.label)
        slot = next((f for f in schema.fields if f.repeat == group and f.binding == binding), None)
        fixes.append(fix_for(slot) if binding and slot else {})
    return fixes


def plan_sheet(form_type: str, spec: SheetSpec, part: dict) -> None:
    """
    Check that a sheet part prints whole, without drawing (as check() does for a form).

    Raises:
        UnprintableLetter: a letter the sheet can't print, which the form's own boxes can't
            either (R62): in a cell, named by its column's label, fixed where its slots'
            binding is changed; or in the filer's name, named as the form's own name box,
            fixed where the filer's name is entered (R23).
        ValueTooLong: a word wider than its cell, or a row taller than a page, named by the
            column with the most lines.
        ValueError: a row's line that doesn't print whole on one line of the line column
            (the group's number pattern; forms.E007 checks the first).
    """
    schema = load_schema(form_type)
    template = schema.template_filename
    name_label = next(
        (f.label for f in schema.fields if f.source == "derived" and f.rule == "full_name"),
        f"{spec.title} (attached sheet)",
    )
    _check(form_type, template, part["name"], WIDTH, name_label, dict(RULE_FIXES["full_name"]))
    header = _header(spec, part["name"])
    fixes = _fixes(schema, part["group"], spec)
    for row in part["rows"]:
        if not fits_line_column(row["line"], template):
            raise ValueError(f"{form_type}: line {row['line']!r} doesn't fit the line column")
        cells = [
            _check(form_type, template, cell, inner_width(column.width), column.label, fix)
            for column, cell, fix in zip(spec.columns, row["cells"], fixes, strict=True)
        ]
        if _height([[row["line"]], *cells]) > _room(spec, header):
            heights = [len(lines) for lines in cells]
            tallest = heights.index(max(heights))
            raise ValueTooLong(form_type, spec.columns[tallest].label, fixes[tallest])


def _text(page: pymupdf.Page, x: float, top: float, lines: list[str]) -> None:
    """Draw lines of text from (x, top) down, one line height each."""
    for n, line in enumerate(lines):
        if not line:
            continue  # nothing to print, and PyMuPDF logs a traceback for an empty line
        # A list, so insert_text never splits the line at a byte it reads as a line break
        # (– is the templates' 0x85, NEL).
        page.insert_text(
            (x, top + n * LEADING + _BASELINE), [_encoded(line)], fontname="helv", fontsize=SIZE
        )


def _new_page(document: pymupdf.Document, spec: SheetSpec, header: list[str]) -> pymupdf.Page:
    """A sheet page with its header and column labels drawn."""
    page = document.new_page(width=PAGE[0], height=PAGE[1])
    _text(page, MARGIN, MARGIN, header)
    case_number = MARGIN + (len(header) - 1) * LEADING + _BASELINE + 1.5
    start = MARGIN + _HELVETICA.text_length(_CASE_NUMBER, SIZE) + 4
    page.draw_line((start, case_number), (start + _BLANK, case_number), width=0.5)
    top = MARGIN + (len(header) + 1) * LEADING
    x = MARGIN + LINE_WIDTH
    for column, lines in zip(spec.columns, _labels(spec), strict=True):
        _text(page, x + PAD, top, lines)
        x += column.width
    rule = _rows_top(spec, header) - _ROW_GAP / 2
    page.draw_line((MARGIN, rule), (MARGIN + WIDTH, rule), width=0.5)
    return page


def draw_sheet(spec: SheetSpec, part: dict) -> bytes:
    """
    Draw a sheet part, as plan_sheet() passed it, on as many US Letter pages as its rows
    need, and return the PDF.
    """
    document = pymupdf.open()
    header = _header(spec, part["name"])
    page, used = None, 0.0  # the height the page's rows take so far
    for row in part["rows"]:
        cells = _cells(spec, row)
        if page is None or used + _height(cells) > _room(spec, header):
            page, used = _new_page(document, spec, header), 0.0
            if _height(cells) > _room(spec, header):
                raise ValueError("a row taller than a page reached the drawing unchecked")
        x = MARGIN
        for lines, width in zip(cells, [LINE_WIDTH, *(c.width for c in spec.columns)], strict=True):
            _text(page, x + PAD, _rows_top(spec, header) + used, lines)
            x += width
        used += _height(cells) + _ROW_GAP
    # The templates' encoding, for the codes _encoded() wrote, on every page's Helvetica.
    for page in document:
        for xref, *_ in page.get_fonts():
            document.xref_set_key(xref, "Encoding", _ENCODING)
    return document.tobytes()
