"""A page answer that names a row that has gone reads as unanswered, so a later save never trips over it."""

import copy

from apps.intake.means_test import ANSWER_KEYS, LIST_KEYS, PROPERTY_CHOICES, normalized_answers

CAR = "asset-7"


def _loan(ref, **over):
    return {"ref": ref, "on_amounts_owed": "no", "debt": None, "secured_by": None} | over


def test_every_key_is_present_unanswered_when_nothing_is_stored():
    got = normalized_answers({}, set(), set())
    assert list(got) == list(ANSWER_KEYS)
    for key in ANSWER_KEYS:
        if key in LIST_KEYS:
            assert got[key] == []
        elif key == "vehicle_claims":
            assert got[key] == {}
        elif key == "vehicle_choice":
            assert got[key] == [None, None]
        else:
            assert got[key] is None


def test_a_key_stored_as_null_reads_as_unanswered_as_an_absent_one_does():
    stored = {"line_16": None, "line_3_rows": None, "vehicle_claims": None, "vehicle_choice": None}
    assert normalized_answers(stored, set(), set()) == normalized_answers({}, set(), set())


def test_a_typed_0_is_an_answer_and_a_missing_purpose_reads_as_blank():
    stored = {"line_16": "0.00", "line_3_rows": [{"amount": "5.00"}]}
    got = normalized_answers(stored, set(), set())
    assert got["line_16"] == "0.00"
    assert got["line_3_rows"] == [{"amount": "5.00"}]


def test_a_claim_on_a_vehicle_that_has_gone_is_dropped():
    stored = {"vehicle_claims": {CAR: "yes", "asset-8": "no"}}
    assert normalized_answers(stored, {CAR}, set())["vehicle_claims"] == {CAR: "yes"}


def test_a_vehicle_choice_naming_a_vehicle_that_has_gone_reads_as_unanswered():
    stored = {"vehicle_choice": [CAR, "asset-8"]}
    assert normalized_answers(stored, {CAR}, set())["vehicle_choice"] == [CAR, None]


def test_a_half_made_vehicle_choice_survives_a_reload():
    stored = {"vehicle_choice": [None, CAR]}
    assert normalized_answers(stored, {CAR}, set())["vehicle_choice"] == [None, CAR]


def test_a_spouse_vehicle_counts_only_while_the_spouse_vehicles_answer_is_yes():
    rows = [{"ref": "spouse-1", "description": "Demo", "leased": "no", "claimed": "yes"}]
    stored = {"spouse_vehicles": rows, "vehicle_choice": [CAR, "spouse-1"]}
    yes = normalized_answers(stored | {"spouse_vehicles_answer": "yes"}, {CAR}, set())
    no = normalized_answers(stored | {"spouse_vehicles_answer": "no"}, {CAR}, set())
    assert yes["vehicle_choice"] == [CAR, "spouse-1"]
    assert no["vehicle_choice"] == [CAR, None]
    assert no["spouse_vehicles"] == rows


def test_a_loan_naming_a_debt_that_is_gone_or_now_secured_reads_as_unanswered():
    loans = [_loan("spouse-1", on_amounts_owed="yes", debt=4)]
    stored = {"spouse_loans": loans}
    assert normalized_answers(stored, set(), {4})["spouse_loans"][0]["debt"] == 4
    assert normalized_answers(stored, set(), set())["spouse_loans"][0]["debt"] is None


def test_a_loan_not_on_the_amounts_owed_step_names_no_debt():
    loans = [_loan("spouse-1", on_amounts_owed="no", debt=4)]
    got = normalized_answers({"spouse_loans": loans}, set(), {4})
    assert got["spouse_loans"][0]["debt"] is None


def test_two_loans_naming_one_debt_keep_it_on_the_first():
    loans = [
        _loan("spouse-1", on_amounts_owed="yes", debt=4),
        _loan("spouse-2", on_amounts_owed="yes", debt=4),
    ]
    got = normalized_answers({"spouse_loans": loans}, set(), {4})["spouse_loans"]
    assert [loan["debt"] for loan in got] == [4, None]


def test_a_loan_on_the_amounts_owed_step_names_no_vehicle_of_the_filers():
    vehicle = [{"ref": "spouse-1", "description": "Demo", "leased": "no", "claimed": "no"}]
    loans = [
        _loan("spouse-1", on_amounts_owed="yes", debt=1, secured_by=CAR),
        _loan("spouse-2", on_amounts_owed="yes", debt=2, secured_by="spouse-1"),
        _loan("spouse-3", on_amounts_owed="yes", debt=3, secured_by="home"),
        _loan("spouse-4", on_amounts_owed="yes", debt=4, secured_by="other"),
        _loan("spouse-5", on_amounts_owed="no", secured_by=CAR),
    ]
    stored = {"spouse_vehicles_answer": "yes", "spouse_vehicles": vehicle, "spouse_loans": loans}
    got = normalized_answers(stored, {CAR}, {1, 2, 3, 4})["spouse_loans"]
    assert [loan["secured_by"] for loan in got] == [None, "spouse-1", "home", "other", CAR]


def test_a_loan_naming_a_vehicle_that_has_gone_reads_as_unanswered():
    loans = [_loan("spouse-1", secured_by="asset-9"), _loan("spouse-2", secured_by="spouse-9")]
    got = normalized_answers({"spouse_loans": loans}, {CAR}, set())["spouse_loans"]
    assert [loan["secured_by"] for loan in got] == [None, None]


def test_the_property_choices_are_home_and_other():
    assert PROPERTY_CHOICES == ("home", "other")


def test_normalizing_never_changes_what_is_stored_and_copies_what_it_returns():
    stored = {
        "spouse_loans": [_loan("spouse-1", on_amounts_owed="yes", debt=4)],
        "line_3_rows": [{"purpose": "Demo", "amount": "1.00"}],
        "vehicle_claims": {CAR: "yes"},
    }
    before = copy.deepcopy(stored)
    got = normalized_answers(stored, {CAR}, set())
    got["line_3_rows"][0]["purpose"] = "changed"
    got["vehicle_claims"][CAR] = "no"
    assert stored == before
