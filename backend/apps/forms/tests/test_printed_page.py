"""
What the printed page shows (3a2 spec §9).

fill() builds each widget's value with pypdf and PyMuPDF bakes it into the page, so the
filer gets a page, not a form to fill. These tests look at that page: what prints in each
box, where each character sits, and, where text can't tell, its pixels. MuPDF extracts a
character whole even when the box hides part of it, so a cut is judged from where the
character sits (its origin and size, against Helvetica's bounding box), not from text.
"""

import unicodedata
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from io import BytesIO
from pathlib import Path

import pymupdf
import pypdf
import pytest
from django.conf import settings
from django.core.management import call_command
from pypdf.generic import DictionaryObject, NameObject, NullObject, TextStringObject
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.districts.models import District
from apps.forms.registry import build_field_values, get_all_form_types, packet
from apps.forms.schema import SheetColumn, SheetSpec, load_schema
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong
from apps.forms.services.sheets import draw_sheet, plan_sheet
from apps.forms.services.text_fit import font_for, printable
from apps.forms.services.widgets import field_of, template_widgets, widget_for
from apps.forms.tests.pdf_readback import read_drawn, read_sheets
from apps.intake.management.commands.seed_demo_data import PERSONAS
from apps.intake.models import IntakeSession

# Helvetica's bounding box per point of size: a glyph's highest point (Å's ring) sits
# 0.931 above its baseline and its lowest (Ç's cedilla) 0.225 below.
_TOP = 0.931
_BOTTOM = 0.225
_BOXES = ("CheckBox", "RadioButton")


def _template(form_type):
    return load_schema(form_type).template_filename


def _template_path(form_type):
    return Path(settings.PDF_FORMS_DIRECTORY) / _template(form_type)


