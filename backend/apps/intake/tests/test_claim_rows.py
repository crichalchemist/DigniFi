"""The rows Schedules D, E/F, G and H print (3c5 spec §9, rulings R1-R6).

Business intent: every confirmed debt, notice party, contract and codebtor sits on one row, with
the line every citation uses; a sworn Column B or C never prints on property the filer shares or
on an answer the filer can no longer see.
"""

from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.districts.models import District
from apps.intake.claim_rows import claim_rows, community_answers, one_read_of_claims
from apps.intake.claims import CODEBTOR_GAP_SPOUSE_DETAILS, _community_gaps
from apps.intake.models import AssetInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_claims,
    complete_codebtor,
    complete_contract,
    complete_debt,
    linked_loan,
    linked_row,
)
from apps.users.models import User


@pytest.fixture
def filer(db):
    District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return User.objects.create_user(username="filer", password="pw")


@pytest.fixture
def session(filer):
    return IntakeSession.objects.create(user=filer, district=District.objects.get(code="ILND"))


def _rows(session):
    return claim_rows(IntakeSession.objects.get(pk=session.pk))


def _party(name):
    return {
        "name": name,
        "street_address": "9 Demo Street",
        "street_2": "",
        "city": "Demoville",
        "state": "IL",
        "zip_code": "60601",
        "outside_us": False,
        "last_4": "",
    }


def _property(session, line, who=None, entire=None, current=None, **flags):
    row = AssetInfo(session=session, ab_line=line, description="Demo item")
    row.set_details({"who": who, **flags})
    row.entire_value = entire
    row.current_value = current
    row.save()
    return row


def test_secured_and_unsecured_debts_are_numbered_apart_in_creditor_order(session):
    complete_debt(session, creditor_name="zeta Card")
    complete_debt(session, creditor_name="Émile Bank")
    complete_debt(session, creditor_name="alpha Medical")
    linked_loan(session, linked_row(session, "3"), "100", creditor_name="Beta Auto")
    R = _rows(session)
    assert [r.line for r in R.unsecured] == ["4.1", "4.2", "4.3"]
    assert [r.debt.creditor_name for r in R.unsecured] == [
        "alpha Medical",
        "Émile Bank",
        "zeta Card",
    ]
    assert R.secured[0].line == "2.1"


def test_a_draft_never_takes_a_line(session):
    complete_debt(session, creditor_name="Aardvark Draft", is_draft=True)
    complete_debt(session, creditor_name="Zed Card")
    R = _rows(session)
    assert [(r.line, r.debt.creditor_name) for r in R.unsecured] == [("4.1", "Zed Card")]


def test_a_notice_party_cites_its_debts_line(session):
    complete_debt(session, creditor_name="A Card")
    complete_debt(session, creditor_name="B Card", notice_parties=[_party("One"), _party("Two")])
    row = linked_row(session, "3")
    linked_loan(session, row, "100", creditor_name="C Auto", notice_parties=[_party("Three")])
    R = _rows(session)
    assert [(r.line, r.party["name"]) for r in R.unsecured_notices] == [
        ("4.2", "One"),
        ("4.2", "Two"),
    ]
    assert R.secured_notices[0].line == "2.1"


def test_contracts_print_in_the_order_they_were_added(session):
    for name in ("Zulu Leasing", "Alpha Leasing", "Mid Leasing"):
        complete_contract(session, counterparty_name=name)
    R = _rows(session)
    assert [(r.line, r.contract.counterparty_name) for r in R.contracts] == [
        ("2.1", "Zulu Leasing"),
        ("2.2", "Alpha Leasing"),
        ("2.3", "Mid Leasing"),
    ]


def test_a_codebtor_link_makes_the_debt_owed_with_another(session):
    complete_debt(session, creditor_name="A Card")
    second = complete_debt(session, creditor_name="B Card")
    complete_codebtor(session, links=[{"kind": "debt", "id": second.pk}])
    assert [r.with_another for r in _rows(session).unsecured] == [False, True]


