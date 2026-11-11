"""
What the printed page shows (3a2 spec §9).

fill() builds each widget's value with pypdf and PyMuPDF bakes it into the page, so the
filer gets a page, not a form to fill. These tests look at that page: what prints in each
box, where each character sits, and, where text can't tell, its pixels. MuPDF extracts a
character whole even when the box hides part of it, so a cut is judged from where the
character sits (its origin and size, and its outline in the Helvetica MuPDF draws the page
with), not from text.
"""

import json
import unicodedata
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from io import BytesIO
from pathlib import Path

import pymupdf
import pypdf
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from pypdf.generic import DictionaryObject, NameObject, NullObject, TextStringObject
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.districts.models import District
from apps.forms.field_index import export_state
from apps.forms.registry import (
    PreconditionMissing,
    build_field_values,
    get_all_form_types,
    packet,
)
from apps.forms.schema import SheetColumn, SheetSpec, load_schema
from apps.forms.services.fill_resolver import resolve_parts
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong
from apps.forms.services.sheets import draw_sheet, fits_line_column, plan_sheet, sheet_spec
from apps.forms.services.text_fit import font_for, printable
from apps.forms.services.widgets import field_of, template_widgets, widget_for
from apps.forms.tests.pdf_readback import read_drawn, read_sheets
from apps.intake.asset_lines import LINE_BY_KEY, LINES
from apps.intake.management.commands.seed_demo_data import PERSONAS
from apps.intake.models import AssetInfo, IntakeSession

# The Helvetica MuPDF draws and reads the baked page with. A glyph's outline, per point of
# size, is glyph_bbox: of the characters a form prints, Å's ring reaches highest, 0.953
# above the baseline, and µ's tail lowest, 0.220 below (g, j, p, q and y 0.218).
_HELV = pymupdf.Font("helv")
# A drawn glyph's outline, by the name MuPDF gives its font: the List of Creditors' boxes
# draw Times-Roman (R9).
_OUTLINES = {"Helvetica": _HELV, "Times-Roman": pymupdf.Font("tiro")}
_TALLEST, _DEEPEST = "Å", "µ"
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
        forms = packet(session)
        values = {}
        for form_type in get_all_form_types():
            try:
                values[form_type] = build_field_values(form_type, session)
            except PreconditionMissing:
                if form_type in forms:
                    raise
                # 103B outside the packet: its own questions are asked only of a waiver filer
        seeded[persona] = (forms, values)
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


@pytest.mark.slow
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


@pytest.mark.slow
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
    # The court's List of Creditors has no buttons; every other template does, so button
    # discovery breaking would show here instead of passing with nothing to judge.
    if form_type != "list_of_creditors":
        assert buttons
    assert all(label.strip() for label in labels.values()), labels
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
    pdf = _drawn_packet()["form_103b"]  # Maria's waiver answer
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


@pytest.mark.slow
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


@pytest.mark.slow
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

# Å's ring reaches higher than any other letter's, g's and q's tails hang within 0.002 of
# the size of the lowest (µ's), and Ç's cedilla nearly as low. No digits: a box's blank
# text ("2") reads as blank.
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


def _overshoot(template, widget):
    """
    side → how far, in points, the tallest and the deepest letter reach past a single-line
    box's rect at the box's own size, where they do (R38): pypdf centres the font's ascent
    in the box, so on a few boxes Å's ring rises past the top and µ's tail hangs past the
    bottom. Both reach less far at a smaller size. check() plans Å or µ alone at the box's
    own size, and never plans a value larger. A multi-line box, or one that sizes its
    text itself, gets nothing.
    """
    if widget.multiline or not widget.size:
        return {}
    size = widget.size
    ascent = font_for(template, widget.font).font_descriptor.ascent
    baseline = widget.margin + (widget.height - 2 * widget.margin - ascent * size / 1000) / 2
    reach = {
        "top": baseline + _HELV.glyph_bbox(ord(_TALLEST)).y1 * size - widget.height,
        "bottom": -(baseline + _HELV.glyph_bbox(ord(_DEEPEST)).y0 * size),
    }
    return {side: by for side, by in reach.items() if by > 0}


