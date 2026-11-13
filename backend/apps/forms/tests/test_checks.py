"""
A schema that disagrees with its template or field index stops the app from starting.

pytest-django runs no system checks, so these tests call the same
validate_form() the check uses (spec §5.4), on every registered form and on
deliberately broken copies of real schemas.
"""

import json
import shutil

import pypdf
import pytest
from django.conf import settings as django_settings
from django.core.management import call_command
from django.core.management.base import SystemCheckError

from apps.forms.checks import validate_form
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.intake.asset_lines import PROPERTY_KINDS


@pytest.fixture
def schema_copy(tmp_path, settings):
    """A writable copy of the real schemas; edit one, then validate it."""
    shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, tmp_path / "schemas")
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path / "schemas"
    load_schema.cache_clear()
    yield tmp_path / "schemas"
    load_schema.cache_clear()


def _edit(schemas, form_type, change):
    path = schemas / f"{form_type}.json"
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))


def _field(data, pdf_field):
    return next(f for f in data["fields"] if f["pdf_field"] == pdf_field)


def _ids(form_type):
    return [e.id for e in validate_form(form_type)]


def _errors(form_type):
    return [(e.id, e.msg) for e in validate_form(form_type)]


@pytest.mark.parametrize("form_type", get_all_form_types())
def test_every_registered_form_passes(form_type):
    assert validate_form(form_type) == []


def test_missing_schema_is_reported(schema_copy):
    (schema_copy / "form_121.json").unlink()
    assert _ids("form_121") == ["forms.E001"]


def test_changed_template_is_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: d.update(template_version="0" * 64))
    assert _ids("form_121") == ["forms.E002"]


def test_short_name_is_reported(schema_copy):
    # A short name is what put the filer's name in Debtor 2 boxes (DIG-63).
    _edit(schema_copy, "form_122a1", lambda d: _field(d, "Debtor1.Name").update(pdf_field="Name"))
    assert _ids("form_122a1") == ["forms.E003"]


def test_checkbox_bound_as_text_is_reported(schema_copy):
    def change(d):
        box = _field(d, "Check Box1")
        box.update(type="text")
        del box["choices"]

    _edit(schema_copy, "form_121", change)
    assert _ids("form_121") == ["forms.E004"]


def test_push_button_binding_is_reported(schema_copy):
    print_button = {
        "pdf_field": "Button.Print1",
        "type": "text",
        "source": "constant",
        "page": 9,
        "label": "",
        "required": False,
        "conditional_on": None,
        "value": "x",
        "rule": None,
        "ingest_key": None,
        "binding": None,
        "repeat": None,
        "repeat_capacity": None,
        "row": None,
        "legal_review": False,
    }
    _edit(schema_copy, "form_101", lambda d: d["fields"].append(print_button))
    # A print button is never drawn, so its page holds no widget that prints (E003).
    assert _ids("form_101") == ["forms.E003", "forms.E004"]


def test_checkbox_without_choices_is_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: _field(d, "Check Box1").pop("choices"))
    assert _errors("form_121") == [
        ("forms.E004", "form_121: 'Check Box1': a checkbox binding needs choices")
    ]


def test_choices_on_a_text_binding_are_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: _field(d, "Debtor1.First name").update(choices={}))
    assert _errors("form_121") == [
        (
            "forms.E004",
            "form_121: 'Debtor1.First name': choices go on checkbox and radio only, not on text",
        )
    ]


def test_choices_key_that_isnt_lower_case_is_reported(schema_copy):
    # The filler lower-cases the answer before the lookup, so "True" could never match.
    _edit(schema_copy, "form_107", lambda d: _field(d, "check5").update(choices={"True": "/no"}))
    assert _errors("form_107") == [
        (
            "forms.E004",
            "form_107: 'check5': choices key 'True' isn't lower-case, so no answer can match it",
        )
    ]


def test_state_the_template_lacks_is_reported(schema_copy):
    # The old schema wrote /Yes; the template's state is /On, so nothing ticked.
    _edit(
        schema_copy, "form_121", lambda d: _field(d, "Check Box1").update(choices={"true": "/Yes"})
    )
    assert _ids("form_121") == ["forms.E005"]


def test_district_constant_outside_the_options_is_reported(schema_copy):
    district = "Bankruptcy District Information"
    _edit(
        schema_copy,
        "form_121",
        lambda d: _field(d, district).update(source="constant", rule=None, value="Nowhere"),
    )
    assert _ids("form_121") == ["forms.E005"]


def test_constant_option_on_a_box_the_template_lacks_is_reported(schema_copy, monkeypatch):
    # The index still names the box, but the template has drifted: an error, not a crash.
    district = "Bankruptcy District Information"
    _edit(
        schema_copy,
        "form_121",
        lambda d: _field(d, district).update(
            source="constant", rule=None, value="Northern District of Illinois"
        ),
    )
    assert _ids("form_121") == []
    monkeypatch.setattr(pypdf.PdfReader, "get_fields", lambda self, *args, **kwargs: {})
    assert _ids("form_121") == ["forms.E005"]


def test_box_bound_twice_is_reported(schema_copy):
    _edit(schema_copy, "form_121", lambda d: d["fields"].append(_field(d, "Debtor1.First name")))
    assert _ids("form_121") == ["forms.E006"]


def _text(pdf_field, page, tag):
    """A constant text binding of one widget: the name's widget `tag` on `page`."""
    return {
        "pdf_field": pdf_field,
        "type": "text",
        "source": "constant",
        "page": page,
        "label": "",
        "required": False,
        "conditional_on": None,
        "value": "x",
        "rule": None,
        "ingest_key": None,
        "binding": None,
        "repeat": None,
        "repeat_capacity": None,
        "row": None,
        "legal_review": False,
        "tag": tag,
    }


@pytest.mark.parametrize(
    "page, tag",
    [(1, "T7"), (2, "T3")],  # T7 is Debtor1.Last name; T3 is this name's widget, but on page 1
)
def test_a_tag_that_isnt_one_of_the_names_widgets_on_its_page_is_reported(schema_copy, page, tag):
    _edit(
        schema_copy,
        "form_121",
        lambda d: _field(d, "Debtor1.First name").update(page=page, tag=tag),
    )
    assert _errors("form_121") == [
        (
            "forms.E003",
            f"form_121: 'Debtor1.First name' has no drawn widget {tag!r} on page {page}",
        )
    ]


def test_an_untagged_binding_on_a_page_without_its_widget_is_reported(schema_copy):
    # Form 121 prints Debtor1.First name on page 1 only.
    _edit(schema_copy, "form_121", lambda d: _field(d, "Debtor1.First name").update(page=2))
    assert _errors("form_121") == [
        ("forms.E003", "form_121: 'Debtor1.First name' has no drawn widget on page 2")
    ]


def test_a_tag_on_the_second_of_a_stacked_pair_is_reported(schema_copy):
    # Schedule D page 2 lays 4_3's T14 over T13; only T13 prints a value. Production D binds
    # 4_3 itself (Part 1's slot 3, ZIP), so the test retags that binding.
    _edit(schema_copy, "schedule_d", lambda d: _field(d, "4_3").update(tag="T14"))
    assert _ids("schedule_d") == ["forms.E003"]
    _edit(schema_copy, "schedule_d", lambda d: _field(d, "4_3").update(tag="T13"))
    load_schema.cache_clear()
    assert _ids("schedule_d") == []