@dataclass(frozen=True)
class _Glyph:
    text: str
    font: str
    bbox: tuple[float, float, float, float]
    origin: tuple[float, float]
    size: float

    def inside(self, rect):
        """The glyph's centre lies inside rect: a glyph only touching it belongs to a neighbour."""
        x, y = (self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2
        return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def _printed(pdf):
    """
    The drawn PDF, opened once no widget is left on any of its pages. MuPDF reads a
    widget's appearance on a page never baked too, so without this a test could read a
    value from a widget a viewer can still change, not from the printed page.
    """
    document = pymupdf.open("pdf", pdf)
    assert [page.number + 1 for page in document if page.first_widget] == []
    return document


def _glyphs(page):
    """Every character on the page, in any font, as MuPDF extracts it."""
    return [
        _Glyph(char["c"], span["font"], char["bbox"], char["origin"], span["size"])
        for block in page.get_text("rawdict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        for char in span["chars"]
    ]


# ── The personas' packets ─────────────────────────────────────────────


@cache
def _seeded():
    """
    persona → (the form types in its packet, every form's values for it), each persona
    seeded as tier 3 seeds it. Kept as plain data: the rows go when the test that
    seeds them ends.
    """
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data", verbosity=0)
    seeded = {}
    for persona in PERSONAS:
        call_command("seed_demo_data", "--reset", persona=persona, verbosity=0)
        session = IntakeSession.objects.filter(user__username=f"demo_{persona}").latest("id")
        seeded[persona] = (
            packet(session),
            {
                form_type: build_field_values(form_type, session)
                for form_type in get_all_form_types()
            },
        )
    return seeded


def _values(form_type):
    """
    The form's values for the first persona whose packet holds it: Maria's 103B, Priya's
    122A-2. Form 122A-1Supp is in no packet until step 4, so it takes the first persona's.
    """
    seeded = _seeded()
    first = next(iter(seeded))
    persona = next((p for p, (forms, _) in seeded.items() if form_type in forms), first)
    return seeded[persona][1][form_type]


@cache
def _drawn_packet():
    """form_type → the form drawn with its _values()."""
    return {
        form_type: PDFFormFiller().fill(form_type, _values(form_type))
        for form_type in get_all_form_types()
    }


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(PERSONAS))
def test_no_persona_is_refused(persona):
    # None of the personas' values holds a letter the forms can't print or one too long
    # even at 6 pt (spec §4.3), so check() lets every form of each packet through.
    forms, values = _seeded()[persona]
    refused = {}
    for form_type in forms:
        try:
            PDFFormFiller().check(form_type, values[form_type])
        except (UnprintableLetter, ValueTooLong) as exc:
            refused[form_type] = str(exc)
    assert refused == {}


@pytest.mark.django_db
@pytest.mark.parametrize("form_type", get_all_form_types())
def test_the_packet_has_no_fillable_fields_left(form_type):
    # Every value is page content now: a viewer can't change what DigniFi printed, and a
    # correction goes through a regeneration.
    assert template_widgets(_template(form_type))
    reader = pypdf.PdfReader(BytesIO(_drawn_packet()[form_type]))
    # pypdf's own get_fields() can't read a null /AcroForm, so the root is read directly.
    assert isinstance(reader.trailer["/Root"]["/AcroForm"], NullObject)
    widgets = [
        annot
        for page in reader.pages
        for annot in page.get("/Annots") or []
        if annot.get_object().get("/Subtype") == "/Widget"
    ]
    assert widgets == []


@pytest.mark.django_db
@pytest.mark.parametrize("form_type", get_all_form_types())
def test_print_buttons_never_print(form_type):
    # The Print, Save As, Add Attachment and Reset buttons are for a screen. Baked as the
    # template stands they print their labels; the drawn form prints nothing there.
    buttons = [w for w in template_widgets(_template(form_type)) if w.kind == "Button"]
    as_it_stands = pymupdf.open(_template_path(form_type))
    as_it_stands.bake(annots=False, widgets=True)
    labels = {
        w.key: "".join(g.text for g in _glyphs(as_it_stands[w.page - 1]) if g.inside(w.rect))
        for w in buttons
    }
    assert buttons and all(label.strip() for label in labels.values()), labels
    drawn = _printed(_drawn_packet()[form_type])
    printed = {
        w.key: "".join(g.text for g in _glyphs(drawn[w.page - 1]) if g.inside(w.rect))
        for w in buttons
    }
    assert printed == {w.key: "" for w in buttons}


@contextmanager
def _no_anti_aliasing():
    """
    Render without anti-aliasing: it shades edge pixels differently from one page to the
    next, even where the drawings are the same.
    """
    level = pymupdf.TOOLS.show_aa_level()["graphics"]
    pymupdf.TOOLS.set_aa_level(0)
    try:
        yield
    finally:
        pymupdf.TOOLS.set_aa_level(level)


def _dark_pixels(page, rect):
    pix = page.get_pixmap(dpi=288, clip=pymupdf.Rect(rect), colorspace=pymupdf.csGRAY)
    return sum(1 for value in pix.samples if value < 128)


def _pixels(document, widget):
    """The widget's rect on its page, rendered."""
    return document[widget.page - 1].get_pixmap(dpi=288, clip=pymupdf.Rect(widget.rect)).samples


@pytest.mark.django_db
def test_unticked_boxes_keep_their_squares():
    # Form 103B's empty squares are its boxes' own appearances, so an unticked box must
    # bake as the blank form shows it, or the filer has nothing to tick by hand.
    pdf = _drawn_packet()["form_103b"]  # Maria's fee-waiver application
    ticked = {(w.page, w.tag) for w in read_drawn("form_103b", pdf) if w.state not in ("", "/Off")}
    unticked = [
        w
        for w in template_widgets(_template("form_103b"))
        if w.kind in _BOXES and w.drawn and (w.page, w.tag) not in ticked
    ]
    assert ticked and unticked
    blank = pymupdf.open(_template_path("form_103b"))
    drawn = _printed(pdf)
    with _no_anti_aliasing():
        counts = {
            w.key: (
                _dark_pixels(blank[w.page - 1], w.rect),
                _dark_pixels(drawn[w.page - 1], w.rect),
            )
            for w in unticked
        }
    assert all(on_blank for on_blank, _ in counts.values()), counts
    assert {key: n for key, n in counts.items() if n[0] != n[1]} == {}


def test_a_stacked_duplicate_prints_once():
    # Schedule D page 2 lays a second widget over 4_3 and over each _3 checkbox, 0.6 pt
    # off. Drawn in both, a value would print twice, one copy smudging the other.
    pairs = {
        name: [w for w in template_widgets(_template("schedule_d")) if w.full_name == name]
        for name in ("4_3", "Contingent_3")
    }
    assert all(len(pair) == 2 and pair[1].stacked for pair in pairs.values())
    page = _printed(PDFFormFiller().fill("schedule_d", {"4_3": "Okafor", "Contingent_3": "/On"}))[1]

    def union(pair):
        """The rect the two widgets cover between them."""
        return (
            min(w.rect[0] for w in pair),
            min(w.rect[1] for w in pair),
            max(w.rect[2] for w in pair),
            max(w.rect[3] for w in pair),
        )

    glyphs = _glyphs(page)
    text = [g.text for g in glyphs if g.font == "Helvetica" and g.inside(union(pairs["4_3"]))]
    ticks = [
        g for g in glyphs if g.font == "ZapfDingbats" and g.inside(union(pairs["Contingent_3"]))
    ]
    assert "".join(text) == "Okafor"
    assert len(ticks) == 1


# A/B's three boxes whose right alignment is set on the widget alone (R26).
_WIDGET_ONLY_ALIGNMENT = {
    "24.2 Interest in an education IRA@7:T8",
    "undefined_166@10:T34",
    "undefined_166@10:T35",
}


def _right_aligned(form_type):
    return [
        w
        for w in template_widgets(_template(form_type))
        if w.drawn and w.kind == "Text" and w.align == 2
    ]


@pytest.mark.parametrize("form_type", [f for f in get_all_form_types() if _right_aligned(f)])
def test_amounts_stay_right_aligned(form_type):
    # An amount's digits line up in the form's column only when each ends at the box's
    # right padding (2 × margin from its right edge, where pypdf puts it).
    boxes = _right_aligned(form_type)
    if form_type == "schedule_a_b":
        assert _WIDGET_ONLY_ALIGNMENT <= {w.key for w in boxes}
    values = {w.key: _first_fitting(form_type, w.key, ["1,234.56", "12.00", "9"]) for w in boxes}
    document = _printed(PDFFormFiller().fill(form_type, values))
    on_page = {}
    off = {}
    for w in boxes:
        if w.page not in on_page:
            on_page[w.page] = _glyphs(document[w.page - 1])
        ends = [
            g.bbox[2]
            for g in on_page[w.page]
            if g.font == "Helvetica" and g.text.strip() and g.inside(w.rect)
        ]
        padding_end = w.rect[2] - 2 * w.margin
        if not ends or abs(max(ends) - padding_end) > 1:
            off[w.key] = (max(ends, default=None), round(padding_end, 2))
    assert off == {}


def _first_fitting(form_type, key, candidates):
    return next(value for value in candidates if _fits(form_type, key, value))


def _fits(form_type, key, value):
    try:
        PDFFormFiller().check(form_type, {key: value})
    except ValueTooLong:
        return False
    return True


@pytest.mark.django_db
def test_ssn_digits_fill_their_cells():
    # A comb box prints one character per cell, each centred in it, as the form's printed
    # cells expect. Schedule D's account boxes carry their cell count on the parent, so
    # the drawing copies it onto each widget (R4); without it the digits pile up.
    ssn = _values("form_121")["Debtor1a.SSNum"]  # the full SSN, as the resolver formats it
    for form_type, key, value in [
        ("form_121", "Debtor1a.SSNum@1:T9", ssn),
        ("schedule_d", "account number@1:T32", "4417"),
        ("schedule_d", "account number@3:T33", "5521"),
    ]:
        (box,) = [w for w in template_widgets(_template(form_type)) if w.key == key]
        assert box.comb and len(value) == box.max_len, key
        page = _printed(PDFFormFiller().fill(form_type, {key: value}))[box.page - 1]
        glyphs = sorted(
            (
                g
                for g in _glyphs(page)
                if g.font == "Helvetica" and g.text.strip() and g.inside(box.rect)
            ),
            key=lambda g: g.bbox[0],
        )
        assert "".join(g.text for g in glyphs) == value, key
        cell = box.width / box.max_len
        off_centre = [
            round((g.bbox[0] + g.bbox[2]) / 2 - (box.rect[0] + (i + 0.5) * cell), 2)
            for i, g in enumerate(glyphs)
        ]
        assert all(abs(offset) <= 0.25 for offset in off_centre), (key, off_centre)


def _warnings_while(action):
    """The lines MuPDF warns or errs with while action runs."""
    pymupdf.TOOLS.reset_mupdf_warnings()
    action()
    warned = pymupdf.TOOLS.mupdf_warnings()
    pymupdf.TOOLS.reset_mupdf_warnings()
    return set(warned.splitlines())


def _view(document):
    """Every page rendered and read, as a viewer or a court's system opens it."""
    for page in document:
        page.get_pixmap(dpi=36)
        page.get_text()


@pytest.mark.django_db
@pytest.mark.parametrize("form_type", get_all_form_types())
def test_every_drawn_pdf_opens_cleanly(form_type):
    # A drawn form must open like the template: every page there, and nothing new for a
    # PDF reader to complain about. (Form 101's template already makes MuPDF say "No
    # common ancestor in structure tree" when its pages render: its tagging, not ours.)
    pages = len(pypdf.PdfReader(_template_path(form_type)).pages)
    from_template = _warnings_while(lambda: _view(pymupdf.open(_template_path(form_type))))
    drawn = []

    def draw_and_view():
        drawn.append(PDFFormFiller().fill(form_type, _values(form_type)))
        _view(pymupdf.open("pdf", drawn[0]))

    from_drawing = _warnings_while(draw_and_view)
    assert len(pypdf.PdfReader(BytesIO(drawn[0])).pages) == pages
    assert _printed(drawn[0]).page_count == pages
    assert from_drawing - from_template == set()


# ── Nothing is cut off ────────────────────────────────────────────────

# Å's ring reaches nearly to the font's top, Ç's cedilla to its bottom, g and q below the
# baseline. No digits: a box's blank text ("2") reads as blank.
_CYCLE = "ÅgÇq"


def _cycled(n):
    return (_CYCLE * n)[:n]


def _longest(form_type, key, value_of):
    """The largest n whose value_of(n) check() fits in the box (0 when none does)."""
    low, high = 0, 1
    while _fits(form_type, key, value_of(high)):
        # No box holds 1,024 letters or lines even at 6 pt.
        assert high < 1024, f"check() fits {key} a value of any length"
        low, high = high, high * 2
    while high - low > 1:
        middle = (low + high) // 2
        if _fits(form_type, key, value_of(middle)):
            low = middle
        else:
            high = middle
    return low


def _boundary(form_type, widget):
    """
    A value that just fits the box, and one that just doesn't, by check(): the longest
    run of letters it fits, one letter more; in a multi-line box, as many lines of that
    run as fit, one line more.
    """
    n = _longest(form_type, widget.key, _cycled)
    if not widget.multiline:
        return _cycled(n), _cycled(n + 1)
    word = _cycled(n)
    lines = _longest(form_type, widget.key, lambda k: "\n".join([word] * k))
    return "\n".join([word] * lines), "\n".join([word] * (lines + 1))


def _hangs_below(template, widget):
    """
    Drawn at its own size, the font's lowest point sits below the box (R38): pypdf
    centres a single-line box's ascent in it, and on 37 boxes Ç's cedilla then dips up to
    0.108 pt under the rect, as it always has.
    """
    if widget.multiline or not widget.size:
        return False
    font = font_for(template, widget.font).font_descriptor
    baseline = (
        widget.margin + (widget.height - 2 * widget.margin - font.ascent * widget.size / 1000) / 2
    )
    return baseline + font.bbox[1] * widget.size / 1000 < 0


@cache
def _rects(template):
    """
    (page, tag) → the widget's /Rect, unrounded, measured from the page's top left: what
    the baked value is clipped to. (The field index rounds rects to 0.1 pt.)
    """
    reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template)
    rects = {}
    for number, page in enumerate(reader.pages, start=1):
        top = float(page.mediabox.top)
        for annot in page.get("/Annots") or []:
            annotation = annot.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue
            widget = widget_for(template, number, annotation, top)
            x0, y0, x1, y1 = (float(v) for v in annotation["/Rect"])
            rects[(number, widget.tag)] = (
                min(x0, x1),
                top - max(y0, y1),
                max(x0, x1),
                top - min(y0, y1),
            )
    return rects


