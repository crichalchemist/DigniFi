"""What Complete and the forms refuse on Schedules D, E/F, G and H (3c3 spec §7.5).

Business intent: a filer is never sent to court with a Schedule D, E/F, G or H row that is
half-answered or silent, and the filer reads the same sentence at Continue and at Complete. A
filer with no debts, contracts or codebtors who said so has finished the steps. A row is named
by what the filer typed, or by its kind when nothing was typed, so a sentence is never blank.
"""

import re
from decimal import Decimal

import pytest
from django.conf import settings

from apps.districts.models import District
from apps.intake.claims import (
    NAMELESS_CODEBTOR,
    NAMELESS_CONTRACT,
    NAMELESS_DEBT,
    address_missing,
    claim_row_name,
    claim_step_gaps,
    link_is_live,
)
from apps.intake.models import AssetInfo, DebtInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_claims,
    complete_codebtor,
    complete_contract,
    complete_debt,
)
from apps.users.models import User

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"
ND, CTR, CB = "Demo Card Services", "Demo Storage Co", "Demo Cosigner"
DRAFT_SENTENCE = "Check the debts read from your documents on the Amounts Owed step."
DEMO = {"street_address": "1 Demo Street", "city": "Demoville", "state": "IL", "zip_code": "60601"}


@pytest.fixture
def session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    return IntakeSession.objects.create(user=user, district=district)


def _gaps(session) -> list[str]:
    return [str(gap) for gap in claim_step_gaps(IntakeSession.objects.get(pk=session.pk))]


def _copy_sentence(name: str) -> str:
    """A sentence from the wizard's copy.ts: Continue says it while Complete would refuse."""
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    source = (FRONTEND / "constants" / "copy.ts").read_text()
    found = re.search(rf"export const {name} =\s*(['\"])(.*?)\1;", source, re.DOTALL)
    assert found, name
    return found.group(2)


def _asset(session, line, description="", **details) -> AssetInfo:
    row = AssetInfo(
        session=session, ab_line=line, description=description, current_value=Decimal("100.00")
    )
    row.set_details(details)
    row.save()
    return row


def _car(session) -> AssetInfo:
    return _asset(session, "3", make="Demo", who="only_you")


def _secured(session, asset=None, **over) -> DebtInfo:
    fields = {
        "is_secured": True,
        "debt_type": "auto_loan",
        "secured_by": asset or _car(session),
        "collateral_description": "2020 Demo Sedan",
        "lien": {"kinds": ["agreement"], "other": ""},
        "monthly_payment": Decimal("250.00"),
        "offset_answer": None,
    } | over
    return complete_debt(session, **fields)


def _other_session(session) -> IntakeSession:
    return IntakeSession.objects.create(user=session.user, district=session.district)


# Each state is the one in which its constant's gap fires. It returns the values the sentence
# is filled with.


def _debt_with(**over):
    def build(session):
        complete_debt(session, **over)
        return {"name": ND}

    return build


def _nameless_debt(**over):
    def build(session):
        complete_debt(session, creditor_name="", **over)
        return {}

    return build


def _secured_with(**over):
    def build(session):
        _secured(session, **over)
        return {"name": ND}

    return build


def _no_debts_but_one(session):
    complete_debt(session)
    answer_claims(session, no_debts=True)
    return {}


def _home_line(session):
    _secured(
        session, _asset(session, "1", street="1 Demo Street", who="only_you", lives_here="yes")
    )
    return {"name": ND}


def _who(session):
    _secured(session, _asset(session, "6", "Demo sofa"))
    return {"name": ND}


def _notice_party(session):
    complete_debt(session, notice_parties=[{"name": "", **DEMO}])
    return {"name": ND}


def _no_row(**answers):
    def build(session):
        if answers:
            answer_claims(session, **answers)
        return {}

    return build


def _contract_with(**over):
    def build(session):
        complete_contract(session, counterparty_name=CTR, **over)
        return {"name": CTR}

    return build