def test_a_tag_on_a_print_button_is_reported(schema_copy):
    _edit(schema_copy, "form_101", lambda d: d["fields"].append(_text("Button.Print1", 9, "T20")))
    assert _ids("form_101") == ["forms.E003", "forms.E004"]


def _unbind_assistance(d):
    """Drop Schedule I's own bindings of the twin box and 5h, so a test can bind them itself."""
    d["fields"] = [
        f for f in d["fields"] if f["pdf_field"] not in ("Assistance 8f", "Other deductions 5h")
    ]


def test_two_tagged_bindings_on_different_widgets_of_one_name_pass(schema_copy):
    # Schedule I prints "Assistance 8f" twice on page 2; each can take its own value.
    def change(d):
        _unbind_assistance(d)
        d["fields"] += [_text("Assistance 8f", 2, "T36"), _text("Assistance 8f", 2, "T49")]

    _edit(schema_copy, "schedule_i", change)
    assert _ids("schedule_i") == []


def test_a_tagged_and_an_untagged_binding_of_one_name_are_reported(schema_copy):
    # The untagged binding fills both widgets, so T49 would get two values.
    def change(d):
        d["fields"] += [_text("Assistance 8f", 2, None), _text("Assistance 8f", 2, "T49")]

    _edit(schema_copy, "schedule_i", change)
    assert _errors("schedule_i") == [
        ("forms.E006", "schedule_i: 'Assistance 8f' is bound 2 times on page 2")
    ]


def _row(tag, row):
    """Row `row` of a repeat group of creditor payments, bound to Assistance 8f's widget `tag`."""
    return {
        **_text("Assistance 8f", 2, tag),
        "source": "asked",
        "value": None,
        "binding": "sofa.creditor_payments[].creditor_name",
        "repeat": "cp",
        "repeat_capacity": 2,
        "row": row,
    }


def _rows(*rows):
    """Add the rows to the schema, and declare their group, continued on page 2."""

    def change(d):
        _unbind_assistance(d)
        d["fields"].extend(rows)
        d["groups"] = {"cp": {"extra_page": 2}}

    return change


_UNTAGGED_SLOT_ON_A_TWIN = (
    "forms.E007",
    "schedule_i: repeat group 'cp': 'Assistance 8f' is drawn 2 times, on pages [2], "
    "so its slot needs a tag",
)


@pytest.mark.parametrize(
    "first, second, also",
    [(("T49", 1), ("T49", 2), []), ((None, 1), ("T49", 2), [_UNTAGGED_SLOT_ON_A_TWIN])],
    ids=["two rows tagged to one widget", "an untagged and a tagged row"],
)
def test_two_rows_of_a_group_that_would_fill_one_widget_are_reported(
    schema_copy, first, second, also
):
    # A box shows one value: the later row would overwrite the earlier one. The untagged row
    # is also refused on its own, below.
    _edit(schema_copy, "schedule_i", _rows(_row(*first), _row(*second)))
    assert _errors("schedule_i") == [
        ("forms.E006", "schedule_i: 'Assistance 8f' is bound 2 times on page 2"),
        *also,
    ]


def test_rows_of_a_group_on_different_widgets_of_one_name_pass(schema_copy):
    _edit(schema_copy, "schedule_i", _rows(_row("T36", 1), _row("T49", 2)))
    assert _ids("schedule_i") == []


def test_an_untagged_slot_whose_name_is_drawn_twice_on_its_page_is_reported(schema_copy):
    # Page 2 draws Assistance 8f twice, and nothing else writes it: row 1 would print in both.
    row_2 = {**_row(None, 2), "pdf_field": "Other deductions 5h"}  # drawn once, on page 2
    _edit(schema_copy, "schedule_i", _rows(_row(None, 1), row_2))
    assert _errors("schedule_i") == [_UNTAGGED_SLOT_ON_A_TWIN]


def test_a_group_continued_on_copies_of_the_last_page_passes(schedule_d_part_2_with_copies):
    assert _errors("schedule_d") == []


def _group(change):
    """Change the synthetic Schedule D group's declaration."""
    return lambda d: change(d["groups"]["d_part_1"])


def _row_3_numbered_on_the_page_of_its_unmapped_box(d):
    # An unmapped box prints nothing, so row 3 is still on page 2, where undefined_2 isn't.
    # Listed before the group's other fields, such a box used to decide the row's page.
    box = {**_text("Contingent", 1, None), "type": "checkbox", "value": None, "choices": {}}
    box |= {"repeat": "d_part_1", "repeat_capacity": 5, "row": 3}
    first = next(i for i, f in enumerate(d["fields"]) if f["repeat"] == "d_part_1")
    d["fields"].insert(first, box)
    d["groups"]["d_part_1"]["number_boxes"]["3"] = "undefined_2"


@pytest.mark.parametrize(
    "change, error",
    [
        (
            lambda d: (d.pop("groups"), d.pop("page_numbers")),
            ("forms.E007", "schedule_d: repeat group 'd_part_1' isn't declared in groups"),
        ),
        (
            lambda d: (d["groups"]["d_part_1"].pop("extra_page"), d.pop("page_numbers")),
            ("forms.E007", "schedule_d: group 'd_part_1' names neither an extra_page nor a sheet"),
        ),
        (
            # Page 3 is Part 2's: no row of Part 1 is there.
            _group(lambda g: g.update(extra_page=3)),
            ("forms.E007", "schedule_d: group 'd_part_1': extra_page 3 holds none of its slots"),
        ),
        (
            # Page 1's copies would print the rows past 2.5 before page 2's 2.3 to 2.5.
            _group(lambda g: g.update(extra_page=1)),
            (
                "forms.E007",
                "schedule_d: group 'd_part_1': extra_page 1 isn't the page of its last slots, 2",
            ),
        ),
        (
            _group(lambda g: g.update(number="2.")),
            ("forms.E007", "schedule_d: group 'd_part_1': number must contain {n}"),
        ),
        (
            # {m} has no value: numbering the first row would fail at Generate.
            _group(lambda g: g.update(number="2.{n}{m}")),
            ("forms.E007", "schedule_d: group 'd_part_1': number '2.{n}{m}' doesn't format"),
        ),
        (
            # A number has no index: this one fails with a TypeError, not a KeyError.
            _group(lambda g: g.update(number="2.{n}{n[0]}")),
            ("forms.E007", "schedule_d: group 'd_part_1': number '2.{n}{n[0]}' doesn't format"),
        ),
        (
            _group(lambda g: g.update(number="2.{n[0]}")),
            ("forms.E007", "schedule_d: group 'd_part_1': number must contain {n}"),
        ),
        (
            # Escaped braces: every row would be numbered "2.{n}".
            _group(lambda g: g.update(number="2.{{n}}")),
            (
                "forms.E007",
                "schedule_d: group 'd_part_1': number '2.{{n}}' prints the same for every row",
            ),
        ),
        (
            # Entry-number boxes, and no number to put in them.
            _group(lambda g: g.pop("number")),
            ("forms.E007", "schedule_d: group 'd_part_1': number must contain {n}"),
        ),
        (
            # A box nothing else writes (row 3's own box would also be two writers, E006).
            _group(lambda g: g["number_boxes"].update({"6": "4_3@2:T13"})),
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': '4_3@2:T13' numbers row 6, "
                "which isn't a slot row",
            ),
        ),
        (
            # 4_3's T14 is the stacked second of a pair, which never prints.
            _group(lambda g: g["number_boxes"].update({"3": "4_3@2:T14"})),
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': '4_3@2:T14' is no drawn widget on page 2",
            ),
        ),
        (
            # Page 1's undefined_2 would number row 3, whose name and amount are on page 2.
            _row_3_numbered_on_the_page_of_its_unmapped_box,
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': 'undefined_2' is no drawn widget on page 2",
            ),
        ),
        (
            # Page 2's own "of" box, declared as page 1's.
            lambda d: d["page_numbers"][0].update({"of": "fill_27.1.1"}),
            (
                "forms.E003",
                "schedule_d: page numbers: 'fill_27.1.1' is no drawn widget on page 1",
            ),
        ),
    ],
    ids=[
        "undeclared",
        "no extra page",
        "extra page without a slot",
        "extra page before its last slots",
        "number without {n}",
        "number that doesn't format",
        "number that indexes n",
        "number with only an indexed n",
        "number with escaped braces",
        "entry-number boxes without a number",
        "entry-number box for a row no slot has",
        "entry-number box that never prints",
        "entry-number box on the page of its row's unmapped box",
        "page-number box on another page",
    ],
)
def test_a_repeat_group_whose_rows_cannot_continue_is_reported(
    schedule_d_with_copies, change, error
):
    _edit(schedule_d_with_copies, "schedule_d", change)
    assert _errors("schedule_d") == [error]


