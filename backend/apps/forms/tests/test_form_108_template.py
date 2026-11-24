"""
The court's Form 108 (Statement of Intention, 12/15) template and its index (forms step 4e).

Business intent: a filer's choice about each secured creditor and each lease prints in the
court's own boxes, so every one of the template's 83 widgets is indexed under the court's own
name by a tool that reads a hand table checked against the tagged render. A choice that lands in
the wrong row prints against the wrong creditor; a box the index misses can't be filled; and a
page whose bytes drifted is a form nobody checked.
"""

import hashlib
import importlib.util
import json
from collections import Counter

from django.conf import settings
from pypdf import PdfReader

ROOT = settings.BASE_DIR.parent
TOOL = ROOT / "data/forms/field_index/tools/build_form_108_index.py"
INDEX_DIR = ROOT / "data/forms/field_index"
PDF_DIR = ROOT / "data/forms/pdfs"
TEMPLATE = "form_b108.pdf"
INDEX = INDEX_DIR / "form_b108.index.json"


def _tool():
    spec = importlib.util.spec_from_file_location("build_form_108_index", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows():
    return json.loads(INDEX.read_text())


def _kids(name):
    return [row for row in _rows() if row["full_name"] == name]


def test_the_committed_index_is_the_tools_output():
    # The index is never hand-edited; the tool reads it off the committed template.
    tool = _tool()
    assert INDEX.read_text() == tool.dumps(tool.index_rows(PDF_DIR / TEMPLATE))


def test_the_template_is_the_12_15_revision_we_indexed():
    data = (PDF_DIR / TEMPLATE).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == "fe51d222d87f461b8695e3d9b7a061e768b2a75824511d167cfba736ca35e8fe"
    assert len(data) == 87667
    assert len(PdfReader(PDF_DIR / TEMPLATE).pages) == 2


def test_the_widget_counts_are_pinned():
    rows = _rows()
    assert len(rows) == 83
    assert Counter(row["type"] for row in rows) == Counter(
        {"Text": 39, "CheckBox": 39, "ComboBox": 1, "Button": 4}
    )
    assert Counter(row["page"] for row in rows) == Counter({1: 45, 2: 38})
    assert len({row["full_name"] for row in rows}) == 58


def test_tags_are_unique_per_page_and_labels_unique_overall():
    rows = _rows()
    tags = [(row["page"], row["tag"]) for row in rows]
    assert len(set(tags)) == len(tags)
    labels = [row["label"] for row in rows]
    assert len(set(labels)) == len(labels)
    assert all(label for label in labels)


def test_the_buttons_are_form_controls_and_every_other_row_adjudicated():
    for row in _rows():
        expected = "form_control" if row["type"] == "Button" else "adjudicated"
        assert row["basis"] == expected, row["label"]


def test_every_checkbox_kid_carries_the_forms_words():
    # The words printed beside each box, so a sheet or a reader never has to guess which kid of a
    # shared name a state belongs to.
    intention = {
        "surrender": "Surrender the property.",
        "retain#20and#20redeem": "Retain the property and redeem it.",
        "retain#20and#20reaffirmation": (
            "Retain the property and enter into a Reaffirmation Agreement."
        ),
        "retain#20and#20explain": "Retain the property and [explain]:",
    }
    boxes = [row for row in _rows() if row["type"] == "CheckBox"]
    assert len(boxes) == 39
    seen = Counter()
    for row in boxes:
        name = row["full_name"]
        if name.startswith("check1 1"):
            assert row["option_text"] == intention[row["on_state"]], row["label"]
        elif name.startswith("check2 1"):
            assert row["option_text"] == {"no": "No", "yes": "Yes"}[row["on_state"]]
        elif name.startswith("check2") and name[6:].isalpha():
            assert row["option_text"] == {"no": "No", "yes": "Yes"}[row["on_state"]]
        else:
            assert name == "Check if this is an"
            assert row["option_text"] == "Check if this is an amended filing"
        seen[row["option_text"]] += 1
    # 4 rows x (4 intentions + No + Yes) + 7 leases x (No + Yes) + the amended box
    assert seen["Surrender the property."] == 4
    assert seen["No"] == 11
    assert seen["Yes"] == 11


def test_check2_1a_and_check2a_are_different_fields():
    # A trap: the two names differ by one space. `check2 1a` is Part 1's "claimed as exempt"
    # pair; `check2a` is Part 2's "will the lease be assumed" pair. A cell that took one for the
    # other would print an exemption answer on a lease.
    exempt, lease = _kids("check2 1a"), _kids("check2a")
    assert [(r["page"], r["on_state"]) for r in exempt] == [(1, "no"), (1, "yes")]
    assert [(r["page"], r["on_state"]) for r in lease] == [(2, "no"), (2, "yes")]
    assert all("Schedule C" in r["label"] for r in exempt)
    assert all("lease" in r["label"] for r in lease)


def test_row_2d_is_keyed_by_rectangle_not_widget_order():
    # A trap: row d's boxes do not sit in the order rows a-c do. On Part 1, the Yes box sits above
    # the redeem box in row d and the other way round in rows a-c, so reading order flips their
    # tags. Part 2's row d splits its words across two blocks. Each box is labelled by where it
    # is drawn, never by which comes next in the file.
    by_label = {row["label"]: row for row in _rows()}

    def box(part, letter, what):
        found = [
            r
            for label, r in by_label.items()
            if label.startswith(f"Part {part}, row {letter}: {what}")
        ]
        assert len(found) == 1, (part, letter, what)
        return found[0]

    for letter in "abcdefg":
        name = box(2, letter, "lessor's name")
        no = box(2, letter, "will the lease be assumed, No")
        yes = box(2, letter, "will the lease be assumed, Yes")
        desc = box(2, letter, "description of leased property")
        assert name["full_name"] == f"Lessors Name 2{letter}"
        assert (no["full_name"], yes["full_name"]) == (f"check2{letter}",) * 2
        assert desc["full_name"] == f"PropertyDescription 2{letter}"
        assert no["rect"][1] < yes["rect"][1] < desc["rect"][1]
        assert name["rect"][1] < no["rect"][1]
    redeem = box(1, "d", "intention, retain and redeem")
    yes = box(1, "d", "claimed as exempt on Schedule C, Yes")
    a_redeem = box(1, "a", "intention, retain and redeem")
    a_yes = box(1, "a", "claimed as exempt on Schedule C, Yes")
    assert yes["rect"][1] < redeem["rect"][1]
    assert a_redeem["rect"][1] > a_yes["rect"][1]
    assert (redeem["tag"], yes["tag"]) != (a_redeem["tag"], a_yes["tag"])


def test_explain1_and_explain2_are_the_two_boxes_of_one_line():
    # The explanation is one line that wraps: a short box after "[explain]:" and a long one on
    # the line below. Their widths decide how a long explanation is split.
    for letter in "abcd":
        (short,), (long_,) = _kids(f"Explain1 1{letter}"), _kids(f"Explain2 1{letter}")
        short_width = short["rect"][2] - short["rect"][0]
        long_width = long_["rect"][2] - long_["rect"][0]
        assert abs(short_width - 50.5) <= 0.1, letter
        assert abs(long_width - 169.7) <= 0.1, letter
        assert short["rect"][1] < long_["rect"][1]
        assert short["page"] == long_["page"] == 1
