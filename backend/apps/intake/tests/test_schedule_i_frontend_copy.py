"""
Steps 2 and 4 ask Schedule I's lines 1, 11 and 13 and Schedule J's line 24 in the browser and the
server judges them, so a few things are typed on both sides: the gap sentences Continue shows
(copy.ts, mirrored from schedule_i.py), the character caps and labels (scheduleILimits.ts and
copy.ts, from schedule_i.limits.json), the keys each step's body names (scheduleIGaps.ts) and the
forms' own words (formText.ts). A sentence worded differently on one side tells the filer one thing
on the step and another on Review; a key spelled differently makes every save of the step a 400.
"""

import json
import re

import pypdf
import pytest
from django.conf import settings

from apps.forms.services.answer_records import record_step
from apps.intake import schedule_i
from apps.intake.models import ScheduleIAnswers
from apps.intake.tests.test_petition_frontend_copy import (
    FRONTEND,
    PDFS,
    _copy_sentences,
    _form_text_strings,
    _numeric_record,
    _record_body,
)

LIMITS = settings.BASE_DIR.parent / "data" / "forms" / "schemas" / "schedule_i.limits.json"
SCHEDULE_I_DIR = FRONTEND / "components" / "wizard" / "steps" / "scheduleI"


@pytest.fixture(autouse=True)
def _frontend_is_here():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")


def _server_sentences(prefix: str) -> dict[str, str]:
    return {
        name: value
        for name, value in vars(schedule_i).items()
        if name.startswith(prefix) and isinstance(value, str)
    }


@pytest.mark.parametrize("kind", ["GATE_", "DETAIL_"])
def test_the_gate_and_detail_sentences_are_the_servers(kind):
    # Both directions: a sentence the server added and the browser lacks fails, and so does one
    # the browser keeps after the server dropped it. DETAIL_TOO_LONG is compared as a template.
    server = {f"SCHEDULE_I_{name}": text for name, text in _server_sentences(kind).items()}
    browser = _copy_sentences(f"SCHEDULE_I_{kind}")
    assert browser == server


def test_the_mirror_has_every_sentence_the_server_has_today():
    # 3 gates and 8 details (7 for line 1, 11, 13 and 24, and the too-long template), so a reader
    # that silently matched nothing can't pass the test above
    assert len(_server_sentences("GATE_")) == 3
    assert len(_server_sentences("DETAIL_")) == 8


def test_only_the_too_long_template_takes_placeholders():
    found = {
        name: set(re.findall(r"\{(\w+)\}", text))
        for kind in ("GATE_", "DETAIL_")
        for name, text in _server_sentences(kind).items()
        if "{" in text
    }
    assert found == {"DETAIL_TOO_LONG": {"label", "form"}}


def test_the_limits_are_the_servers():
    limits = json.loads(LIMITS.read_text())["limits"]
    path = FRONTEND / "constants" / "scheduleILimits.ts"
    assert _numeric_record(path, "SCHEDULE_I_TEXT_LIMITS") == limits
    assert limits == ScheduleIAnswers.TEXT_LIMITS
    assert set(limits) == set(ScheduleIAnswers.TEXT_KEYS)


# W18 of the owner's 2026-11-22 approval: yours, then the spouse's each starting "Your spouse's",
# then the three lines (PF-4c-E: the spouse's tenure label is the one that isn't a plain twin)
APPROVED_LABELS = {
    "occupation": "Occupation",
    "employer_name": "Employer's name",
    "employer_street": "Employer's address",
    "employer_street_2": "Employer's address, line 2",
    "employer_city": "Employer's city",
    "employer_state": "Employer's state",
    "employer_zip": "Employer's ZIP Code",
    "time_employed": "How long employed there",
    "spouse_occupation": "Your spouse's occupation",
    "spouse_employer_name": "Your spouse's employer's name",
    "spouse_employer_street": "Your spouse's employer's address",
    "spouse_employer_street_2": "Your spouse's employer's address, line 2",
    "spouse_employer_city": "Your spouse's employer's city",
    "spouse_employer_state": "Your spouse's employer's state",
    "spouse_employer_zip": "Your spouse's employer's ZIP Code",
    "spouse_time_employed": "How long your spouse has been employed there",
    "line_11_text": "Line 11, Specify",
    "line_13_text": "Line 13, Explain",
    "schedule_j_line_24_text": "Line 24, Explain",
}


def _quoted_record(path, name: str) -> dict[str, str]:
    """A record of plain keys to strings in either quote style (prettier writes one holding an
    apostrophe in double quotes), in order."""
    found = re.findall(
        r"^  (\w+):\s*(?:'([^'\n]*)'|\"([^\"\n]*)\"),$", _record_body(path, name), re.M
    )
    return {key: single or double for key, single, double in found}


def test_the_too_long_labels_are_the_approved_words():
    labels = json.loads(LIMITS.read_text())["labels"]
    assert labels == APPROVED_LABELS
    assert labels == ScheduleIAnswers.TEXT_LABELS
    browser = _quoted_record(FRONTEND / "constants" / "copy.ts", "SCHEDULE_I_TEXT_LABELS")
    assert browser == labels


def _key_list(name: str) -> list[str]:
    source = (SCHEDULE_I_DIR / "scheduleIGaps.ts").read_text()
    match = re.search(rf"^export const {name} = \[(.*?)\] as const;", source, re.M | re.S)
    assert match, f"scheduleIGaps.ts has no {name}"
    return re.findall(r"'(\w+)'", match.group(1))