def test_a_codebtor_link_to_a_draft_or_another_sessions_row_is_no_link(session, filer):
    complete_debt(session, creditor_name="A Card")
    draft = complete_debt(session, creditor_name="B Draft", is_draft=True)
    other = IntakeSession.objects.create(user=filer, district=session.district)
    foreign = complete_debt(other, creditor_name="C Foreign")
    links = [
        {"kind": "debt", "id": draft.pk},
        {"kind": "debt", "id": foreign.pk},
        {"kind": "debt", "id": 999999},
    ]
    complete_codebtor(session, links=links)
    R = _rows(session)
    assert len(R.codebtors) == 1
    only = R.codebtors[0]
    assert (only.d_lines, only.ef_lines, only.g_lines) == ((), (), ())
    assert [r.with_another for r in R.unsecured] == [False]


def test_a_codebtor_cites_two_lines_a_box_and_spills_the_rest_to_a_further_row(session):
    secured = linked_loan(session, linked_row(session, "3"), "100", creditor_name="S Auto")
    u1 = complete_debt(session, creditor_name="U1")
    u2 = complete_debt(session, creditor_name="U2")
    u3 = complete_debt(session, creditor_name="U3")
    contract = complete_contract(session)
    links = [
        {"kind": "debt", "id": u3.pk},
        {"kind": "debt", "id": secured.pk},
        {"kind": "debt", "id": u1.pk},
        {"kind": "debt", "id": u2.pk},
        {"kind": "contract", "id": contract.pk},
    ]
    codebtor = complete_codebtor(session, links=links)
    R = _rows(session)
    assert [(r.d_lines, r.ef_lines, r.g_lines) for r in R.codebtors] == [
        (("2.1",), ("4.1", "4.2"), ("2.1",)),
        ((), ("4.3",), ()),
    ]
    assert all(r.codebtor.pk == codebtor.pk for r in R.codebtors)


def test_a_codebtor_with_no_live_link_prints_one_row(session):
    complete_codebtor(session, links=[])
    R = _rows(session)
    assert [(r.d_lines, r.ef_lines, r.g_lines) for r in R.codebtors] == [((), (), ())]


def test_column_b_is_the_entire_value_of_property_the_filer_owns_alone(session):
    row = _property(session, "3", who="only_you", entire=Decimal("14000"))
    linked_loan(session, row, "100", amount_owed=Decimal("8500"))
    D = _rows(session).secured[0]
    assert D.value == Decimal("14000.00")
    assert D.unsecured == Decimal("0.00")


def test_column_c_is_the_part_the_property_doesnt_cover(session):
    row = _property(session, "3", who="only_you", entire=Decimal("5000"))
    linked_loan(session, row, "100", amount_owed=Decimal("8500"))
    D = _rows(session).secured[0]
    assert D.value == Decimal("5000.00")
    assert D.unsecured == Decimal("3500.00")


def test_column_b_is_blank_for_property_owned_with_someone(session):
    row = _property(session, "3", who="with_someone", entire=Decimal("14000"))
    linked_loan(session, row, "100")
    D = _rows(session).secured[0]
    assert (D.value, D.unsecured) == (None, None)


def test_a_property_worth_nothing_still_prints_column_b_and_the_whole_debt_in_c(session):
    row = _property(session, "3", who="only_you", entire=Decimal("0"))
    linked_loan(session, row, "100", amount_owed=Decimal("8500"))
    D = _rows(session).secured[0]
    assert D.value == Decimal("0.00")
    assert D.unsecured == Decimal("8500.00")


def test_column_b_reads_the_debts_who_on_an_item(session):
    row = _property(session, "6", current=Decimal("1200"))
    linked_loan(session, row, "100", collateral_who="only_you")
    assert _rows(session).secured[0].value == Decimal("1200.00")


@pytest.mark.parametrize("who", ["with_someone", None])
def test_column_b_is_blank_for_an_item_owned_with_someone(session, who):
    # R5: an item owned with someone leaves B and C blank until counsel rules on C-1, and an
    # unanswered owner is no "only you"
    row = _property(session, "6", current=Decimal("1200"))
    linked_loan(session, row, "100", collateral_who=who)
    D = _rows(session).secured[0]
    assert (D.value, D.unsecured) == (None, None)