def _slots(change, first_only=False):
    """Change every field of the synthetic Schedule D group, or only its first."""

    def apply(d):
        fields = [f for f in d["fields"] if f["repeat"] == "d_part_1"]
        for f in fields[:1] if first_only else fields:
            f.update(change)

    return apply


@pytest.mark.parametrize(
    "change, error",
    [
        (
            # Row 5 would print in its slot on page 2 and again on a copy.
            _slots({"repeat_capacity": 4}),
            "repeat group 'd_part_1': its slot rows aren't exactly 1 to its repeat_capacity, 4",
        ),
        (
            # Row 6 would print nowhere: past the last slot, and before the first copy row.
            _slots({"repeat_capacity": 6}),
            "repeat group 'd_part_1': its slot rows aren't exactly 1 to its repeat_capacity, 6",
        ),
        (
            # Which capacity counts would hang on the first field left after filtering.
            _slots({"repeat_capacity": 4}, first_only=True),
            "repeat group 'd_part_1' has more than one repeat_capacity",
        ),
        (
            # The group would print in part: some of a row's boxes, and not the others.
            _slots({"conditional_on": "has_creditor_payments"}, first_only=True),
            "repeat group 'd_part_1' has more than one conditional_on",
        ),
    ],
    ids=[
        "capacity below the slots",
        "capacity above the slots",
        "two capacities",
        "two conditions",
    ],
)
def test_a_repeat_group_whose_capacity_isnt_its_slots_is_reported(
    schedule_d_with_copies, change, error
):
    _edit(schedule_d_with_copies, "schedule_d", change)
    assert _errors("schedule_d") == [("forms.E007", f"schedule_d: {error}")]


def _slot(box, **change):
    """Change one field of the synthetic Schedule D group, found by its full name."""

    def apply(d):
        next(f for f in d["fields"] if f["repeat"] == "d_part_1" and f["pdf_field"] == box).update(
            change
        )

    return apply


def _amount_of_row_5_on_page_3(d):
    # Page 3's Name_6 is a drawn widget there, so every page is right: the row spans two.
    _slot("undefined_20", pdf_field="Name_6", page=3)(d)
    d["groups"]["d_part_1"]["extra_page"] = 3
    d["groups"]["d_part_1"]["number_boxes"].pop("5")


def _rows_1_to_3_on_page_2(d):
    # Page 1's two slots take rows 4 and 5, so the form would print 2.4 before 2.1.
    rows = {"Creditors Name_3": 1, "undefined_10": 1, "Creditors Name_4": 2, "undefined_14": 2}
    rows |= {"Creditors Name_5": 3, "undefined_20": 3, "Creditors Name": 4, "undefined": 4}
    rows |= {"Creditors Name_2": 5, "undefined_5": 5}
    for f in d["fields"]:
        if f["repeat"] == "d_part_1":
            f["row"] = rows[f["pdf_field"]]
    d["groups"]["d_part_1"].pop("number")
    d["groups"]["d_part_1"]["number_boxes"] = {}


@pytest.mark.parametrize(
    "change, errors",
    [
        (
            # Row 5's amount is a page 2 widget: a copy would print its name and not its amount.
            _slot("undefined_20", page=1),
            [
                ("forms.E003", "schedule_d: 'undefined_20' has no drawn widget on page 1"),
                (
                    "forms.E007",
                    "schedule_d: repeat group 'd_part_1': row 5 is on pages [1, 2], not one",
                ),
            ],
        ),
        (
            # Row 2's amount is a page 1 widget: a copy would take row 2's box as one of its own.
            _slot("undefined_5", page=2),
            [
                ("forms.E003", "schedule_d: 'undefined_5' has no drawn widget on page 2"),
                (
                    "forms.E007",
                    "schedule_d: repeat group 'd_part_1': row 2 is on pages [1, 2], not one",
                ),
            ],
        ),
        (
            # A null page names no page: reported, not a crash comparing None with a page.
            _slot("undefined_20", page=None),
            [("forms.E003", "schedule_d: 'undefined_20' has no drawn widget on page None")],
        ),
        (
            _amount_of_row_5_on_page_3,
            [
                (
                    "forms.E007",
                    "schedule_d: repeat group 'd_part_1': row 5 is on pages [2, 3], not one",
                )
            ],
        ),
        (
            _rows_1_to_3_on_page_2,
            [
                (
                    "forms.E007",
                    "schedule_d: repeat group 'd_part_1': row 4 is on a page before row 3's",
                )
            ],
        ),
    ],
    ids=[
        "a box declared on the page before its widget's",
        "a box declared on the page after its widget's",
        "a box with no page",
        "a row on two pages",
        "rows that go back a page",
    ],
)
def test_a_repeat_group_whose_rows_sit_on_the_wrong_pages_is_reported(
    schedule_d_with_copies, change, errors
):
    _edit(schedule_d_with_copies, "schedule_d", change)
    assert _errors("schedule_d") == errors


@pytest.mark.parametrize(
    "change, name",
    [
        # A one-digit typo: row 3's number box written as row 3's own amount box.
        (_group(lambda g: g["number_boxes"].update({"3": "undefined_10"})), "undefined_10"),
        # Row 5's amount box by its tagged spelling.
        (_group(lambda g: g["number_boxes"].update({"5": "undefined_20@2:T65"})), "undefined_20"),
        # Rows 4 and 5 both number themselves in row 5's box.
        (_group(lambda g: g["number_boxes"].update({"4": "undefined_19@2:T63"})), "undefined_19"),
        # Page 2's position written into row 5's amount box.
        (lambda d: d["page_numbers"][1].update({"this": "undefined_20"}), "undefined_20"),
        # Page 2's page count written into row 5's amount box.
        (lambda d: d["page_numbers"][1].update({"of": "undefined_20"}), "undefined_20"),
    ],
    ids=[
        "a number box on a slot's own box",
        "a number box on a bound widget's tagged spelling",
        "two rows naming one number box",
        "a page-number box on a slot's box",
        "a page-count box on a slot's box",
    ],
)
def test_a_group_box_that_another_writer_fills_is_reported(schedule_d_with_copies, change, name):
    # The later key would overwrite the other's value without a word.
    _edit(schedule_d_with_copies, "schedule_d", change)
    assert _errors("schedule_d") == [
        ("forms.E006", f"schedule_d: {name!r} is bound 2 times on page 2")
    ]


