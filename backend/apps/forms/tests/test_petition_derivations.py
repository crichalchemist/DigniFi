"""
The derivations Form 101 (11/26) prints through (forms step 4b, Task 3).

One stored answer feeds several boxes (a nine-digit number, a street's Number and Street),
each choice has its own single box, and a detail prints only under its Yes. A session with no
answer prints nothing, never a No the filer didn't give.
"""

from types import SimpleNamespace

import pytest

from apps.forms.services import derivations
from apps.forms.services.answer_records import PETITION_STEP_OF_KEY
from apps.forms.services.derivations import (
    DERIVATIONS,
    PREDICATES,
    RULE_FIXES,
    digits,
    nine_digit_slice,
    split_district_name,
    split_number_street,
)
from apps.forms.services.text_fit import fit
from apps.forms.services.widgets import template_widgets


def session(answers=None, ssn="", street="", district="Northern District of Illinois", fee=None):
    """A DB-free session: only the attributes the derivations read."""
    return SimpleNamespace(
        petition_answers=(
            None if answers is None else SimpleNamespace(get_answers=lambda: dict(answers))
        ),
        debtor_info=SimpleNamespace(ssn=ssn, street_address=street),
        district=SimpleNamespace(name=district),
        filing_fee=None if fee is None else SimpleNamespace(payment_choice=fee),
    )


def rule(name, s):
    return DERIVATIONS[name](s)


@pytest.mark.parametrize("value", ["900-70-1234", "900701234"])
def test_digit_rules_read_digits_through_dashes(value):
    s = session({"itin": value, "other_ssn": value})
    assert [rule(f"itin_last4_digit_{n}", s) for n in (1, 2, 3, 4)] == ["1", "2", "3", "4"]
    assert rule("itin_whole", s) == "900701234"
    assert rule("other_ssn_whole", s) == "900701234"
    ein = session({"ein": "12-3456789"})
    assert (rule("ein_prefix", ein), rule("ein_suffix", ein)) == ("12", "3456789")


@pytest.mark.parametrize("value", ["90070123", "9007012345", "", None])
def test_a_value_that_is_not_nine_digits_prints_blank_in_every_box(value):
    s = session({"itin": value, "other_ssn": value, "ein": value}, ssn=value)
    names = [f"{p}_last4_digit_{n}" for p in ("ssn", "itin") for n in (1, 2, 3, 4)]
    names += ["itin_whole", "other_ssn_whole", "ein_prefix", "ein_suffix"]
    assert [rule(name, s) for name in names] == [""] * len(names)


def test_the_ssn_last_four_print_one_digit_per_box_in_order():
    s = session(ssn="900-70-5678")
    assert [rule(f"ssn_last4_digit_{n}", s) for n in (1, 2, 3, 4)] == ["5", "6", "7", "8"]


def test_helpers_read_only_digits():
    assert digits("9-0 0") == "900"
    assert digits(None) == ""
    assert nine_digit_slice("123-45-6789", 0, 2) == "12"
    assert nine_digit_slice("12345678", 0, 2) == ""


@pytest.mark.parametrize(
    "street,number,rest",
    [
        ("1234 Main St", "1234", "Main St"),
        ("1234A Main St", "1234A", "Main St"),
        ("12-14 Main St", "12-14", "Main St"),
        ("Rural Route 2", "", "Rural Route 2"),
        ("1234 Main St Apt 3", "1234", "Main St Apt 3"),
        ("", "", ""),
    ],
)
def test_number_street_split(street, number, rest):
    assert split_number_street(street) == (number, rest)


def test_number_and_street_come_from_the_address_that_box_group_asks():
    s = session(
        {
            "mailing_answer": "yes",
            "mailing_street": "55 Oak Ave",
            "sole_proprietor_answer": "yes",
            "business_street": "9B Elm Rd",
            "hazard_answer": "yes",
            "hazard_street": "Rural Route 2",
        },
        street="1234 Main St",
    )
    assert (rule("home_number", s), rule("home_street", s)) == ("1234", "Main St")
    assert (rule("mailing_number", s), rule("mailing_street", s)) == ("55", "Oak Ave")
    assert (rule("business_number", s), rule("business_street", s)) == ("9B", "Elm Rd")
    assert (rule("hazard_number", s), rule("hazard_street", s)) == ("", "Rural Route 2")