def test_column_b_ignores_a_collateral_who_the_filer_was_not_asked(session):
    row = _property(session, "3", who="with_someone", entire=Decimal("14000"))
    linked_loan(session, row, "100", collateral_who="only_you")
    D = _rows(session).secured[0]
    assert (D.value, D.unsecured) == (None, None)


def test_column_b_is_blank_for_a_value_the_filer_doesnt_know(session):
    row = _property(session, "3", who="only_you", entire=None, entire_unknown=True)
    linked_loan(session, row, "100")
    D = _rows(session).secured[0]
    assert (D.value, D.unsecured) == (None, None)


def test_column_b_is_blank_when_two_debts_share_the_property(session):
    row = _property(session, "3", who="only_you", entire=Decimal("14000"))
    linked_loan(session, row, "100", creditor_name="A Auto")
    linked_loan(session, row, "100", creditor_name="B Auto")
    for D in _rows(session).secured:
        assert (D.value, D.unsecured) == (None, None)


def test_a_link_to_another_sessions_row_prints_no_value(session, filer):
    other = IntakeSession.objects.create(user=filer, district=session.district)
    row = _property(other, "3", who="only_you", entire=Decimal("14000"))
    linked_loan(session, row, "100")
    D = _rows(session).secured[0]
    assert (D.value, D.unsecured) == (None, None)


def test_h_line_2_prints_the_spouse_only_under_both_yes(session):
    full = {
        "community_lived": "yes",
        "community_spouse_lived_with": "yes",
        "community_state": "Arizona",
        "community_spouse_name": "Demo Spouse",
        "community_spouse_street_address": "2 Demo Street",
        "community_spouse_street_2": "Unit 4",
        "community_spouse_city": "Demoville",
        "community_spouse_state": "AZ",
        "community_spouse_zip_code": "85001",
        "community_spouse_outside_us": False,
    }
    answer_claims(session, **full)
    stored = {
        "lived": "yes",
        "spouse_lived_with": "yes",
        "state": "Arizona",
        "spouse_name": "Demo Spouse",
        "spouse_street": "2 Demo Street",
        "spouse_street_2": "Unit 4",
        "spouse_city": "Demoville",
        "spouse_state": "AZ",
        "spouse_zip": "85001",
    }
    fresh = lambda: IntakeSession.objects.get(pk=session.pk)  # noqa: E731
    assert community_answers(fresh()) == stored

    answer_claims(session, community_lived="yes", community_spouse_outside_us=True)
    assert community_answers(fresh()) == stored | {"spouse_state": "", "spouse_zip": ""}

    blank = dict.fromkeys(stored, "")
    # lived turns No while the spouse's Yes and details stay stored: none of it prints
    answer_claims(session, community_lived="no")
    assert community_answers(fresh()) == blank | {"lived": "no"}

    answer_claims(session, community_lived="yes", community_spouse_lived_with="no")
    assert community_answers(fresh()) == blank | {"lived": "yes", "spouse_lived_with": "no"}

    answer_claims(session, community_lived="no")
    assert community_answers(fresh()) == blank | {"lived": "no"}


def test_h_line_2_is_blank_with_no_answers_row(session):
    keys = (
        "lived",
        "spouse_lived_with",
        "state",
        "spouse_name",
        "spouse_street",
        "spouse_street_2",
        "spouse_city",
        "spouse_state",
        "spouse_zip",
    )
    answers = community_answers(IntakeSession.objects.get(pk=session.pk))
    assert answers == dict.fromkeys(keys, "")


_SPOUSE_DETAILS = {
    "community_state": "Arizona",
    "community_spouse_name": "Demo Spouse",
    "community_spouse_street_address": "2 Demo Street",
    "community_spouse_city": "Demoville",
    "community_spouse_state": "AZ",
    "community_spouse_zip_code": "85001",
    "community_spouse_outside_us": False,
}


