"""
Step 1 asks Form 101's questions in the browser and the server judges them, so a few things are
typed on both sides: the gap sentences Continue shows (copy.ts, mirrored from petition.py), the
character caps the boxes stop at (petitionLimits.ts, from form_101.limits.json), the keys the
step's body names (IntakeWizard.tsx), the choices it offers and the form's revision it names
(formText.ts). A sentence worded differently on one side tells the filer one thing on step 1 and
another on Review; a key or choice spelled differently makes every step 1 save a 400.
"""

import json
import re

import pypdf
import pytest
from django.conf import settings

from apps.forms.services.answer_records import PETITION_STEP_OF_KEY
from apps.intake import petition
from apps.intake.models import PetitionAnswers

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"
LIMITS = settings.BASE_DIR.parent / "data" / "forms" / "schemas" / "form_101.limits.json"
LIMITS_101A = settings.BASE_DIR.parent / "data" / "forms" / "schemas" / "form_101a.limits.json"
TEMPLATE = settings.BASE_DIR.parent / "data" / "forms" / "pdfs" / "form_b101.pdf"
PETITION_DIR = FRONTEND / "components" / "wizard" / "steps" / "petition"


@pytest.fixture(autouse=True)
def _frontend_is_here():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")


def _record_body(path, name: str) -> str:
    """The body of one `export const NAME … = {` record, between its braces."""
    match = re.search(
        rf"^export const {name}\b[^\n]*= \{{\n(.*?)^\}};", path.read_text(), re.M | re.S
    )
    assert match, f"{path.name} has no {name}"
    return match.group(1)


def _string_record(path, name: str) -> dict[str, str]:
    """A record of plain keys to single-quoted strings, in order."""
    return dict(re.findall(r"^  (\w+): '([^'\n]+)',$", _record_body(path, name), re.M))


def _numeric_record(path, name: str) -> dict[str, int]:
    """A record of plain keys to whole numbers, in order (E-7: `_keys` reads only strings)."""
    pairs = re.findall(r"^  (\w+): (\d+),$", _record_body(path, name), re.M)
    return {key: int(value) for key, value in pairs}


def _copy_sentences(prefix: str) -> dict[str, str]:
    """Every `export const <prefix>…` string in copy.ts, single- or double-quoted."""
    source = (FRONTEND / "constants" / "copy.ts").read_text()
    found = re.findall(rf"^export const ({prefix}\w+) =\s*(['\"])(.*?)\2;", source, re.M | re.S)
    return {name: text for name, _, text in found}


def _server_sentences(prefix: str) -> dict[str, str]:
    return {
        name: value
        for name, value in vars(petition).items()
        if name.startswith(prefix) and isinstance(value, str)
    }


@pytest.mark.parametrize("kind", ["GATE_", "DETAIL_"])
def test_every_petition_sentence_the_browser_shows_is_the_servers(kind):
    # Both directions (PF2-T8-2): a sentence the server added and the browser lacks fails, and so
    # does one the browser keeps after the server dropped it. DETAIL_TOO_LONG and
    # DETAIL_TOO_LONG_ROW are compared as templates (F-16, owner ruling Q5).
    server = {f"PETITION_{name}": text for name, text in _server_sentences(kind).items()}
    browser = _copy_sentences(f"PETITION_{kind}")
    assert browser == server


def test_only_the_too_long_templates_take_placeholders_and_each_only_its_own():
    # The server fills these in and the browser compares the templates (F-16): {label} in both
    # text templates (Form 101's and, 4b2-R3, Form 101A's), {noun} and {n} for the row (owner
    # ruling Q5), and {forms}, the forms whose box refuses the row's cell (owner ruling Q10).
    found = {
        name: set(re.findall(r"\{(\w+)\}", text))
        for kind in ("GATE_", "DETAIL_")
        for name, text in _server_sentences(kind).items()
        if "{" in text
    }
    assert found == {
        "DETAIL_TOO_LONG": {"label"},
        "DETAIL_TOO_LONG_101A": {"label"},
        "DETAIL_TOO_LONG_ROW": {"label", "noun", "n", "forms"},
    }


def test_the_mirror_has_every_sentence_the_server_has_today():
    # The counts as petition.py holds them after 4b2 (10 gates, 18 details: 16 as 4b-ii left
    # them, with 7c's row template and owner ruling Q7's DETAIL_ITIN_NINE, plus the landlord's
    # detail and Form 101A's too-long template), so a reader that silently matched nothing can't
    # pass the test above
    assert len(_server_sentences("GATE_")) == 10
    assert len(_server_sentences("DETAIL_")) == 18