def test_a_detail_address_prints_nothing_under_a_no_or_no_answer():
    stored = {"mailing_street": "55 Oak Ave", "business_street": "9 Elm", "hazard_street": "7 X"}
    for answers in (stored, {**stored, "mailing_answer": "no", "hazard_answer": "no"}):
        s = session(answers)
        for name in ("mailing", "business", "hazard"):
            assert rule(f"{name}_number", s) == rule(f"{name}_street", s) == ""


def test_the_court_splits_into_district_and_state():
    assert split_district_name("Northern District of Illinois") == ("Northern", "Illinois")
    assert split_district_name("Illinois") == ("", "Illinois")
    s = session()
    assert (rule("court_district", s), rule("court_state", s)) == ("Northern", "Illinois")


_SINGLE_BOX_GROUPS = [
    ("venue_choice", ["venue_lived_here", "venue_other"], ["lived_here", "other"]),
    (
        "business_kind",
        [
            "business_kind_health_care",
            "business_kind_single_asset",
            "business_kind_stockbroker",
            "business_kind_commodity_broker",
            "business_kind_none",
        ],
        ["health_care", "single_asset", "stockbroker", "commodity_broker", "none"],
    ),
    (
        "credit_counseling",
        [
            "credit_counseling_certificate",
            "credit_counseling_no_certificate",
            "credit_counseling_exigent",
            "credit_counseling_not_required",
        ],
        ["certificate", "no_certificate", "exigent", "not_required"],
    ),
    (
        "not_required_reason",
        ["not_required_incapacity", "not_required_disability", "not_required_active_duty"],
        ["incapacity", "disability", "active_duty"],
    ),
    ("paid_preparer", ["paid_preparer_no", "paid_preparer_yes"], ["no", "yes"]),
    ("sole_proprietor_answer", ["sole_proprietor_no", "sole_proprietor_yes"], ["no", "yes"]),
]


@pytest.mark.parametrize("key,rules,values", _SINGLE_BOX_GROUPS)
def test_exactly_one_box_ticks_per_value_and_none_for_absent(key, rules, values):
    for index, value in enumerate(values):
        # A kind and a reason are read only under their gates; satisfy them, then the answer.
        s = session(
            {"sole_proprietor_answer": "yes", "credit_counseling": "not_required", key: value}
        )
        ticked = [r for r in rules if rule(r, s) == "true"]
        assert ticked == [rules[index]], (value, ticked)
        assert {rule(r, s) for r in rules} <= {"true", ""}
    assert [rule(r, session({})) for r in rules] == [""] * len(rules)
    assert [rule(r, session(None)) for r in rules] == [""] * len(rules)


def test_the_fee_choice_has_one_box_per_choice_and_none_while_unanswered():
    rules = ["fee_choice_pay_in_full", "fee_choice_installments", "fee_choice_waiver"]
    for index, value in enumerate(["pay_in_full", "installments", "waiver"]):
        ticked = [r for r in rules if rule(r, session(fee=value)) == "true"]
        assert ticked == [rules[index]]
    assert [rule(r, session()) for r in rules] == [""] * 3


def test_the_eviction_boxes_print_only_under_a_rent_yes():
    stale = session({"rents_residence": "no", "eviction_judgment": "yes"})
    assert (rule("eviction_no", stale), rule("eviction_yes", stale)) == ("", "")
    unasked = session({"eviction_judgment": "yes"})
    assert (rule("eviction_no", unasked), rule("eviction_yes", unasked)) == ("", "")
    rent = session({"rents_residence": "yes", "eviction_judgment": "yes"})
    assert (rule("eviction_no", rent), rule("eviction_yes", rent)) == ("", "true")
    no = session({"rents_residence": "yes", "eviction_judgment": "no"})
    assert (rule("eviction_no", no), rule("eviction_yes", no)) == ("true", "")


def test_the_business_kind_prints_only_under_a_sole_proprietor_yes():
    s = session({"sole_proprietor_answer": "no", "business_kind": "none"})
    assert rule("business_kind_none", s) == ""


def test_line_16_consumer_leaves_16b_blank_and_neither_fills_both_nos():
    names = ["debt_nature_16a_yes", "debt_nature_16a_no", "debt_nature_16b_yes"]
    names.append("debt_nature_16b_no")

    def ticked(nature):
        s = session({"debt_nature": nature})
        return [n for n in names if rule(n, s) == "true"]

    assert ticked("consumer") == ["debt_nature_16a_yes"]
    assert ticked("business") == ["debt_nature_16a_no", "debt_nature_16b_yes"]
    assert ticked("neither") == ["debt_nature_16a_no", "debt_nature_16b_no"]
    assert ticked("") == []