@pytest.mark.parametrize("lived", ["yes", "no", None])
@pytest.mark.parametrize("with_spouse", ["yes", "no", None])
def test_h_line_2_prints_the_spouse_exactly_where_the_codebtors_step_asks_for_them(
    session, lived, with_spouse
):
    # community_answers copies _community_gaps' gate (R4): H must print the spouse's details
    # where the step asks for them and nowhere else, whatever is still stored.
    answer_claims(
        session,
        community_lived=lived,
        community_spouse_lived_with=with_spouse,
        **_SPOUSE_DETAILS,
    )
    stored = IntakeSession.objects.get(pk=session.pk).claim_answers.get_answers()
    asked = CODEBTOR_GAP_SPOUSE_DETAILS in _community_gaps(stored | dict.fromkeys(_SPOUSE_DETAILS))
    printed = community_answers(IntakeSession.objects.get(pk=session.pk))["spouse_name"]
    assert printed == ("Demo Spouse" if asked else "")


def test_resolving_the_rows_twice_in_one_read_reads_once(session):
    row = linked_row(session, "3")
    linked_loan(session, row, "100", creditor_name="S Auto", notice_parties=[_party("One")])
    for n in range(4):
        complete_debt(session, creditor_name=f"Card {n}", notice_parties=[_party("Two")])
    complete_contract(session, counterparty_name="First Leasing")
    contract = complete_contract(session, counterparty_name="Second Leasing")
    complete_codebtor(session, links=[{"kind": "contract", "id": contract.pk}])
    fresh = IntakeSession.objects.get(pk=session.pk)
    with one_read_of_claims():
        first = claim_rows(fresh)
        with CaptureQueriesContext(connection) as again:
            second = claim_rows(fresh)
        assert second is first
        assert len(again) == 0
    # a cache that outlived the block would make either of these read nothing
    with CaptureQueriesContext(connection) as outside_one:
        claim_rows(fresh)
    with CaptureQueriesContext(connection) as outside_two:
        claim_rows(fresh)
    assert len(outside_one) >= 1
    assert len(outside_two) >= 1


def test_a_codebtors_contract_link_never_reads_as_a_debt_with_the_same_id(session):
    complete_debt(session, creditor_name="A Card")
    debt = complete_debt(session, creditor_name="B Card")
    # contracts and debts are different tables: give the contract the debt's id on purpose
    contract = complete_contract(session, pk=debt.pk)
    assert contract.pk == debt.pk
    complete_codebtor(session, links=[{"kind": "contract", "id": contract.pk}])
    R = _rows(session)
    assert [r.with_another for r in R.unsecured] == [False, False]
    only = R.codebtors[0]
    assert (only.d_lines, only.ef_lines, only.g_lines) == ((), (), ("2.1",))


def test_a_debt_answered_with_a_kind_is_numbered_in_part_1_and_leaves_part_2(session):
    complete_debt(
        session,
        creditor_name="Alpha Tax Office",
        priority_answer="taxes",
        past_due_amount=Decimal("0.00"),
    )
    complete_debt(session, creditor_name="Beta Card")
    complete_debt(
        session,
        creditor_name="Delta Support",
        priority_answer="domestic_support",
        past_due_amount=Decimal("0.00"),
    )
    complete_debt(session, creditor_name="Gamma Care", priority_answer="not_sure")
    R = _rows(session)
    assert [(r.line, r.debt.creditor_name) for r in R.priority] == [
        ("2.1", "Alpha Tax Office"),
        ("2.2", "Delta Support"),
    ]
    assert [(r.line, r.debt.creditor_name) for r in R.unsecured] == [
        ("4.1", "Beta Card"),
        ("4.2", "Gamma Care"),
    ]


def test_no_not_sure_and_an_unanswered_debt_print_in_part_2(session):
    complete_debt(session, creditor_name="A Card", priority_answer="no")
    complete_debt(session, creditor_name="B Card", priority_answer="not_sure")
    complete_debt(session, creditor_name="C Card", priority_answer=None)
    R = _rows(session)
    assert R.priority == ()
    assert [r.debt.creditor_name for r in R.unsecured] == ["A Card", "B Card", "C Card"]


