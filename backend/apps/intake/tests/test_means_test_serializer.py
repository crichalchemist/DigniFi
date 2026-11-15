"""The PUT refuses an answer no question could take before it locks the session or reads a row."""

from decimal import Decimal

import pytest

from apps.intake import serializers as means_serializers
from apps.intake.means_test import (
    ANSWER_KEYS,
    LIST_KEYS,
    MEANS_EXPLANATION_LETTER,
    MEANS_EXPLANATION_TOO_LONG,
    MEANS_TOO_LONG,
    NOT_A_MEANS_ANSWER,
)
from apps.intake.serializers import (
    DEBT_SENT_TWICE,
    DIFFERENT_VEHICLES,
    NOT_A_MEANS_CHOICE,
    NOT_A_PAYMENTS_LEFT,
    NOT_A_VEHICLE,
    NOT_IN_THIS_SAVE,
    OWN_VEHICLE_ON_AMOUNTS_OWED,
    ROW_NEEDS_ITS_ID,
    MeansTestSerializer,
)


def check(data):
    serializer = MeansTestSerializer(data=data, partial=True)
    valid = serializer.is_valid()
    return valid, serializer


def errors_of(data):
    valid, serializer = check(data)
    assert not valid, data
    return serializer.errors


def stored_of(data):
    valid, serializer = check(data)
    assert valid, serializer.errors
    return serializer.validated_data


def test_the_serializer_takes_exactly_the_page_answers_and_the_debts():
    assert set(MeansTestSerializer().fields) == {*ANSWER_KEYS, "debts"}


@pytest.mark.parametrize(
    "data, path",
    [
        ({"line_99": 1}, ["line_99"]),
        ({"line_3_rows": [{"nope": 1}]}, ["line_3_rows", 0, "nope"]),
        ({"spouse_vehicles": [{"nope": 1}]}, ["spouse_vehicles", 0, "nope"]),
        ({"spouse_loans": [{"nope": 1}]}, ["spouse_loans", 0, "nope"]),
        ({"debts": [{"id": 1, "nope": 1}]}, ["debts", 0, "nope"]),
        ({"line_43_circumstances": [{"nope": 1}]}, ["line_43_circumstances", 0, "nope"]),
    ],
)
def test_an_unknown_key_is_refused_by_name(data, path):
    node = errors_of(data)
    for step in path:
        node = node[step]
    assert [str(m) for m in node] == [NOT_A_MEANS_ANSWER]


def test_an_answer_outside_its_choices_is_refused_without_repeating_it():
    errors = errors_of({"line_3_answer": "maybe"})
    assert [str(m) for m in errors["line_3_answer"]] == [NOT_A_MEANS_CHOICE]
    assert "maybe" not in str(errors)


@pytest.mark.parametrize("amount", ["-1.00", "10000000000.00"])
def test_an_amount_below_0_or_too_wide_is_refused(amount):
    assert "line_16" in errors_of({"line_16": amount})


def test_an_amount_of_minus_0_is_stored_without_its_sign():
    top = stored_of({"line_16": "-0"})
    assert top["line_16"] == Decimal("0.00")
    assert str(top["line_16"]) == "0.00"
    row = stored_of({"line_3_rows": [{"purpose": "Demo", "amount": "-0"}]})
    assert str(row["line_3_rows"][0]["amount"]) == "0.00"


@pytest.mark.parametrize(
    "value, stored",
    [(0, "0"), (59, "59"), ("60_or_more", "60_or_more")],
)
def test_payments_left_takes_only_0_to_59_or_60_or_more_stored(value, stored):
    row = stored_of({"debts": [{"id": 4, "payments_left": value}]})["debts"][0]
    assert row["payments_left"] == stored


@pytest.mark.parametrize("value", [60, -1, "12", True, "sixty"])
def test_payments_left_takes_only_0_to_59_or_60_or_more(value):
    errors = errors_of({"debts": [{"id": 4, "payments_left": value}]})
    assert [str(m) for m in errors["debts"][0]["payments_left"]] == [NOT_A_PAYMENTS_LEFT]
    assert "sixty" not in str(errors)