def test_a_page_count_box_drawn_on_two_pages_is_one_writer():
    # Schedule E/F draws one "of" box, fill_27.1.7, on pages 5 and 6. Every page prints the
    # same count, so production declares it for both pages without a conflict.
    schema = load_schema("schedule_e_f")

    assert {p.page: p.of for p in schema.page_numbers if p.page in (5, 6)} == {
        5: "fill_27.1.7",
        6: "fill_27.1.7",
    }
    assert _errors("schedule_e_f") == []


@pytest.mark.parametrize(
    "change, error",
    [
        (
            # Case number is drawn on pages 1 to 3: row 1's amount would print on each.
            _slot("undefined", pdf_field="Case number"),
            (
                "forms.E007",
                "schedule_d: repeat group 'd_part_1': 'Case number' is drawn 3 times, on pages "
                "[1, 2, 3], so its slot needs a tag",
            ),
        ),
        (
            # Row 3's number would print on pages 1 and 3 as well.
            _group(lambda g: g["number_boxes"].update({"3": "Case number"})),
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': 'Case number' is drawn 3 times, on pages "
                "[1, 2, 3], so it needs a tag",
            ),
        ),
        (
            # Page 2 draws undefined_19 twice: row 3's number would print in rows 4 and 5's.
            _group(lambda g: g.update(number_boxes={"3": "undefined_19"})),
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': 'undefined_19' is drawn 2 times, on pages [2], "
                "so it needs a tag",
            ),
        ),
        (
            # Page 2's position would print on pages 1 and 3 as well.
            lambda d: d["page_numbers"][1].update({"this": "Case number"}),
            (
                "forms.E003",
                "schedule_d: page numbers: 'Case number' is drawn 3 times, on pages "
                "[1, 2, 3], so it needs a tag",
            ),
        ),
    ],
    ids=[
        "a slot",
        "a number box",
        "a number box with a twin on its page",
        "a page number's this box",
    ],
)
def test_an_untagged_group_key_drawn_on_other_pages_is_reported(
    schedule_d_with_copies, change, error
):
    _edit(schedule_d_with_copies, "schedule_d", change)
    assert _errors("schedule_d") == [error]


def _box_slot(pdf_field, row, choices, value):
    """Add an untagged checkbox slot to the synthetic Schedule D group: row `row`, on page 2."""
    box = {**_text(pdf_field, 2, None), "type": "checkbox", "value": value, "choices": choices}
    box |= {"repeat": "d_part_1", "repeat_capacity": 5, "row": row}
    return lambda d: d["fields"].append(box)


def test_an_untagged_box_slot_whose_boxes_share_a_state_is_reported(schedule_d_with_copies):
    # Row 4's "Who owes the debt?" draws four boxes, each on at /On: one answer would tick all.
    _edit(schedule_d_with_copies, "schedule_d", _box_slot("check 5", 4, {"true": "/On"}, "true"))
    assert _errors("schedule_d") == [
        (
            "forms.E007",
            "schedule_d: repeat group 'd_part_1': 'check 5' is drawn 4 times, on pages [2], "
            "so its slot needs a tag",
        )
    ]


def test_an_untagged_box_slot_whose_boxes_each_have_their_own_state_passes(
    schedule_d_with_copies,
):
    # Row 3's "Who owes the debt?": each of its four boxes has its own state, so an answer
    # ticks one of them.
    choices = {
        "debtor 1": "/debtor 1",
        "debtor 2": "/debtor 2",
        "both": "/Debtor 1 and 2",
        "another": "/One of debtors and another",
    }
    _edit(schedule_d_with_copies, "schedule_d", _box_slot("check 4", 3, choices, "debtor 2"))
    assert _errors("schedule_d") == []


def _part_2(declaration):
    """Add a second group to the synthetic Schedule D: Part 2's six names on page 3."""

    def add(d):
        for row, box in enumerate(["Name", "Name_2", "Name_3", "Name_4", "Name_5", "Name_6"], 1):
            d["fields"].append(
                {
                    **_text(box, 3, None),
                    "source": "asked",
                    "value": None,
                    "binding": "sofa.creditor_payments[].creditor_name",
                    "repeat": "d_part_2",
                    "repeat_capacity": 6,
                    "row": row,
                }
            )
        d["groups"]["d_part_2"] = declaration

    return add


def test_a_form_takes_several_groups_continued_on_copies(schedule_d_with_copies):
    # D's Parts 1 and 2 (3c spec §5.1): E/F needs three.
    _edit(schedule_d_with_copies, "schedule_d", _part_2({"extra_page": 3}))
    assert _errors("schedule_d") == []


def test_two_groups_cannot_continue_on_copies_of_one_page(schedule_d_with_copies):
    # A copy's place in the form comes from its page and its number, so two groups' copies of
    # one page would print under one number.
    def add(d):
        d["fields"] = [
            f
            for f in d["fields"]
            if not (f["pdf_field"] == "Creditors Name_2" and f["repeat"] == "d_part_1")
        ]
        d["fields"].append(
            {
                **_text("Creditors Name_2", 1, None),
                "source": "asked",
                "value": None,
                "binding": "sofa.creditor_payments[].creditor_name",
                "repeat": "other",
                "repeat_capacity": 1,
                "row": 1,
            }
        )
        d["groups"]["other"] = {"extra_page": 2}

    _edit(schedule_d_with_copies, "schedule_d", add)
    assert (
        "forms.E007",
        "schedule_d: groups 'd_part_1' and 'other' both continue on copies of page 2",
    ) in _errors("schedule_d")


def test_page_numbers_on_a_form_with_copies_pass(schedule_d_with_two_groups):
    assert _errors("schedule_d") == []


def test_page_numbers_that_leave_out_a_continued_page_are_reported(schedule_d_with_copies):
    # Page 2's copies would count in "of N" and print no number of their own.
    _edit(schedule_d_with_copies, "schedule_d", lambda d: d["page_numbers"].pop(1))
    assert _errors("schedule_d") == [
        (
            "forms.E007",
            "schedule_d: group 'd_part_1' continues on copies of page 2, "
            "which has no page-number boxes",
        )
    ]


def test_a_second_group_with_no_extra_page_is_reported(schedule_d_with_copies):
    # Such a group is refused for its own reason.
    _edit(schedule_d_with_copies, "schedule_d", _part_2({}))
    assert _errors("schedule_d") == [
        ("forms.E007", "schedule_d: group 'd_part_2' names neither an extra_page nor a sheet")
    ]


def test_a_group_on_a_sheet_passes_beside_a_group_on_copies(
    schedule_d_with_copies,
):
    # A sheet's pages aren't copies of the form's, so they number none of its pages (R56).
    sheet = {
        "title": "Official Form 106D, Schedule D: Creditors Who Have Claims Secured by Property",
        "columns": [
            {"label": "Name", "binding": "sofa.creditor_payments[].creditor_name", "width": 300}
        ],
    }
    _edit(schedule_d_with_copies, "schedule_d", _part_2({"number": "3.{n}", "sheet": sheet}))
    assert _errors("schedule_d") == []


