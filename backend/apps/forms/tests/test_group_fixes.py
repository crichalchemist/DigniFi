"""
R12: a refusal for a page number too wide names the fix of the first group on copies.

Business intent: when a page number can't fit, the filer is sent to the step that changes the
rows. That is only honest if every group on copies of one form is changed on the same step
(D: debts, E/F: debts, G: contracts, H: codebtors), so "the first" is as good as any.
"""

import pytest

from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import group_fix


@pytest.mark.parametrize("form_type", get_all_form_types())
def test_a_forms_groups_on_copies_share_one_fix(form_type):
    schema = load_schema(form_type)

    fixes = {
        tuple(sorted(group_fix(schema, name).items()))
        for name, group in schema.groups.items()
        if group.extra_page is not None
    }

    assert len(fixes) <= 1, fixes
