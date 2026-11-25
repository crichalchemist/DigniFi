"""
Form 108's schema (forms step 4e, R-SHAPE, 4e-R9).

Business intent: Form 108 prints the filer's own choices, each beside the creditor or lessor it
belongs to, ticks only a box the filer chose, and prints nothing the filer signs in ink. A row of
the form prints the row of the claims lists it names, so a swapped box would put a sworn choice
beside another creditor.
"""

import json
import re

from django.conf import settings

from apps.forms.checks import validate_form
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.services.widgets import template_widgets
from apps.forms.tests.pdf_readback import read_drawn

ROOT = settings.BASE_DIR.parent
INDEX = ROOT / "data/forms/field_index/form_b108.index.json"
LIMITS = ROOT / "data/forms/schemas/form_108.limits.json"
TEMPLATE = "form_b108.pdf"

INTENTIONS = {
    "surrender": "/surrender",
    "retain_redeem": "/retain and redeem",
    "retain_reaffirm": "/retain and reaffirmation",
    "retain_explain": "/retain and explain",
}
YES_NO = {"no": "/no", "yes": "/yes"}
# Schedule D's row 4 property box, 196.2 × 26.5 pt and one line (F5), as the tool measures it.
PINNED_D_PROPERTY_CAP = 57


def _fields():
    return load_schema("form_108").fields


def test_every_binding_is_asked_and_never_legal_review():
    fields = _fields()
    claims = [f for f in fields if f.binding]

    assert len(fields) == 47
    assert {f.rule for f in fields if not f.binding} == {"full_name", "district_name"}
    # An asked answer prints as stored; a legal_review box outside ANSWER_BOX_RULES would print
    # blank whatever the filer chose.
    assert all(f.binding.startswith("claims.") for f in claims)
    assert all(f.source == "asked" and not f.legal_review for f in claims)
    assert all(not f.legal_review for f in fields)


def test_the_header_name_fills_both_pages():
    (name,) = [f for f in _fields() if f.pdf_field == "Debtor 1"]
    assert name.tag is None and name.rule == "full_name"

    drawn = read_drawn("form_108", PDFFormFiller().fill("form_108", {"Debtor 1": "Demo Q Filer"}))

    assert sorted((w.page, w.value) for w in drawn if w.full_name == "Debtor 1") == [
        (1, "Demo Q Filer"),
        (2, "Demo Q Filer"),
    ]


def test_the_seven_signing_and_case_boxes_stay_unbound():
    bound = {f.pdf_field for f in _fields()}
    unbound = {
        "Debtor 2",
        "Case number",
        "Check if this is an",
        "Signature of Debtor 1",
        "Signature of Debtor 2",
        "Date signed Debtor 1",
        "Date signed Debtor 2",
    }
    names = {w.full_name for w in template_widgets(TEMPLATE)}

    assert unbound <= names
    assert bound & unbound == set()


def test_each_choice_maps_to_its_own_box_state():
    widgets = template_widgets(TEMPLATE)
    states = {}
    for w in widgets:
        states.setdefault(w.full_name, set()).update(w.states)
    fields = _fields()

    for row in "abcd":
        (intention,) = [f for f in fields if f.pdf_field == f"check1 1{row}"]
        (exempt,) = [f for f in fields if f.pdf_field == f"check2 1{row}"]
        assert intention.choices == INTENTIONS
        assert exempt.choices == YES_NO
        assert set(INTENTIONS.values()) == states[f"check1 1{row}"]
        assert set(YES_NO.values()) == states[f"check2 1{row}"]
    for row in "abcdefg":
        (assumed,) = [f for f in fields if f.pdf_field == f"check2{row}"]
        assert assumed.choices == YES_NO
        assert set(YES_NO.values()) == states[f"check2{row}"]
    # No answer DigniFi stores outside the form's choices, "undecided" above all, has a state.
    for f in fields:
        if f.type == "checkbox":
            assert "undecided" not in f.choices


def test_the_sheet_groups_print_every_slot_column():
    schema = load_schema("form_108")
    part_1, part_2 = schema.groups["f108_part_1"], schema.groups["f108_part_2"]

    assert part_1.number == "1.{n}"
    assert part_2.number == "2.{n}"
    assert [c.binding for c in part_1.sheet.columns] == [
        "claims.secured[].name",
        "claims.secured[].property",
        "claims.secured[].intention",
        "claims.secured[].explain",
        "claims.secured[].exempt",
    ]
    assert part_1.sheet.columns[3].covers == (
        "claims.secured[].explain_1",
        "claims.secured[].explain_2",
    )
    assert [c.binding for c in part_2.sheet.columns] == [
        "claims.leases[].name",
        "claims.leases[].purpose",
        "claims.leases[].assumed",
    ]
    capacities = {
        f.repeat: (f.repeat_capacity, sorted({f.row for f in schema.fields if f.repeat == g}))
        for g in ("f108_part_1", "f108_part_2")
        for f in schema.fields
        if f.repeat == g
    }
    assert capacities == {"f108_part_1": (4, [1, 2, 3, 4]), "f108_part_2": (7, list(range(1, 8)))}
    # forms.E007 measures every column's width and label, and that each slot prints in one.
    assert validate_form("form_108") == []


def test_each_part_1_rows_boxes_carry_that_rows_letter():
    # T3-H1: the index names each box by its label's row letter; a box whose rectangle was read
    # from another row would print a sworn choice beside another creditor.
    index = json.loads(INDEX.read_text())
    part_1 = [r for r in index if r["label"].startswith("Part 1, row ")]
    names = re.compile(
        r"(?:Creditors Name|PropertyDescription|check1|check2|Explain1|Explain2) 1([a-d])"
    )

    assert len(part_1) == 4 * 10  # name, description, four intentions, two exempt, two Explain
    for row in part_1:
        letter = row["label"][len("Part 1, row ")]
        match = names.fullmatch(row["full_name"])
        assert match, row["full_name"]
        assert match[1] == letter, (row["label"], row["full_name"])


def test_the_caps_name_the_boxes_each_text_prints_in_and_their_labels():
    limits = json.loads(LIMITS.read_text())

    assert set(limits["boxes"]) == {
        "form_108:claims.secured[].name",
        "schedule_d:claims.secured[].name",
        "schedule_e_f:claims.priority[].name",
        "schedule_e_f:claims.unsecured[].name",
        "form_108:claims.secured[].property",
        "schedule_d:claims.secured[].property",
        "schedule_g:claims.contracts[].name",
        "form_108:claims.leases[].name",
        "schedule_g:claims.contracts[].purpose",
        "form_108:claims.leases[].purpose",
        "form_108:explain",
    }
    assert limits["labels"] == {
        "creditor_name": "the creditor's name",
        "collateral_description": "the description of the property",
        "counterparty_name": "the lessor's name",
        "description": "the description of the leased property",
        "explain": "the explanation of your plan",
    }
    # F5: Schedule D's row 4 property box is one line, so its narrow one-line cap governs.
    assert limits["boxes"]["schedule_d:claims.secured[].property"] == PINNED_D_PROPERTY_CAP
    # 4e-R5: DeShawn's words are 59 characters; a cap under that flags a persona's own words.
    assert limits["boxes"]["form_108:explain"] >= 59