def _vehicle_lease_with(**over):
    def build(session):
        fields = {
            "lease_kind": "vehicle",
            "vehicle_asset": _car(session),
            "monthly_payment": Decimal("100.00"),
        } | over
        complete_contract(session, counterparty_name=CTR, **fields)
        return {"name": CTR}

    return build


def _no_but_contract(session):
    complete_contract(session)
    answer_claims(session, contracts_answer="no")
    return {}


def _same_vehicle(session):
    car = _car(session)
    debt = _secured(session, car)
    complete_contract(
        session,
        counterparty_name=CTR,
        lease_kind="vehicle",
        vehicle_asset=car,
        monthly_payment=Decimal("100.00"),
        owes_now="yes",
        owed_debt=debt,
    )
    return {"name": CTR, "debt": ND}


def _no_but_codebtor(session):
    complete_debt(session)
    complete_codebtor(session)
    answer_claims(session, codebtors_answer="no")
    return {}


def _codebtor_with(**over):
    def build(session):
        complete_debt(session)
        complete_codebtor(session, **({"name": CB} | over))
        return {"name": CB}

    return build


def _nameless_codebtor(session):
    complete_debt(session)
    complete_codebtor(session, name="")
    return {}


STATES = {
    "CLAIM_GAP_KIND": _debt_with(debt_type=""),
    "CLAIM_GAP_ADDRESS": _debt_with(state="I"),
    "CLAIM_GAP_STREET_CITY": _debt_with(outside_us=True, city=""),
    "DEBT_GAP_NO_ANSWER": _no_row(),
    "DEBT_GAP_NONE_BUT_LISTED": _no_debts_but_one,
    "DEBT_GAP_NO_NAME": _nameless_debt(),
    "DEBT_GAP_AMOUNT": _debt_with(amount_owed=Decimal("0")),
    "DEBT_GAP_AMOUNT_NO_NAME": _nameless_debt(amount_owed=Decimal("0")),
    "DEBT_GAP_ADDRESS_NO_NAME": _nameless_debt(state=""),
    "DEBT_GAP_STREET_CITY_NO_NAME": _nameless_debt(outside_us=True, city=""),
    "DEBT_GAP_PROPERTY": _secured_with(secured_by=None),
    "DEBT_GAP_DESCRIBE": _secured_with(collateral_description=""),
    "DEBT_GAP_LIEN": _secured_with(lien=None),
    "DEBT_GAP_LIEN_OTHER": _secured_with(lien={"kinds": ["other"], "other": " "}),
    "DEBT_GAP_PAYMENT": _secured_with(monthly_payment=None),
    "DEBT_GAP_HOME_LINE": _home_line,
    "DEBT_GAP_WHO": _who,
    "DEBT_GAP_STATUS": _debt_with(claim_status=None),
    "DEBT_GAP_OFFSET": _debt_with(offset_answer=None),
    "DEBT_GAP_NOTICE": _debt_with(notice_parties=None),
    "DEBT_GAP_NOTICE_PARTY": _notice_party,
    "CONTRACT_GAP_NO_ANSWER": _no_row(),
    "CONTRACT_GAP_YES_BUT_NONE": _no_row(contracts_answer="yes"),
    "CONTRACT_GAP_NO_BUT_LISTED": _no_but_contract,
    "CONTRACT_GAP_NO_NAME": lambda s: complete_contract(s, counterparty_name="") and {},
    "CONTRACT_GAP_PURPOSE": _contract_with(description=""),
    "CONTRACT_GAP_LEASE_KIND": _contract_with(lease_kind=None),
    "CONTRACT_GAP_VEHICLE": _vehicle_lease_with(vehicle_asset=None),
    "CONTRACT_GAP_PAYMENT": _vehicle_lease_with(monthly_payment=None),
    "CONTRACT_GAP_OWES_NOW": _contract_with(owes_now=None),
    "CONTRACT_GAP_OWED_DEBT": _contract_with(owes_now="yes", owed_debt=None),
    "CONTRACT_GAP_SAME_VEHICLE": _same_vehicle,
    "CODEBTOR_GAP_NO_ANSWER": _no_row(),
    "CODEBTOR_GAP_YES_BUT_NONE": _no_row(codebtors_answer="yes"),
    "CODEBTOR_GAP_NO_BUT_LISTED": _no_but_codebtor,
    "CODEBTOR_GAP_COMMUNITY": _no_row(),
    "CODEBTOR_GAP_SPOUSE_LIVED": _no_row(community_lived="yes"),
    "CODEBTOR_GAP_SPOUSE_DETAILS": _no_row(
        community_lived="yes", community_spouse_lived_with="yes", community_state=""
    ),
    "CODEBTOR_GAP_NO_NAME": _nameless_codebtor,
    "CODEBTOR_GAP_NO_LINK": _codebtor_with(links=[]),
}