# (form type, box, side) where _overshoot finds a letter past the rect: the only boxes the
# cut-off test lets a letter cross, by that much. Å rises up to 0.228 pt above 49 boxes and
# µ hangs up to 0.048 pt below 20 of them (g and q 0.024 pt); Ç stays inside. Whether
# filers' forms may print this hairline is the owner's R38 question.
_R38_HAIRLINES = [
    ("form_101", "Attorney.Sig@8:T3", "bottom"),
    ("form_101", "Attorney.Sig@8:T3", "top"),
    ("form_101", "Case number1@2:T2", "bottom"),
    ("form_101", "Case number1@2:T2", "top"),
    ("form_101", "Debtor1.Name@2:T1", "bottom"),
    ("form_101", "Debtor1.Name@2:T1", "top"),
    ("form_101", "Debtor1.Name@3:T1", "bottom"),
    ("form_101", "Debtor1.Name@3:T1", "top"),
    ("form_101", "Debtor1.Name@4:T1", "bottom"),
    ("form_101", "Debtor1.Name@4:T1", "top"),
    ("form_101", "Debtor1.Name@5:T1", "bottom"),
    ("form_101", "Debtor1.Name@5:T1", "top"),
    ("form_101", "Debtor1.Name@6:T1", "bottom"),
    ("form_101", "Debtor1.Name@6:T1", "top"),
    ("form_101", "Debtor1.Name@7:T1", "bottom"),
    ("form_101", "Debtor1.Name@7:T1", "top"),
    ("form_101", "Debtor1.Name@8:T1", "bottom"),
    ("form_101", "Debtor1.Name@8:T1", "top"),
    ("form_101", "Debtor1.Name@9:T1", "bottom"),
    ("form_101", "Debtor1.Name@9:T1", "top"),
    ("form_103b", "13 Other real estate city sate@2:T29", "top"),
    ("form_103b", "Case number@1:T4", "top"),
    ("form_103b", "Case number@2:T2", "top"),
    ("form_103b", "Case number@3:T2", "top"),
    ("form_103b", "Case number@4:T4", "top"),
    ("form_103b", "Debtor 1@1:T1", "top"),
    ("form_103b", "Debtor 1@4:T1", "top"),
    ("form_103b", "Debtor.Name1@2:T1", "top"),
    ("form_103b", "Debtor.Name1@3:T1", "top"),
    ("form_103b", "Examples House condominium@2:T24", "top"),
    ("form_103b", "Mileage_2@2:T41", "bottom"),
    ("form_103b", "Mileage_2@2:T41", "top"),
    ("form_103b", "Year_2@2:T39", "bottom"),
    ("form_103b", "Year_2@2:T39", "top"),
    ("form_103b", "undefined_29@3:T10", "bottom"),
    ("form_103b", "undefined_29@3:T10", "top"),
    ("form_121", "Case number1@1:T2", "bottom"),
    ("form_121", "Case number1@1:T2", "top"),
    ("list_of_creditors", "Case number1@1:T3", "bottom"),
    ("list_of_creditors", "Case number1@1:T3", "top"),
    ("list_of_creditors", "Debtor1.Name@1:T1", "bottom"),
    ("list_of_creditors", "Debtor1.Name@1:T1", "top"),
    ("list_of_creditors", "Debtor1.Name@2:T2", "bottom"),
    ("list_of_creditors", "Debtor1.Name@2:T2", "top"),
    ("list_of_creditors", "Debtor2.Name@1:T2", "bottom"),
    ("list_of_creditors", "Debtor2.Name@1:T2", "top"),
    ("schedule_a_b", "23.3 Annuities amount@6:T54", "top"),
    ("schedule_a_b", "undefined_12@2:T17", "top"),
    ("schedule_a_b", "undefined_4@1:T23", "top"),
    ("schedule_a_b", "undefined_8@1:T47", "top"),
    ("schedule_c", "Schedule AB@1:T14", "top"),
    ("schedule_c", "Schedule AB_2@1:T21", "top"),
    ("schedule_c", "Schedule AB_3@1:T28", "top"),
    ("schedule_c", "description@1:T9", "top"),
    ("schedule_c", "description_2@1:T16", "top"),
    ("schedule_c", "description_3@1:T23", "top"),
    ("schedule_c", "undefined@1:T10", "top"),
    ("schedule_c", "undefined_2@1:T12", "top"),
    ("schedule_c", "undefined_6@1:T17", "top"),
    ("schedule_c", "undefined_7@1:T19", "top"),
    ("schedule_c", "undefined_8@1:T24", "top"),
    ("schedule_c", "undefined_9@1:T26", "top"),
    ("schedule_d", "On which line in Part 1 did you enter the creditor_4@3:T32", "bottom"),
    ("schedule_d", "On which line in Part 1 did you enter the creditor_4@3:T32", "top"),
    ("schedule_d", "On which line in Part 1 did you enter the creditor_5@3:T41", "bottom"),
    ("schedule_d", "On which line in Part 1 did you enter the creditor_5@3:T41", "top"),
    ("schedule_d", "On which line in Part 1 did you enter the creditor_6@3:T50", "top"),
    ("schedule_d", "undefined_26@3:T14", "top"),
    ("schedule_d", "undefined_27@3:T22", "top"),
]


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
        allowed = {
            side: by
            for side, by in _overshoot(template, widget).items()
            if (form_type, widget.key, side) in _R38_HAIRLINES
        }
        if widget.page not in pages:
            pages[widget.page] = _glyphs(document[widget.page - 1])
        for g in pages[widget.page]:
            # A space prints nothing; MuPDF also adds one where a line's text breaks off.
            if g.font not in _OUTLINES or not g.text.strip() or not g.inside(rect):
                continue
            outline = _OUTLINES[g.font].glyph_bbox(ord(g.text))
            past = {
                "top": rect[1] - (g.origin[1] - outline.y1 * g.size),
                "bottom": g.origin[1] - outline.y0 * g.size - rect[3],
                "left": rect[0] - g.bbox[0],
                "right": g.bbox[2] - rect[2],
            }
            cut += [
                (widget.key, side, round(by, 3))
                for side, by in past.items()
                if by > allowed.get(side, 0) + 0.001  # 0.001 pt: MuPDF's rounding
            ]
    return cut


def test_a_letter_reaches_past_its_box_only_where_r38_allows():
    # The cut-off test lets a letter past the rect only on the boxes _R38_HAIRLINES lists.
    # Should a revised template or another PyMuPDF add a box to them or drop one, this
    # fails until the list changes with it, so no box gains the allowance unseen.
    reaching = sorted(
        (form_type, w.key, side)
        for form_type in get_all_form_types()
        for w in template_widgets(_template(form_type))
        if w.drawn and w.kind == "Text"
        for side in _overshoot(_template(form_type), w)
    )
    assert reaching == _R38_HAIRLINES


def _past_padding(form_type, widget, just, over):
    """
    pypdf clips a single-line box's text 2 × margin in from its left and right edges (R5),
    and a glyph inside the rect can still cross that clip. So the value that just fits
    must be no wider than the clip at the size check() plans it at, and one letter more
    must be wider than the clip even at 6 pt. Returns each that isn't: (key, which value,
    how far past or short of the clip).
    """
    room = widget.width - 4 * widget.margin
    # Font.text_length, not get_text_length, which drops the letter after any of U+00A0 to
    # U+00FF ("Åg" measures as "Å") and mis-measures letters above U+00FF.
    # On every value this test measures, its width is text_fit's to within 0.00001 pt.
    # 0.01 pt: one letter more in Schedule J's Other 15d box is as wide as the clip to
    # within 0.0001 pt.
    font = {"/Helv": _HELV, "/TiRo": pymupdf.Font("tiro")}[widget.font]
    fits = font.text_length(just, _planned_size(form_type, widget.key, just)) - room
    refused = font.text_length(over, 6.0) - room
    past = []
    if fits > 0.01:
        past.append((widget.key, "just", round(fits, 3)))
    if refused <= -0.01:
        past.append((widget.key, "over", round(refused, 3)))
    return past


@pytest.mark.slow
@pytest.mark.parametrize("form_type", get_all_form_types())
def test_no_value_is_ever_cut_off(form_type):
    # The longest value check() lets through prints whole, every character inside its box,
    # and one letter or line more is refused, never drawn cut off (spec §9). In a
    # single-line box that isn't comb and has no MaxLen, it must also end inside pypdf's
    # padding. A short value stays inside too, but for R38's hairline on the boxes
    # _R38_HAIRLINES lists. A combo box takes only its own options, so it has no boundary
    # to probe: it prints its widest whole.
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
    assert [
        past
        for w in boxes
        if not (w.multiline or w.comb) and w.max_len is None
        for past in _past_padding(form_type, w, just[w.key], over[w.key])
    ] == []
    assert _cut_off(form_type, just) == []
    assert _cut_off(form_type, short) == []
    # Every form but the List of Creditors has its district box, which lists every district
    # (the list's one combo box is its chapter).
    widest = {
        w.key: max(
            (o for o in w.options if o.strip()),
            key=lambda o: pymupdf.get_text_length(o, fontname="helv", fontsize=10),
        )
        for w in template_widgets(_template(form_type))
        if w.drawn and w.kind == "ComboBox"
    }
    assert widest
    assert _cut_off(form_type, widest) == []


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


@pytest.mark.slow
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


def _inside(document, widget):
    """The widget's rect on its page, less 2 pt on each side (inside its border), rendered."""
    clip = pymupdf.Rect(widget.rect) + (2, 2, -2, -2)
    return document[widget.page - 1].get_pixmap(dpi=288, clip=clip).samples


