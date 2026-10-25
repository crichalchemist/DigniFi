"""Each form counts the household list by its own definition (3e1 spec §4.4).

Business intent: 122A-1 line 13 counts everyone at home, 122A-2 line 5 everyone claimed or
supported, Schedule J line 2 the dependents, and 103B line 1 the people in the household. So a
spouse or a roommate counts on one form and not another, and no one is counted twice.
"""

import pytest

from apps.intake.household import (
    count_exemptions,
    count_family_size,
    count_fee_waiver_household,
    dependents,
    is_answered,
)


def _row(relationship, age, lives_with_you, claimed_or_supported, **spouse):
    return {
        "relationship": relationship,
        "age": age,
        "lives_with_you": lives_with_you,
        "claimed_or_supported": claimed_or_supported,
        **spouse,
    }


# The persona targets' lists (§11); each spouse answered No to "Is your spouse a dependent of
# yours?" (3e1.Q1).
MARIA = [_row("son", 8, True, True), _row("daughter", 5, True, True)]
JAMES = []
PRIYA = [
    _row("spouse", 45, True, True, spouse_is_dependent=False),
    _row("daughter", 10, True, True),
    _row("son", 7, True, True),
]
DESHAWN = [_row("spouse", 44, True, True, spouse_is_dependent=False)]
SARAH = [_row("roommate", 29, True, False)]
ANDRES = [_row("daughter", 9, True, True)]


@pytest.mark.parametrize(
    "members, size",
    [(MARIA, 3), (JAMES, 1), (PRIYA, 4), (DESHAWN, 2), (SARAH, 2), (ANDRES, 2)],
    ids=["maria", "james", "priya", "deshawn", "sarah", "andres"],
)
def test_line_13_counts_the_filer_and_everyone_at_home(members, size):
    assert count_family_size(members) == size


def test_a_roommate_counts_in_line_13_but_not_as_a_dependent():
    assert count_family_size(SARAH) == 2
    assert dependents(SARAH) == []
    assert count_exemptions(SARAH) == 1


def test_a_spouse_on_a_joint_tax_return_isnt_a_dependent_unless_the_filer_says_so():
    assert dependents(PRIYA) == [PRIYA[1], PRIYA[2]]
    assert dependents(DESHAWN) == []
    spouse = {**DESHAWN[0], "spouse_is_dependent": True}
    assert dependents([spouse]) == [spouse]


def test_line_5_counts_everyone_claimed_or_supported():
    assert count_exemptions(PRIYA) == 4


@pytest.mark.parametrize("marital_status", ["married_together", "married_spouse_filing"])
@pytest.mark.parametrize("spouse_is_dependent", [False, True])
def test_103b_counts_a_spouse_at_home_once(marital_status, spouse_is_dependent):
    spouse = {**DESHAWN[0], "spouse_is_dependent": spouse_is_dependent}
    assert count_fee_waiver_household([spouse], marital_status) == 2
    assert count_fee_waiver_household(MARIA, "not_married") == 3
    assert count_fee_waiver_household(SARAH, "not_married") == 1


@pytest.mark.parametrize("spouse_is_dependent, size", [(True, 2), (False, 1)])
def test_103b_counts_a_separated_spouse_only_as_a_dependent(spouse_is_dependent, size):
    members = [_row("spouse", 44, False, True, spouse_is_dependent=spouse_is_dependent)]
    assert count_fee_waiver_household(members, "married_separately") == size


@pytest.mark.parametrize(
    "row, answered",
    [
        (_row("son", 8, True, True), True),
        (_row("son", 0, False, False), True),
        (_row("spouse", 45, True, True, spouse_is_dependent=False), True),
        (_row("son", None, True, True), False),
        (_row(None, 8, True, True), False),
        (_row("son", 8, True, None), False),
        (_row("spouse", 45, True, True), False),
        (_row("spouse", 45, True, True, spouse_is_dependent=None), False),
    ],
)
def test_a_row_is_answered_only_when_every_question_is(row, answered):
    assert is_answered(row) is answered
