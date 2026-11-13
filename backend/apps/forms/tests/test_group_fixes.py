"""
R12: a refusal for a page number too wide names the fix of the first group on copies.

Business intent: when a page number can't fit, the filer is sent to the step that changes the
rows. That is only honest if every group on copies of one form is changed on the same step
(D: debts, E/F: debts, G: contracts, H: codebtors), so "the first" is as good as any.
"""

import pytest

from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema, number_box_keys, page_number_keys, total_box_keys
from apps.forms.services.fill_resolver import group_fix
from apps.forms.services.pdf_filler import _group_box


@pytest.mark.parametrize("form_type", get_all_form_types())
def test_a_forms_groups_on_copies_share_one_fix(form_type):
    schema = load_schema(form_type)

    fixes = {
        tuple(sorted(group_fix(schema, name).items()))
        for name, group in schema.groups.items()
        if group.extra_page is not None
    }

    assert len(fixes) <= 1, fixes


@pytest.mark.parametrize(
    "form_type,step",
    [
        ("schedule_d", "debts"),
        ("schedule_e_f", "debts"),
        ("schedule_g", "contracts"),
        ("schedule_h", "codebtors"),
    ],
)
def test_every_group_box_of_a_claims_schedule_sends_the_filer_to_its_rows_step(form_type, step):
    # Agreeing on one fix isn't enough: it must be the step where the filer changes these rows.
    schema = load_schema(form_type)
    keys = number_box_keys(schema) | page_number_keys(schema)
    keys |= {key for group in schema.groups.values() for key in total_box_keys(group)}

    fixes = {key: _group_box(schema, key)[1] for key in keys}

    assert keys
    assert fixes == dict.fromkeys(keys, {"step": step})


def test_schedule_cs_page_numbers_send_the_filer_to_the_exemptions_page():
    # Schedule C's copies hold the filer's claims, which they change on the exemptions page.
    schema = load_schema("schedule_c")
    keys = page_number_keys(schema)

    fixes = {key: _group_box(schema, key)[1] for key in keys}

    assert keys
    assert fixes == dict.fromkeys(keys, {"page": "/exemptions"})
