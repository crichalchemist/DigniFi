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
    complete_debt(
        session,
        creditor_name="Part 1 Tax",
        priority_answer="taxes",
        past_due_amount=Decimal("0.00"),
    )
    complete_debt(
        session,
        creditor_name="Part 1 Fine",
        priority_answer="other",
        priority_other="Demo fine",
        past_due_amount=Decimal("0.00"),
    )
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
        "priority": 2,
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
    [
        "claims.secured[].offset",
        "claims.nonpriority[].name",
        "claims.secured.name",
        "claims.creditor_list[].name",
    ],
)
def test_an_unknown_claims_list_or_cell_is_refused(session, binding):
    with pytest.raises(ValueError, match="unrecognized binding"):
        resolve_binding(binding, session)


@pytest.mark.parametrize(
    "binding,fix",
    [
        ("claims.secured[].name", {"step": "debts"}),
        ("claims.secured_notices[].name", {"step": "debts"}),
        ("claims.priority[].name", {"step": "debts"}),
        ("claims.unsecured[].name", {"step": "debts"}),
        ("claims.unsecured_notices[].name", {"step": "debts"}),
        ("claims.contracts[].name", {"step": "contracts"}),
        ("claims.codebtors[].name", {"step": "codebtors"}),
    ],
)
def test_a_claims_binding_sends_the_filer_to_its_step(binding, fix):
    assert binding_fix(binding) == fix


_TORONTO = {"outside_us": True, "state": "ON", "zip_code": "M5V 2T6", "city": "Toronto"}


@pytest.mark.parametrize(
    "name,street,build",
    [
        ("secured", "street", lambda s: complete_debt(s, is_secured=True, **_TORONTO)),
        (
            "secured_notices",
            "street",
            lambda s: complete_debt(s, is_secured=True, notice_parties=[_party(**_TORONTO)]),
        ),
        ("unsecured", "street_joined", lambda s: complete_debt(s, **_TORONTO)),
        (
            "unsecured_notices",
            "street",
            lambda s: complete_debt(s, notice_parties=[_party(**_TORONTO)]),
        ),
        ("contracts", "street_joined", lambda s: complete_contract(s, **_TORONTO)),
        ("codebtors", "street_joined", lambda s: complete_codebtor(s, links=[], **_TORONTO)),
    ],
)
def test_an_address_outside_the_us_prints_no_state_or_zip(session, name, street, build):
    # Every row shape keeps its own address, so each list is held to B49 apart.
    build(session)
    assert _cell(session, f"claims.{name}[].state") == [""]
    assert _cell(session, f"claims.{name}[].zip") == [""]
    assert _cell(session, f"claims.{name}[].city") == ["Toronto"]
    assert _cell(session, f"claims.{name}[].{street}") == ["1 Demo Street"]


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


def test_a_debt_not_marked_community_ticks_no_community_box(session):
    # community_debt is "" unless the filer said yes (B33): "" must not read as an answer
    complete_debt(session, is_secured=True)
    complete_debt(session)
    assert _cell(session, "claims.secured[].community") == [""]
    assert _cell(session, "claims.unsecured[].community") == [""]


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
    assert is_money_binding("claims.priority[].priority_amount")
    assert is_money_binding("claims.priority[].nonpriority_amount")
    assert not is_money_binding("claims.priority[].other_specify")
    assert is_money_binding("sofa.creditor_payments[].total_paid")
    assert not is_money_binding("claims.secured[].name")
    assert not is_money_binding("sofa.creditor_payments[].creditor_name")


def test_a_part_1_row_prints_its_kind_and_its_own_figures(session):
    complete_debt(
        session,
        creditor_name="Demo Revenue",
        priority_answer="taxes",
        amount_owed=Decimal("5000.00"),
        priority_amount=Decimal("1200.00"),
        nonpriority_amount=None,
        past_due_amount=Decimal("1200.00"),
        street_2="Suite 2",
    )
    expected = {
        "amount": "5000.00",
        "priority_amount": "1200.00",
        "nonpriority_amount": "",
        "type_taxes": "true",
        "type_domestic_support": "",
        "type_intoxicated": "",
        "type_other": "",
        "street_2": "Suite 2",
    }
    for attr, value in expected.items():
        assert _cell(session, f"claims.priority[].{attr}") == [value], attr