def test_the_step_keys_split_the_record_by_step():
    # One wrong key is a 400 for the whole step's save, and a key in neither step is never saved
    step_2 = _key_list("STEP_2_SCHEDULE_I_KEYS")
    step_4 = _key_list("STEP_4_SCHEDULE_I_KEYS")
    assert step_2 + step_4 == [
        key for key in ScheduleIAnswers.KEYS if key in step_2 or key in step_4
    ]
    assert set(step_2) | set(step_4) == set(ScheduleIAnswers.KEYS)
    assert set(step_2) & set(step_4) == set()
    # schedule_j_* belong to the Expenses step alone, as the forms' own refusals link them
    assert step_4 and all(key.startswith("schedule_j_") for key in step_4)
    assert not any(key.startswith("schedule_j_") for key in step_2)
    assert {record_step(f"schedule_i.{key}") for key in step_2} == {"income_info"}
    assert {record_step(f"schedule_i.{key}") for key in step_4} == {"expense_info"}


def _squeezed(template: str, page: int) -> str:
    """One page's text layer with every space removed: the layer splits some words ("infor
    mation") and a quotation has to match it all the same."""
    return "".join(pypdf.PdfReader(PDFS / template).pages[page - 1].extract_text().split())


def _quote(name: str) -> str:
    (text,) = _form_text_strings(name)
    return "".join(text.split())


# Sentences, each found whole: after the end of a sentence or a line number, before a capital or
# an answer line (the check boxes the template draws from a private-use font count too)
SENTENCES = [
    ("FORM_106I_LINE_11", "form_b106i.pdf", 2),
    ("FORM_106I_LINE_13_QUESTION", "form_b106i.pdf", 2),
    ("FORM_106J_LINE_24_QUESTION", "form_b106j.pdf", 3),
    ("FORM_106J_LINE_24_EXAMPLE", "form_b106j.pdf", 3),
]
# Labels, found as printed
LABELS = [
    ("FORM_106I_COLUMN_YOU", "form_b106i.pdf", 1),
    ("FORM_106I_COLUMN_SPOUSE", "form_b106i.pdf", 1),
    ("FORM_106I_EMPLOYMENT_STATUS", "form_b106i.pdf", 1),
    ("FORM_106I_EMPLOYED", "form_b106i.pdf", 1),
    ("FORM_106I_NOT_EMPLOYED", "form_b106i.pdf", 1),
    ("FORM_106I_OCCUPATION", "form_b106i.pdf", 1),
    ("FORM_106I_EMPLOYER_NAME", "form_b106i.pdf", 1),
    ("FORM_106I_EMPLOYER_ADDRESS", "form_b106i.pdf", 1),
    ("FORM_106I_HOW_LONG", "form_b106i.pdf", 1),
    ("FORM_106I_LINE_11_BOX_LABEL", "form_b106i.pdf", 2),
]
NOTES = ("FORM_106I_LINE_1_NOTES", "form_b106i.pdf", 1)
# A question and the two answers printed after it, in this order
ANSWERS = [
    (
        "FORM_106I_LINE_13_QUESTION",
        "FORM_106I_LINE_13_NO",
        "FORM_106I_LINE_13_YES",
        "form_b106i.pdf",
        2,
    ),
    (
        "FORM_106J_LINE_24_EXAMPLE",
        "FORM_106J_LINE_24_NO",
        "FORM_106J_LINE_24_YES",
        "form_b106j.pdf",
        3,
    ),
]

WHOLE_BEFORE = re.compile(r"(?:^|[.?:\uf000-\uf8ff_])$")
WHOLE_AFTER = re.compile(r"^(?:$|[A-Z(\uf000-\uf8ff_])")


def _assert_whole(name: str, text: str, page_text: str, template: str, page: int):
    at = page_text.find(text)
    assert at >= 0, f"{name}: {text!r} is not on {template} page {page}"
    before, after = page_text[:at], page_text[at + len(text) :]
    assert WHOLE_BEFORE.search(before), f"{name} begins mid-sentence, after {before[-30:]!r}"
    assert WHOLE_AFTER.match(after), f"{name} stops mid-sentence, before {after[:30]!r}"


def test_every_schedule_i_and_j_quote_is_pinned():
    # A new quotation can't reach the steps unread against its template
    source = (FRONTEND / "constants" / "formText.ts").read_text()
    owned = re.findall(r"^export const (FORM_106[IJ]_\w+)\b", source, re.M)
    pinned = [name for name, _, _ in SENTENCES + LABELS] + [NOTES[0]]
    for _question, no, yes, _, _ in ANSWERS:
        pinned += [no, yes]
    assert sorted(owned) == sorted(set(pinned))


@pytest.mark.parametrize("name, template, page", SENTENCES)
def test_the_schedule_i_and_j_sentences_are_the_forms_own(name, template, page):
    _assert_whole(name, _quote(name), _squeezed(template, page), template, page)


def test_line_1_notes_are_the_forms_own():
    name, template, page = NOTES
    page_text = _squeezed(template, page)
    notes = _form_text_strings(name)
    assert len(notes) == 2
    for note in notes:
        _assert_whole(name, "".join(note.split()), page_text, template, page)


@pytest.mark.parametrize("name, template, page", LABELS)
def test_the_schedule_i_labels_are_the_forms_own(name, template, page):
    assert _quote(name) in _squeezed(template, page), f"{name} is not on {template} page {page}"


@pytest.mark.parametrize("question, no, yes, template, page", ANSWERS)
def test_the_yes_and_no_answers_follow_their_question_on_the_page(
    question, no, yes, template, page
):
    # "No." alone is on many pages; it is the form's own only as the question's first answer
    page_text = _squeezed(template, page)
    # The check boxes the template draws from a private-use font sit between the words
    glyphs = "[\uf000-\uf8ff]*"
    pattern = glyphs.join(re.escape(_quote(name)) for name in (question, no, yes))
    assert re.search(pattern, page_text), f"{no} and {yes} don't follow {question} on {template}"