@pytest.mark.parametrize("name", list(STATES))
def test_continue_and_complete_give_the_same_sentence(session, name):
    # The wizard stops at Continue, so the filer reads its copy of the sentence, never Complete's.
    values = STATES[name](session)

    assert _copy_sentence(name).format(**values) in _gaps(session)


def test_every_gap_sentence_in_copy_is_pinned():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    source = (FRONTEND / "constants" / "copy.ts").read_text()
    found = set(re.findall(r"export const ((?:DEBT|CONTRACT|CODEBTOR|CLAIM)_GAP_\w+) =", source))

    assert found == set(STATES)


def test_a_nameless_row_is_called_by_its_kind_in_copy():
    assert _copy_sentence("NAMELESS_DEBT") == claim_row_name("  ", NAMELESS_DEBT)
    assert _copy_sentence("NAMELESS_CONTRACT") == NAMELESS_CONTRACT
    assert _copy_sentence("NAMELESS_CODEBTOR") == NAMELESS_CODEBTOR


def test_a_nameless_contract_and_codebtor_are_named_by_the_servers_kind(session):
    # The server's own sentence for a nameless row quotes the same words copy.ts holds
    complete_debt(session)
    complete_codebtor(session, name="", links=[])
    complete_contract(session, counterparty_name="", description="")
    gaps = _gaps(session)

    assert any(_copy_sentence("NAMELESS_CODEBTOR") in gap for gap in gaps)
    assert any(_copy_sentence("NAMELESS_CONTRACT") in gap for gap in gaps)


def test_a_complete_debt_has_no_gap(session):
    complete_debt(session)
    answer_claims(session)

    assert _gaps(session) == []


def test_a_residential_lease_has_no_gap(session):
    complete_contract(session)
    answer_claims(session, no_debts=True, contracts_answer="yes")

    assert _gaps(session) == []


def test_a_vehicle_lease_has_no_gap(session):
    _vehicle_lease_with()(session)
    answer_claims(session, no_debts=True, contracts_answer="yes")

    assert _gaps(session) == []


def test_a_codebtor_on_a_live_debt_has_no_gap(session):
    complete_debt(session)
    complete_codebtor(session)
    answer_claims(session, codebtors_answer="yes")

    assert _gaps(session) == []


def test_a_secured_car_debt_has_no_gap(session):
    _secured(session)
    answer_claims(session)

    assert _gaps(session) == []


def test_a_filer_with_no_debts_who_said_so_has_no_gap(session):
    answer_claims(session, no_debts=True)

    assert _gaps(session) == []


@pytest.mark.parametrize("draft", [False, True], ids=["confirmed", "draft"])
def test_a_debt_with_no_amount_above_zero_is_a_gap(session, draft):
    debt = complete_debt(session, amount_owed=Decimal("0.00"), is_draft=draft)
    answer_claims(session)
    sentence = _copy_sentence("DEBT_GAP_AMOUNT").format(name=ND)

    assert sentence in _gaps(session)

    # Confirming a $0 balance doesn't make it an answer (§7.7)
    DebtInfo.objects.filter(pk=debt.pk).update(is_draft=False)

    assert sentence in _gaps(session)