def test_a_reason_prints_only_under_not_required():
    s = session({"credit_counseling": "certificate", "not_required_reason": "disability"})
    assert rule("not_required_disability", s) == ""
    s = session({"credit_counseling": "not_required", "not_required_reason": "disability"})
    assert rule("not_required_disability", s) == "true"


def test_itin_answer_no_ticks_form_121s_box_for_a_no_only():
    assert rule("itin_answer_no", session({"itin_answer": "no"})) == "true"
    assert rule("itin_answer_no", session({"itin_answer": "yes"})) == ""
    assert rule("itin_answer_no", session({})) == ""


def test_the_range_rules_tick_one_box_for_the_stored_range(monkeypatch):
    monkeypatch.setattr(derivations, "_total_assets", lambda s: "75000.00")
    monkeypatch.setattr(derivations, "_total_debts", lambda s: "999999999999")
    s = session()
    assets = [n for n in DERIVATIONS if n.startswith("total_assets_is_")]
    debts = [n for n in DERIVATIONS if n.startswith("total_debts_is_")]
    assert len(assets) == len(debts) == 12
    assert [n for n in assets if rule(n, s) == "true"] == ["total_assets_is_50001"]
    assert [n for n in debts if rule(n, s) == "true"] == ["total_debts_is_more"]
    creditors = [n for n in DERIVATIONS if n.startswith("creditor_count_is_")]
    assert sorted(creditors) == sorted(
        f"creditor_count_is_{k}"
        for k in ("1", "50", "100", "200", "1000", "5001", "10001", "25001", "50001", "more")
    )


def test_the_predicates_read_the_record_and_are_false_without_one():
    pairs = {
        "petition_other_names_yes": ("other_names_answer", "yes"),
        "petition_itin_yes": ("itin_answer", "yes"),
        "petition_other_ssn_yes": ("other_ssn_answer", "yes"),
        "petition_mailing_yes": ("mailing_answer", "yes"),
        "petition_venue_other": ("venue_choice", "other"),
        "petition_prior_bankruptcy_yes": ("prior_bankruptcy_answer", "yes"),
        "petition_pending_case_yes": ("pending_case_answer", "yes"),
        "petition_sole_proprietor_yes": ("sole_proprietor_answer", "yes"),
        "petition_hazard_yes": ("hazard_answer", "yes"),
        "petition_rents_yes": ("rents_residence", "yes"),
        "petition_debt_nature_neither": ("debt_nature", "neither"),
        "petition_credit_counseling_exigent": ("credit_counseling", "exigent"),
        "petition_paid_preparer_yes": ("paid_preparer", "yes"),
    }
    for name, (key, value) in pairs.items():
        assert PREDICATES[name](session({key: value})) is True, name
        assert PREDICATES[name](session({key: "no" if value != "no" else "yes"})) is False
        assert PREDICATES[name](session(None)) is False


def test_venue_reason_wraps_into_four_lines_and_the_fourth_carries_the_rest():
    short = session({"venue_reason": "My business is based here."})
    lines = [rule(f"venue_reason_line_{n}", short) for n in (1, 2, 3, 4)]
    assert lines == ["My business is based here.", "", "", ""]

    long_text = " ".join(f"word{n}" for n in range(200))
    s = session({"venue_reason": long_text})
    lines = [rule(f"venue_reason_line_{n}", s) for n in (1, 2, 3, 4)]
    assert all(lines)
    assert " ".join(lines) == long_text
    widget = next(
        w for w in template_widgets("form_b101.pdf") if w.full_name == "See 28 USC  1408 1"
    )
    # The first three lines fit the box at 6 pt; the fourth, holding the rest, is refused.
    assert all(fit(widget, "form_b101.pdf", line) is not None for line in lines[:3])
    assert fit(widget, "form_b101.pdf", lines[3]) is None


def test_a_word_wider_than_the_box_goes_whole_to_the_first_line_to_be_refused():
    s = session({"venue_reason": "x" * 300})
    assert rule("venue_reason_line_1", s) == "x" * 300
    assert rule("venue_reason_line_2", s) == ""