def test_payments_left_reads_back_as_an_integer_or_60_or_more():
    field = means_serializers.PaymentsLeftField()
    assert field.to_representation("12") == 12
    assert field.to_representation("60_or_more") == "60_or_more"


@pytest.mark.parametrize("key", LIST_KEYS)
def test_a_list_of_11_rows_is_refused(key):
    assert key in errors_of({key: [{}] * 11})


def test_debts_has_no_row_cap():
    rows = [{"id": n} for n in range(1, 13)]
    assert len(stored_of({"debts": rows})["debts"]) == 12


def test_an_aid_answer_past_450_characters_is_refused():
    errors = errors_of({"line_43_circumstances": [{"happened": "D" * 451}]})
    assert "happened" in errors["line_43_circumstances"][0]
    assert stored_of({"line_43_circumstances": [{"happened": "D" * 450}]})


def test_an_explanation_past_2000_characters_is_refused():
    errors = errors_of({"line_43_circumstances": [{"explanation": "D" * 2001}]})
    assert "explanation" in errors["line_43_circumstances"][0]


def test_an_explanation_of_spaces_and_line_breaks_is_stored_as_none():
    rows = stored_of({"line_43_circumstances": [{"explanation": "  \n \n "}]})
    assert rows["line_43_circumstances"][0]["explanation"] is None


def test_an_explanation_that_cant_print_is_refused_in_its_own_sentence():
    letter = errors_of({"line_43_circumstances": [{"explanation": "Demo □"}]})
    assert [str(m) for m in letter["line_43_circumstances"][0]["explanation"]] == [
        MEANS_EXPLANATION_LETTER
    ]
    long = errors_of({"line_43_circumstances": [{"explanation": "\n".join(["Demo"] * 40)}]})
    assert [str(m) for m in long["line_43_circumstances"][0]["explanation"]] == [
        MEANS_EXPLANATION_TOO_LONG
    ]


def test_a_line_3_purpose_too_long_for_its_box_is_refused():
    errors = errors_of({"line_3_rows": [{"purpose": "Demo " * 30}]})
    assert [str(m) for m in errors["line_3_rows"][0]["purpose"]] == [MEANS_TOO_LONG]


def test_a_stored_line_3_row_has_exactly_purpose_and_amount():
    row = stored_of({"line_3_rows": [{"purpose": "Demo tax debt", "amount": "10"}]})
    assert set(row["line_3_rows"][0]) == {"purpose", "amount"}


def test_words_that_do_not_fit_a_box_the_loan_could_print_in_are_refused():
    vehicle = errors_of(
        {
            "spouse_vehicles": [
                {"ref": "new-1", "description": "2019 Toyota Sienna LE minivan"},
            ]
        }
    )
    assert [str(m) for m in vehicle["spouse_vehicles"][0]["description"]] == [MEANS_TOO_LONG]
    loan = errors_of(
        {
            "spouse_loans": [
                {
                    "ref": "new-1",
                    "creditor": "Demo Prairie Credit Union of Illinois",
                    "property": "2019 Toyota Sienna LE minivan",
                }
            ]
        }
    )
    row = loan["spouse_loans"][0]
    assert [str(m) for m in row["creditor"]] == [MEANS_TOO_LONG]
    assert [str(m) for m in row["property"]] == [MEANS_TOO_LONG]


def test_a_stored_loan_debt_is_an_int():
    row = stored_of({"spouse_loans": [{"ref": "new-1", "debt": "12"}]})["spouse_loans"][0]
    assert row["debt"] == 12
    assert isinstance(row["debt"], int)


def test_a_loan_on_the_amounts_owed_step_is_never_secured_by_the_filers_own_vehicle():
    errors = errors_of(
        {"spouse_loans": [{"ref": "spouse-1", "on_amounts_owed": "yes", "secured_by": "asset-3"}]}
    )
    assert [str(m) for m in errors["spouse_loans"][0]["secured_by"]] == [
        OWN_VEHICLE_ON_AMOUNTS_OWED
    ]
    assert stored_of(
        {"spouse_loans": [{"ref": "spouse-1", "on_amounts_owed": "no", "secured_by": "asset-3"}]}
    )