def test_the_row_nouns_the_browser_names_are_the_servers():
    assert _string_record(PETITION_DIR / "petitionGaps.ts", "PETITION_ROW_NOUNS") == (
        petition.ROW_NOUNS
    )


def test_each_text_box_stops_at_the_cap_the_server_measures():
    # The union of both forms' caps (4b2-R1): Form 101's file and Form 101A's.
    limits = (
        json.loads(LIMITS.read_text())["limits"] | json.loads(LIMITS_101A.read_text())["limits"]
    )
    path = FRONTEND / "constants" / "petitionLimits.ts"
    assert _numeric_record(path, "PETITION_TEXT_LIMITS") == limits
    assert limits == PetitionAnswers.TEXT_LIMITS


def test_no_key_has_a_cap_in_both_limits_files():
    # A key measured on two forms' boxes would have two caps and one record (4b2-R1).
    first = set(json.loads(LIMITS.read_text())["limits"])
    second = set(json.loads(LIMITS_101A.read_text())["limits"])
    assert first and second
    assert first & second == set()


def test_a_row_cell_stops_at_the_servers_ceiling():
    # PF2-10b: no per-cell cap; a cell stops where the server stops storing text
    text = (FRONTEND / "constants" / "petitionLimits.ts").read_text()
    match = re.search(r"^export const PETITION_ROW_CELL_MAX_LENGTH = (\d+);$", text, re.M)
    assert match, "petitionLimits.ts has no PETITION_ROW_CELL_MAX_LENGTH"
    assert int(match.group(1)) == PetitionAnswers.TEXT_CEILING == 500


def _record_keys(path, name: str) -> list[str]:
    """A record's plain keys, in order, whatever their values (prettier wraps a long one)."""
    return re.findall(r"^  (\w+):", _record_body(path, name), re.M)


def test_the_choices_step_1_offers_are_the_servers():
    form_text = FRONTEND / "constants" / "formText.ts"
    assert _record_keys(form_text, "FORM_101_BUSINESS_KINDS") == list(
        PetitionAnswers.CHOICE_KEYS["business_kind"]
    )
    assert _record_keys(form_text, "FORM_101_VENUE_CHOICES") == list(
        PetitionAnswers.CHOICE_KEYS["venue_choice"]
    )


def test_the_step_1_body_names_exactly_the_keys_step_1_asks():
    # One wrong key is a 400 for the whole step 1 save. The secrets go only when typed.
    source = (FRONTEND / "pages" / "IntakeWizard.tsx").read_text()
    match = re.search(r"^const STEP_1_PETITION_KEYS = \[\n(.*?)^\] as const;", source, re.M | re.S)
    assert match, "IntakeWizard.tsx has no STEP_1_PETITION_KEYS"
    keys = re.findall(r"^  '(\w+)',$", match.group(1), re.M)
    assert keys == [
        key
        for key, step in PETITION_STEP_OF_KEY.items()
        if step == "debtor_info" and key not in PetitionAnswers.SECRET_KEYS
    ]


def test_the_revision_the_wizard_names_is_the_one_the_template_prints():
    # 4b-R9, PF2-11: the whole record, against the edition mark on page 1's title line
    page = pypdf.PdfReader(TEMPLATE).pages[0].extract_text()
    mark = re.search(
        r"^Voluntary Petition for Individuals Filing for Bankruptcy (\d{2}/\d{2}) *$", page, re.M
    )
    assert mark, "page 1 has no title line with an edition mark"
    form_text = FRONTEND / "constants" / "formText.ts"
    assert _string_record(form_text, "FORM_REVISIONS") == {"form_101": mark.group(1)}


PDFS = settings.BASE_DIR.parent / "data" / "forms" / "pdfs"


def _page_words(template: str, page: int) -> str:
    """One page's text layer with its line breaks and runs of spaces read as one space."""
    return " ".join(pypdf.PdfReader(PDFS / template).pages[page - 1].extract_text().split())


FORM_TEXT_STRING = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"")


def _form_text_strings(name: str) -> list[str]:
    """A formText.ts constant: one string, or each string of an array or record, unescaped.

    Either quote style (prettier writes a string holding an apostrophe in double quotes), and
    nothing quoted left unread, so a string this reader can't parse fails instead of going
    unchecked."""
    source = (FRONTEND / "constants" / "formText.ts").read_text()
    match = re.search(rf"^export const {name}\b[^=]*=\s*(.*?);$", source, re.M | re.S)
    assert match, f"formText.ts has no {name}"
    found = FORM_TEXT_STRING.findall(match.group(1))
    assert found, f"{name} holds no string"
    rest = FORM_TEXT_STRING.sub("", match.group(1))
    assert not re.search(r"['\"`]", rest), f"{name} holds a string this test can't read: {rest!r}"
    return [(single or double).replace("\\'", "'").replace('\\"', '"') for single, double in found]