def test_a_part_1_row_prints_other_words_only_under_other(session):
    complete_debt(
        session,
        creditor_name="A Restitution",
        priority_answer="other",
        priority_other="Demo restitution",
        past_due_amount=Decimal("0.00"),
    )
    complete_debt(
        session,
        creditor_name="B Tax",
        priority_answer="taxes",
        priority_other="Stale words",
        past_due_amount=Decimal("0.00"),
    )
    assert _cell(session, "claims.priority[].other_specify") == ["Demo restitution", ""]
    assert _cell(session, "claims.priority[].type_other") == ["true", ""]


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
    # No: check2 prints "no" (two-state box); nothing else was asked, so a stale answer prints nowhere.
    answer_claims(session, community_lived="no", community_spouse_lived_with="yes", **SPOUSE)
    assert _h(session) == {**dict.fromkeys(HOUSE_RULES, ""), "schedule_h_community_lived": "no"}

    # Yes, spouse did not live with the filer: check3 prints "no", no name or address.
    answer_claims(session, community_lived="yes", community_spouse_lived_with="no", **SPOUSE)
    assert _h(session) == {
        **dict.fromkeys(HOUSE_RULES, ""),
        "schedule_h_community_lived": "yes",
        "schedule_h_spouse_lived_with": "no",
    }

    # Yes and Yes: the state, the name and the address, the street joined with its second line.
    answer_claims(session, community_lived="yes", community_spouse_lived_with="yes", **SPOUSE)
    assert _h(session) == {
        "schedule_h_community_lived": "yes",
        "schedule_h_spouse_lived_with": "yes",
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


def test_a_notice_party_prints_its_own_line_address_and_account(session):
    # Notices copy the creditor's line, so the court sees which claim each notice belongs to.
    complete_debt(
        session,
        is_secured=True,
        creditor_name="Secured",
        notice_parties=[_party("Sec Notice", street_2="Suite 9", last_4="1111")],
    )
    complete_debt(
        session,
        creditor_name="Unsecured",
        notice_parties=[_party("Unsec Notice", street_2="Floor 3", last_4="2222")],
    )
    for name, line, street_2, last_4 in (
        ("secured_notices", "2.1", "Suite 9", "1111"),
        ("unsecured_notices", "4.1", "Floor 3", "2222"),
    ):
        assert _cell(session, f"claims.{name}[].line") == [line]
        assert _cell(session, f"claims.{name}[].street") == ["1 Demo Street"]
        assert _cell(session, f"claims.{name}[].street_2") == [street_2]
        assert _cell(session, f"claims.{name}[].last_4") == [last_4]
    assert _cell(session, "claims.unsecured_notices[].part") == ["2"]


def test_a_contract_and_a_codebtor_print_their_own_name_and_address(session):
    complete_debt(session)
    complete_contract(
        session,
        counterparty_name="Demo Lessor",
        city="Chicago",
        zip_code="60610",
        description="Equipment lease",
    )
    complete_codebtor(session, name="Demo Cosigner", city="Evanston", zip_code="60611")
    assert _cell(session, "claims.contracts[].name") == ["Demo Lessor"]
    assert _cell(session, "claims.contracts[].city") == ["Chicago"]
    assert _cell(session, "claims.contracts[].zip") == ["60610"]
    assert _cell(session, "claims.contracts[].purpose") == ["Equipment lease"]
    assert _cell(session, "claims.codebtors[].name") == ["Demo Cosigner"]
    assert _cell(session, "claims.codebtors[].city") == ["Evanston"]
    assert _cell(session, "claims.codebtors[].zip") == ["60611"]


def test_each_status_and_lien_kind_ticks_only_its_own_box(session):
    complete_debt(
        session,
        is_secured=True,
        creditor_name="A only other",
        lien={"kinds": ["other"], "other": "Demo words"},
        claim_status=["unliquidated"],
    )
    complete_debt(
        session,
        is_secured=True,
        creditor_name="B only contingent",
        lien={"kinds": ["judgment"], "other": ""},
        claim_status=["contingent"],
    )
    one = lambda attr: _cell(session, f"claims.secured[].{attr}")  # noqa: E731
    assert one("lien_other") == ["true", ""]
    assert one("lien_judgment") == ["", "true"]
    assert one("lien_agreement") == ["", ""]
    assert one("lien_statutory") == ["", ""]
    assert one("unliquidated") == ["true", ""]
    assert one("contingent") == ["", "true"]
    assert one("disputed") == ["", ""]


def test_a_secured_debt_fully_covered_by_its_property_prints_zero_unsecured(session):
    row = linked_row(session, "3")
    row.set_details({"who": "only_you"})
    row.entire_value = Decimal("0")
    row.save()
    linked_loan(session, row, Decimal("100"), amount_owed=Decimal("0"))
    assert _cell(session, "claims.secured[].unsecured") == ["0.00"]


def test_a_debt_with_no_type_ticks_neither_type_box(session):
    complete_debt(session, debt_type="", creditor_name="No type")
    assert _cell(session, "claims.unsecured[].student_loans") == [""]
    assert _cell(session, "claims.unsecured[].other_type") == [""]
    assert _cell(session, "claims.unsecured[].other_type_words") == [""]


def test_an_unsecured_debt_prints_the_offset_answer_it_was_given(session):
    complete_debt(session, offset_answer="no")
    assert _cell(session, "claims.unsecured[].offset") == ["no"]


def test_a_codebtor_names_each_schedule_line_it_is_on(session):
    secured = complete_debt(session, is_secured=True, creditor_name="Sec")
    contract = complete_contract(session)
    complete_codebtor(
        session,
        links=[{"kind": "debt", "id": secured.pk}, {"kind": "contract", "id": contract.pk}],
    )
    complete_codebtor(session, name="Lease only", links=[{"kind": "contract", "id": contract.pk}])
    one = lambda attr: _cell(session, f"claims.codebtors[].{attr}")  # noqa: E731
    assert one("on_d") == ["true", ""]
    assert one("d_lines") == ["2.1", ""]
    assert one("on_g") == ["true", "true"]
    assert one("g_lines") == ["2.1", "2.1"]
    assert one("on_ef") == ["", ""]
    assert one("ef_lines") == ["", ""]


def test_resolve_parts_reads_the_claims_once_for_the_whole_form(session, monkeypatch):
    # Every rule and binding of a form asks for the rows; one read per call, never per cell.
    from apps.forms.services import fill_resolver
    from apps.intake import claim_rows as claim_rows_module

    held = []
    monkeypatch.setattr(
        fill_resolver,
        "_resolve_parts",
        lambda schema, s: held.append(claim_rows_module._ONE_READ.get()) or {},
    )
    fill_resolver.resolve_parts(None, session)
    assert held[0] is not None
