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
    # Schedule D page 2 lays 4_3's T14 over T13; only T13 prints a value.
    _edit(schema_copy, "schedule_d", lambda d: d["fields"].append(_text("4_3", 2, "T14")))
    assert _ids("schedule_d") == ["forms.E003"]
    _edit(schema_copy, "schedule_d", lambda d: _field(d, "4_3").update(tag="T13"))
    load_schema.cache_clear()
    assert _ids("schedule_d") == []


def test_a_tag_on_a_print_button_is_reported(schema_copy):
    _edit(schema_copy, "form_101", lambda d: d["fields"].append(_text("Button.Print1", 9, "T20")))
    assert _ids("form_101") == ["forms.E003", "forms.E004"]


def test_two_tagged_bindings_on_different_widgets_of_one_name_pass(schema_copy):
    # Schedule I prints "Assistance 8f" twice on page 2; each can take its own value.
    def change(d):
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


def test_a_group_continued_on_copies_of_its_extra_page_passes(schedule_d_with_copies):
    assert _errors("schedule_d") == []


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
            lambda d: d.pop("groups"),
            ("forms.E007", "schedule_d: repeat group 'd_part_1' isn't declared in groups"),
        ),
        (
            _group(lambda g: g.pop("extra_page")),
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
            _group(lambda g: g["page_numbers"][0].update({"of": "fill_27.1.1"})),
            (
                "forms.E003",
                "schedule_d: group 'd_part_1': 'fill_27.1.1' is no drawn widget on page 1",
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
        (_group(lambda g: g["page_numbers"][1].update({"this": "undefined_20"})), "undefined_20"),
        # Page 2's page count written into row 5's amount box.
        (_group(lambda g: g["page_numbers"][1].update({"of": "undefined_20"})), "undefined_20"),
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


def test_a_page_count_box_drawn_on_two_pages_is_one_writer(schema_copy):
    # Schedule E/F draws one "of" box, fill_27.1.7, on pages 5 and 6. Every page prints the
    # same count, so declaring it for both pages can't conflict.
    def declare(d):
        d["groups"] = {
            "e_f": {
                "extra_page": 6,
                "page_numbers": [
                    {"page": 5, "of": "fill_27.1.7"},
                    {"page": 6, "of": "fill_27.1.7"},
                ],
            }
        }

    _edit(schema_copy, "schedule_e_f", declare)
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
    ],
    ids=["a slot", "a number box", "a number box with a twin on its page"],
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


def test_a_second_group_continued_on_copies_is_reported(schedule_d_with_copies):
    # 3a2 numbers a form's pages counting one group's copies only (R21, R56).
    _edit(schedule_d_with_copies, "schedule_d", _part_2({"extra_page": 3}))
    assert _errors("schedule_d") == [
        (
            "forms.E007",
            "schedule_d: groups 'd_part_1' and 'd_part_2' both declare extra_page; "
            "3a2 continues one group per form on copies",
        )
    ]


def test_a_group_with_no_extra_page_is_not_counted_as_a_second(schedule_d_with_copies):
    # Such a group is refused for its own reason.
    _edit(schedule_d_with_copies, "schedule_d", _part_2({}))
    assert _errors("schedule_d") == [
        ("forms.E007", "schedule_d: group 'd_part_2' names neither an extra_page nor a sheet")
    ]


def test_a_group_continued_on_an_attached_sheet_is_not_counted_as_a_second(
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


def test_a_group_continued_on_an_attached_sheet_passes(schedule_a_b_with_sheet):
    assert _errors("schedule_a_b") == []


def test_a_sheet_line_too_wide_for_a_later_row_is_reported(schedule_a_b_with_sheet):
    # "Line 5", the first line, fits the 36 pt line column; "Line 10" doesn't, so every
    # Generate of ten rows or more would fail. Row 9999's line is the widest checked.
    _edit(
        schedule_a_b_with_sheet,
        "schedule_a_b",
        lambda d: d["groups"]["ab_line_3"].update(number="Line {n}"),
    )
    assert _errors("schedule_a_b") == [
        (
            "forms.E007",
            "schedule_a_b: group 'ab_line_3': its sheet can't print row 9999's line, "
            "'Line 9999', whole in the 36 pt line column",
        )
    ]


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
    # Each vehicle's community-property box, ticked from a list: a sheet has no box to tick.
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
            _sheet(lambda g: g.update(page_numbers=[{"page": 2}])),
            ("forms.E007", f"{_AB}: a sheet group has no copies, so it numbers no pages"),
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
                "not a sofa.<collection>[].<attr> list",
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
            _a_column_of_boxes,
            (
                "forms.E007",
                f"{_AB}: sheet column 'Community property' binds a box's answer, "
                "which a sheet can't tick",
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
            # Rows 1 to 4 tick their boxes on the form; a fifth row has no box to tick.
            _community_property_boxes,
            (
                "forms.E007",
                f"{_AB}: a box slot binds 'sofa.creditor_payments[].dates_of_payments', "
                "and a sheet can't tick a box",
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
        "a slot with no column",
        "a box slot",
        "a first line wider than the line column",
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


def test_manage_py_check_fails_on_a_bad_schema(schema_copy):
    """migrate runs the same checks, so this is what fails a Heroku release."""
    _edit(schema_copy, "form_121", lambda d: d.update(template_version="0" * 64))
    with pytest.raises(SystemCheckError, match="forms.E002"):
        call_command("check")
