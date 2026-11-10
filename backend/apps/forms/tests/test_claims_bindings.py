"""
claims.<list>[].<attr>: the rows Schedules D, E/F, G and H print, and H line 2's rules (3c5 spec §9).

Business intent: a sworn box prints only an answer the filer was asked and can see (R4), a
creditor's address outside the US prints no state or ZIP, and a debt stored at $0 prints 0.00,
never a blank that would hide it from a group's total.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.services.derivations import DERIVATIONS, RULE_FIXES
from apps.forms.services.fill_resolver import (
    CLAIM_CELLS,
    binding_fix,
    is_money_binding,
    resolve_binding,
)
from apps.intake.claim_rows import CLAIM_LISTS
from apps.intake.models import IntakeSession
from apps.intake.tests.builders import (
    DEMO_ADDRESS,
    answer_claims,
    complete_codebtor,
    complete_contract,
    complete_debt,
    linked_loan,
    linked_row,
)

User = get_user_model()

HOUSE_RULES = (
    "schedule_h_community_lived",
    "schedule_h_spouse_lived_with",
    "schedule_h_community_state",
    "schedule_h_spouse_name",
    "schedule_h_spouse_street",
    "schedule_h_spouse_city",
    "schedule_h_spouse_state",
    "schedule_h_spouse_zip",
)


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="claimsbind", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def _party(name="Demo Notice Co", **over):
    return {"name": name, **{k: DEMO_ADDRESS[k] for k in DEMO_ADDRESS}, "last_4": "9999"} | {
        "street_address": "1 Demo Street",
        "zip_code": "60601",
        **over,
    }


def _cell(session, binding):
    return resolve_binding(binding, session)


def test_every_claims_cell_resolves_one_value_a_row(session):
    secured_a = complete_debt(session, is_secured=True, creditor_name="Secured A")
    complete_debt(
        session,
        is_secured=True,
        creditor_name="Secured B",
        notice_parties=[_party()],
    )
    complete_debt(session, creditor_name="Unsecured A", notice_parties=[_party(), _party("Two")])
    complete_debt(session, creditor_name="Unsecured B")
    # bare: no lien, status, date, notice parties or offset answer
    bare = complete_debt(
        session,
        creditor_name="Bare",
        claim_status=None,
        offset_answer=None,
        notice_parties=None,
    )
    assert bare.get_notice_parties() is None
    complete_contract(session)
    complete_contract(session, counterparty_name="Second lease")
    complete_codebtor(session, links=[{"kind": "debt", "id": secured_a.pk}])
    expected = {
        "secured": 2,
        "secured_notices": 1,
        "unsecured": 3,
        "unsecured_notices": 2,
        "contracts": 2,
        "codebtors": 1,
    }
    assert set(expected) == set(CLAIM_LISTS)
    for name in CLAIM_LISTS:
        for attr in CLAIM_CELLS[name]:
            values = _cell(session, f"claims.{name}[].{attr}")
            assert len(values) == expected[name], (name, attr)
            assert all(isinstance(v, str) for v in values), (name, attr)


@pytest.mark.parametrize(
    "binding",
    ["claims.secured[].offset", "claims.priority[].name", "claims.secured.name"],
)
def test_an_unknown_claims_list_or_cell_is_refused(session, binding):
    with pytest.raises(ValueError, match="unrecognized binding"):
        resolve_binding(binding, session)


@pytest.mark.parametrize(
    "binding,fix",
    [
        ("claims.secured[].name", {"step": "debts"}),
        ("claims.secured_notices[].name", {"step": "debts"}),
        ("claims.unsecured[].name", {"step": "debts"}),
        ("claims.unsecured_notices[].name", {"step": "debts"}),
        ("claims.contracts[].name", {"step": "contracts"}),
        ("claims.codebtors[].name", {"step": "codebtors"}),
    ],
)
def test_a_claims_binding_sends_the_filer_to_its_step(binding, fix):
    assert binding_fix(binding) == fix


def test_an_address_outside_the_us_prints_no_state_or_zip(session):
    complete_debt(
        session,
        is_secured=True,
        outside_us=True,
        state="ON",
        zip_code="M5V 2T6",
        city="Toronto",
        notice_parties=[_party(outside_us=True, state="ON", zip_code="M5V 2T6", city="Toronto")],
    )
    for name in ("secured", "secured_notices"):
        assert _cell(session, f"claims.{name}[].state") == [""]
        assert _cell(session, f"claims.{name}[].zip") == [""]
        assert _cell(session, f"claims.{name}[].city") == ["Toronto"]
        assert _cell(session, f"claims.{name}[].street") == ["1 Demo Street"]


@pytest.mark.parametrize(
    "second,joined", [("Suite 4", "1 Demo Street, Suite 4"), ("", "1 Demo Street")]
)
def test_a_row_with_one_street_line_joins_the_second(session, second, joined):
    complete_contract(session, street_2=second)
    assert _cell(session, "claims.contracts[].street_joined") == [joined]


def test_a_debt_stored_at_zero_prints_zero(session):
    complete_debt(session, amount_owed=Decimal("0"))
    assert _cell(session, "claims.unsecured[].amount") == ["0.00"]


def test_a_secured_row_prints_the_filers_answers(session):
    complete_debt(
        session,
        is_secured=True,
        lien={"kinds": ["agreement", "other"], "other": "Demo lien"},
        claim_status=["contingent", "disputed"],
        community_debt="yes",
        date_incurred="2019",
        account_number="1234-5678",
        collateral_description="Demo car",
    )
    one = lambda attr: _cell(session, f"claims.secured[].{attr}")  # noqa: E731
    assert one("lien_agreement") == ["true"]
    assert one("lien_statutory") == [""]
    assert one("lien_other") == ["true"]
    assert one("lien_other_text") == ["Demo lien"]
    assert one("contingent") == ["true"]
    assert one("unliquidated") == [""]
    assert one("disputed") == ["true"]
    assert one("community") == ["true"]
    assert one("date") == ["2019"]
    assert one("last_4") == ["5678"]
    assert one("property") == ["Demo car"]
    assert one("who") == ["debtor_1"]


def test_an_unticked_other_lien_prints_no_words(session):
    complete_debt(
        session,
        is_secured=True,
        lien={"kinds": ["agreement"], "other": "Stale words"},
    )
    assert _cell(session, "claims.secured[].lien_other_text") == [""]


def test_an_unsecured_row_prints_its_type(session):
    complete_debt(session, debt_type="student_loan", creditor_name="A loan")
    complete_debt(session, debt_type="medical", creditor_name="B bill")
    assert _cell(session, "claims.unsecured[].student_loans") == ["true", ""]
    assert _cell(session, "claims.unsecured[].other_type") == ["", "true"]
    assert _cell(session, "claims.unsecured[].other_type_words") == ["", "Medical bill"]


def test_a_codebtor_makes_the_debt_owed_with_another(session):
    debt = complete_debt(session)
    complete_codebtor(session, links=[{"kind": "debt", "id": debt.pk}])
    assert _cell(session, "claims.unsecured[].who") == ["another"]
    assert _cell(session, "claims.unsecured[].who_another") == ["true"]
    assert _cell(session, "claims.unsecured[].who_debtor_1") == [""]
    assert _cell(session, "claims.codebtors[].on_ef") == ["true"]
    assert _cell(session, "claims.codebtors[].ef_lines") == ["4.1"]
    assert _cell(session, "claims.codebtors[].on_d") == [""]


def test_a_property_worth_nothing_prints_zero_in_column_b(session):
    row = linked_row(session, "3")
    row.set_details({"who": "only_you"})
    row.entire_value = Decimal("0")
    row.save()
    linked_loan(session, row, Decimal("100"), amount_owed=Decimal("8500"))
    assert _cell(session, "claims.secured[].value") == ["0.00"]
    assert _cell(session, "claims.secured[].unsecured") == ["8500.00"]


def test_money_bindings_are_the_amount_columns():
    assert is_money_binding("claims.secured[].amount")
    assert is_money_binding("claims.secured[].value")
    assert is_money_binding("claims.secured[].unsecured")
    assert is_money_binding("sofa.creditor_payments[].total_paid")
    assert not is_money_binding("claims.secured[].name")
    assert not is_money_binding("sofa.creditor_payments[].creditor_name")


def _h(session):
    return {rule: DERIVATIONS[rule](session) for rule in HOUSE_RULES}


SPOUSE = {
    "community_state": "Wisconsin",
    "community_spouse_name": "Demo Spouse",
    "community_spouse_street_address": "2 Demo Street",
    "community_spouse_street_2": "Apt 5",
    "community_spouse_city": "Madison",
    "community_spouse_state": "WI",
    "community_spouse_zip_code": "53703",
}


def test_schedule_h_line_2_prints_only_what_the_filer_was_asked(session):
    # No: nothing else was asked, so a stale answer prints nowhere.
    answer_claims(session, community_lived="no", community_spouse_lived_with="yes", **SPOUSE)
    assert _h(session) == dict.fromkeys(HOUSE_RULES, "")

    # Yes, spouse did not live with the filer: line 2's box 3 stays blank, no name or address.
    answer_claims(session, community_lived="yes", community_spouse_lived_with="no", **SPOUSE)
    assert _h(session) == {**dict.fromkeys(HOUSE_RULES, ""), "schedule_h_community_lived": "true"}

    # Yes and Yes: the state, the name and the address, the street joined with its second line.
    answer_claims(session, community_lived="yes", community_spouse_lived_with="yes", **SPOUSE)
    assert _h(session) == {
        "schedule_h_community_lived": "true",
        "schedule_h_spouse_lived_with": "true",
        "schedule_h_community_state": "Wisconsin",
        "schedule_h_spouse_name": "Demo Spouse",
        "schedule_h_spouse_street": "2 Demo Street, Apt 5",
        "schedule_h_spouse_city": "Madison",
        "schedule_h_spouse_state": "WI",
        "schedule_h_spouse_zip": "53703",
    }

    # A spouse's address outside the US prints no state or ZIP.
    answer_claims(
        session,
        community_lived="yes",
        community_spouse_lived_with="yes",
        community_spouse_outside_us=True,
        **SPOUSE,
    )
    answers = _h(session)
    assert answers["schedule_h_spouse_state"] == answers["schedule_h_spouse_zip"] == ""
    assert answers["schedule_h_spouse_city"] == "Madison"


def test_schedule_h_text_rules_send_the_filer_to_the_codebtors_step():
    for rule in HOUSE_RULES[2:]:
        assert RULE_FIXES[rule] == {"step": "codebtors"}
    assert not {"schedule_h_community_lived", "schedule_h_spouse_lived_with"} & RULE_FIXES.keys()