def test_every_petition_rule_has_a_fix_on_the_step_that_asks_it():
    asked = {
        "itin_whole": "itin",
        "other_ssn_whole": "other_ssn",
        "ein_prefix": "ein",
        "ein_suffix": "ein",
        "mailing_number": "mailing_street",
        "mailing_street": "mailing_street",
        "business_number": "business_street",
        "business_street": "business_street",
        "hazard_number": "hazard_street",
        "hazard_street": "hazard_street",
        "venue_lived_here": "venue_choice",
        "venue_other": "venue_choice",
        "eviction_no": "eviction_judgment",
        "eviction_yes": "eviction_judgment",
        "sole_proprietor_no": "sole_proprietor_answer",
        "sole_proprietor_yes": "sole_proprietor_answer",
        "paid_preparer_no": "paid_preparer",
        "paid_preparer_yes": "paid_preparer",
        "itin_answer_no": "itin_answer",
        "debt_nature_16a_yes": "debt_nature",
        "debt_nature_16a_no": "debt_nature",
        "debt_nature_16b_yes": "debt_nature",
        "debt_nature_16b_no": "debt_nature",
    }
    for n in (1, 2, 3, 4):
        asked[f"itin_last4_digit_{n}"] = "itin"
        asked[f"venue_reason_line_{n}"] = "venue_reason"
    for kind in ("health_care", "single_asset", "stockbroker", "commodity_broker", "none"):
        asked[f"business_kind_{kind}"] = "business_kind"
    for name in ("certificate", "no_certificate", "exigent", "not_required"):
        asked[f"credit_counseling_{name}"] = "credit_counseling"
    for name in ("incapacity", "disability", "active_duty"):
        asked[f"not_required_{name}"] = "not_required_reason"
    for rule_name, key in asked.items():
        assert RULE_FIXES[rule_name] == {"step": PETITION_STEP_OF_KEY[key]}, rule_name
    for n in (1, 2, 3, 4):
        assert RULE_FIXES[f"ssn_last4_digit_{n}"] == {"step": "debtor_info"}
    for name in ("home_number", "home_street"):
        assert RULE_FIXES[name] == {"step": "debtor_info"}
    for name in ("fee_choice_pay_in_full", "fee_choice_installments", "fee_choice_waiver"):
        assert RULE_FIXES[name] == {"page": "/filing-fee"}
    assert RULE_FIXES["court_district"] == RULE_FIXES["court_state"] == {}
    for name in DERIVATIONS:
        if name.startswith("creditor_count_is_") or name.startswith("total_debts_is_"):
            assert RULE_FIXES[name] == {"step": "debts"}, name
        if name.startswith("total_assets_is_"):
            assert RULE_FIXES[name] == {"step": "assets"}, name


@pytest.fixture
def db_session(db):
    from decimal import Decimal

    from apps.districts.models import District
    from apps.intake.models import IntakeSession
    from apps.users.models import User

    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    return IntakeSession.objects.create(user=user, district=district)


def test_line_18_ticks_the_box_of_the_confirmed_creditor_count_and_none_without_one(db_session):
    from apps.intake.tests.builders import complete_debt

    names = [n for n in DERIVATIONS if n.startswith("creditor_count_is_")]

    def ticked():
        return [n for n in names if rule(n, db_session) == "true"]

    # No confirmed debt: never a box for an answer nobody gave.
    assert ticked() == []
    complete_debt(db_session, is_draft=True)
    assert ticked() == [], "a draft is not counted"
    complete_debt(db_session)
    assert ticked() == ["creditor_count_is_1"]
    for n in range(2, 51):
        complete_debt(db_session, creditor_name=f"Creditor {n}")
    assert ticked() == ["creditor_count_is_50"]


def test_a_reason_typed_with_combining_marks_wraps_as_it_prints():
    import unicodedata

    decomposed = unicodedata.normalize("NFD", "café ") * 48
    composed = unicodedata.normalize("NFC", decomposed)
    assert decomposed != composed
    nums = (1, 2, 3, 4)
    got = [rule(f"venue_reason_line_{n}", session({"venue_reason": decomposed})) for n in nums]
    want = [rule(f"venue_reason_line_{n}", session({"venue_reason": composed})) for n in nums]
    assert got == want
    widget = next(
        w for w in template_widgets("form_b101.pdf") if w.full_name == "See 28 USC  1408 1"
    )
    assert all(got)
    assert all(fit(widget, "form_b101.pdf", line) is not None for line in got)