def _cut_off(form_type, values):
    """
    Draw the values and return each box whose value reads back other than whole, or with
    a character past its rect: (key, what read back or the side and points past).
    """
    template = _template(form_type)
    pdf = PDFFormFiller().fill(form_type, values)
    printed = {(w.page, w.tag): w.value for w in read_drawn(form_type, pdf)}
    document = _printed(pdf)
    pages = {}
    cut = []
    for widget in template_widgets(template):
        if widget.key not in values:
            continue
        if printed[(widget.page, widget.tag)] != " ".join(values[widget.key].splitlines()):
            cut.append((widget.key, printed[(widget.page, widget.tag)]))
        rect = _rects(template)[(widget.page, widget.tag)]
        allowed = {"top": 0, "bottom": 0.11 if _hangs_below(template, widget) else 0}
        if widget.page not in pages:
            pages[widget.page] = _glyphs(document[widget.page - 1])
        for g in pages[widget.page]:
            # A space prints nothing; MuPDF also adds one where a line's text breaks off.
            if g.font != "Helvetica" or not g.text.strip() or not g.inside(rect):
                continue
            past = {
                "top": rect[1] - (g.origin[1] - _TOP * g.size),
                "bottom": g.origin[1] + _BOTTOM * g.size - rect[3],
                "left": rect[0] - g.bbox[0],
                "right": g.bbox[2] - rect[2],
            }
            cut += [
                (widget.key, side, round(by, 3))
                for side, by in past.items()
                if by > allowed.get(side, 0) + 0.001  # 0.001 pt: MuPDF's rounding
            ]
    return cut


