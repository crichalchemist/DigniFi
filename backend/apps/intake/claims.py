"""The order Schedules D and E/F list claims in (3c spec §6.2), and what Schedules D, E/F, G and H
still lack (3c3 spec §7.5), and which monthly payments on property reach Schedule J and its
totals (3c4 spec §8: linked_payments, total_monthly_expenses, format_figure).

The module imports no models: it reads a session's relations by attribute, as asset_step_gaps
does. The gap sentences are spelled as copy.ts spells them, filled with .format(name=...), and
test_claim_gaps.py pins each pair, so the filer reads the same words at Continue and at Complete.
"""

import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from apps.intake.asset_lines import LINE_BY_KEY, _row_name, ordered_assets

NAMELESS_DEBT = "one amount owed"
NAMELESS_CONTRACT = "one contract"
NAMELESS_CODEBTOR = "one codebtor"

# Server only: the wizard's steps never say these two (Continue on Assets doesn't ask
# "Do you live here?", and the draft check is not on the Amounts Owed step's copy).
ASSET_GAP_LIVES_HERE = "Answer “Do you live here?” for {row} on line {line} of the Assets step."
DEBT_GAP_DRAFT = "Check the debts read from your documents on the Amounts Owed step."

CLAIM_GAP_KIND = "Choose a kind for {name}."
CLAIM_GAP_ADDRESS = "Enter the street, city, two-letter state and ZIP for {name}."
CLAIM_GAP_STREET_CITY = "Enter the street and city for {name}."
CLAIM_GAP_LEGACY_VEHICLE = (
    "You told us you pay ${typed} a month for a car, and the payments you linked add up to "
    "${linked}. Add the rest to the loan on Amounts Owed or the lease on Contracts & Leases, "
    "or remove this figure."
)
CLAIM_GAP_LEGACY_OTHER = (
    "You told us you pay ${typed} a month in mortgages on other property, and the payments "
    "you linked add up to ${linked}. Add the rest to the mortgage on Amounts Owed, "
    "or remove this figure."
)
CLAIM_GAP_LINE_4 = (
    "You entered ${typed} for rent or lot rent, and your first mortgage on Amounts Owed is "
    "${linked} a month. Line 4 adds them. Do you pay both?"
)

DEBT_GAP_NO_ANSWER = "List each amount you owe, or press “I have no amounts owed.”"
DEBT_GAP_NONE_BUT_LISTED = (
    "You said you have no amounts owed, but some are listed. Remove them, or change that answer."
)
DEBT_GAP_NO_NAME = "One amount owed has no creditor name. Enter who you owe."
DEBT_GAP_AMOUNT = "Enter the amount you owe {name}. It must be above $0."
DEBT_GAP_AMOUNT_NO_NAME = (
    "Enter the amount you owe on the row with no creditor name. It must be above $0."
)
DEBT_GAP_ADDRESS_NO_NAME = (
    "Enter the street, city, two-letter state and ZIP on the row with no creditor name."
)
DEBT_GAP_STREET_CITY_NO_NAME = "Enter the street and city on the row with no creditor name."
DEBT_GAP_PROPERTY = "Choose the property that secures {name}."
DEBT_GAP_DESCRIBE = "Describe the property that secures {name}."
DEBT_GAP_LIEN = "Check at least one kind of lien for {name}."
DEBT_GAP_LIEN_OTHER = "Say what the other kind of lien is, for {name}."
DEBT_GAP_PAYMENT = "Enter the monthly payment for {name}. Enter 0 if you pay nothing on it."
DEBT_GAP_HOME_LINE = (
    "Say whether {name} is a first mortgage or an additional one, such as home equity."
)
DEBT_GAP_WHO = "Answer who owns the property that secures {name}."
DEBT_GAP_STATUS = (
    "Check any that fit {name}: contingent, unliquidated or disputed. Or choose None of these."
)
DEBT_GAP_OFFSET = "Answer whether {name} is subject to offset."
DEBT_GAP_NOTICE = "Answer whether anyone else is contacting you about {name}."
DEBT_GAP_NOTICE_PARTY = (
    "Enter the name and full address of each person contacting you about {name}."
)

