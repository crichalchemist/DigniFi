"""
Schedule C's boxes print the filer's exemption answers in the rows and columns the form labels.

Business intent: Schedule C is signed under oath, so a claim's law, amount or description must
land on its own row and in its own column, and nothing prints that the filer didn't answer. The
old law answer, one `answer:` binding on row 2's law box, is gone: every claim box now reads
the exemptions page (3g2 spec §6).
"""

import json
import re

from django.conf import settings

from apps.forms.schema import load_schema, page_number_keys
from apps.forms.services.widgets import template_widgets

COLUMN_BY_WORDS = {
    "Brief description:": "description",
    "Line from Schedule A/B:": "line",
    "Current value of the portion you own, $": "value",
    "Amount of the exemption you claim: check only one box": "amount_kind",
    "Amount of the exemption you claim: $ specific dollar amount": "amount",
    "Specific laws that allow exemption": "law",
}
LABEL = re.compile(r"^(?P<words>.*?) \((?P<page_2>Part 2 Additional Page )?row (?P<n>\d+)\)$")


def _index():
    path = settings.FORM_INDEX_DIRECTORY / "b_106c_0425-form.index.json"
    return json.loads(path.read_text())


def _labelled_boxes():
    """(row, column) of every index row the form labels with a row, read from its own words.
    Page 2's rows continue page 1's three."""
    boxes = {}
    for row in _index():
        match = LABEL.match(row["label"])
        if match:
            number = int(match["n"]) + (3 if match["page_2"] else 0)
            boxes.setdefault(row["full_name"], set()).add((number, COLUMN_BY_WORDS[match["words"]]))
    return boxes


def test_every_box_a_claim_prints_is_on_the_row_and_column_its_label_names():
    labelled = _labelled_boxes()
    bound = set()

    for f in load_schema("schedule_c").fields:
        if not f.binding or not f.binding.startswith("exemptions.claims[]."):
            continue
        # One name may be several widgets (the two amount boxes of a row): each must be its row's.
        assert labelled[f.pdf_field] == {(f.row, f.binding.rsplit(".", 1)[-1])}, f.pdf_field
        bound.add((f.row, f.binding.rsplit(".", 1)[-1]))

    all_labelled = {pair for pairs in labelled.values() for pair in pairs}
    assert len(bound) == 90
    assert all_labelled == bound


def test_every_exemptions_binding_is_the_filers_own_answer():
    # Nothing prints on Schedule C that the filer didn't give: no `answer:` binding, no rule but
    # the name and the district, and every exemptions box is asked and held for legal review.
    for f in load_schema("schedule_c").fields:
        if f.binding and f.binding.startswith("exemptions."):
            assert f.source == "asked", f.pdf_field
            assert f.legal_review is True, f.pdf_field
        else:
            assert f.binding is None, f.pdf_field
            assert f.rule in ("full_name", "district_name"), f.pdf_field


def test_every_box_schedule_c_draws_is_bound():
    # A box left unbound prints blank on a sworn form. Only Debtor 2's name, the case number
    # (both pages) and the amended-filing box stay out.
    schema = load_schema("schedule_c")
    names = {f.pdf_field for f in schema.fields if f.tag is None}
    tagged = {(f.pdf_field, f.tag) for f in schema.fields if f.tag is not None}
    page_boxes = page_number_keys(schema)
    assert page_boxes == {"page@1:T33", "page 2", "page@2:T88"}

    unbound = set()
    for w in template_widgets(schema.template_filename):
        if not w.drawn:
            continue
        if w.full_name in names or (w.full_name, w.tag) in tagged:
            continue
        if w.full_name in page_boxes or f"{w.full_name}@{w.page}:{w.tag}" in page_boxes:
            continue
        unbound.add((w.page, w.tag))

    assert unbound == {(1, "T2"), (1, "T4"), (2, "T2"), (1, "T5")}


def test_line_1_3_and_3_1_tick_the_box_the_filers_answer_names():
    by_name = {f.pdf_field: f for f in load_schema("schedule_c").fields}

    assert by_name["check 1"].binding == "exemptions.line_1"
    assert by_name["check 1"].choices == {
        "state_and_federal": "/state and federal",
        "federal": "/federal",
    }
    assert by_name["check 3"].binding == "exemptions.line_3"
    assert by_name["check 3"].choices == {"no": "/no", "yes": "/yes"}
    assert by_name["check 3-1"].binding == "exemptions.line_3_1"
    assert by_name["check 3-1"].choices == {"no": "/no", "yes": "/yes"}


def test_a_refusal_quotes_the_forms_own_words_for_the_box():
    # R13: a filer told a value is too long to fit must be told which box, in the form's words.
    fields = load_schema("schedule_c").fields
    words = {
        "description": "Brief description",
        "line": "Line from Schedule A/B",
        "value": "Current value of the portion you own",
        "amount_kind": "Amount of the exemption you claim",
        "amount": "Amount of the exemption you claim",
        "law": "Specific laws that allow exemption",
    }
    slots = [f for f in fields if f.repeat == "c_part_2"]

    assert len(slots) == 90
    for f in slots:
        assert f.label == "Exemption claim: " + words[f.binding.rsplit(".", 1)[-1]], f.pdf_field
    by_name = {f.pdf_field: f for f in fields}
    assert by_name["check 1"].label == "Which set of exemptions are you claiming?"
    assert by_name["check 3"].label == (
        "Are you claiming a homestead exemption of more than $214,000?"
    )
    assert by_name["check 3-1"].label == (
        "Did you acquire the property covered by the exemption within 1,215 days before you "
        "filed this case?"
    )