def test_a_groups_total_boxes_pass(schedule_d_with_totals):
    assert _errors("schedule_d") == []


def _totals(change):
    """Change the synthetic Schedule D group's total boxes."""
    return lambda d: change(d["groups"]["d_part_1"]["totals"])


@pytest.mark.parametrize(
    "change, error",
    [
        (
            # Page 3 is Part 2's: no row of the group prints there to add up.
            _totals(lambda t: t.update(page_boxes={"3": "fill_28.1.1"})),
            (
                "forms.E007",
                "schedule_d: group 'd_part_1': total box 'fill_28.1.1' is for page 3, "
                "which holds none of its slots",
            ),
        ),
        (
            _totals(lambda t: t.update(column="sofa.creditor_payments[].nothing")),
            (
                "forms.E007",
                "schedule_d: group 'd_part_1': its totals add "
                "'sofa.creditor_payments[].nothing', which isn't a text slot of the group",
            ),
        ),
        (
            _totals(lambda t: t.update(page_boxes={}, last_page_box=None)),
            ("forms.E007", "schedule_d: group 'd_part_1': its totals name no box"),
        ),
        (
            # Page 1's box, declared as page 2's.
            _totals(lambda t: t.update(page_boxes={"2": "undefined_9"})),
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': 'undefined_9' is no drawn widget on page 2",
            ),
        ),
        (
            # The last page's box must print on the extra page and its copies.
            _totals(lambda t: t.update(last_page_box="fill_27.0")),
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': 'fill_27.0' is no drawn widget on page 2",
            ),
        ),
        (
            # Page 2's total would print on pages 1 and 3 as well.
            _totals(lambda t: t.update(page_boxes={"2": "Case number"})),
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': 'Case number' is drawn 3 times, on pages "
                "[1, 2, 3], so it needs a tag",
            ),
        ),
        (
            # A figure can't tick a box: every filer with a row would be refused.
            _totals(lambda t: t.update(page_boxes={"2": "Contingent_3"})),
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': total box 'Contingent_3' isn't a text box",
            ),
        ),
    ],
    ids=[
        "a box on no page of the group",
        "a column no slot binds",
        "no box",
        "a box on another page",
        "a last box off the extra page",
        "a box drawn on other pages",
        "a checkbox",
    ],
)
def test_a_total_box_that_cannot_add_its_own_rows_is_reported(
    schedule_d_with_totals, change, error
):
    _edit(schedule_d_with_totals, "schedule_d", change)
    assert _errors("schedule_d") == [error]


def test_a_total_over_a_column_that_holds_no_amount_is_refused(schedule_d_with_totals):
    # A name can't be added: the total box would print a sum of words, or raise on a filer's row.
    _edit(
        schedule_d_with_totals,
        "schedule_d",
        _totals(lambda t: t.update(column="sofa.creditor_payments[].creditor_name")),
    )
    assert _errors("schedule_d") == [
        (
            "forms.E007",
            "schedule_d: group 'd_part_1': its total adds "
            "'sofa.creditor_payments[].creditor_name', which holds no amount",
        )
    ]


def test_a_claims_binding_passes_the_namespace_check(schedule_d_with_totals):
    def rebind(d):
        for f in d["fields"]:
            if f["binding"] == "sofa.creditor_payments[].creditor_name":
                f["binding"] = "claims.secured[].name"

    _edit(schedule_d_with_totals, "schedule_d", rebind)
    assert not [e for e in _errors("schedule_d") if "unknown binding namespace" in e[1]]


def test_an_exemptions_binding_passes_the_namespace_check(schedule_d_with_totals):
    def rebind(d):
        for f in d["fields"]:
            if f["binding"] == "sofa.creditor_payments[].creditor_name":
                f["binding"] = "exemptions.claims[].description"

    _edit(schedule_d_with_totals, "schedule_d", rebind)
    assert not [e for e in _errors("schedule_d") if "unknown binding namespace" in e[1]]


def test_a_total_box_another_binding_fills_is_reported(schedule_d_with_totals):
    # A binding of undefined_24 put back (the rule that once bound it is gone, 3c5 R8): its figure
    # and the group's would fight.
    def add(d):
        d["fields"].append(_text("undefined_24", 2, None))

    _edit(schedule_d_with_totals, "schedule_d", add)
    assert _errors("schedule_d") == [
        ("forms.E006", "schedule_d: 'undefined_24' is bound 2 times on page 2")
    ]


def test_a_group_on_a_sheet_has_no_total_boxes(schedule_a_b_with_sheet):
    def add(d):
        d["groups"]["ab_line_3"]["totals"] = {"column": "sofa.creditor_payments[].total_paid"}

    _edit(schedule_a_b_with_sheet, "schedule_a_b", add)
    assert (
        "forms.E007",
        "schedule_a_b: group 'ab_line_3': only a group continued on copies has total boxes",
    ) in _errors("schedule_a_b")


def test_a_group_of_the_households_dependents_passes(schedule_j_with_dependents):
    # Line 2 as 3e1 declares it: a household list, its "lives with you?" column from boxes.
    assert _errors("schedule_j") == []


def _sheet(change):
    """Change the synthetic Schedule A/B group's declaration."""
    return lambda d: change(d["groups"]["ab_line_3"])


def _column(n, **change):
    """Change the nth column of the synthetic Schedule A/B group's sheet."""
    return _sheet(lambda g: g["sheet"]["columns"][n].update(change))


def _makes_asked_on_ask_page(d):
    # The slots and the column bind one answer: a binding, but no list of rows.
    for f in d["fields"]:
        if f["repeat"] == "ab_line_3" and f["binding"].endswith("creditor_name"):
            f["binding"] = "answer:schedule_a_b.make"
    d["groups"]["ab_line_3"]["sheet"]["columns"][0]["binding"] = "answer:schedule_a_b.make"


def _community_property_boxes(d):
    # Each vehicle's community-property box, ticked from a list.
    for row, (page, box) in enumerate([(2, ""), (2, "_2"), (3, "_3"), (3, "_4")], start=1):
        d["fields"].append(
            {
                **_text(f"Check if this is community property see{box}", page, None),
                "type": "checkbox",
                "source": "asked",
                "value": None,
                "choices": {"true": "/On"},
                "binding": "sofa.creditor_payments[].dates_of_payments",
                "repeat": "ab_line_3",
                "repeat_capacity": 4,
                "row": row,
            }
        )


def _unmapped_community_property_boxes(d):
    # Not yet mapped to a state, so they tick nothing for now; once mapped, they would.
    _community_property_boxes(d)
    for f in d["fields"]:
        if f["repeat"] == "ab_line_3" and f["type"] == "checkbox":
            f["choices"] = {}


def _a_column_of_boxes(d):
    _community_property_boxes(d)
    columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
    columns[0]["width"] = 200
    columns.append(
        {
            "label": "Community property",
            "binding": "sofa.creditor_payments[].dates_of_payments",
            "width": 100,
        }
    )


def _a_column_of_boxes_sharing_a_state(d):
    _a_column_of_boxes(d)
    for f in d["fields"]:
        if f["repeat"] == "ab_line_3" and f["type"] == "checkbox":
            f["choices"] = {"yes": "/On", "no": "/On"}