def test_r38s_cedilla_tolerance_covers_only_its_37_boxes():
    # The cut-off test lets these boxes' bottoms hang 0.11 pt under the rect. Should a
    # template or pypdf change make more boxes hang, the allowance must not grow with them.
    hanging = [
        (form_type, w.key)
        for form_type in get_all_form_types()
        for w in template_widgets(_template(form_type))
        if w.drawn and w.kind == "Text" and _hangs_below(_template(form_type), w)
    ]
    assert len(hanging) == 37, hanging


@pytest.mark.parametrize("form_type", get_all_form_types())
def test_no_value_is_ever_cut_off(form_type):
    # The longest value check() lets through prints whole, every character inside its box,
    # and one letter or line more is refused, never drawn cut off (spec §9). A short value
    # at the box's own size stays inside too: there R38's 37 boxes hang Ç's cedilla up to
    # 0.108 pt under the rect, as the template always has. (Combo boxes take only their
    # own options, so they have no boundary to probe.)
    boxes = [w for w in template_widgets(_template(form_type)) if w.drawn and w.kind == "Text"]
    boundaries = {}  # boxes alike in every measure check() takes share a boundary
    just, over, short = {}, {}, {}
    for w in boxes:
        alike = (w.font, w.size, w.width, w.height, w.margin, w.comb, w.multiline, w.max_len)
        if alike not in boundaries:
            boundaries[alike] = _boundary(form_type, w)
        just[w.key], over[w.key] = boundaries[alike]
        short[w.key] = "Åg\nÇq" if w.multiline else "ÅgÇq"
        if not _fits(form_type, w.key, short[w.key]):  # Schedule G's entry-number boxes
            short[w.key] = just[w.key]
    assert all(just.values()), [key for key, value in just.items() if not value]
    assert [key for key in over if _fits(form_type, key, over[key])] == []
    assert _cut_off(form_type, just) == []
    assert _cut_off(form_type, short) == []