def test_a_scanned_zero_balance_is_a_gap_until_corrected(session):
    debt = complete_debt(session, amount_owed=Decimal("0.00"), is_draft=True)
    answer_claims(session)
    sentence = _copy_sentence("DEBT_GAP_AMOUNT").format(name=ND)

    assert sentence in _gaps(session)

    debt.amount_owed = Decimal("12.00")
    debt.save()

    assert sentence not in _gaps(session)


def test_a_draft_remains_is_the_first_debts_gap(session):
    complete_debt(session, is_draft=True)
    answer_claims(session, no_debts=True)
    gaps = _gaps(session)

    assert gaps[0] == DRAFT_SENTENCE
    assert gaps.index(DRAFT_SENTENCE) < gaps.index(_copy_sentence("DEBT_GAP_NONE_BUT_LISTED"))
    assert [gap.step for gap in claim_step_gaps(IntakeSession.objects.get(pk=session.pk))][
        0
    ] == "debts"


@pytest.mark.parametrize(
    ("line", "details", "name"),
    [
        ("1", {"street": "1 Demo Street", "who": "only_you"}, "1 Demo Street"),
        ("4", {"make": "Demo Motor Home", "who": "only_you"}, "Demo Motor Home"),
    ],
    ids=["line_1", "line_4"],
)
def test_a_home_mortgage_never_reaches_line_20a_unasked(session, line, details, name):
    home = _asset(session, line, **details)
    _secured(session, home, debt_type="mortgage")
    answer_claims(session)
    sentence = f"Answer “Do you live here?” for {name} on line {line} of the Assets step."

    gaps = claim_step_gaps(IntakeSession.objects.get(pk=session.pk))

    assert [str(gap) for gap in gaps][0] == sentence
    assert gaps[0].step == "assets"

    home.set_details({**details, "lives_here": "no"})
    home.save()

    assert sentence not in _gaps(session)


def test_a_secured_debt_on_a_line_4_row_the_filer_does_not_live_in_asks_no_home_question(session):
    home = _asset(session, "4", make="Demo Motor Home", who="only_you", lives_here="no")
    _secured(session, home, collateral_who=None, home_payment_line=None)
    answer_claims(session)

    assert _gaps(session) == []


def test_a_ticked_outside_us_address_needs_no_state_or_zip_but_needs_a_city(session):
    debt = complete_debt(session, outside_us=True, state="", zip_code="")
    answer_claims(session)

    assert _gaps(session) == []

    debt.city = ""
    debt.save()

    assert _gaps(session) == [_copy_sentence("CLAIM_GAP_STREET_CITY").format(name=ND)]


@pytest.mark.parametrize(
    "asset_row",
    [
        lambda s: _asset(s, "1", street="1 Demo Street", who="only_you", lives_here="yes"),
        lambda s: _asset(s, "6", "Demo sofa"),
    ],
    ids=["a_home_the_filer_lives_in", "a_row_that_asks_no_owner"],
)
def test_a_link_to_a_row_moved_to_another_intake_is_no_link(session, asset_row):
    asset = asset_row(session)
    _secured(session, asset)
    answer_claims(session)
    asset.session = _other_session(session)
    asset.save()
    gaps = _gaps(session)

    assert _copy_sentence("DEBT_GAP_PROPERTY").format(name=ND) in gaps
    assert _copy_sentence("DEBT_GAP_HOME_LINE").format(name=ND) not in gaps
    assert _copy_sentence("DEBT_GAP_WHO").format(name=ND) not in gaps
    assert not any("Do you live here" in gap for gap in gaps)


def test_a_nameless_row_is_called_by_its_kind(session):
    _secured(session, creditor_name="", secured_by=None)

    assert "Choose the property that secures one amount owed." in _gaps(session)