def _letters_print_as_check_says(form_type, boxes):
    """
    check() refuses exactly the letters the drawing can't print (spec §4.3), judged through
    these boxes of one form.
    """
    template = _template(form_type)
    accepted, refused = [], []
    for letter in _LETTERS:
        try:
            PDFFormFiller().check(form_type, {boxes[0].key: f"x{letter}x"})
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
    # The baseline is a box holding a lone space, drawn as a letter's box is, border and all.
    # It matches the pristine empty form inside the border: a lone space and a zero-width
    # space (a format character, R36) leave no ink. The border itself is not compared with
    # the pristine form's: two of the list's boxes have a rect 0.25 pt shorter than their
    # appearance's BBox, which scales the template's own stroke by 0.9964, a sub-pixel move.
    pristine = _printed(PDFFormFiller().fill(form_type, {}))
    empty = _printed(PDFFormFiller().fill(form_type, {w.key: " " for w in boxes}))
    with _no_anti_aliasing():
        for nothing in (" ", "\u200b"):
            blank = _printed(PDFFormFiller().fill(form_type, {w.key: nothing for w in boxes}))
            differing = [
                w.key
                for w in boxes
                if _inside(blank, w) != _inside(pristine, w)
                or _pixels(blank, w) != _pixels(empty, w)
            ]
            assert differing == []
    misprinted, no_ink = {}, []
    for pairs in in_boxes(accepted):
        pdf = PDFFormFiller().fill(form_type, {w.key: f"x{c}x" for w, c in pairs})
        _printed(pdf)
        printed = {(w.page, w.tag): w.value for w in read_drawn(form_type, pdf)}
        misprinted |= {
            f"U+{ord(c):04X}": printed[(w.page, w.tag)]
            for w, c in pairs
            if printed[(w.page, w.tag)] != _as_printed(c)
        }
        glyphs = [(w, c) for w, c in pairs if _as_printed(c) == f"x{c}x" and not c.isspace()]
        alone = _printed(PDFFormFiller().fill(form_type, {w.key: c for w, c in glyphs}))
        with _no_anti_aliasing():
            no_ink += [
                f"U+{ord(c):04X}" for w, c in glyphs if _pixels(alone, w) == _pixels(empty, w)
            ]
    assert misprinted == {}
    assert no_ink == []

    # Refused: "x<letter>x" drawn without check() reads back as something else, or the
    # letter leaves ink, alone in its box. The baseline is drawn the same way (a lone space
    # in each box), since a box drawn without check() has no border to compare with the
    # template's own.
    empty = pymupdf.open(
        "pdf", _drawn_without_check(template, {(w.page, w.tag): " " for w in boxes})
    )
    inked = []
    for pairs in in_boxes(refused):
        pdf = _drawn_without_check(template, {(w.page, w.tag): f"x{c}x" for w, c in pairs})
        printed = {(w.page, w.tag): w.value for w in read_drawn(form_type, pdf)}
        as_itself = [(w, c) for w, c in pairs if printed[(w.page, w.tag)] == f"x{c}x"]
        alone = pymupdf.open(
            "pdf", _drawn_without_check(template, {(w.page, w.tag): c for w, c in as_itself})
        )
        with _no_anti_aliasing():
            inked += [
                f"U+{ord(c):04X}" for w, c in as_itself if _pixels(alone, w) != _pixels(empty, w)
            ]
    assert inked == []


@pytest.mark.slow
def test_check_agrees_with_the_drawing_on_every_letter():
    # check() refuses exactly the letters the drawing can't print (spec §4.3): a letter it
    # accepts prints as itself, and one it refuses would print as "?", as another glyph,
    # or as nothing. MuPDF reads back a character's code even where the font draws
    # nothing for it, so whether a letter prints is judged by its ink too. Every
    # template's text font has the same encoding, so one form's boxes stand for all 18
    # here. Form 107's boxes carry no /DR of their own. Some boxes on five other templates
    # do, and the drawing deletes it (R32): undoing that deletion fails test_pdf_filler.py's
    # test_a_letter_outside_latin_1_prints_on_every_box.
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
    _letters_print_as_check_says("form_107", boxes)

    # The second call exists because the List of Creditors' 30 entry boxes are multiline
    # Times-Roman, which Form 107's single-line Helvetica boxes can't stand for. All 30 boxes,
    # not one: one box would take about 400 rounds of fill and read-back.
    list_template = _template("list_of_creditors")
    creditors = [
        w for w in template_widgets(list_template) if w.drawn and w.full_name.startswith("creditor")
    ]
    assert len(creditors) == 30
    _letters_print_as_check_says("list_of_creditors", creditors)


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


@pytest.mark.slow
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


# ── Schedule A/B's rows (3b spec §8) ──────────────────────────────────


