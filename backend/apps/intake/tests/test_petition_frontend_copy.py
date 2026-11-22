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


def test_the_mirror_has_every_sentence_the_server_has_today():
    # The counts as petition.py holds them at Task 8 (10 gates, 16 details with 7c's row
    # template and owner ruling Q7's DETAIL_ITIN_NINE), so a reader that silently matched
    # nothing can't pass the test above
    assert len(_server_sentences("GATE_")) == 10
    assert len(_server_sentences("DETAIL_")) == 16


def test_the_row_nouns_the_browser_names_are_the_servers():
    assert _string_record(PETITION_DIR / "petitionGaps.ts", "PETITION_ROW_NOUNS") == (
        petition.ROW_NOUNS
    )


def test_each_text_box_stops_at_the_cap_the_server_measures():
    limits = json.loads(LIMITS.read_text())["limits"]
    path = FRONTEND / "constants" / "petitionLimits.ts"
    assert _numeric_record(path, "PETITION_TEXT_LIMITS") == limits
    assert limits == PetitionAnswers.TEXT_LIMITS


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


def _form_text_strings(name: str) -> list[str]:
    """A formText.ts constant: one string, or each string of an array or record, unescaped."""
    source = (FRONTEND / "constants" / "formText.ts").read_text()
    match = re.search(rf"^export const {name}\b[^=]*=\s*(.*?);$", source, re.M | re.S)
    assert match, f"formText.ts has no {name}"
    found = re.findall(r"'((?:[^'\\]|\\.)*)'", match.group(1))
    assert found, f"{name} holds no string"
    return [text.replace("\\'", "'") for text in found]


@pytest.mark.parametrize(
    "name, template, page",
    [
        ("FORM_101_LINE_11_RENT", "form_b101.pdf", 3),
        ("FORM_101_LINE_11_EVICTION", "form_b101.pdf", 3),
        ("FORM_101_LINE_11_NOTICE", "form_b101.pdf", 3),
        ("FORM_101_LINE_14", "form_b101.pdf", 4),
        ("FORM_101_LINE_14_EXAMPLE", "form_b101.pdf", 4),
        ("FORM_101_LINE_14_PROMPTS", "form_b101.pdf", 4),
        ("FORM_101A_SERVICE_SENTENCE", "form_b101a_0.pdf", 1),
        ("FORM_101A_SERVICE_CONDITIONS", "form_b101a_0.pdf", 1),
        ("FORM_101B_STAY_SENTENCE", "form_b101a_0.pdf", 1),
    ],
)
def test_the_eviction_and_hazard_words_are_the_forms_own(name, template, page):
    # Owner answer Q2: the Contracts & Leases notice quotes the forms and never a DigniFi summary
    # shown as theirs, so each sentence is found word for word on its template's page
    words = _page_words(template, page)
    for text in _form_text_strings(name):
        assert text in words, f"{name}: {text!r} is not on {template} page {page}"