def test_a_rows_gaps_all_come_before_the_next_rows(session):
    complete_debt(session, creditor_name="Zeta Bank", debt_type="", amount_owed=Decimal("0"))
    complete_debt(session, creditor_name="Émile Lending", debt_type="", amount_owed=Decimal("0"))
    answer_claims(session)
    kind, amount = _copy_sentence("CLAIM_GAP_KIND"), _copy_sentence("DEBT_GAP_AMOUNT")

    assert _gaps(session) == [
        kind.format(name="Émile Lending"),
        amount.format(name="Émile Lending"),
        kind.format(name="Zeta Bank"),
        amount.format(name="Zeta Bank"),
    ]


def test_gaps_come_in_wizard_order_and_carry_their_step(session):
    _secured(session, _asset(session, "1", street="1 Demo Street", who="only_you"))
    complete_debt(session, creditor_name="Demo Lender", debt_type="")
    complete_contract(session, counterparty_name=CTR, description="")
    answer_claims(session, contracts_answer="yes", codebtors_answer=None)
    gaps = claim_step_gaps(IntakeSession.objects.get(pk=session.pk))

    assert [gap.step for gap in gaps] == ["assets", "debts", "contracts", "codebtors"]


@pytest.mark.parametrize("dead", ["a_row_on_another_intake", "an_id_naming_nothing"])
def test_a_link_to_a_removed_or_foreign_row_is_no_link_on_a_contract_and_a_codebtor(session, dead):
    other = _other_session(session)
    foreign_debt, foreign_car = complete_debt(other), _car(other)
    foreign_contract = complete_contract(other)
    if dead == "an_id_naming_nothing":
        links = [{"kind": "debt", "id": 999999}, {"kind": "contract", "id": 999999}]
    else:
        links = [
            {"kind": "debt", "id": foreign_debt.pk},
            {"kind": "contract", "id": foreign_contract.pk},
        ]
    complete_contract(
        session,
        counterparty_name=CTR,
        lease_kind="vehicle",
        vehicle_asset=foreign_car if dead == "a_row_on_another_intake" else None,
        monthly_payment=Decimal("100.00"),
        owes_now="yes",
        owed_debt=foreign_debt if dead == "a_row_on_another_intake" else None,
    )
    complete_codebtor(session, links=links, name=CB)
    gaps = _gaps(session)

    assert _copy_sentence("CONTRACT_GAP_VEHICLE").format(name=CTR) in gaps
    assert _copy_sentence("CONTRACT_GAP_OWED_DEBT").format(name=CTR) in gaps
    assert _copy_sentence("CODEBTOR_GAP_NO_LINK").format(name=CB) in gaps


@pytest.mark.parametrize("row", ["contract", "codebtor"])
def test_contract_and_codebtor_addresses_are_checked_like_a_debts(session, row):
    def build(**over):
        if row == "contract":
            return complete_contract(session, counterparty_name=CTR, **over), CTR
        return complete_codebtor(session, name=CB, **over), CB

    complete_debt(session)
    saved, name = build(state="I")
    answer_claims(session, contracts_answer="yes", codebtors_answer="yes")

    assert _copy_sentence("CLAIM_GAP_ADDRESS").format(name=name) in _gaps(session)

    saved.state, saved.outside_us, saved.city = "", True, ""
    saved.save()

    assert _copy_sentence("CLAIM_GAP_STREET_CITY").format(name=name) in _gaps(session)


def test_a_spouse_address_missing_is_a_gap_unless_outside_us(session):
    spouse = {
        "community_lived": "yes",
        "community_spouse_lived_with": "yes",
        "community_state": "Demo State",
        "community_spouse_name": "Demo Spouse",
        "community_spouse_street_address": "1 Demo Street",
        "community_spouse_city": "Demoville",
        "community_spouse_state": "IL",
        "community_spouse_zip_code": "60601",
    }
    sentence = _copy_sentence("CODEBTOR_GAP_SPOUSE_DETAILS")

    answer_claims(session, **spouse)
    assert sentence not in _gaps(session)

    answer_claims(session, **(spouse | {"community_spouse_state": "I"}))
    assert sentence in _gaps(session)

    outside = spouse | {"community_spouse_state": None, "community_spouse_zip_code": None}
    answer_claims(session, **outside, community_spouse_outside_us=True)
    assert sentence not in _gaps(session)

    answer_claims(session, community_lived="yes", community_spouse_city=None)
    assert sentence in _gaps(session)