# ── A capital's mark on a multi-line box's first line ─────────────────

OTHER_PROPERTY = "53 Examples Season tickets country club membership"  # A/B line 53
# Where Helvetica's accented capitals carry their marks, per point of size: clear of the
# cap height (0.718) up to past the font's top.
_MARK = (0.735, 0.95)


def _planned_size(form_type, key, value):
    ((planned,),) = [part.widgets for part in PDFFormFiller().check(form_type, {key: value})]
    return planned.size


def _six_point_value(form_type, key):
    """
    É Ñ Š on two lines, line 1 one word just too wide for the box at 6.5 pt, so check()
    plans the value at 6 pt, the smallest print.
    """
    for n in range(1, 200):
        value = f"ÉÑŠ{'x' * n}\nÉÑŠ"
        if _planned_size(form_type, key, value) == 6.0:
            return value
    raise AssertionError(f"no value plans {key} at 6 pt")


def _mark_ink(page, empty, glyph):
    """The ink the drawing adds where the glyph's mark sits, rendered at 1440 dpi."""
    rect = pymupdf.Rect(
        glyph.bbox[0],
        glyph.origin[1] - _MARK[1] * glyph.size,
        glyph.bbox[2],
        glyph.origin[1] - _MARK[0] * glyph.size,
    )
    drawn = page.get_pixmap(dpi=1440, clip=rect, colorspace=pymupdf.csGRAY).samples
    blank = empty.get_pixmap(dpi=1440, clip=rect, colorspace=pymupdf.csGRAY).samples
    return sum(max(b - d, 0) for d, b in zip(drawn, blank, strict=True))