CONTRACT_GAP_NO_ANSWER = "Answer whether you have any contracts or leases."
CONTRACT_GAP_YES_BUT_NONE = (
    "You answered Yes. Add each contract or lease, or change the answer to No."
)
CONTRACT_GAP_NO_BUT_LISTED = (
    "You answered No, but contracts or leases are listed. Remove them, or change the answer to Yes."
)
CONTRACT_GAP_NO_NAME = "One contract has no name. Enter the other party's name."
CONTRACT_GAP_PURPOSE = "Enter what the contract or lease is for, for {name}."
CONTRACT_GAP_LEASE_KIND = "Choose the kind of lease for {name}."
CONTRACT_GAP_VEHICLE = "Choose the vehicle you lease from {name}."
CONTRACT_GAP_PAYMENT = "Enter the monthly lease payment for {name}."
# DRAFT: counsel C-9
CONTRACT_GAP_OWES_NOW = "Answer “Do you owe money on this now?” for {name}."
CONTRACT_GAP_OWED_DEBT = (
    "Choose the amount owed that goes with {name}, or add it on the Amounts Owed step."
)
CONTRACT_GAP_SAME_VEHICLE = (
    "Your lease with {name} and your debt to {debt} are on the same vehicle, and each has a "
    "monthly payment above $0. Enter the monthly payment once, on either row, and $0 on the "
    "other."
)
CONTRACT_GAP_VEHICLE_NO_NAME = "Choose the vehicle you lease on the row with no name."
CONTRACT_GAP_SAME_VEHICLE_NO_NAME = (
    "Your lease on the row with no name and your debt to {debt} are on the same vehicle, and "
    "each has a monthly payment above $0. Enter the monthly payment once, on either row, and "
    "$0 on the other."
)

CODEBTOR_GAP_NO_ANSWER = "Answer whether you have any codebtors."
CODEBTOR_GAP_YES_BUT_NONE = "You answered Yes. Add each codebtor, or change the answer to No."
CODEBTOR_GAP_NO_BUT_LISTED = (
    "You answered No, but codebtors are listed. Remove them, or change the answer to Yes."
)
CODEBTOR_GAP_COMMUNITY = (
    "Did you live in a community property state or territory in the last 8 years? "
    "Answer Yes or No."
)
CODEBTOR_GAP_SPOUSE_LIVED = (
    "Answer whether your spouse, former spouse or legal equivalent lived with you then."
)
CODEBTOR_GAP_SPOUSE_DETAILS = (
    "Enter the community property state, and that person’s name and full address."
)
CODEBTOR_GAP_NO_NAME = "One codebtor has no name. Enter the person's name."
CODEBTOR_GAP_NO_LINK = "Choose which amounts owed or contracts {name} shares with you."

# The shapes of a row whose own answers say who owns it (asset_lines.py)
_SHAPES_THAT_ASK_WHO = ("place", "vehicle", "vehicle_no_mileage")
_HOME_LINES = ("1", "4")
_ZERO = Decimal("0")


class ClaimStepGap(Exception):
    """One thing Schedules D, E/F, G or H, or Schedule J line 4, still lack, in the filer's words.

    Claim gaps fix on five steps (assets, debts, contracts, codebtors and expense_info), so each
    carries its own `step` (a WIZARD_STEPS key).
    str(gap) is the sentence.
    """

    def __init__(self, message: str, step: str):
        super().__init__(message)
        self.step = step