def test_adding_a_part_1_debt_leaves_part_2_numbers_as_they_were(session):
    complete_debt(session, creditor_name="Beta Card")
    complete_debt(session, creditor_name="Gamma Card")
    before = [(r.line, r.debt.creditor_name) for r in _rows(session).unsecured]
    assert before == [("4.1", "Beta Card"), ("4.2", "Gamma Card")]
    complete_debt(
        session,
        creditor_name="Alpha Tax Office",
        priority_answer="taxes",
        past_due_amount=Decimal("0.00"),
    )
    after = [(r.line, r.debt.creditor_name) for r in _rows(session).unsecured]
    assert after == before


def test_moving_a_debt_to_part_1_renumbers_only_the_part_2_rows_after_it(session):
    complete_debt(session, creditor_name="A Card")
    b = complete_debt(session, creditor_name="B Card", priority_answer="no")
    c = complete_debt(
        session,
        creditor_name="C Card",
        priority_answer="no",
        notice_parties=[_party("C Agent")],
    )
    complete_codebtor(session, links=[{"kind": "debt", "id": c.pk}])
    R = _rows(session)
    assert [(r.part, r.line) for r in R.unsecured_notices] == [("2", "4.3")]
    assert R.codebtors[0].ef_lines == ("4.3",)
    b.priority_answer = "taxes"
    b.past_due_amount = Decimal("0.00")
    b.save()
    R = _rows(session)
    assert [(r.line, r.debt.creditor_name) for r in R.unsecured] == [
        ("4.1", "A Card"),
        ("4.2", "C Card"),
    ]
    assert [(r.line, r.debt.creditor_name) for r in R.priority] == [("2.1", "B Card")]
    assert [(r.part, r.line) for r in R.unsecured_notices] == [("2", "4.2")]
    assert R.codebtors[0].ef_lines == ("4.2",)


def test_a_secured_debt_stored_with_a_kind_stays_on_schedule_d(session):
    linked_loan(
        session,
        linked_row(session, "3"),
        "100",
        creditor_name="S Auto",
        priority_answer="taxes",
    )
    R = _rows(session)
    assert [r.debt.creditor_name for r in R.secured] == ["S Auto"]
    assert R.priority == ()


def test_a_draft_answered_with_a_kind_never_takes_a_line(session):
    complete_debt(
        session,
        creditor_name="Aardvark Tax",
        priority_answer="taxes",
        is_draft=True,
    )
    complete_debt(session, creditor_name="Zed Card")
    R = _rows(session)
    assert R.priority == ()
    assert [(r.line, r.debt.creditor_name) for r in R.unsecured] == [("4.1", "Zed Card")]


def test_part_3_lists_part_1_parties_first_with_their_part_and_line(session):
    complete_debt(
        session,
        creditor_name="Alpha Card",
        priority_answer="no",
        notice_parties=[_party("Card Agent")],
    )
    complete_debt(
        session,
        creditor_name="Zeta Tax",
        priority_answer="taxes",
        past_due_amount=Decimal("0.00"),
        notice_parties=[_party("Tax Agent")],
    )
    linked_loan(
        session,
        linked_row(session, "3"),
        "100",
        creditor_name="Auto Loan",
        notice_parties=[_party("Auto Agent")],
    )
    R = _rows(session)
    assert [(r.part, r.line, r.party["name"]) for r in R.unsecured_notices] == [
        ("1", "2.1", "Tax Agent"),
        ("2", "4.1", "Card Agent"),
    ]
    assert R.secured_notices[0].part == ""


def test_a_codebtor_cites_part_1_lines_before_part_2_lines(session):
    u1 = complete_debt(session, creditor_name="U1")
    u2 = complete_debt(session, creditor_name="U2")
    p1 = complete_debt(
        session,
        creditor_name="P1",
        priority_answer="taxes",
        past_due_amount=Decimal("0.00"),
    )
    complete_codebtor(
        session,
        links=[{"kind": "debt", "id": pk} for pk in (u2.pk, p1.pk, u1.pk)],
    )
    assert [r.ef_lines for r in _rows(session).codebtors] == [("2.1", "4.1"), ("4.2",)]