@pytest.mark.parametrize(
    "form_type,key", [("schedule_a_b", OTHER_PROPERTY), ("form_103b", "3 type")]
)
@pytest.mark.parametrize("small", [False, True], ids=["own size", "6 pt"])
def test_a_capitals_mark_survives_the_first_line(form_type, key, small):
    # pypdf hangs a multi-line box's first line from the font's top at the box's height
    # plus its margin, so the box cut off part of É's accent, Ñ's tilde and Š's caron on
    # line 1, nearly all of it at 6 pt (R35). MuPDF still reads the letter whole, so the
    # mark is measured in pixels against the same letter on line 2.
    (box,) = [w for w in template_widgets(_template(form_type)) if w.full_name == key]
    value = _six_point_value(form_type, key) if small else "ÉÑŠ\nÉÑŠ"
    assert _planned_size(form_type, key, value) == (6.0 if small else box.size)
    page = _printed(PDFFormFiller().fill(form_type, {key: value}))[box.page - 1]
    empty = _printed(PDFFormFiller().fill(form_type, {}))[box.page - 1]
    glyphs = [g for g in _glyphs(page) if g.font == "Helvetica" and g.inside(box.rect)]
    for letter in "ÉÑŠ":
        line_1, line_2 = sorted((g for g in glyphs if g.text == letter), key=lambda g: g.origin[1])
        assert line_1.origin[1] < line_2.origin[1]
        ink_1, ink_2 = _mark_ink(page, empty, line_1), _mark_ink(page, empty, line_2)
        assert ink_2 > 0
        # Rendered at different heights, the same mark varies by up to 14% in ink; a cut
        # one keeps a third of it at most.
        assert ink_1 >= 0.8 * ink_2, (letter, round(ink_1 / ink_2, 3))


# ── check() and the drawing agree on every letter ─────────────────────

_LETTERS = list(
    dict.fromkeys(
        [chr(c) for c in range(0x20, 0x180)]
        + list("’‘“”–—…€•")
        + ["\N{NO-BREAK SPACE}", "\N{THIN SPACE}", "\N{NARROW NO-BREAK SPACE}"]
        + ["\N{SOFT HYPHEN}", "\N{ZERO WIDTH SPACE}", "\t"]
    )
)


def _as_printed(letter):
    """What "x<letter>x" prints in a single-line box when check() accepts it."""
    if (
        letter == "\t"
        or unicodedata.category(letter) == "Zs"
        or len(f"x{letter}x".splitlines()) > 1
    ):
        return "x x"  # a space, or a line break, which a single-line box prints as one
    if unicodedata.category(letter) == "Cf":
        return "xx"  # a format character prints nothing
    return f"x{letter}x"


def _encoding(template):
    font = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template).root_object["/AcroForm"][
        "/DR"
    ]["/Font"]["/Helv"]
    encoding = font.get_object()["/Encoding"].get_object()
    return str(encoding.get("/BaseEncoding")), tuple(
        str(entry) for entry in encoding["/Differences"]
    )