# The eviction and hazard quotes this test owns: every formText.ts constant with one of these
# prefixes is a quotation and must be listed below
OWNED_PREFIXES = re.compile(r"^export const (FORM_101_LINE_1[14]\w*|FORM_101[AB]_\w*)\b", re.M)

QUOTES = [
    ("FORM_101_LINE_11_RENT", "form_b101.pdf", 3),
    ("FORM_101_LINE_11_EVICTION", "form_b101.pdf", 3),
    ("FORM_101_LINE_11_NOTICE", "form_b101.pdf", 3),
    ("FORM_101_LINE_14", "form_b101.pdf", 4),
    ("FORM_101_LINE_14_EXAMPLE", "form_b101.pdf", 4),
    ("FORM_101_LINE_14_PROMPTS", "form_b101.pdf", 4),
    ("FORM_101A_SERVICE_SENTENCE", "form_b101a_0.pdf", 1),
    ("FORM_101A_SERVICE_CONDITIONS", "form_b101a_0.pdf", 1),
    ("FORM_101A_CERTIFICATION_HEADING", "form_b101a_0.pdf", 1),
    ("FORM_101A_CERTIFICATION_SENTENCE", "form_b101a_0.pdf", 1),
    ("FORM_101A_CERTIFICATION_BOX_1", "form_b101a_0.pdf", 1),
    ("FORM_101A_CERTIFICATION_BOX_2", "form_b101a_0.pdf", 1),
    ("FORM_101A_STAY_HEADING_A", "form_b101a_0.pdf", 1),
    ("FORM_101A_STAY_SENTENCE_A", "form_b101a_0.pdf", 1),
    ("FORM_101A_STAY_HEADING_B", "form_b101a_0.pdf", 1),
    ("FORM_101B_STAY_SENTENCE", "form_b101a_0.pdf", 1),
]

# What may sit on either side of a whole quotation on the page: the page's edge; before it, the end
# of a sentence, a line number ("11.") or an edition mark ("12/15"), or a heading this test pins
# (HEADINGS: the certification's sentence follows its heading); after it, a capital starting a new
# sentence or a heading ("(b) Stay…"); on either side a check box or bullet glyph (the templates
# draw them from a private-use font, U+F000 to U+F8FF) or an answer line's underscores
WHOLE_BEFORE = re.compile(r"(?:^|[.?:\uf000-\uf8ff_]|\d{2}/\d{2})$")
WHOLE_AFTER = re.compile(r"^(?:$|[A-Z(\uf000-\uf8ff_])")

# Headings printed without a closing mark, each a quotation pinned above in its own right
HEADINGS = ("FORM_101A_CERTIFICATION_HEADING",)


def test_every_eviction_and_hazard_quote_is_pinned():
    # A new quotation can't reach the notice unread against its template
    source = (FRONTEND / "constants" / "formText.ts").read_text()
    assert sorted(OWNED_PREFIXES.findall(source)) == sorted(name for name, _, _ in QUOTES)


@pytest.mark.parametrize("name, template, page", QUOTES)
def test_the_eviction_and_hazard_words_are_the_forms_own(name, template, page):
    # Owner answer Q2: the Contracts & Leases notice quotes the forms and never a DigniFi summary
    # shown as theirs, so each sentence is found word for word on its template's page, and whole:
    # a quote cut short, or begun mid-sentence, would put words in the form's mouth
    words = _page_words(template, page)
    for text in _form_text_strings(name):
        at = words.find(text)
        assert at >= 0, f"{name}: {text!r} is not on {template} page {page}"
        before = words[:at].rstrip()
        after = words[at + len(text) :].lstrip()
        cut_start = f"{name}: {text[:40]!r}… begins mid-sentence, after {before[-40:]!r}"
        after_heading = any(
            before.endswith(heading) for h in HEADINGS for heading in _form_text_strings(h)
        )
        assert WHOLE_BEFORE.search(before) or after_heading, cut_start
        cut_end = f"{name}: …{text[-40:]!r} stops mid-sentence, before {after[:40]!r}"
        assert WHOLE_AFTER.match(after), cut_end