def _letters(name):
    """A creditor's name as it sorts: its letters, without accents, ignoring case."""
    decomposed = unicodedata.normalize("NFKD", name.strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def account_last_4(number):
    """The last four digits of the digits in an account number (fewer, if it has fewer)."""
    digits = "".join(c for c in (number or "") if c in "0123456789")
    return digits[-4:]


def ordered_debts(rows):
    """The rows alphabetical by creditor name, ignoring case and accents, then by id.

    Sorted in Python: the name is ciphertext in the table.
    """
    return sorted(rows, key=lambda row: (_letters(row.creditor_name), row.pk))


def _blank(text) -> bool:
    return not (text or "").strip()


def claim_row_name(name, nameless: str) -> str:
    """What the filer knows a row by: its name stripped, else the words for a row with none."""
    return (name or "").strip() or nameless


def address_missing(street, city, state, zip_code, outside_us) -> bool:
    """A street or city is blank, or, unless ticked outside the US, the state isn't two letters
    or the ZIP is blank (R7)."""
    if _blank(street) or _blank(city):
        return True
    if outside_us:
        return False
    state = (state or "").strip()
    return not (len(state) == 2 and state.isalpha()) or _blank(zip_code)


def link_is_live(linked, session) -> bool:
    """A link names a row that is still on this session (R6)."""
    return linked is not None and linked.session_id == session.pk


def _row_address_missing(row) -> bool:
    return address_missing(row.street_address, row.city, row.state, row.zip_code, row.outside_us)


def _address_gap(row, name, sentence, street_city_sentence):
    """The address gap of a row, or None; the street-and-city form when ticked outside the US."""
    if not _row_address_missing(row):
        return None
    return (street_city_sentence if row.outside_us else sentence).format(name=name)


def _asks_who(linked) -> bool:
    """Whether the linked row's own answers say who owns it. An old row, with no line, doesn't."""
    line = LINE_BY_KEY.get(linked.ab_line)
    return line is not None and line.shape in _SHAPES_THAT_ASK_WHO


def _live(link, session):
    return link if link_is_live(link, session) else None


def _asset_gaps(session, debts, contracts):
    """Each line 1 or line 4 row a debt or a vehicle lease links to whose "Do you live here?" is
    unanswered: the answer decides which Schedule J line the payment prints on."""
    linked = {live.pk for debt in debts if (live := _live(debt.secured_by, session))}
    linked |= {
        live.pk
        for contract in contracts
        if contract.contract_type == "lease"
        and contract.lease_kind == "vehicle"
        and (live := _live(contract.vehicle_asset, session))
    }
    gaps = []
    for row in ordered_assets(session):
        if row.pk in linked and row.ab_line in _HOME_LINES:
            if row.get_details().get("lives_here") is None:
                message = ASSET_GAP_LIVES_HERE.format(row=_row_name(row), line=row.ab_line)
                gaps.append(ClaimStepGap(message, "assets"))
    return gaps


def _debt_step_gaps(rows, answers):
    messages = []
    if any(row.is_draft for row in rows):
        messages.append(DEBT_GAP_DRAFT)
    if not rows and answers.get("no_debts") is not True:
        messages.append(DEBT_GAP_NO_ANSWER)
    if rows and answers.get("no_debts") is True:
        messages.append(DEBT_GAP_NONE_BUT_LISTED)
    return messages


def _notice_party_missing(party) -> bool:
    return _blank(party.get("name")) or address_missing(
        party.get("street_address"),
        party.get("city"),
        party.get("state"),
        party.get("zip_code"),
        party.get("outside_us"),
    )


def _debt_identity_gaps(debt, name):
    named = not _blank(debt.creditor_name)
    messages = []
    if not named:
        messages.append(DEBT_GAP_NO_NAME)
    if _blank(debt.debt_type):
        messages.append(CLAIM_GAP_KIND.format(name=name))
    if debt.amount_owed is None or debt.amount_owed <= Decimal("0"):
        messages.append((DEBT_GAP_AMOUNT if named else DEBT_GAP_AMOUNT_NO_NAME).format(name=name))
    sentence, street_city = (
        (CLAIM_GAP_ADDRESS, CLAIM_GAP_STREET_CITY)
        if named
        else (DEBT_GAP_ADDRESS_NO_NAME, DEBT_GAP_STREET_CITY_NO_NAME)
    )
    messages.append(_address_gap(debt, name, sentence, street_city))
    return messages


def _debt_secured_gaps(debt, name, session):
    if not debt.is_secured:
        return []
    messages = []
    linked = _live(debt.secured_by, session)
    lien = debt.get_lien()
    if linked is None:
        messages.append(DEBT_GAP_PROPERTY)
    if _blank(debt.collateral_description):
        messages.append(DEBT_GAP_DESCRIBE)
    if lien is None or not lien.get("kinds"):
        messages.append(DEBT_GAP_LIEN)
    elif "other" in lien["kinds"] and _blank(lien.get("other")):
        messages.append(DEBT_GAP_LIEN_OTHER)
    if debt.monthly_payment is None:
        messages.append(DEBT_GAP_PAYMENT)
    if linked is not None:
        if linked.get_details().get("lives_here") == "yes" and debt.home_payment_line is None:
            messages.append(DEBT_GAP_HOME_LINE)
        if not _asks_who(linked) and debt.collateral_who is None:
            messages.append(DEBT_GAP_WHO)
    return [message.format(name=name) for message in messages]


def _debt_answer_gaps(debt, name):
    messages = []
    if debt.get_claim_status() is None:
        messages.append(DEBT_GAP_STATUS)
    if not debt.is_secured and debt.offset_answer is None:
        messages.append(DEBT_GAP_OFFSET)
    parties = debt.get_notice_parties()
    if parties is None:
        messages.append(DEBT_GAP_NOTICE)
    elif any(_notice_party_missing(party) for party in parties):
        messages.append(DEBT_GAP_NOTICE_PARTY)
    return [message.format(name=name) for message in messages]


def _debt_gaps(session, rows, answers):
    messages = _debt_step_gaps(rows, answers)
    for debt in ordered_debts(rows):
        name = claim_row_name(debt.creditor_name, NAMELESS_DEBT)
        messages += _debt_identity_gaps(debt, name)
        messages += _debt_secured_gaps(debt, name, session)
        messages += _debt_answer_gaps(debt, name)
    return [ClaimStepGap(message, "debts") for message in messages if message]


def _list_answer_gaps(answer, rows, no_answer, yes_but_none, no_but_listed):
    if answer is None:
        return [no_answer]
    if answer == "yes" and not rows:
        return [yes_but_none]
    if answer == "no" and rows:
        return [no_but_listed]
    return []


def _same_vehicle_gap(contract, name, session):
    """B44: the lease and the debt on one vehicle each carry a payment above $0."""
    debt = _live(contract.owed_debt, session)
    vehicle = _live(contract.vehicle_asset, session)
    if debt is None or vehicle is None or not debt.is_secured:
        return None
    secured_by = _live(debt.secured_by, session)
    if secured_by is None or secured_by.pk != vehicle.pk:
        return None
    zero = Decimal("0")
    if (contract.monthly_payment or zero) > zero and (debt.monthly_payment or zero) > zero:
        debt_name = claim_row_name(debt.creditor_name, NAMELESS_DEBT)
        if _blank(contract.counterparty_name):
            return CONTRACT_GAP_SAME_VEHICLE_NO_NAME.format(debt=debt_name)
        return CONTRACT_GAP_SAME_VEHICLE.format(name=name, debt=debt_name)
    return None


def _contract_row_gaps(contract, session):
    name = claim_row_name(contract.counterparty_name, NAMELESS_CONTRACT)
    messages = []
    if _blank(contract.counterparty_name):
        messages.append(CONTRACT_GAP_NO_NAME)
    messages.append(_address_gap(contract, name, CLAIM_GAP_ADDRESS, CLAIM_GAP_STREET_CITY))
    if _blank(contract.contract_type):
        messages.append(CLAIM_GAP_KIND.format(name=name))
    if _blank(contract.description):
        messages.append(CONTRACT_GAP_PURPOSE.format(name=name))
    is_lease = contract.contract_type == "lease"
    if is_lease and contract.lease_kind is None:
        messages.append(CONTRACT_GAP_LEASE_KIND.format(name=name))
    is_vehicle = is_lease and contract.lease_kind == "vehicle"
    named = not _blank(contract.counterparty_name)
    if is_vehicle and _live(contract.vehicle_asset, session) is None:
        messages.append(
            CONTRACT_GAP_VEHICLE.format(name=name) if named else CONTRACT_GAP_VEHICLE_NO_NAME
        )
    if is_vehicle and contract.monthly_payment is None:
        messages.append(CONTRACT_GAP_PAYMENT.format(name=name))
    if contract.owes_now is None:
        messages.append(CONTRACT_GAP_OWES_NOW.format(name=name))
    if contract.owes_now == "yes" and _live(contract.owed_debt, session) is None:
        messages.append(CONTRACT_GAP_OWED_DEBT.format(name=name))
    if is_vehicle:
        messages.append(_same_vehicle_gap(contract, name, session))
    return messages


def _contract_gaps(session, rows, answers):
    messages = _list_answer_gaps(
        answers.get("contracts_answer"),
        rows,
        CONTRACT_GAP_NO_ANSWER,
        CONTRACT_GAP_YES_BUT_NONE,
        CONTRACT_GAP_NO_BUT_LISTED,
    )
    for contract in rows:
        messages += _contract_row_gaps(contract, session)
    return [ClaimStepGap(message, "contracts") for message in messages if message]


def _community_gaps(answers):
    lived = answers.get("community_lived")
    if lived is None:
        return [CODEBTOR_GAP_COMMUNITY]
    if lived != "yes":
        return []
    with_spouse = answers.get("community_spouse_lived_with")
    if with_spouse is None:
        return [CODEBTOR_GAP_SPOUSE_LIVED]
    if with_spouse != "yes":
        return []
    spouse_address_missing = address_missing(
        answers.get("community_spouse_street_address"),
        answers.get("community_spouse_city"),
        answers.get("community_spouse_state"),
        answers.get("community_spouse_zip_code"),
        answers.get("community_spouse_outside_us"),
    )
    if (
        _blank(answers.get("community_state"))
        or _blank(answers.get("community_spouse_name"))
        or spouse_address_missing
    ):
        return [CODEBTOR_GAP_SPOUSE_DETAILS]
    return []


def _codebtor_row_gaps(codebtor, live_ids):
    name = claim_row_name(codebtor.name, NAMELESS_CODEBTOR)
    messages = []
    if _blank(codebtor.name):
        messages.append(CODEBTOR_GAP_NO_NAME)
    messages.append(_address_gap(codebtor, name, CLAIM_GAP_ADDRESS, CLAIM_GAP_STREET_CITY))
    if not any((link.get("kind"), link.get("id")) in live_ids for link in codebtor.get_links()):
        messages.append(CODEBTOR_GAP_NO_LINK.format(name=name))
    return messages


def _codebtor_gaps(session, rows, debts, contracts, answers):
    messages = _list_answer_gaps(
        answers.get("codebtors_answer"),
        rows,
        CODEBTOR_GAP_NO_ANSWER,
        CODEBTOR_GAP_YES_BUT_NONE,
        CODEBTOR_GAP_NO_BUT_LISTED,
    )
    messages += _community_gaps(answers)
    live_ids = {("debt", debt.pk) for debt in debts} | {
        ("contract", contract.pk) for contract in contracts
    }
    for codebtor in rows:
        messages += _codebtor_row_gaps(codebtor, live_ids)
    return [ClaimStepGap(message, "codebtors") for message in messages if message]


def claim_step_gaps(session) -> list[ClaimStepGap]:
    """Everything the claims steps and the payments on property still lack, row by row (R8).

    The first four blocks (Assets' "Do you live here?", Amounts Owed, Contracts, Codebtors) are in
    wizard order. The tail comes after Codebtors, out of wizard order on purpose: the legacy gaps
    (step `debts`) and then the line 4 question (step `expense_info`), since both read the links
    the earlier steps made.

    The four blocks read the session's debts (drafts included, so a draft's gaps show),
    contracts and codebtors, and its ClaimAnswers: no row means every answer is null. The Assets
    block asks "Do you live here?" of a line 1 or line 4 row that a debt or a vehicle lease links
    to. Contracts and codebtors go in id order, debts in ordered_debts' order. The tail also reads
    the Expenses row (_legacy_figure) and, through linked_payments, the session's assets, its
    vehicle leases and only its confirmed debts, so a draft never counts there.
    """
    row = getattr(session, "claim_answers", None)
    answers = row.get_answers() if row is not None else {}
    debts = list(session.debts.all())
    contracts = sorted(session.executory_contracts.all(), key=lambda row: row.pk)
    codebtors = sorted(session.codebtors.all(), key=lambda row: row.pk)
    gaps = [
        *_asset_gaps(session, debts, contracts),
        *_debt_gaps(session, debts, answers),
        *_contract_gaps(session, contracts, answers),
        *_codebtor_gaps(session, codebtors, debts, contracts, answers),
    ]
    linked = linked_payments(session)
    return [*gaps, *_legacy_gaps(session, linked), *_line_4_gap(session, linked, answers)]


def _legacy_figure(session, field) -> Decimal:
    """One Expenses figure (a retired one, or rent_or_mortgage), $0 with no Expenses row or a
    null. Reads the row by attribute, as claim_step_gaps reads claim_answers, since this module
    imports no model."""
    row = getattr(session, "expense_info", None)
    return (getattr(row, field, None) or _ZERO) if row is not None else _ZERO


def _legacy_gaps(session, linked) -> list[ClaimStepGap]:
    """A stored car or other-property payment above what the links add up to (R6).

    Each figure compares with its own sum: a mortgage on other property never covers a car.
    """
    gaps = []
    for field, covered, sentence in (
        ("vehicle_payment", linked.vehicle_total, CLAIM_GAP_LEGACY_VEHICLE),
        ("other_property_mortgages", linked.other_real_property, CLAIM_GAP_LEGACY_OTHER),
    ):
        typed = _legacy_figure(session, field)
        if typed > covered:
            message = sentence.format(typed=format_figure(typed), linked=format_figure(covered))
            gaps.append(ClaimStepGap(message, "debts"))
    return gaps


def _line_4_gap(session, linked, answers) -> list[ClaimStepGap]:
    """A typed rent beside a linked first mortgage, until the filer confirms the typed figure (R7).

    Counts first-mortgage debts only: a vehicle lease on a home row adds to J 4 without asking.
    """
    typed = _legacy_figure(session, "rent_or_mortgage")
    if typed <= _ZERO or linked.first_mortgage <= _ZERO:
        return []
    stored = answers.get("line_4_both_confirmed")
    if stored is not None and Decimal(stored) == typed:
        return []
    message = CLAIM_GAP_LINE_4.format(
        typed=format_figure(typed), linked=format_figure(linked.first_mortgage)
    )
    return [ClaimStepGap(message, "expense_info")]


def legacy_payments(session) -> dict:
    """The session read's retired figures: a decimal string while above $0, else None."""
    out = {}
    for field in ("vehicle_payment", "other_property_mortgages"):
        value = _legacy_figure(session, field)
        out[field] = f"{value:.2f}" if value > _ZERO else None
    return out


VEHICLE_WORDS = ("Vehicle 3", "Vehicle 4")
OTHER_PROPERTY_WORDS = "Payment on other property"
SPILL_WORDS = "Other secured payments"


@dataclass(frozen=True)
class LinkedPayments:
    first_mortgage: Decimal  # J 4's debt part
    home_lease: Decimal  # J 4's lease part (a vehicle lease on a home row)
    additional_mortgage: Decimal  # J 5
    other_real_property: Decimal  # J 20a
    j17: dict[str, Decimal]  # keys "17a", "17b", "17c", "17d"
    j17_words: dict[str, str]  # keys "17c", "17d": one of the four words, or ""
    vehicle_total: Decimal  # every payment on a vehicle row, spill included (R6)
    total: Decimal  # every counted payment


def format_figure(value: Decimal) -> str:
    """A figure as the filer reads it: 1200 is "1,200.00"."""
    return f"{value:,.2f}"


def _payment(row) -> Decimal:
    return row.monthly_payment or _ZERO


def linked_payments(session) -> LinkedPayments:
    """Every monthly payment on property that Schedule J prints, by line (3c4 R1).

    A debt counts when it is confirmed, secured and linked to a row of this session; a lease when
    it is a vehicle lease linked the same way. A stale link (a debt answered No, a lease changed
    to another kind) is kept on the row but never counted. Payments on one row add.
    """
    rows = ordered_assets(session)
    by_id = {row.pk: row for row in rows}
    home_ids = {
        row.pk
        for row in rows
        if row.ab_line in _HOME_LINES and row.get_details().get("lives_here") == "yes"
    }
    # A null "Do you live here?" on line 1 reads as No: a claim gap refuses it first (R1).
    line_1_away = {row.pk for row in rows if row.ab_line == "1" and row.pk not in home_ids}
    vehicles = [row for row in rows if row.ab_line == "3"] + [
        row for row in rows if row.ab_line == "4" and row.pk not in home_ids
    ]
    vehicle_ids = {row.pk for row in vehicles}

    first_mortgage = home_lease = additional = other_real = _ZERO
    on_row: dict[int, Decimal] = {}
    for debt in session.debts.confirmed():
        if not debt.is_secured or not link_is_live(by_id.get(debt.secured_by_id), session):
            continue
        pk, amount = debt.secured_by_id, _payment(debt)
        if pk in home_ids:
            if debt.home_payment_line == "additional":
                additional += amount
            else:
                first_mortgage += amount
        elif pk in line_1_away:
            other_real += amount
        else:
            on_row[pk] = on_row.get(pk, _ZERO) + amount
    for contract in session.executory_contracts.all():
        if (
            contract.contract_type != "lease"
            or contract.lease_kind != "vehicle"
            or not link_is_live(by_id.get(contract.vehicle_asset_id), session)
        ):
            continue
        pk, amount = contract.vehicle_asset_id, _payment(contract)
        if pk in home_ids:
            home_lease += amount
        else:
            on_row[pk] = on_row.get(pk, _ZERO) + amount

    vehicle_pays = [on_row.get(row.pk, _ZERO) for row in vehicles]
    others = [
        on_row[row.pk]
        for row in rows
        if row.pk in on_row and row.pk not in vehicle_ids and on_row[row.pk] > 0
    ]
    j17 = {"17a": _ZERO, "17b": _ZERO, "17c": _ZERO, "17d": _ZERO}
    for key, amount in zip(("17a", "17b"), vehicle_pays, strict=False):
        j17[key] = amount
    entries = [
        (amount, VEHICLE_WORDS[i - 2] if i < 4 else "")
        for i, amount in enumerate(vehicle_pays)
        if i >= 2
    ] + [(amount, OTHER_PROPERTY_WORDS) for amount in others]
    words = {"17c": "", "17d": ""}
    if entries:
        j17["17c"] = entries[0][0]
        words["17c"] = entries[0][1] if j17["17c"] > 0 else ""
    if len(entries) > 1:
        rest = sum((amount for amount, _ in entries[2:]), _ZERO)
        j17["17d"] = entries[1][0] + rest
        if rest > 0:
            words["17d"] = SPILL_WORDS
        elif j17["17d"] > 0:
            words["17d"] = entries[1][1]

    vehicle_total = sum(vehicle_pays, _ZERO)
    total = (
        first_mortgage + home_lease + additional + other_real + vehicle_total + sum(others, _ZERO)
    )
    return LinkedPayments(
        first_mortgage=first_mortgage,
        home_lease=home_lease,
        additional_mortgage=additional,
        other_real_property=other_real,
        j17=j17,
        j17_words=words,
        vehicle_total=vehicle_total,
        total=total,
    )


def total_monthly_expenses(session) -> Decimal:
    """The typed expense amounts plus every counted payment (3c4 R2).

    Reads the typed sum through the model, as the schema tests patch it. A session with no
    Expenses row raises ExpenseInfo.DoesNotExist, which the form's total rule turns into 0.00.
    """
    typed = Decimal(str(session.expense_info.calculate_total_monthly_expenses()))
    return typed.quantize(Decimal("0.01")) + linked_payments(session).total