def _drawn_without_check(template, texts):
    """
    The template with each box in texts ((page, tag) → text) built as fill() builds it,
    but never checked: pypdf's appearance at the box's own size, from the template's
    font (R32), baked by PyMuPDF.
    """
    writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
    acro_form = writer.root_object["/AcroForm"].get_object()
    for number, page in enumerate(writer.pages, start=1):
        for annot in page.get("/Annots") or []:
            annotation = annot.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue
            widget = widget_for(template, number, annotation, float(page.mediabox.top))
            if (number, widget.tag) not in texts:
                continue
            field = field_of(annotation)
            if "/DR" in annotation:
                del annotation["/DR"]
            field[NameObject("/V")] = TextStringObject(texts[(number, widget.tag)])
            appearance = TextStreamAppearance.from_text_annotation(
                writer, page, False, acro_form, field, annotation
            )
            annotation[NameObject("/AP")] = DictionaryObject(
                {NameObject("/N"): writer._add_object(appearance)}
            )
    buffer = BytesIO()
    writer.write(buffer)
    document = pymupdf.open("pdf", buffer.getvalue())
    document.bake(annots=False, widgets=True)
    return document.tobytes()


def test_check_agrees_with_the_drawing_on_every_letter():
    # check() refuses exactly the letters the drawing can't print (spec §4.3): a letter it
    # accepts prints as itself, and one it refuses would print as "?", as another glyph,
    # or as nothing. MuPDF reads back a character's code even where the font draws
    # nothing for it, so whether a letter prints is judged by its ink too. Every
    # template's text font has the same encoding, so one form's boxes stand for all 17.
    assert len({_encoding(_template(form_type)) for form_type in get_all_form_types()}) == 1
    template = _template("form_107")
    names = Counter(w.full_name for w in template_widgets(template) if w.drawn)
    boxes = [
        w
        for w in template_widgets(template)
        if w.drawn
        and w.kind == "Text"
        and not (w.multiline or w.comb)
        and w.max_len is None
        and names[w.full_name] == 1  # its value can't reach a sibling
    ]
    accepted, refused = [], []
    for letter in _LETTERS:
        try:
            PDFFormFiller().check("form_107", {boxes[0].key: f"x{letter}x"})
            accepted.append(letter)
        except UnprintableLetter:
            refused.append(letter)
    assert accepted and refused
    # A tab and every space separator print as a space, a format character as nothing
    # (R36): none of them is refused.
    invisible = [c for c in refused if c == "\t" or unicodedata.category(c) in ("Zs", "Cf")]
    assert [f"U+{ord(c):04X}" for c in invisible] == []

    def in_boxes(letters):
        """The letters, a box each, in as many rounds as the boxes need."""
        rounds = range(0, len(letters), len(boxes))
        return [list(zip(boxes, letters[i : i + len(boxes)], strict=False)) for i in rounds]

    # Accepted: "x<letter>x" reads back as it prints, and a letter that prints a glyph
    # leaves ink, alone in its box.
    empty = _printed(PDFFormFiller().fill("form_107", {}))
    misprinted, no_ink = {}, []
    for pairs in in_boxes(accepted):
        pdf = PDFFormFiller().fill("form_107", {w.key: f"x{c}x" for w, c in pairs})
        _printed(pdf)
        printed = {(w.page, w.tag): w.value for w in read_drawn("form_107", pdf)}
        misprinted |= {
            f"U+{ord(c):04X}": printed[(w.page, w.tag)]
            for w, c in pairs
            if printed[(w.page, w.tag)] != _as_printed(c)
        }
        glyphs = [(w, c) for w, c in pairs if _as_printed(c) == f"x{c}x" and not c.isspace()]
        alone = _printed(PDFFormFiller().fill("form_107", {w.key: c for w, c in glyphs}))
        with _no_anti_aliasing():
            no_ink += [
                f"U+{ord(c):04X}" for w, c in glyphs if _pixels(alone, w) == _pixels(empty, w)
            ]
    assert misprinted == {}
    assert no_ink == []

    # Refused: "x<letter>x" drawn without check() reads back as something else, or the
    # letter leaves no ink, alone in its box.
    empty = pymupdf.open("pdf", _drawn_without_check(template, {}))
    inked = []
    for pairs in in_boxes(refused):
        pdf = _drawn_without_check(template, {(w.page, w.tag): f"x{c}x" for w, c in pairs})
        printed = {(w.page, w.tag): w.value for w in read_drawn("form_107", pdf)}
        as_itself = [(w, c) for w, c in pairs if printed[(w.page, w.tag)] == f"x{c}x"]
        alone = pymupdf.open(
            "pdf", _drawn_without_check(template, {(w.page, w.tag): c for w, c in as_itself})
        )
        with _no_anti_aliasing():
            inked += [
                f"U+{ord(c):04X}" for w, c in as_itself if _pixels(alone, w) != _pixels(empty, w)
            ]
    assert inked == []