@pytest.fixture
def filer(db):
    user = get_user_model().objects.create_user(username="abfiler", password="pass")
    district = District.objects.create(
        code="abilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def _ab_row(session, line, value=None, description="", entire=None, **details):
    return AssetInfo.objects.create(
        session=session,
        ab_line=line,
        description=description,
        current_value=None if value is None else Decimal(value),
        entire_value=None if entire is None else Decimal(entire),
        details=json.dumps(details),
    )


def _ab_place(session, street, value="1000.00", entire="2000.00", **details):
    return _ab_row(
        session,
        "1",
        value,
        entire=entire,
        street=street,
        city="Elgin",
        state="IL",
        zip="60120",
        county="Kane",
        property_kinds=["land"],
        who="only_you",
        **details,
    )


def _ab_car(session, make, line="3", value="1000.00", entire="2000.00", who="only_you", **details):
    return _ab_row(session, line, value, entire=entire, make=make, who=who, **details)


def _ab_drawn(session):
    """(box → the text or the ticks it prints, the parts, the PDF), read off the baked page."""
    parts = resolve_parts(load_schema("schedule_a_b"), session)
    pdf = PDFFormFiller().fill("schedule_a_b", parts)
    shows = {}
    for widget in read_drawn("schedule_a_b", pdf, parts["parts"]):
        seen = shows.setdefault(widget.full_name, set())
        if widget.state:
            if widget.state != "/Off":
                seen.add(widget.state)
        elif widget.value:
            seen.add(widget.value)
    return shows, parts, pdf


def _ab_sheet_rows(parts, pdf):
    """The rows of the form's one attached sheet, as a person reads them."""
    (part,) = [part for part in parts["parts"] if part["kind"] == "sheet"]
    (page,) = read_sheets(pdf, sheet_spec(part))
    return page.rows


def test_a_home_prints_on_line_1_1_with_both_values_and_its_kinds(filer):
    # The first thing a trustee reads: where it is, what it is, who has it and both values.
    _ab_row(
        filer,
        "1",
        "90000.00",
        entire="180000.00",
        street="12 Elm St",
        street_2="Unit 3",
        city="Elgin",
        state="IL",
        zip="60120",
        county="Kane",
        property_kinds=["single_family", "other"],
        other_kind="Garage",
        nature="Fee simple",
        who="only_you",
        other_info="PIN 900",
    )

    shows, _, _ = _ab_drawn(filer)

    assert {
        box: shows[box]
        for box in (
            "Check 2",
            "1 1",
            "1 1a",
            "City",
            "State",
            "ZIP Code",
            "County",
            "Singlefamily home",
            "Other",
            "undefined_4",
            "Land",
            "the entireties or a life estate if known",
            "Who has interest in property",
            "property identification number",
            "undefined_2",
            "undefined_3",
            "undefined_13",
        )
    } == {
        "Check 2": {"/yes"},
        "1 1": {"12 Elm St"},
        "1 1a": {"Unit 3"},
        "City": {"Elgin"},
        "State": {"IL"},
        "ZIP Code": {"60120"},
        "County": {"Kane"},
        "Singlefamily home": {"/On"},
        "Other": {"/On"},
        "undefined_4": {"Garage"},
        "Land": set(),
        "the entireties or a life estate if known": {"Fee simple"},
        "Who has interest in property": {"/Debtor 1"},
        "property identification number": {"PIN 900"},
        "undefined_2": {"180000.00"},
        "undefined_3": {"90000.00"},
        "undefined_13": {"90000.00"},
    }


def test_a_third_property_prints_on_page_2_and_a_fourth_on_a_sheet_counted_in_line_2(filer):
    # The form says to attach a sheet for more, and its line 2 adds the attached pages too.
    for n in range(1, 5):
        _ab_place(filer, f"{n} Elm St", value=f"{n}000.00", entire="9000.00", nature="Joint")

    shows, parts, pdf = _ab_drawn(filer)

    assert shows["13"] == {"3 Elm St"}
    assert shows["undefined_11"] == {"3000.00"}
    assert _ab_sheet_rows(parts, pdf) == (
        (
            "1.4",
            "4 Elm St, Elgin, IL 60120, Kane",
            "Land",
            "Debtor 1 only; Joint",
            "9000.00",
            "4000.00",
        ),
    )
    assert shows["undefined_13"] == {"10000.00"}


def test_the_largest_amount_a_row_can_hold_prints_whole_on_its_sheet(filer):
    # A word never wraps, so a value column narrower than the widest amount refuses the form.
    for n in range(1, 5):
        _ab_place(filer, f"{n} Elm St", value="9999999999.99", entire="9999999999.99")
    for n in range(1, 6):
        _ab_car(filer, f"Make{n}", value="9999999999.99", entire="9999999999.99")

    parts = resolve_parts(load_schema("schedule_a_b"), filer)

    assert [part["group"] for part in parts["parts"] if part["kind"] == "sheet"] == [
        "ab_1",
        "ab_3",
    ]
    PDFFormFiller().check("schedule_a_b", parts)


_PIN = "17-16-123-045-0000"
_VIN = "1HGCM82633A004352"
# VINs are not one width. These two print wider than _VIN, by their W, M and D: a Mercedes-format
# VIN such as a Sprinter-based motor home's, and a MINI-format one, the widest format measured.
_VIN_MERCEDES = "WDBUF56X88B123456"
_VIN_MINI = "WMWZC3C5XGWA12345"


@pytest.mark.parametrize(
    ("line", "answer"),
    [
        ("1", {"other_info": _PIN}),
        ("3", {"mileage": "125,000"}),
        ("3", {"mileage": "Unknown"}),
        ("3", {"make": "Harley-Davidson"}),
        ("3", {"model": "Thunderbird"}),
        ("3", {"year": "Unknown"}),
        ("3", {"other_info": _VIN}),
        ("3", {"other_info": _VIN_MERCEDES}),
        ("3", {"other_info": _VIN_MINI}),
        ("4", {"other_info": _VIN}),
        ("4", {"other_info": _VIN_MERCEDES}),
        ("4", {"other_info": _VIN_MINI}),
        ("4", {"year": "Unknown"}),
        ("4", {"make": "Harley-Davidson"}),
        ("4", {"model": "Thunderbird"}),
        ("4", {"model": "WaveRunner"}),
    ],
    ids=lambda case: next(iter(case)) if isinstance(case, dict) else f"line_{case}",
)
def test_an_answer_the_form_s_box_takes_prints_whole_on_its_sheet(filer, line, answer):
    # A word never wraps, so a column narrower than a real answer refuses the whole form, and the
    # filer could only fix it by mangling a correct number. The row past the slots goes on a sheet.
    if line == "1":
        for n in range(1, 4):
            _ab_place(filer, f"{n} Elm St")
        _ab_place(filer, "4 Elm St", **answer)
    else:
        for make in ("A", "B", "C", "D")[: LINE_BY_KEY[line].capacity]:
            _ab_car(filer, make, line=line)
        _ab_car(filer, **{"make": "Spare", **answer}, line=line)

    parts = resolve_parts(load_schema("schedule_a_b"), filer)

    PDFFormFiller().check("schedule_a_b", parts)
    (part,) = [part for part in parts["parts"] if part["kind"] == "sheet"]
    (word,) = answer.values()
    assert word in " ".join(cell for row in part["rows"] for cell in row["cells"])


def test_a_boat_s_model_and_vin_read_whole_in_their_own_columns_on_the_drawn_sheet(filer):
    # Line 4's Model and Who are split to the half point to take both, so read what a court reads.
    for make in ("A", "B"):
        _ab_car(filer, make, line="4")
    _ab_car(filer, "Sea-Doo", line="4", model="WaveRunner", year="Unknown", other_info=_VIN_MINI)

    parts = resolve_parts(load_schema("schedule_a_b"), filer)
    pdf = PDFFormFiller().fill("schedule_a_b", parts)

    assert _ab_sheet_rows(parts, pdf) == (
        (
            "4.3",
            "Sea-Doo",
            "WaveRunner",
            "Unknown",
            f"Debtor 1 only; {_VIN_MINI}",
            "2000.00",
            "1000.00",
        ),
    )


@pytest.mark.parametrize(
    ("answers", "year_and_miles"),
    [
        ({"year": "Unknown", "mileage": "Unknown"}, "Unknown Unknown"),
        ({"year": "2015", "mileage": "125,000"}, "2015 125,000"),
        ({"year": "2015"}, "2015"),
        ({"mileage": "125,000"}, "125,000"),
        ({}, ""),
    ],
    ids=["both_unknown", "both", "year_only", "miles_only", "neither"],
)
def test_a_car_s_year_and_miles_and_its_vin_read_whole_on_the_drawn_sheet(
    filer, answers, year_and_miles
):
    # Line 3's sheet has no room for a VIN beside a Year and a Miles column, so one column holds
    # both answers, each on its own line: "Unknown" only just fits, and a comma would refuse it.
    for make in ("A", "B", "C", "D"):
        _ab_car(filer, make)
    _ab_car(filer, "Mini", model="Cooper", other_info=_VIN_MINI, **answers)

    parts = resolve_parts(load_schema("schedule_a_b"), filer)
    pdf = PDFFormFiller().fill("schedule_a_b", parts)

    assert _ab_sheet_rows(parts, pdf) == (
        (
            "3.5",
            "Mini",
            "Cooper",
            year_and_miles,
            f"Debtor 1 only; {_VIN_MINI}",
            "2000.00",
            "1000.00",
        ),
    )


@pytest.mark.parametrize(
    ("line", "answer", "label"),
    [
        ("3", {"other_info": "W" * 17}, "Who has an interest"),
        ("3", {"year": "Approximately"}, "Year and miles"),
        ("4", {"other_info": "W" * 17}, "Who has an interest"),
    ],
    ids=["line_3_past_its_widest_vin", "line_3_year_too_wide", "line_4_past_its_widest_vin"],
)
def test_a_word_too_wide_for_a_vehicle_s_sheet_is_refused_with_a_link_to_the_assets_step(
    filer, line, answer, label
):
    # The refusal is the filer's only sign that a row won't print, so it names the column and says
    # where to change it.
    for make in ("A", "B", "C", "D")[: LINE_BY_KEY[line].capacity]:
        _ab_car(filer, make, line=line)
    _ab_car(filer, "Spare", line=line, **answer)

    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_a_b", resolve_parts(load_schema("schedule_a_b"), filer))

    assert refused.value.label == label
    assert refused.value.step == "assets"


def test_a_leased_car_prints_zero_in_both_value_boxes(filer):
    # The filer typed $0 for each: a zero is an answer, so it prints, unlike an unknown value.
    _ab_car(filer, "Toyota", value="0", entire="0", model="Corolla", other_info="Leased")

    shows, _, _ = _ab_drawn(filer)

    assert shows["3 1"] == {"Toyota"}
    assert shows["3 2"] == {"Corolla"}
    assert shows["Other information"] == {"Leased"}
    assert shows["undefined_14"] == {"0.00"}
    assert shows["undefined_15"] == {"0.00"}


def test_a_car_of_unknown_value_prints_its_make_and_blank_values(filer):
    # "I don't know the value" keeps the row on the sworn list without inventing a figure.
    _ab_row(filer, "3", None, make="Honda", who="only_you", value_unknown=True, entire_unknown=True)

    shows, _, _ = _ab_drawn(filer)

    assert shows["3 1"] == {"Honda"}
    assert shows["undefined_14"] == set()
    assert shows["undefined_15"] == set()
    assert shows["undefined_26"] == {"0.00"}


def test_a_co_owned_car_ticks_the_another_box_and_no_debtor_2_box(filer):
    # Each row's "another" box has its own spelling of the state, and rows 3.3 and 3.4 export On.
    for make in ("A", "B", "C", "D"):
        _ab_car(filer, make, who="with_someone")

    shows, _, _ = _ab_drawn(filer)

    assert [shows[f"Who has interest in property {n}"] for n in (4, 5, 6, 7)] == [
        {"/One of Debtors and another"},
        {"/One of Debtors and another"},
        {"/On"},
        {"/On"},
    ]


def test_the_community_box_stays_unticked_unless_the_filer_ticks_it(filer):
    _ab_car(filer, "Unticked")
    _ab_car(filer, "Ticked", community=True)

    shows, _, _ = _ab_drawn(filer)

    assert shows["Check if this is community property see"] == set()
    assert shows["Check if this is community property see_2"] == {"/On"}


def test_a_boat_prints_on_line_4_not_line_3(filer):
    # The RV gap: a filer whose only vehicle is a boat must not swear to owning a car.
    _ab_car(filer, "Bayliner", line="4", value="700.00", entire="1400.00", model="VR5", year="2010")

    shows, _, _ = _ab_drawn(filer)

    assert shows["Check 3"] == {"/no"}
    assert shows["3 1"] == set()
    assert shows[
        "Examples Boats trailers motors personal watercraft fishing vessels snowmobiles "
        "motorcycle accessories"
    ] == {"/Yes_2"}
    assert shows["Make"] == {"Bayliner"}
    assert shows["Model"] == {"VR5"}
    assert shows["Year"] == {"2010"}
    assert shows["undefined_22"] == {"1400.00"}
    assert shows["undefined_23"] == {"700.00"}
    assert shows["undefined_26"] == {"700.00"}


def test_a_second_item_on_a_one_box_line_goes_on_a_sheet_numbered_6_2(filer):
    # A second row is never merged or dropped: it prints under its own number, and line 15 adds it.
    _ab_row(filer, "6", "100.00", "Sofa")
    _ab_row(filer, "6", "300.00", "Dining table")

    shows, parts, pdf = _ab_drawn(filer)

    assert shows["6 check"] == {"/yes"}
    assert shows["6 description"] == {"Sofa"}
    assert shows["6 description amount"] == {"100.00"}
    assert _ab_sheet_rows(parts, pdf) == (("6.2", "Dining table", "300.00"),)
    assert shows["15 amount"] == {"400.00"}


def test_cash_prints_its_amount(filer):
    _ab_row(filer, "16", "60.00")

    shows, _, _ = _ab_drawn(filer)

    assert shows["Check 16"] == {"/yes"}
    assert shows["16 Cash amount"] == {"60.00"}


def test_line_43_s_describe_prints_under_its_yes(filer):
    # The form's Describe sits under "Yes" to "Do your lists include personally identifiable
    # information", so it prints there.
    _ab_row(filer, "43", "50.00", "Customer emails", has_personal_info=True)

    shows, _, _ = _ab_drawn(filer)

    assert shows["check 43"] == {"/yes"}
    assert shows["check 43_1"] == {"/yes"}
    assert shows["43 Identifiable information"] == {"Customer emails"}
    assert shows["undefined_135"] == {"50.00"}


def test_line_43_s_describe_stays_blank_under_its_no(filer):
    # A description kept from before the filer changed the answer would contradict the tick.
    _ab_row(filer, "43", "50.00", "Customer emails", has_personal_info=False)

    shows, _, _ = _ab_drawn(filer)

    assert shows["check 43_1"] == {"/no"}
    assert shows["43 Identifiable information"] == set()
    assert shows["undefined_135"] == {"50.00"}


def test_other_s_words_stay_blank_once_other_is_unticked(filer):
    # Words kept from before the filer unticked Other would sit beside an empty box on a sworn
    # form. A row on a sheet already leaves them out, and a row in a box must read the same.
    for n in range(1, 5):
        _ab_place(filer, f"{n} Elm St", other_kind="Garage")

    shows, parts, pdf = _ab_drawn(filer)

    for box in ("undefined_4", "undefined_8", "undefined_12"):
        assert shows[box] == set()
    assert shows["Land"] == {"/On"}
    assert shows["Other"] == set()
    assert _ab_sheet_rows(parts, pdf)[0][2] == "Land"


# The Yes/No boxes under each gate (3b spec §8.1).
_UNDER_37 = ("check 38", "check 39", "check 40", "check 41", "check 42", "check 43", "check 44")
_UNDER_46 = ("check 47", "check 48", "check 49", "check 50", "check 51")


def test_a_no_to_line_37_leaves_38_to_45_blank_and_59_at_zero(filer):
    # The form says "No. Go to Part 6", so those lines were never answered; line 59 still adds up.
    shows, _, _ = _ab_drawn(filer)

    assert shows["check 37"] == {"/no"}
    assert {box: shows[box] for box in _UNDER_37} == {box: set() for box in _UNDER_37}
    assert shows["undefined_143"] == set()
    assert shows["undefined_163"] == {"0.00"}


def test_a_no_to_line_46_leaves_47_to_52_blank_and_60_at_zero(filer):
    shows, _, _ = _ab_drawn(filer)

    assert shows["check 46"] == {"/no"}
    assert {box: shows[box] for box in _UNDER_46} == {box: set() for box in _UNDER_46}
    assert shows["undefined_154"] == set()
    assert shows["undefined_164"] == {"0.00"}


def test_a_yes_to_a_gate_answers_every_line_under_it_and_prints_its_total(filer):
    # A Yes shows the Part, so a line under it with nothing on it says No rather than nothing.
    _ab_row(filer, "38", "310.00", "Unpaid invoices")
    _ab_row(filer, "47", "20.00", "Hens")

    shows, _, _ = _ab_drawn(filer)

    assert shows["check 37"] == {"/yes"}
    assert shows["check 38"] == {"/yes"}
    assert shows["check 39"] == {"/no"}
    assert shows["undefined_143"] == {"310.00"}
    assert shows["undefined_163"] == {"310.00"}
    assert shows["check 46"] == {"/yes"}
    assert shows["check 47"] == {"/On"}
    assert shows["check 48"] == {"/no"}
    assert shows["undefined_154"] == {"20.00"}
    assert shows["undefined_164"] == {"20.00"}


def test_a_no_to_line_1_leaves_line_2_blank_and_55_at_zero(filer):
    # "No. Go to Part 2" skips line 2, but 106Sum copies line 55, which always prints.
    _ab_row(filer, "6", "100.00", "Sofa")

    shows, _, _ = _ab_drawn(filer)

    assert shows["Check 2"] == {"/On"}
    assert shows["undefined_13"] == set()
    assert shows["undefined_159"] == {"0.00"}


def test_every_line_says_no_for_a_filer_with_nothing_and_totals_print_zero(filer):
    # Sarah's form: nothing owned is sworn line by line, and every total says 0.00.
    shows, _, _ = _ab_drawn(filer)

    questions = [
        f for f in load_schema("schedule_a_b").fields if f.rule and f.rule.startswith("ab_has_")
    ]
    assert {f.rule.removeprefix("ab_has_") for f in questions} == {line.key for line in LINES}
    under_a_gate = {
        f.pdf_field for f in questions if LINE_BY_KEY[f.rule.removeprefix("ab_has_")].gate
    }
    assert {f.pdf_field: shows[f.pdf_field] for f in questions} == {
        f.pdf_field: set() if f.pdf_field in under_a_gate else {f.choices["no"]} for f in questions
    }
    totals = (
        "undefined_26",  # 5
        "15 amount",
        "undefined_124",  # 36
        "undefined_158",  # 54
        "undefined_159",  # 55
        "undefined_160",
        "undefined_161",
        "undefined_162",
        "undefined_163",  # 59
        "undefined_164",  # 60
        "undefined_165",
        "undefined_166",
        "undefined_167",  # 63
    )
    assert {box: shows[box] for box in totals} == {box: {"0.00"} for box in totals}
    blank = ("undefined_13", "undefined_143", "undefined_154")  # 2, 45, 52
    assert {box: shows[box] for box in blank} == {box: set() for box in blank}


# The lines whose boxes this checks. They come from the index, not the schema, so a binding
# spelled wrong, or set on another row's box, prints in the wrong place and fails here.
_ROW_SHAPES = ("place", "vehicle", "vehicle_no_mileage", "item", "item_question", "cash")
_ROW_TEXT = {
    "City": "city",
    "State": "state",
    "ZIP Code": "zip",
    "County": "county",
    "Other information": "other_info",
    "Other": "other_kind",
    "Describe the nature": "nature",
    "Make": "make",
    "Model": "model",
    "Year": "year",
    "Approximate mileage": "mileage",
}


def _row_answers(key, n):
    """Every answer a row of line `key` can give, each its own, short enough for any box.

    Rows take turns at each answer to "who has an interest", so each line prints both.
    """
    shape = LINE_BY_KEY[key].shape
    answers = {"value": f"{key}{n}2.00", "description": f"D{key}", "details": {}}
    if shape in ("item", "item_question", "cash"):
        if shape == "item_question":
            answers["details"]["has_personal_info"] = True
        return answers
    answers["entire"] = f"{key}{n}1.00"
    answers["details"] = {attr: f"{attr[:2]}{key}{n}" for attr in _ROW_TEXT.values()}
    who = "only_you" if n % 2 else "with_someone"
    answers["details"] |= {"who": who, "community": True}
    if shape == "place":
        answers["details"] |= {
            "street": f"St{key}{n}",
            "street_2": f"Sd{key}{n}",
            "property_kinds": [
                "single_family",
                "duplex",
                "condo",
                "manufactured",
                "land",
                "investment",
                "timeshare",
                "other",
            ],
        }
    return answers


def _printed_for(row, answers, street_field):
    """What a box should print for these answers, from the index's words for it; None for nothing."""
    label = row["label"]
    if row["kind"] == "checkbox":
        words = row["option_text"]
        who = answers["details"].get("who")
        if words == "Debtor 1 only" and who == "only_you":
            return export_state(row["on_state"])
        if words.startswith("At least one of the debtors") and who != "with_someone":
            return None
        if words.startswith(("No", "Debtor")):
            return None
        return export_state(row["on_state"])
    if row["kind"] == "amount":
        return answers["entire"] if "entire" in label else answers["value"]
    if label.startswith("Street address"):
        return answers["details"][street_field]
    for words, attr in _ROW_TEXT.items():
        if label.startswith(words) and attr in answers["details"]:
            return answers["details"][attr]
    return answers["description"]


def test_every_row_box_prints_its_own_answer_on_the_page(filer):
    # Every slot, filled at once with an answer of its own: nothing lands on another row or
    # another line, and each box takes the answer its printed words ask for.
    lines = [line for line in LINES if line.shape in _ROW_SHAPES]
    for line in lines:
        for n in range(1, line.capacity + 1):
            answers = _row_answers(line.key, n)
            _ab_row(
                filer,
                line.key,
                answers["value"],
                "" if line.shape == "cash" else answers["description"],
                answers.get("entire"),
                **answers["details"],
            )

    shows, _, _ = _ab_drawn(filer)

    keys = {line.key for line in lines} | {"37", "46"}
    index = json.loads((settings.FORM_INDEX_DIRECTORY / "form_b106ab.index.json").read_text())
    expected, streets = {}, set()
    for row in sorted(index, key=lambda r: (r["page"], r["rect"][1])):
        key, _, n = row["line"].rstrip(".").partition(".")
        if key not in keys:
            continue
        # The upper box of a row's two is the first address line.
        street_field = "street_2" if (key, n) in streets else "street"
        if row["label"].startswith("Street address"):
            streets.add((key, n))
        printed = _printed_for(row, _row_answers(key, int(n or 1)), street_field)
        box = expected.setdefault(row["full_name"], set())
        if printed is not None:
            box.add(printed)
    assert {name: shows[name] for name in expected} == expected


# ── Schedule A/B's lists, labelled lines and shared boxes (3b spec §5, §8.3) ─────


def test_a_savings_account_prints_on_17_3_not_17_1(filer):
    # The form prints 17.1 and 17.2 as checking: filling by position would swear a savings
    # account is a checking account.
    _ab_row(filer, "17", "85.00", "Prairie Line Credit Union", kind="savings")

    shows, _, _ = _ab_drawn(filer)

    assert shows["Check 17"] == {"/yes"}
    assert shows["17.1 Checking account"] == set()
    assert shows["17.1 Checking amount"] == set()
    assert shows["17.3 Checking account"] == {"Prairie Line Credit Union"}
    assert shows["17.3 Checking amount"] == {"85.00"}


def test_a_third_checking_account_goes_on_a_sheet_numbered_17c_3_and_counts_in_line_36(filer):
    # "17c" keeps it from colliding with the form's own 17.3, a savings account.
    for n in range(1, 4):
        _ab_row(filer, "17", f"{n}00.00", f"Bank {n}", kind="checking")

    shows, parts, pdf = _ab_drawn(filer)

    assert shows["17.2 Checking account"] == {"Bank 2"}
    assert shows["17.3 Checking account"] == set()
    assert _ab_sheet_rows(parts, pdf) == (("17c.3", "Bank 3", "300.00"),)
    (part,) = [part for part in parts["parts"] if part["kind"] == "sheet"]
    assert part["title"] == (
        "Official Form 106A/B, Schedule A/B: Property, line 17, checking accounts"
    )
    assert shows["undefined_124"] == {"600.00"}


def test_a_second_401k_goes_on_a_sheet_and_additional_stays_the_filer_s_choice(filer):
    # A row keeps its stated kind, so it never moves into "Additional account" on its own.
    _ab_row(filer, "21", "100.00", "First Plan", kind="401k")
    _ab_row(filer, "21", "200.00", "Second Plan", kind="401k")

    shows, parts, pdf = _ab_drawn(filer)

    assert shows["21.1 401k or similar plan"] == {"First Plan"}
    assert shows["21.6 Additional account"] == set()
    assert _ab_sheet_rows(parts, pdf) == (("21k.2", "Second Plan", "200.00"),)

    _ab_row(filer, "21", "300.00", "Third Plan", kind="additional")

    shows, _, _ = _ab_drawn(filer)

    assert shows["21.6 Additional account"] == {"Third Plan"}
    assert shows["21.6 Additional account amount"] == {"300.00"}


def test_line_19_prints_entity_share_and_value(filer):
    # The template prints the "%" itself, so the box takes the number alone.
    _ab_row(filer, "19", "500.00", "Corner Shop LLC", percent="25")

    shows, _, _ = _ab_drawn(filer)

    assert shows["check 19"] == {"/yes"}
    assert shows["19.1 Name of entity"] == {"Corner Shop LLC"}
    assert shows["19.1 % of ownership"] == {"25"}
    assert shows["19.1 amount"] == {"500.00"}


def test_each_of_line_24_s_three_rows_prints_in_its_own_box(filer):
    # The template gives rows 1 and 3 one name, and row 2's text and amount another: by name
    # alone, a row's words would print on two rows, or its amount over its words.
    for n in range(1, 4):
        _ab_row(filer, "24", f"{n}00.00", f"Plan {n}")

    _, parts, pdf = _ab_drawn(filer)

    printed = {(w.page, w.tag): w.value for w in read_drawn("schedule_a_b", pdf, parts["parts"])}
    assert {tag: printed[(7, tag)] for tag in ("T5", "T6", "T7", "T8", "T9", "T10")} == {
        "T5": "Plan 1",
        "T6": "100.00",
        "T7": "Plan 2",
        "T8": "200.00",
        "T9": "Plan 3",
        "T10": "300.00",
    }


def test_line_31_prints_company_beneficiary_and_a_zero_value(filer):
    # A policy with no cash value is typed as $0: an answer, which prints, unlike an unknown value.
    _ab_row(filer, "31", "0", "Sample Mutual Life", beneficiary="Spouse")

    shows, _, _ = _ab_drawn(filer)

    assert shows["check 31"] == {"/yes"}
    assert shows["Company name 1"] == {"Sample Mutual Life"}
    assert shows["Beneficiary 1"] == {"Spouse"}
    assert shows["undefined_109"] == {"0.00"}
    assert shows["undefined_110"] == set()


def test_two_federal_refunds_add_up_and_their_texts_join(filer):
    # The form has one amount a kind and one text box, so two rows of a kind print one sum.
    _ab_row(filer, "28", "100.00", "2024 return filed", kind="federal")
    _ab_row(filer, "28", "50.00", "2025 return filed", kind="federal")

    shows, parts, _ = _ab_drawn(filer)

    assert shows["check 28"] == {"/On"}
    assert shows["28 Tax refunds owed"] == {"2024 return filed; 2025 return filed"}
    assert shows["28 Tax refunds owed amout1"] == {"150.00"}
    assert shows["28 Tax refunds owed amout2"] == set()
    assert [part for part in parts["parts"] if part["kind"] == "sheet"] == []


@pytest.mark.parametrize(
    ("values", "prints"),
    [
        ((None,), set()),
        (("0",), {"0.00"}),
        ((None, "40.00"), {"40.00"}),
    ],
    ids=["unknown_prints_blank", "a_typed_zero_prints", "an_unknown_adds_nothing"],
)
def test_a_shared_amount_adds_what_the_filer_knows(filer, values, prints):
    # A value the filer doesn't know prints blank and adds zero, never a figure nobody gave.
    for value in values:
        _ab_row(filer, "29", value, "Order of 2020", kind="support", value_unknown=value is None)

    shows, _, _ = _ab_drawn(filer)

    assert shows["29 Family support amount3"] == prints
    assert shows["29 Family support amount1"] == set()


def test_line_53_s_fourth_row_goes_on_a_sheet_with_its_text(filer):
    # The one text box prints the three rows beside the form's three amounts; a fourth row's
    # words stay beside its own value, on the sheet.
    for n in range(1, 5):
        _ab_row(filer, "53", f"{n}0.00", f"Item {n}")

    shows, parts, pdf = _ab_drawn(filer)

    assert shows["check 53"] == {"/On"}
    assert shows["53 Examples Season tickets country club membership"] == {"Item 1; Item 2; Item 3"}
    assert shows["undefined_155"] == {"10.00"}
    assert shows["undefined_156"] == {"20.00"}
    assert shows["undefined_157"] == {"30.00"}
    assert _ab_sheet_rows(parts, pdf) == (("53.4", "Item 4", "40.00"),)
    assert shows["undefined_158"] == {"100.00"}


@pytest.mark.parametrize(
    ("line", "details", "cells"),
    [
        ("18", {}, ("Spare", "5.00")),
        ("19", {"percent": "25"}, ("Spare", "25", "5.00")),
        ("20", {}, ("Spare", "5.00")),
        ("23", {}, ("Spare", "5.00")),
        ("24", {}, ("Spare", "5.00")),
        ("31", {"beneficiary": "Spouse"}, ("Spare", "Spouse", "5.00")),
        ("42", {"percent": "25"}, ("Spare", "25", "5.00")),
        ("44", {}, ("Spare", "5.00")),
    ],
    ids=lambda case: case if isinstance(case, str) else "",
)
def test_a_row_past_a_list_s_boxes_goes_on_a_sheet_with_every_answer(filer, line, details, cells):
    # The rows past a line's boxes go on an attached sheet, so nothing the filer gave is dropped.
    capacity = LINE_BY_KEY[line].capacity
    for n in range(1, capacity + 1):
        _ab_row(filer, line, "1.00", f"Row {n}", **details)
    _ab_row(filer, line, "5.00", "Spare", **details)

    _, parts, pdf = _ab_drawn(filer)

    assert _ab_sheet_rows(parts, pdf) == ((f"{line}.{capacity + 1}", *cells),)


def _sheeted_lists():
    """(line, kind, its slots) of every list that goes on a sheet past its slots."""
    for line in LINES:
        if line.shape == "gate" or line.key in ("28", "29"):
            continue
        for kind, capacity in line.kinds or ((None, line.capacity),):
            yield line.key, kind, capacity


@pytest.mark.parametrize(
    ("line", "kind", "capacity"),
    list(_sheeted_lists()),
    ids=lambda case: None if isinstance(case, int) else case,
)
def test_the_largest_amount_a_row_can_hold_prints_whole_on_every_sheet(filer, line, kind, capacity):
    # A word never wraps, so a column narrower than the widest amount refuses the whole form.
    details = {"kind": kind} if kind else {}
    for _ in range(capacity + 1):
        _ab_row(filer, line, "9999999999.99", "Words", "9999999999.99", **details)

    parts = resolve_parts(load_schema("schedule_a_b"), filer)

    (part,) = [part for part in parts["parts"] if part["kind"] == "sheet"]
    assert "9999999999.99" in part["rows"][0]["cells"]
    PDFFormFiller().check("schedule_a_b", parts)


def test_each_labelled_kind_has_its_own_sheet_number():
    # A row's number on a sheet names its kind, so it never reads as the form's own 17.3.
    groups = load_schema("schedule_a_b").groups
    numbers = {name: group.number for name, group in groups.items() if name.count("_") >= 2}
    assert numbers == {
        "ab_17_checking": "17c.{n}",
        "ab_17_savings": "17s.{n}",
        "ab_17_cd": "17d.{n}",
        "ab_17_other": "17o.{n}",
        "ab_21_401k": "21k.{n}",
        "ab_21_pension": "21p.{n}",
        "ab_21_ira": "21i.{n}",
        "ab_21_retirement": "21r.{n}",
        "ab_21_keogh": "21h.{n}",
        "ab_21_additional": "21a.{n}",
        "ab_22_electric": "22a.{n}",
        "ab_22_gas": "22b.{n}",
        "ab_22_heating_oil": "22c.{n}",
        "ab_22_security_deposit": "22d.{n}",
        "ab_22_prepaid_rent": "22e.{n}",
        "ab_22_telephone": "22f.{n}",
        "ab_22_water": "22g.{n}",
        "ab_22_rented_furniture": "22h.{n}",
        "ab_22_other": "22i.{n}",
    }
    template = load_schema("schedule_a_b").template_filename
    for name in numbers:
        assert fits_line_column(numbers[name].format(n=9999), template, 48), name


def test_a_letter_the_form_can_t_print_is_a_422_linking_to_assets(filer):
    # The refusal is the filer's only sign a row won't print, so it names the box and the step.
    _ab_row(filer, "18", "5.00", "Bad □ name")

    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("schedule_a_b", resolve_parts(load_schema("schedule_a_b"), filer))

    assert refused.value.label == "Line 18.1: Institution or issuer name"
    assert refused.value.step == "assets"


def test_a_letter_the_form_can_t_print_on_a_sheet_links_to_assets(filer):
    for n in range(1, 4):
        _ab_row(filer, "18", "5.00", f"Row {n}")
    _ab_row(filer, "18", "5.00", "Bad □ name")

    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("schedule_a_b", resolve_parts(load_schema("schedule_a_b"), filer))

    assert refused.value.label == "Institution or issuer name"
    assert refused.value.step == "assets"


@pytest.mark.parametrize(
    ("line", "kind", "label"),
    [
        ("18", None, "Line 18.1: Institution or issuer name"),
        ("28", "federal", "Line 28: Give specific information"),
        ("53", None, "Line 53: Give specific information"),
    ],
)
def test_a_description_too_long_for_its_box_is_a_422_linking_to_assets(filer, line, kind, label):
    # A row's text can be split with "Add another", so the refusal points to where to do that.
    details = {"kind": kind} if kind else {}
    _ab_row(filer, line, "5.00", "words " * 800, **details)

    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_a_b", resolve_parts(load_schema("schedule_a_b"), filer))

    assert refused.value.label == label
    assert refused.value.step == "assets"


# The words beside each labelled box → its kind (the form's 17.3 is named "17.3 Checking account").
_LABELLED_BOXES = {
    "Checking account": "checking",
    "Savings account": "savings",
    "Certificates of deposit": "cd",
    "Other financial account": "other",
    "401(k) or similar plan": "401k",
    "Pension plan": "pension",
    "IRA": "ira",
    "Retirement account": "retirement",
    "Keogh": "keogh",
    "Additional account": "additional",
    "Electric": "electric",
    "Gas": "gas",
    "Heating oil": "heating_oil",
    "Security deposit on rental unit": "security_deposit",
    "Prepaid rent": "prepaid_rent",
    "Telephone": "telephone",
    "Water": "water",
    "Rented furniture": "rented_furniture",
    "Other": "other",
}


def _box_role(row):
    """Which of a row's answers a box prints, from the words beside it."""
    if row["label"].startswith("% of ownership"):
        return "percent"
    if row["label"].startswith("Beneficiary"):
        return "beneficiary"
    return "value" if row["kind"] == "amount" else "description"


def _list_boxes():
    """{(line, kind, row): {role: (page, tag)}}, each column of boxes read down the page."""
    index = json.loads((settings.FORM_INDEX_DIRECTORY / "form_b106ab.index.json").read_text())
    columns = {}
    shapes = ("named", "named_share", "insurance", "labelled")
    for row in sorted(index, key=lambda r: (r["page"], r["rect"][1])):
        key = row["line"].rstrip(".").partition(".")[0]
        line = LINE_BY_KEY.get(key)
        if line is None or line.shape not in shapes or row["kind"] == "checkbox":
            continue
        kind = _LABELLED_BOXES[row["label"].rstrip(":").strip()] if line.kinds else None
        columns.setdefault((key, kind, _box_role(row)), []).append((row["page"], row["tag"]))
    boxes = {}
    for (key, kind, role), column in columns.items():
        for n, box in enumerate(column, start=1):
            boxes.setdefault((key, kind, n), {})[role] = box
    return boxes


def test_every_list_box_prints_its_own_answer_on_the_page(filer):
    # Every slot of every list, filled at once with answers of its own. The template's names don't
    # say which row a box is on (42.1's value is undefined_129, its share undefined_130), so the
    # row comes from where each box sits on the page.
    expected = {}
    for i, ((key, kind, _), boxes) in enumerate(_list_boxes().items(), start=1):
        answers = {"description": f"W{i}", "value": f"{i}.00", "percent": str(i)}
        answers["beneficiary"] = f"B{i}"
        expected |= {at: answers[role] for role, at in boxes.items()}
        details = {
            **({"kind": kind} if kind else {}),
            **({"percent": str(i)} if "percent" in boxes else {}),
            **({"beneficiary": f"B{i}"} if "beneficiary" in boxes else {}),
        }
        _ab_row(filer, key, answers["value"], answers["description"], **details)

    _, parts, pdf = _ab_drawn(filer)

    printed = {(w.page, w.tag): w.value for w in read_drawn("schedule_a_b", pdf, parts["parts"])}
    assert {at: printed[at] for at in expected} == expected
    assert [part for part in parts["parts"] if part["kind"] == "sheet"] == []