def _ab_slot(**binding):
    """Add a slot to row 1 of the synthetic Schedule A/B group, filled as `binding` says."""

    def change(d):
        d["fields"].append(
            {**_text(None, 2, None), "repeat": "ab_line_3", "repeat_capacity": 4, "row": 1}
            | binding
        )

    return change


def _another_lists_column(d):
    columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
    columns[0]["width"] = 200
    columns.append(
        {"label": "Paid on", "binding": "sofa.creditor_payments[].dates_of_payments", "width": 100}
    )


def _ab_slots(change):
    """Change every field of the synthetic Schedule A/B group."""
    return lambda d: [change(f) for f in d["fields"] if f["repeat"] == "ab_line_3"]


def _swap_rows_2_and_3(f):
    f["row"] = {2: 3, 3: 2}.get(f["row"], f["row"])


_AB = "schedule_a_b: group 'ab_line_3'"


@pytest.mark.parametrize(
    "change, error",
    [
        (
            _sheet(lambda g: g.update(extra_page=3)),
            ("forms.E007", f"{_AB} names both an extra_page and a sheet"),
        ),
        (
            # T6's slot rules hold for a sheet group's slots too.
            _ab_slots(lambda f: f.update(repeat_capacity=5)),
            (
                "forms.E007",
                "schedule_a_b: repeat group 'ab_line_3': its slot rows aren't exactly 1 to "
                "its repeat_capacity, 5",
            ),
        ),
        (
            _ab_slots(_swap_rows_2_and_3),
            (
                "forms.E007",
                "schedule_a_b: repeat group 'ab_line_3': row 3 is on a page before row 2's",
            ),
        ),
        (
            # A sheet labels each row with the line it continues.
            _sheet(lambda g: g.pop("number")),
            ("forms.E007", f"{_AB}: number must contain {{n}}"),
        ),
        (
            lambda d: d.update(page_numbers=[{"page": 2}]),
            (
                "forms.E007",
                "schedule_a_b: no group continues on copies, so the form numbers no pages",
            ),
        ),
        (
            # A row of line numbers alone.
            _sheet(lambda g: g["sheet"].update(columns=[])),
            ("forms.E007", f"{_AB}: its sheet has no columns for its rows"),
        ),
        (
            # 36 pt of line column, then 301 and 168: one point past the margins.
            _column(0, width=301),
            (
                "forms.E007",
                f"{_AB}: its sheet's columns and line column are 505 pt wide, "
                "more than the 504 pt (7 in) between its margins",
            ),
        ),
        (
            _makes_asked_on_ask_page,
            (
                "forms.E007",
                f"{_AB}: sheet column 'Make' binds 'answer:schedule_a_b.make', "
                "not a sofa.<collection>[].<attr>, household.dependents[].<attr>, "
                "income.statement[].<attr> or assets.line_<key>[].<attr> list",
            ),
        ),
        (
            # Another list of the same report: its rows aren't the group's.
            _another_lists_column,
            (
                "forms.E007",
                f"{_AB}: sheet column 'Paid on' binds "
                "'sofa.creditor_payments[].dates_of_payments', which no slot of the group binds",
            ),
        ),
        (
            # One box per row: its No would print blank on the sheet, the same as no answer.
            _a_column_of_boxes,
            (
                "forms.E007",
                f"{_AB}: sheet column 'Community property' binds a box that doesn't give "
                "every answer its own state",
            ),
        ),
        (
            # Two answers ticking one box: the sheet couldn't tell them apart.
            _a_column_of_boxes_sharing_a_state,
            (
                "forms.E007",
                f"{_AB}: sheet column 'Community property' binds a box that doesn't give "
                "every answer its own state",
            ),
        ),
        (
            # Rows 1 to 4 print their values on the form, the fifth's nowhere.
            _sheet(lambda g: g["sheet"].update(columns=g["sheet"]["columns"][:1])),
            (
                "forms.E007",
                f"{_AB}: no sheet column prints 'sofa.creditor_payments[].total_paid', "
                "which a slot of the group binds",
            ),
        ),
        (
            # A box in the Make column's list, its answer not yet mapped to a state: the
            # sheet would have no words to print for it.
            _ab_slot(
                pdf_field="Check if this is community property see",
                type="checkbox",
                source="asked",
                value=None,
                choices={},
                binding="sofa.creditor_payments[].creditor_name",
            ),
            (
                "forms.E007",
                f"{_AB}: sheet column 'Make' binds a box that doesn't give every answer its "
                "own state",
            ),
        ),
        (
            # A box ticked for every row, bound to nothing: still no box on the sheet.
            _ab_slot(
                pdf_field="Check if this is community property see",
                type="checkbox",
                value="yes",
                choices={"true": "/On"},
            ),
            (
                "forms.E007",
                f"{_AB}: a box slot fills 'Check if this is community property see' on row 1, "
                "and a sheet can't tick a box",
            ),
        ),
        (
            # A value DigniFi works out (the filer's name, in row 1's model box): no column
            # holds it, so a fifth row would lose it.
            _ab_slot(pdf_field="3 2", source="derived", value=None, rule="full_name"),
            (
                "forms.E007",
                f"{_AB}: no sheet column prints '3 2' on row 1, a slot of the group that "
                "binds no list",
            ),
        ),
        (
            # "Line 3.5" is 35.58 pt at 10 pt, wider than the 32 pt inside the line column's
            # padding: it would print on two lines.
            _sheet(lambda g: g.update(number="Line 3.{n}")),
            (
                "forms.E007",
                f"{_AB}: its sheet can't print its first line, 'Line 3.5', whole in the "
                "36 pt line column",
            ),
        ),
        (
            # "Line 5", the first line, fits the 36 pt line column; "Line 10" doesn't, so every
            # Generate of ten rows or more would fail. Row 9999's line is the widest checked.
            _sheet(lambda g: g.update(number="Line {n}")),
            (
                "forms.E007",
                f"{_AB}: its sheet can't print row 9999's line, 'Line 9999', whole in the "
                "36 pt line column",
            ),
        ),
        (
            # The filer couldn't tell the two apart, nor could a refusal's fix.
            _column(1, label="Make"),
            ("forms.E007", f"{_AB}: its sheet has more than one column labelled 'Make'"),
        ),
        (
            # "Make" is 24.45 pt wide at 10 pt: it doesn't fit 20 pt less its padding.
            _column(0, width=20),
            ("forms.E007", f"{_AB}: sheet column 'Make' can't print its label whole in 20 pt"),
        ),
        (
            _column(0, width=0),
            ("forms.E007", f"{_AB}: sheet column 'Make' can't print its label whole in 0 pt"),
        ),
        (
            _column(0, label="Mąke"),
            ("forms.E007", f"{_AB}: sheet column 'Mąke' can't print its label whole in 300 pt"),
        ),
        (
            _sheet(lambda g: g["sheet"].update(title="Schedule A/B: Własność")),
            ("forms.E007", f"{_AB}: its sheet can't print its title whole"),
        ),
    ],
    ids=[
        "an extra page too",
        "capacity other than the slots",
        "rows that go back a page",
        "no number",
        "page numbers",
        "no columns",
        "wider than the margins",
        "a column of no list",
        "a column of another list",
        "a column of boxes",
        "a column of boxes sharing a state",
        "a slot with no column",
        "a box slot not yet mapped, in a column",
        "a constant box slot",
        "a derived slot",
        "a first line wider than the line column",
        "a later line wider than the line column",
        "two columns with one label",
        "a label wider than its column",
        "a column with no width",
        "a label with a letter the sheet can't print",
        "a title with a letter the sheet can't print",
    ],
)
def test_a_sheet_that_cannot_print_its_rows_whole_is_reported(
    schedule_a_b_with_sheet, change, error
):
    _edit(schedule_a_b_with_sheet, "schedule_a_b", change)
    assert _errors("schedule_a_b") == [error]