# ── An attached sheet's letter check agrees with what it prints ───────

_SHEET = SheetSpec(
    "Official Form 106A/B, Schedule A/B: Property",
    (SheetColumn("Make", "sofa.creditor_payments[].creditor_name", 300.0),),
)


def _sheet_of(cells):
    """A sheet part with a row for each cell, numbered from 3.5."""
    return {
        "kind": "sheet",
        "group": "ab_line_3",
        "title": _SHEET.title,
        "columns": [{"label": "Make", "width": 300.0}],
        "name": "Maria Torres",
        "rows": [{"line": f"3.{n}", "cells": [cell]} for n, cell in enumerate(cells, start=5)],
    }


def _sheet_rows(cells):
    """What each row's cell of a sheet drawn with those cells reads back as."""
    pages = read_sheets(draw_sheet(_SHEET, _sheet_of(cells)), _SHEET)
    return [row[1] for page in pages for row in page.rows]


def _cell_ink(cell):
    """The Make cell of a sheet's one row holding `cell`, rendered."""
    page = pymupdf.open("pdf", draw_sheet(_SHEET, _sheet_of([cell])))[0]
    line = page.search_for("3.5")[0]
    return page.get_pixmap(dpi=288, clip=pymupdf.Rect(90, line.y0, 390, line.y1)).samples


def _template_letters():
    """Every BMP character a template's text font prints (text_fit.printable), in code order."""
    font = font_for(_template("schedule_a_b"), "/Helv")
    return [chr(c) for c in range(0x10000) if not 0xD800 <= c <= 0xDFFF and printable(font, chr(c))]


def test_the_sheets_letter_check_agrees_with_what_it_prints():
    # plan_sheet() refuses exactly the letters the sheet can't print as themselves (spec
    # §5.3, §4.3): one it accepts reads back as it prints, and leaves ink alone in its
    # cell; one it refuses, drawn without the check, reads back as something else or
    # leaves no ink. The sheet prints in the templates' encoding (R62), so every letter a
    # template's text font prints is drawn, those at codes other than WinAnsi's among
    # them, and so is □, which a template's /.notdef reads as.
    letters = _template_letters()
    accepted, refused = [], []
    for letter in dict.fromkeys([*_LETTERS, *letters, "□"]):
        try:
            plan_sheet("schedule_a_b", _SHEET, _sheet_of([f"x{letter}x"]))
            accepted.append(letter)
        except UnprintableLetter:
            refused.append(letter)
    # Of the font's letters, the sheet refuses only control characters, as check() does.
    assert [f"U+{ord(c):04X}" for c in letters if c in refused and c.isprintable()] == []
    assert "□" in refused
    invisible = [c for c in refused if c == "\t" or unicodedata.category(c) in ("Zs", "Cf")]
    assert [f"U+{ord(c):04X}" for c in invisible] == []

    printed = _sheet_rows([f"x{c}x" for c in accepted])
    assert {
        f"U+{ord(c):04X}": p for c, p in zip(accepted, printed, strict=True) if p != _as_printed(c)
    } == {}
    glyphs = [c for c in accepted if _as_printed(c) == f"x{c}x" and not c.isspace()]
    with _no_anti_aliasing():
        empty = _cell_ink("")
        assert [f"U+{ord(c):04X}" for c in glyphs if _cell_ink(c) == empty] == []

    printed = _sheet_rows([f"x{c}x" for c in refused])
    as_itself = [c for c, p in zip(refused, printed, strict=True) if p == f"x{c}x"]
    with _no_anti_aliasing():
        assert [f"U+{ord(c):04X}" for c in as_itself if _cell_ink(c) != empty] == []
