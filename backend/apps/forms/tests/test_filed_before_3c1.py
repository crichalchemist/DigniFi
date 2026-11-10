"""
A form filed before 3c1 prints what was filed (3c spec §5.5): its page numbers and totals are
stored in its parts, and neither check() nor fill() works them out again, whatever the schema says
now. The document below is what the engine stored before 3c1, written out by hand, so it can't
move with the engine.
"""

import copy
import json
import shutil

import pytest
from django.conf import settings as django_settings

from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.forms.tests.pdf_readback import read_drawn

FILED = {
    "version": 2,
    "parts": [
        {
            "kind": "form",
            "values": {
                "Debtor 1": "Maria Torres",
                "Creditors Name": "First Creditor",
                "undefined": "100.00",
                "Creditors Name_3": "Third Creditor",
                "undefined_10": "300.00",
                "undefined_12": "2.3",
                "undefined_24": "0.00",
                "fill_27.0": "4",
                "fill_27.1.0": "2",
                "fill_27.1.1": "4",
                "fill_28.1.1": "4",
                "fill_28.1.2": "4",
            },
        },
        {
            "kind": "copy",
            "page": 2,
            "number": 1,
            "values": {
                "Debtor 1": "Maria Torres",
                "Creditors Name_3": "Sixth Creditor",
                "undefined_10": "600.00",
                "undefined_12": "2.6",
                "fill_27.1.0": "3",
                "fill_27.1.1": "4",
            },
        },
    ],
}
PRINTED = {
    (1, None, "Creditors Name"): "First Creditor",
    (1, None, "fill_27.0"): "4",
    (1, None, "undefined_9"): "",
    (2, None, "Creditors Name_3"): "Third Creditor",
    (2, None, "undefined_10"): "300.00",
    (2, None, "undefined_12"): "2.3",
    (2, None, "undefined_23"): "",
    (2, None, "undefined_24"): "0.00",
    (2, None, "fill_27.1.0"): "2",
    (2, None, "fill_27.1.1"): "4",
    (2, 1, "Creditors Name_3"): "Sixth Creditor",
    (2, 1, "undefined_10"): "600.00",
    (2, 1, "undefined_12"): "2.6",
    (2, 1, "undefined_23"): "",
    (2, 1, "undefined_24"): "",
    (2, 1, "fill_27.1.0"): "3",
    (2, 1, "fill_27.1.1"): "4",
    (3, None, "fill_28.1.1"): "4",
    (3, None, "fill_28.1.2"): "4",
}
NAMES = {name for _, _, name in PRINTED}


def _printed(values):
    pdf = PDFFormFiller().fill("schedule_d", values)
    parts = values.get("parts", [])
    return {
        (w.page, w.copy, w.full_name): w.value
        for w in read_drawn("schedule_d", pdf, parts)
        if w.full_name in NAMES
    }


@pytest.mark.slow
def test_a_filed_form_with_copies_redraws_as_it_was_filed():
    assert _printed(FILED) == PRINTED


@pytest.mark.slow
def test_a_form_filed_before_parts_existed_redraws_as_it_was_filed():
    flat = {"Debtor 1": "Maria Torres", "undefined_24": "1500.00"}
    printed = _printed(flat)
    assert printed[(2, None, "undefined_24")] == "1500.00"
    assert printed[(2, None, "undefined_23")] == ""


@pytest.mark.slow
def test_a_filed_form_ignores_totals_the_schema_declares_later(schedule_d_with_totals):
    # undefined_24 still prints the stored 0.00 on page 2, and no total appears anywhere else.
    assert _printed(FILED) == PRINTED


@pytest.mark.slow
def test_a_filed_form_prints_its_stored_page_numbers_whatever_the_schema_counts(
    schedule_d_with_two_groups,
):
    # The schema declares the form's page_numbers, and a recompute would print "4" in each box.
    filed = copy.deepcopy(FILED)
    form, page_copy = filed["parts"]
    for name in ("fill_27.0", "fill_27.1.1", "fill_28.1.2"):
        form["values"][name] = "9"
    page_copy["values"]["fill_27.1.1"] = "9"

    printed = _printed(filed)

    assert printed[(1, None, "fill_27.0")] == "9"
    assert printed[(2, None, "fill_27.1.1")] == "9"
    assert printed[(2, 1, "fill_27.1.1")] == "9"
    assert printed[(3, None, "fill_28.1.2")] == "9"


@pytest.fixture
def schedule_g_without_number_boxes(tmp_path, settings):
    """A copy of the real schemas whose Schedule G declares no number box in any group."""
    shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, tmp_path / "schemas")
    path = tmp_path / "schemas" / "schedule_g.json"
    data = json.loads(path.read_text())
    for group in data.get("groups", {}).values():
        group.pop("number_boxes", None)
    path.write_text(json.dumps(data))
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path / "schemas"
    load_schema.cache_clear()
    yield
    load_schema.cache_clear()


def _g_filed(number_boxes=None):
    part = {"kind": "form", "values": {"fill 2.10": "10"}}
    if number_boxes is not None:
        part["number_boxes"] = number_boxes
    return {"version": 2, "parts": [part]}


def test_a_filed_number_keeps_its_room_after_the_schema_drops_its_box(
    schedule_g_without_number_boxes,
):
    # The part stored the box that took room, so a later schema can't take the room back.
    filed = _g_filed(["fill 2.10"])

    (part,) = PDFFormFiller().check("schedule_g", filed)
    assert [(p.value, p.size) for p in part.widgets] == [("10", 10.0)]

    pdf = PDFFormFiller().fill("schedule_g", filed)
    drawn = {w.full_name: w.value for w in read_drawn("schedule_g", pdf, filed["parts"])}
    assert drawn["fill 2.10"] == "10"


def test_a_copy_gets_the_room_its_own_part_stored(schedule_g_without_number_boxes):
    # Each part's own number_boxes decide: the form part's room is not the copy's.
    def document(copy_boxes):
        copy_part = {"kind": "copy", "page": 2, "number": 1, "values": {"fill 2.6": "14"}}
        if copy_boxes is not None:
            copy_part["number_boxes"] = copy_boxes
        form_part = {"kind": "form", "values": {"fill 2.10": "10"}, "number_boxes": ["fill 2.10"]}
        return {"version": 2, "parts": [form_part, copy_part]}

    with pytest.raises(ValueTooLong):
        PDFFormFiller().check("schedule_g", document(None))

    _, copy_plan = PDFFormFiller().check("schedule_g", document(["fill 2.6"]))
    assert [p.value for p in copy_plan.widgets] == ["14"]


def test_a_part_with_no_stored_number_boxes_gets_no_room():
    # A part, not the schema, decides: "fill 2.10" holds one letter (/MaxLen 1).
    with pytest.raises(ValueTooLong):
        PDFFormFiller().check("schedule_g", _g_filed())