@pytest.mark.parametrize(
    "change",
    [_community_property_boxes, _unmapped_community_property_boxes],
    ids=["mapped", "not yet mapped"],
)
def test_a_box_slot_no_column_prints_is_refused_as_a_text_slot_is(schedule_a_b_with_sheet, change):
    # Rows 1 to 4 tick their boxes on the form; a fifth row's answer would have no column.
    _edit(schedule_a_b_with_sheet, "schedule_a_b", change)
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: no sheet column prints 'sofa.creditor_payments[].dates_of_payments', "
            "which a slot of the group binds",
        )
    ]


def test_a_template_that_doesnt_match_its_index_is_reported_not_raised(schema_copy, index_copy):
    def move_a_row_off_its_widget(rows):
        next(row for row in rows if row["page"] == 2)["rect"] = [1, 1, 2, 2]

    index_copy("form_b106d.pdf", move_a_row_off_its_widget)
    # The tag check needs the widget map, so it is skipped: this good tag adds no error.
    _edit(schema_copy, "schedule_d", lambda d: d["fields"].append(_text("4_3", 2, "T13")))
    assert _errors("schedule_d") == [
        (
            "forms.E003",
            "schedule_d: form_b106d.pdf page 2: "
            "the widgets don't match the field index one-to-one",
        )
    ]


def test_a_full_name_with_an_at_sign_in_the_index_is_reported(index_copy):
    # "@" separates a full name from a widget's page and tag in the resolved values.
    def rename(rows):
        next(row for row in rows if row["full_name"] == "Case number1")["full_name"] = "Case@1"

    index_copy("form_b121.pdf", rename)
    assert _errors("form_121") == [
        ("forms.E003", "form_121: 'Case@1': a full name in the field index contains '@'")
    ]


@pytest.mark.parametrize(
    "change",
    [
        {"source": "TBD"},
        {"source": "derived", "rule": "no_such_rule"},
        {"conditional_on": "no_such_predicate"},
        {"source": "asked", "rule": None, "binding": "intake.first_name"},
    ],
)
def test_unresolvable_source_is_reported(schema_copy, change):
    _edit(schema_copy, "form_121", lambda d: _field(d, "Debtor1.First name").update(change))
    assert _ids("form_121") == ["forms.E007"]


@pytest.mark.slow
def test_manage_py_check_fails_on_a_bad_schema(schema_copy):
    """migrate runs the same checks, so this is what fails a Heroku release."""
    _edit(schema_copy, "form_121", lambda d: d.update(template_version="0" * 64))
    with pytest.raises(SystemCheckError, match="forms.E002"):
        call_command("check")


def test_a_statement_column_binding_another_list_is_reported(schema_copy):
    def change(d):
        d["groups"]["i_line_8a"]["sheet"]["columns"][0]["binding"] = "household.dependents[].age"

    _edit(schema_copy, "schedule_i", change)

    assert (
        "forms.E007",
        "schedule_i: group 'i_line_8a': statement column 'Income of' binds "
        "'household.dependents[].age', not an income.statement[].<attr> list",
    ) in _errors("schedule_i")


def test_a_statement_line_too_wide_for_row_9999_is_reported(schema_copy):
    _edit(
        schema_copy,
        "schedule_i",
        lambda d: d["groups"]["i_line_8a"].update(number="8a.{n}"),
    )

    assert (
        "forms.E007",
        "schedule_i: group 'i_line_8a': its sheet can't print row 9999's line, "
        "'8a.9999', whole in the 36 pt line column",
    ) in _errors("schedule_i")


def _two_digit_lines(d):
    d["groups"]["ab_line_3"]["number"] = "17.{n}"


def _widened_line_column(d):
    _two_digit_lines(d)
    d["groups"]["ab_line_3"]["sheet"]["line_width"] = 48
    d["groups"]["ab_line_3"]["sheet"]["columns"][0]["width"] = 288  # 48 + 288 + 168 = 504


def test_a_two_digit_line_fits_a_sheet_that_widens_its_line_column(schedule_a_b_with_sheet):
    # "17.9999" is 36.1 pt, wider than the 32 pt inside a 36 pt column's padding.
    _edit(schedule_a_b_with_sheet, "schedule_a_b", _two_digit_lines)
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: its sheet can't print row 9999's line, '17.9999', whole in the "
            "36 pt line column",
        )
    ]

    _edit(schedule_a_b_with_sheet, "schedule_a_b", _widened_line_column)
    load_schema.cache_clear()
    assert _errors("schedule_a_b") == []


def test_a_line_too_wide_for_the_widened_column_names_that_width(schedule_a_b_with_sheet):
    def change(d):
        _widened_line_column(d)
        d["groups"]["ab_line_3"]["number"] = "Line 17.{n}"

    _edit(schedule_a_b_with_sheet, "schedule_a_b", change)
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: its sheet can't print row 9999's line, 'Line 17.9999', whole in the "
            "48 pt line column",
        )
    ]


def test_columns_too_wide_for_the_wider_line_column_are_refused(schedule_a_b_with_sheet):
    # 300 and 168 fit beside 36 pt of line column, not beside 48.
    def change(d):
        d["groups"]["ab_line_3"]["sheet"]["line_width"] = 48

    _edit(schedule_a_b_with_sheet, "schedule_a_b", change)
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: its sheet's columns and line column are 516 pt wide, "
            "more than the 504 pt (7 in) between its margins",
        )
    ]


_COMMUNITY = "assets.line_3[].community"


def _on_asset_rows(d, slots="assets.line_3"):
    """The synthetic group's slots and columns as Schedule A/B binds them: one line's rows."""
    attrs = {"creditor_name": "make", "total_paid": "value", "dates_of_payments": "community"}

    def rebound(binding):
        return f"{slots}[].{attrs[binding.partition('[].')[2]]}"

    for f in d["fields"]:
        if f["repeat"] == "ab_line_3":
            f["binding"] = rebound(f["binding"])
    for column in d["groups"]["ab_line_3"]["sheet"]["columns"]:
        column["binding"] = rebound(column["binding"])


def _a_covering_column(covers, binding="assets.line_3[].interest", slots="assets.line_3"):
    def change(d):
        _community_property_boxes(d)
        _on_asset_rows(d, slots)
        columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
        columns[0]["width"] = 200
        columns.append(
            {
                "label": "Who has an interest",
                "binding": binding,
                "covers": covers,
                "width": 100,
            }
        )

    return change


def test_a_covering_column_counts_its_boxes_as_printed(schedule_a_b_with_sheet):
    # A single box can't be a column of its own (its No would print blank), and needs no
    # column once one column prints it in words.
    _edit(schedule_a_b_with_sheet, "schedule_a_b", _a_covering_column([_COMMUNITY]))
    assert _errors("schedule_a_b") == []


