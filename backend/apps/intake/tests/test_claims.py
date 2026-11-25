"""Which of the filer's leases Form 108 asks about (4e-R23): every lease but a residential one.

Business intent: a residential lease belongs on Form 101A's questions, never on Form 108's
"Will the lease be assumed?"; a lease stored with no kind (an API client's row) is still asked,
so no personal-property lease drops off the form.
"""

from types import SimpleNamespace

import pytest

from apps.intake.claims import FORM_108_LEASE_KINDS, is_form_108_lease


@pytest.mark.parametrize(
    ("contract_type", "lease_kind", "asked"),
    [
        ("lease", "vehicle", True),
        ("lease", "other_personal_property", True),
        ("lease", "other", True),
        ("lease", None, True),
        ("lease", "residential", False),
        ("contract", "vehicle", False),
        ("", "vehicle", False),
    ],
)
def test_a_form_108_lease_is_any_lease_but_residential(contract_type, lease_kind, asked):
    contract = SimpleNamespace(contract_type=contract_type, lease_kind=lease_kind)
    assert is_form_108_lease(contract) is asked


def test_the_kinds_are_the_four_the_form_reaches():
    assert FORM_108_LEASE_KINDS == ("vehicle", "other_personal_property", "other", None)