def test_a_secured_by_that_is_no_vehicle_or_property_is_refused():
    errors = errors_of({"spouse_loans": [{"ref": "spouse-1", "secured_by": "boat"}]})
    assert [str(m) for m in errors["spouse_loans"][0]["secured_by"]] == [NOT_A_VEHICLE]


def test_vehicle_1_and_2_must_be_different_vehicles():
    errors = errors_of({"vehicle_choice": ["asset-1", "asset-1"]})
    assert [str(m) for m in errors["vehicle_choice"]] == [DIFFERENT_VEHICLES]
    assert stored_of({"vehicle_choice": ["asset-1", None]})
    assert stored_of({"vehicle_choice": [None, None]})
    assert "vehicle_choice" in errors_of({"vehicle_choice": ["asset-1"]})


def test_a_vehicle_claim_key_must_name_a_filer_vehicle():
    errors = errors_of({"vehicle_claims": {"spouse-1": "yes"}})
    assert [str(m) for m in errors["vehicle_claims"]["spouse-1"]] == [NOT_A_VEHICLE]
    assert stored_of({"vehicle_claims": {"asset-1": "yes", "asset-2": None}})
    bad = errors_of({"vehicle_claims": {"asset-1": "maybe"}})
    assert "maybe" not in str(bad)


def test_a_new_vehicle_named_but_not_sent_is_refused():
    loan = errors_of({"spouse_loans": [{"ref": "new-1", "secured_by": "new-2"}]})
    assert [str(m) for m in loan["spouse_loans"][0]["secured_by"]] == [NOT_IN_THIS_SAVE]
    choice = errors_of({"vehicle_choice": ["new-2", None]})
    assert [str(m) for m in choice["vehicle_choice"]] == [NOT_IN_THIS_SAVE]
    assert stored_of(
        {
            "spouse_vehicles": [{"ref": "new-2"}],
            "spouse_loans": [{"ref": "new-1", "secured_by": "new-2"}],
            "vehicle_choice": ["new-2", None],
        }
    )


def test_a_debt_is_sent_at_most_once_and_always_with_its_id():
    twice = errors_of({"debts": [{"id": 5}, {"id": 5}]})
    assert [str(m) for m in twice["debts"][1]["id"]] == [DEBT_SENT_TWICE]
    for row in ({"payments_left": 3}, {"id": None, "payments_left": 3}):
        errors = errors_of({"debts": [row]})
        assert [str(m) for m in errors["debts"][0]["id"]] == [ROW_NEEDS_ITS_ID]


def test_null_clears_every_nullable_answer():
    data = {key: None for key in ANSWER_KEYS}
    data["debts"] = None
    assert stored_of(data)


def test_every_refusal_is_a_fixed_sentence():
    sent = {
        "line_3_answer": "maybe",
        "line_16": "sixty",
        "line_3_rows": [{"purpose": "Demo " * 30, "amount": "x"}],
        "debts": [{"id": 1, "payments_left": "sixty"}, {"id": 1}],
        "vehicle_claims": {"boat-sixty": "maybe"},
        "vehicle_choice": ["asset-1", "asset-1"],
        "spouse_loans": [{"ref": "sixty", "secured_by": "sixty"}],
        "spouse_vehicles": [{"ref": "sixty"}],
        "line_43_circumstances": [{"explanation": "Demo □ sixty"}],
        "line_99": 1,
    }
    errors = errors_of(sent)
    sentences = {
        NOT_A_MEANS_CHOICE,
        NOT_A_PAYMENTS_LEFT,
        NOT_A_VEHICLE,
        means_serializers.NOT_A_ROW,
        OWN_VEHICLE_ON_AMOUNTS_OWED,
        DEBT_SENT_TWICE,
        ROW_NEEDS_ITS_ID,
        DIFFERENT_VEHICLES,
        NOT_IN_THIS_SAVE,
        MEANS_TOO_LONG,
        MEANS_EXPLANATION_TOO_LONG,
        MEANS_EXPLANATION_LETTER,
        NOT_A_MEANS_ANSWER,
    }
    messages = []

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        else:
            messages.append(str(node))

    walk(errors)
    assert messages
    for message in messages:
        assert message in sentences or message.startswith(("Ensure", "A valid number")), message
        for value in ("maybe", "sixty", "Demo"):
            assert value not in message