def test_an_uncovered_single_box_is_still_refused(schedule_a_b_with_sheet):
    _edit(schedule_a_b_with_sheet, "schedule_a_b", _a_covering_column([]))
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: no sheet column prints {_COMMUNITY!r}, which a slot of the group binds",
        )
    ]


def test_a_covering_column_naming_a_binding_no_slot_has_is_refused(schedule_a_b_with_sheet):
    _edit(
        schedule_a_b_with_sheet,
        "schedule_a_b",
        _a_covering_column([_COMMUNITY, "assets.line_3[].street"]),
    )
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: sheet column 'Who has an interest' covers 'assets.line_3[].street', "
            "which no slot of the group binds",
        )
    ]


def test_a_covering_column_may_cover_nothing_and_print_an_attribute_no_slot_binds(
    schedule_a_b_with_sheet,
):
    # Line 53's text: one box on the form for three rows, its own words on a sheet.
    def change(d):
        _on_asset_rows(d)
        columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
        columns[0]["width"] = 200
        columns.append(
            {
                "label": "What it is",
                "binding": "assets.line_3[].description",
                "covers": [],
                "width": 100,
            }
        )

    _edit(schedule_a_b_with_sheet, "schedule_a_b", change)
    assert _errors("schedule_a_b") == []


@pytest.mark.parametrize(
    "slots, binding",
    [
        ("assets.line_3", "assets.line_4[].interest"),  # a boat's words beside a car
        ("assets.line_17_checking", "assets.line_17[].description"),  # every kind's rows
        ("assets.line_3", "sofa.creditor_payments[].creditor_name"),
    ],
)
def test_a_sworn_sheet_cannot_print_another_rows_words_beside_a_row(
    schedule_a_b_with_sheet, slots, binding
):
    # A sheet's rows are its slots' rows, and a covering column prints by position: any other
    # list prints another row's words, or runs out and fails Generate.
    _edit(
        schedule_a_b_with_sheet,
        "schedule_a_b",
        _a_covering_column([f"{slots}[].community"], binding, slots),
    )
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: sheet column 'Who has an interest' covers slots but binds {binding!r}, "
            "which isn't the one list its slots bind",
        )
    ]


def test_a_kinds_sheet_may_print_that_kinds_own_words(schedule_a_b_with_sheet):
    slots = "assets.line_17_checking"
    _edit(
        schedule_a_b_with_sheet,
        "schedule_a_b",
        _a_covering_column([f"{slots}[].community"], f"{slots}[].interest", slots),
    )
    assert _errors("schedule_a_b") == []


def test_a_covering_column_cannot_follow_slots_on_two_lists(schedule_a_b_with_sheet):
    # Neither list is the group's rows: the row count is the longer one's.
    def change(d):
        _a_covering_column([_COMMUNITY])(d)
        for f in d["fields"]:
            if f["repeat"] == "ab_line_3" and f["binding"].endswith(".value"):
                f["binding"] = "assets.line_4[].value"
        d["groups"]["ab_line_3"]["sheet"]["columns"][1]["binding"] = "assets.line_4[].value"

    _edit(schedule_a_b_with_sheet, "schedule_a_b", change)
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: sheet column 'Who has an interest' covers slots but binds "
            "'assets.line_3[].interest', which isn't the one list its slots bind",
        )
    ]


def test_a_misspelled_words_column_is_refused_at_startup_not_at_a_fourth_property(
    schedule_a_b_with_sheet,
):
    # No slot resolves this binding, so only a row past the slots would reach it, as a 500.
    binding = "assets.line_3[].wher"
    _edit(
        schedule_a_b_with_sheet,
        "schedule_a_b",
        _a_covering_column([_COMMUNITY], binding),
    )
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: sheet column 'Who has an interest' covers slots but binds {binding!r}, "
            "which no Schedule A/B row can print",
        )
    ]


@pytest.mark.parametrize(
    "attr", ["who", "community", "has_personal_info", f"kind_{PROPERTY_KINDS[0]}"]
)
def test_a_words_column_cannot_print_a_boxs_raw_answer(schedule_a_b_with_sheet, attr):
    # A covering cell prints its list as it is, so the court would read "with_someone" or "true".
    binding = f"assets.line_3[].{attr}"
    _edit(
        schedule_a_b_with_sheet,
        "schedule_a_b",
        _a_covering_column([_COMMUNITY], binding),
    )
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            f"{_AB}: sheet column 'Who has an interest' covers slots but binds {binding!r}, "
            "a box's answer, not words",
        )
    ]


@pytest.mark.parametrize("attr", ["where", "what", "interest", "description", "value", "make"])
def test_a_words_column_may_print_words_or_what_the_filer_typed(schedule_a_b_with_sheet, attr):
    _edit(
        schedule_a_b_with_sheet,
        "schedule_a_b",
        _a_covering_column([_COMMUNITY], f"assets.line_3[].{attr}"),
    )
    assert _errors("schedule_a_b") == []


def test_a_slot_may_bind_an_asset_list(schedule_a_b_with_sheet):
    def change(d):
        for f in d["fields"]:
            if f["repeat"] == "ab_line_3":
                f["binding"] = f["binding"].replace(
                    "sofa.creditor_payments[].creditor_name", "assets.line_3[].make"
                )
        d["groups"]["ab_line_3"]["sheet"]["columns"][0]["binding"] = "assets.line_3[].make"

    _edit(schedule_a_b_with_sheet, "schedule_a_b", change)
    assert _errors("schedule_a_b") == []


def test_a_statement_column_cannot_cover_a_slot_it_does_not_have(schema_copy):
    def change(d):
        column = d["groups"]["i_line_8a"]["sheet"]["columns"][0]
        column["covers"] = ["income.statement[].net"]

    _edit(schema_copy, "schedule_i", change)
    assert (
        "forms.E007",
        "schedule_i: group 'i_line_8a': sheet column 'Income of' covers "
        "'income.statement[].net', which no slot of the group binds",
    ) in _errors("schedule_i")


def test_a_number_box_that_isnt_a_text_box_is_reported(schedule_g_numbered):
    def change(d):
        d["groups"]["g"]["number_boxes"]["1"] = "check1"

    _edit(schedule_g_numbered, "schedule_g", change)
    assert (
        "forms.E003",
        "schedule_g: group 'g': number box 'check1' isn't a text box",
    ) in _errors("schedule_g")


def test_a_number_box_drawn_on_another_page_is_refused_once(schedule_g_numbered):
    def change(d):
        d["groups"]["g"]["number_boxes"]["6"] = "check1"  # drawn on page 1, row 6 is on page 2

    _edit(schedule_g_numbered, "schedule_g", change)
    mentions = [
        m
        for _, m in _errors("schedule_g")
        if "group 'g': 'check1'" in m or "number box 'check1'" in m
    ]
    assert "schedule_g: group 'g': 'check1' is no drawn widget on page 2" in mentions
    assert not [m for m in mentions if "isn't a text box" in m]


def test_a_page_number_box_that_isnt_a_text_box_is_reported(schedule_g_numbered):
    def change(d):
        d["page_numbers"] = [
            {"page": 1, "this": None, "of": "check1"},
            {"page": 2, "this": "fill_27.1.0", "of": "fill_27.1.1"},
        ]

    _edit(schedule_g_numbered, "schedule_g", change)
    assert (
        "forms.E003",
        "schedule_g: page numbers: box 'check1' on page 1 isn't a text box",
    ) in _errors("schedule_g")