def test_a_whitespace_only_text_is_a_gap(session):
    answer_claims(
        session,
        community_lived="yes",
        community_spouse_lived_with="yes",
        community_state="Demo State",
        community_spouse_name="   ",
        community_spouse_street_address="1 Demo Street",
        community_spouse_city="Demoville",
        community_spouse_state="IL",
        community_spouse_zip_code="60601",
    )

    assert _copy_sentence("CODEBTOR_GAP_SPOUSE_DETAILS") in _gaps(session)


@pytest.mark.parametrize(
    ("lease_payment", "debt_payment", "same_car", "debt_secured", "is_gap"),
    [
        ("100.00", "250.00", True, True, True),
        ("0.00", "250.00", True, True, False),
        ("100.00", "0.00", True, True, False),
        ("100.00", "250.00", False, True, False),
        ("100.00", "250.00", True, False, False),
    ],
    ids=["both_paid", "lease_pays_zero", "debt_pays_zero", "other_vehicle", "not_secured"],
)
def test_two_payments_on_one_vehicle_are_a_gap_until_one_is_zero(
    session, lease_payment, debt_payment, same_car, debt_secured, is_gap
):
    car = _car(session)
    debt = _secured(session, car, monthly_payment=Decimal(debt_payment), is_secured=debt_secured)
    complete_contract(
        session,
        counterparty_name=CTR,
        lease_kind="vehicle",
        vehicle_asset=car if same_car else _car(session),
        monthly_payment=Decimal(lease_payment),
        owes_now="yes",
        owed_debt=debt,
    )
    sentence = _copy_sentence("CONTRACT_GAP_SAME_VEHICLE").format(name=CTR, debt=ND)

    assert (sentence in _gaps(session)) is is_gap


@pytest.mark.parametrize(
    ("args", "missing"),
    [
        (("1 Demo St", "Demoville", "IL", "60601", False), False),
        (("", "Demoville", "IL", "60601", False), True),
        (("1 Demo St", " ", "IL", "60601", False), True),
        (("1 Demo St", "Demoville", "I", "60601", False), True),
        (("1 Demo St", "Demoville", "I1", "60601", False), True),
        (("1 Demo St", "Demoville", "IL", " ", False), True),
        (("1 Demo St", "Paris", "", "", True), False),
        (("1 Demo St", "", "", "", True), True),
    ],
)
def test_an_address_is_missing_without_street_city_two_letter_state_and_zip(args, missing):
    assert address_missing(*args) is missing


def test_a_link_is_live_only_on_the_same_intake(session):
    mine, theirs = _car(session), _car(_other_session(session))

    assert link_is_live(mine, session)
    assert not link_is_live(theirs, session)
    assert not link_is_live(None, session)


def test_a_non_lease_contract_asks_no_lease_kind(session):
    complete_contract(
        session, contract_type="contract", lease_kind=None, description="Gym membership"
    )
    answer_claims(session, no_debts=True, contracts_answer="yes")

    assert _gaps(session) == []


def test_a_spouse_who_did_not_share_the_community_state_asks_no_spouse_details(session):
    answer_claims(session, no_debts=True, community_lived="yes", community_spouse_lived_with="no")

    assert _gaps(session) == []


def test_a_debt_on_a_home_the_filer_does_not_live_in_asks_no_payment_line(session):
    home = _asset(session, "1", street="1 Demo Street", who="only_you", lives_here="no")
    _secured(session, home, home_payment_line=None)
    answer_claims(session)

    assert _gaps(session) == []


def test_a_lien_of_kind_other_with_its_text_is_no_gap(session):
    _secured(session, lien={"kinds": ["other"], "other": "Demo mechanic's lien"})
    answer_claims(session)

    assert _gaps(session) == []
