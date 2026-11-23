"""Synthetic household answers for intake, eligibility and forms tests.

Every value here is invented. answer_household's defaults make a session that passes 3e1's new
checks: not married, no one else in the home or supported ([]), and Cook County. The 3e2
defaults answer the other four: income not now different, no business or rental ([]), no other
government assistance, and $0 taken out of pay. answer_household also chooses to pay the filing
fee in full (Form 101 line 8), so a forms test meets no refusal for a missing answer;
payment_choice=None leaves the answer as it is. The claim answers default to no debts, and No on
contracts, codebtors and H line 2. Schedule I's answers default to not employed and No on lines
11, 13 and Schedule J line 24 (SCHEDULE_I_DEFAULTS).
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from types import MappingProxyType

from apps.districts.dated_tables import fill_date
from apps.eligibility.means_inputs import counted_debts, vehicle_rows
from apps.intake.asset_lines import shown_lines
from apps.intake.means_test import PER_DEBT_KEYS
from apps.intake.models import (
    AssetInfo,
    AssetLineAnswers,
    ClaimAnswers,
    Codebtor,
    DebtInfo,
    ExecutoryContract,
    ExemptionAnswers,
    ExpenseInfo,
    FilingFee,
    Household,
    MeansTestAnswers,
    PetitionAnswers,
    ScheduleIAnswers,
    SecuredDebtAnswers,
    SpouseIncome,
)
from apps.intake.petition import STEP_1_GATES
from apps.intake.schedule_i import married_together

# Schedule I's and Schedule J line 24's answers that leave no gap (4c-R13): not employed, and No
# on lines 11, 13 and 24. answer_household adds the spouse's "not employed" for a filer married
# with the spouse at home (`married_together`).
SCHEDULE_I_DEFAULTS = MappingProxyType(
    {
        "employment_status": "not_employed",
        "line_11_answer": "no",
        "line_13_answer": "no",
        "schedule_j_line_24_answer": "no",
    }
)


def answer_income_detail(
    row,
    *,
    income_now_different: str | None = "no",
    business_and_rental: Sequence[dict] | None = (),
    assistance_answer: str | None = "no",
    payroll_tax: Decimal | None = Decimal("0"),
) -> None:
    """Store the four 3e2 answers on an IncomeInfo or SpouseIncome row and save it.

    The list goes through store_entries as copies, so a caller's rows never gain an id. A test
    that builds a row by hand calls this on it.
    """
    row.income_now_different = income_now_different
    row.store_entries(
        None if business_and_rental is None else [dict(entry) for entry in business_and_rental]
    )
    row.assistance_answer = assistance_answer
    row.payroll_tax = payroll_tax
    row.save()


def answer_asset_lines(session, yes: Iterable[str] = ()) -> None:
    """Store "yes" for the named Schedule A/B lines and "no" for every other line shown.

    A gate named in yes shows its lines (37 and 46), which then store "no". A line whose
    gate isn't answered "yes" is hidden and stores nothing, as the wizard stores it.
    """
    answers = dict.fromkeys(yes, "yes")
    for line in shown_lines(answers):
        answers.setdefault(line.key, "no")
    row = getattr(session, "asset_lines", None) or AssetLineAnswers(session=session)
    row.answers = json.dumps(answers)
    row.save()


def answer_household(
    session,
    *,
    marital_status: str | None = "not_married",
    members: Sequence[dict] | None = (),
    county: str | None = "Cook",
    spouse_income: Mapping[str, Decimal | None] | None = None,
    income_now_different: str | None = "no",
    business_and_rental: Sequence[dict] | None = (),
    assistance_answer: str | None = "no",
    payroll_tax: Decimal | None = Decimal("0"),
    payment_choice: str | None = "pay_in_full",
    asset_lines: Iterable[str] | None = (),
    claims: Mapping[str, object] | None = MappingProxyType({}),
    exemptions: Mapping[str, object] | None = MappingProxyType({}),
    schedule_i: Mapping[str, object] | None = SCHEDULE_I_DEFAULTS,
) -> Household:
    """Store the marriage answer, the county and the household list, and the spouse's amounts
    when given, through the session's own relations, so a test holding the session reads them.

    The session needs an income row. A second call replaces the answer, the county and the
    list. spouse_income={} stores all ten amounts empty; None leaves any stored row alone.

    The four 3e2 answers (defaults: "no", [], "no", $0) go to the filer's row, and to the
    spouse's row when spouse_income is given.

    payment_choice goes to the session's FilingFee, created if missing; None leaves any stored
    row alone.

    asset_lines names the Schedule A/B lines answered Yes (default none: every shown line No);
    None leaves the stored answers alone.

    claims overrides the claim answers answer_claims stores (3c3), which default to no_debts true
    while the session has no debt rows, and No on contracts, codebtors and H line 2; claims=None
    leaves them alone.

    exemptions overrides the Schedule C answers answer_exemptions stores (3g1), which default to
    line 1 answered, line 3 No and "not claiming" while the session has no stored claim (False
    once it has one); exemptions=None leaves them alone.

    schedule_i answers Schedule I lines 1, 11 and 13 and Schedule J line 24 (4c). The default,
    SCHEDULE_I_DEFAULTS (plus the spouse's "not employed" under married_together), gives way to
    any key already stored, so a second call keeps what a test stored; a mapping passed is
    applied whole, through answer_schedule_i; None leaves the record alone.
    """
    session.income_info.marital_status = marital_status
    session.income_info.save(update_fields=["marital_status"])
    detail = {
        "income_now_different": income_now_different,
        "business_and_rental": business_and_rental,
        "assistance_answer": assistance_answer,
        "payroll_tax": payroll_tax,
    }
    answer_income_detail(session.income_info, **detail)

    household = getattr(session, "household", None) or Household(session=session)
    # Copies, so a caller's module-level rows never gain an id.
    household.store_members(None if members is None else [dict(row) for row in members])
    household.county = county
    household.save()

    if spouse_income is not None:
        row = getattr(session, "spouse_income", None) or SpouseIncome(session=session)
        for field in SpouseIncome.SOURCE_FIELDS:
            setattr(row, field, spouse_income.get(field))
        row.save()
        answer_income_detail(row, **detail)
        row.refresh_from_db()  # the Decimals the encrypted column returns
    if asset_lines is not None:
        answer_asset_lines(session, asset_lines)
    if payment_choice is not None:
        fee = getattr(session, "filing_fee", None) or FilingFee(session=session)
        fee.payment_choice = payment_choice
        fee.save()
    if claims is not None:
        answer_claims(
            session, **{"no_debts": True if not session.debts.exists() else None, **claims}
        )
    if exemptions is not None:
        answer_exemptions(session, **exemptions)
    if schedule_i is SCHEDULE_I_DEFAULTS:
        defaults = dict(SCHEDULE_I_DEFAULTS)
        if married_together(session):
            defaults["spouse_employment_status"] = "not_employed"
        record = getattr(session, "schedule_i_answers", None)
        stored = record.get_answers() if record else {}
        answer_schedule_i(session, **{k: v for k, v in defaults.items() if k not in stored})
    elif schedule_i is not None:
        answer_schedule_i(session, **schedule_i)
    return household


def finish_intake(session, **expense_over) -> None:
    """Give a session that answer_household finished the Expenses row Complete requires, and
    Form 101's answers (answer_petition's defaults; a stored answer is kept).

    answer_household's $0 payroll_tax already covers take-home pay, so the row and the petition
    answers are the last things a gate in completion_gaps asks of it. expenses_include_others is
    the form's own word, "no", never False: the column holds the string and Schedule J prints
    it, so a boolean would print "False", a No the filer did not give. update_or_create,
    because ExpenseInfo.session is one-to-one and a test may have made the row itself.
    """
    ExpenseInfo.objects.update_or_create(
        session=session, defaults={"expenses_include_others": "no", **expense_over}
    )
    answer_petition(session)


# Form 101's answers that finish its steps (4b-ii): every step 1 question No, the venue as "lived
# here", the hazard No and the rent No. Nothing for 4d's or 4i's keys, which no step asks yet.
PETITION_DEFAULTS = MappingProxyType(
    {
        **dict.fromkeys(STEP_1_GATES, "no"),
        "venue_choice": "lived_here",
        "hazard_answer": "no",
        "rents_residence": "no",
    }
)


def answer_petition(session, **over) -> PetitionAnswers:
    """Store Form 101's asked answers (4b-ii), through the session's own relation.

    The record is made if missing. A stored answer beats a default, so a second call keeps what
    a test stored; `over` beats both, a None in it removes the key (unanswered), and an unknown
    key raises KeyError, as the record's own merge does. Never a fresh query, so the session a
    test holds never reads a stale copy.
    """
    record = getattr(session, "petition_answers", None) or PetitionAnswers(session=session)
    stored = record.get_answers()
    defaults = {key: value for key, value in PETITION_DEFAULTS.items() if key not in stored}
    record.merge({**defaults, **over})
    record.save()
    return record


def answer_schedule_i(session, **answers) -> ScheduleIAnswers:
    """Store Schedule I's and Schedule J line 24's answers (4c), through the session's own
    relation.

    The record is made if missing. A None removes the key (unanswered), and an unknown key raises
    KeyError, as the record's own merge does. Never a fresh query, so the session a test holds
    never reads a stale copy.
    """
    record = getattr(session, "schedule_i_answers", None) or ScheduleIAnswers(session=session)
    record.merge(answers)
    record.save()
    return record


def answer_exemptions(
    session,
    *,
    line_1: str | None = "state_and_federal",
    line_3: str | None = "no",
    line_3_1: str | None = None,
    no_claims: bool | None = None,
) -> ExemptionAnswers:
    """Store Schedule C's page answers (3g1), through the session's own relation. The defaults
    finish the page: line 1 answered, line 3 No, and "I'm not claiming any property as exempt"
    only while the session has no claim (the API refuses both together); with claims it is
    False, the column's unanswered. An explicit no_claims wins."""
    row = getattr(session, "exemption_answers", None) or ExemptionAnswers(session=session)
    if no_claims is None:
        no_claims = not session.exemption_claims.exists()
    row.line_1 = line_1
    row.line_3 = line_3
    row.line_3_1 = line_3_1
    row.no_claims = no_claims
    row.save()
    return row


MEANS_DEBT_ANSWERS = MappingProxyType(
    {"payments_left": "60_or_more", "payment_changes": "no", "taxes_or_insurance": "no"}
)


def answer_means_test(
    session, *, debts: Mapping = MappingProxyType({}), **over
) -> MeansTestAnswers:
    """Store every Form 122A-2 page answer (3h2), through the session's own relation. These are
    test answers, not defaults the app ever offers.

    The defaults answer No (or "0.00") to every question; line 3 and the spouse's two
    questions are answered only under married_together, and Vehicle 1 and 2 are left unset.
    Each call writes every default again, and each counted secured debt's, before `over` (a
    page key, replacing its answer whole; None stores null) and `debts` ({debt pk: per-debt
    answers}, merged over that debt's defaults), so pass the whole of both each time.

    The two spouse id counters move past every `spouse-N` ref stored. An unknown page key
    raises KeyError, and so does a `debts` key naming no counted debt or a per-debt key not
    in PER_DEBT_KEYS, before anything is written.
    """
    rows = vehicle_rows(session)
    counted = counted_debts(session)
    if any(pk not in {debt.pk for debt in counted} for pk in debts):
        raise KeyError("debts names a debt the page doesn't ask about.")
    if any(key not in PER_DEBT_KEYS for answers in debts.values() for key in answers):
        raise KeyError("debts names a per-debt answer the page doesn't ask.")
    income = getattr(session, "income_info", None)
    together = getattr(income, "marital_status", None) == "married_together"
    answers = {
        "line_3_answer": "no" if together else None,
        "spouse_vehicles_answer": "no" if together else None,
        "spouse_loans_answer": "no" if together else None,
        "vehicle_claims": {f"asset-{row.pk}": "no" for row in rows},
        "line_15_answer": "no",
        "line_22_answer": "no",
        "line_25_answer": "no",
        **{f"line_{n}_answer": "no" for n in range(26, 32)},
        **{f"line_{n}": "0.00" for n in (16, 17, 18, 19, 20, 21, 23)},
        "line_34_answer": "no",
        "line_36_answer": "no",
        "line_43_answer": "no",
    }
    record = getattr(session, "means_test_answers", None) or MeansTestAnswers(session=session)
    record.merge(answers | over)
    # a stored spouse row keeps its ref, so the next one a test sends starts past every stored ref
    stored = record.get_answers()
    for list_key, counter in (
        ("spouse_vehicles", "next_spouse_vehicle_id"),
        ("spouse_loans", "next_spouse_loan_id"),
    ):
        numbers = [
            int(row["ref"].removeprefix("spouse-"))
            for row in stored.get(list_key) or []
            if str(row.get("ref", "")).startswith("spouse-")
        ]
        setattr(record, counter, max([getattr(record, counter), *(n + 1 for n in numbers)]))
    record.debts_answered_on = fill_date().isoformat()
    record.save()
    for debt in counted:
        per_debt = {key: MEANS_DEBT_ANSWERS.get(key) for key in PER_DEBT_KEYS}
        per_debt |= debts.get(debt.pk, {})
        row = getattr(debt, "means_answers", None) or SecuredDebtAnswers(debt=debt)
        for key, value in per_debt.items():
            if key in ("total_60_months", "cure") and value is not None:
                value = Decimal(str(value))
            setattr(row, key, value)
        row.save()
    return record


DEMO_ADDRESS = {
    "street_address": "1 Demo Street",
    "city": "Demoville",
    "state": "IL",
    "zip_code": "60601",
}


def _claim_answers_row(session, *, create: bool) -> ClaimAnswers | None:
    """The session's ClaimAnswers through its own relation, never a fresh query, so the
    session a test holds never reads a stale copy. create=True makes a missing row."""
    row = getattr(session, "claim_answers", None)
    if row is None and create:
        row = ClaimAnswers(session=session)
        session.claim_answers = row
    return row


def _merge_claim_answers(session, **sent) -> ClaimAnswers:
    row = _claim_answers_row(session, create=True)
    row.merge(sent)
    row.save()
    return row


def answer_claims(
    session,
    *,
    no_debts: bool | None = None,
    contracts_answer: str | None = "no",
    codebtors_answer: str | None = "no",
    community_lived: str | None = "no",
    **more,
) -> ClaimAnswers:
    """Store the filer's claim answers (3c3): by default no contracts, no codebtors and no
    community property state, and no_debts unanswered. A None clears an answer.

    Call it after the rows a test builds, as answer_household is.
    """
    return _merge_claim_answers(
        session,
        no_debts=no_debts,
        contracts_answer=contracts_answer,
        codebtors_answer=codebtors_answer,
        community_lived=community_lived,
        **more,
    )


def complete_debt(session, **over) -> DebtInfo:
    """A confirmed, unsecured credit card debt with every answer a gap could ask for.

    Overridable by field. lien and claim_status are Python values, dumped here;
    notice_parties goes through store_notice_parties. A session that says it has no debts
    stops saying so (when it has a ClaimAnswers row).
    """
    fields = {
        "creditor_name": "Demo Card Services",
        "debt_type": "credit_card",
        "amount_owed": Decimal("500.00"),
        **DEMO_ADDRESS,
        "claim_status": [],
        "offset_answer": "no",
        "priority_answer": "no",
        "notice_parties": [],
        "is_draft": False,
        "is_secured": False,
    } | over
    notice_parties = fields.pop("notice_parties")
    for key in DebtInfo.JSON_ANSWERS:
        if fields.get(key) is not None:
            fields[key] = json.dumps(fields[key])
    debt = DebtInfo(session=session, **fields)
    debt.store_notice_parties(notice_parties)
    debt.save()
    row = _claim_answers_row(session, create=False)
    if row is not None:
        row.merge({"no_debts": None})
        row.save()
    return debt


def complete_contract(session, **over) -> ExecutoryContract:
    """A residential lease with every answer, which also answers Yes to "any contracts"."""
    fields = {
        "counterparty_name": "Demo Property Management LLC",
        **DEMO_ADDRESS,
        "contract_type": "lease",
        "lease_kind": "residential",
        "description": "Apartment lease",
        "owes_now": "no",
    } | over
    contract = ExecutoryContract.objects.create(session=session, **fields)
    _merge_claim_answers(session, contracts_answer="yes")
    return contract


def complete_codebtor(session, links=None, **over) -> Codebtor:
    """A codebtor on the session's first debt (build it first, with complete_debt), which also
    answers Yes to "any codebtors". links is a list of {kind, id}, dumped here."""
    if links is None:
        links = [{"kind": "debt", "id": session.debts.order_by("pk").first().pk}]
    fields = {"name": "Demo Codebtor", **DEMO_ADDRESS} | over
    codebtor = Codebtor.objects.create(session=session, links=json.dumps(links), **fields)
    _merge_claim_answers(session, codebtors_answer="yes")
    return codebtor


def linked_row(session, line, lives_here=None, description="Demo item") -> AssetInfo:
    """An A/B row on a line with its "Do you live here?" answer (3c4's payment mapping)."""
    row = AssetInfo(session=session, ab_line=line, description=description)
    row.set_details({"lives_here": lives_here})
    row.save()
    return row


def linked_loan(session, row, payment, **over) -> DebtInfo:
    """A secured debt on a row, paying the given monthly figure."""
    return complete_debt(
        session,
        **(
            {
                "is_secured": True,
                "secured_by": row,
                "monthly_payment": Decimal(payment),
                "collateral_description": "Demo",
                "lien": {"kinds": ["agreement"], "other": ""},
            }
            | over
        ),
    )


def linked_lease(session, row, payment, **over) -> ExecutoryContract:
    """A vehicle lease on a row, paying the given monthly figure."""
    return complete_contract(
        session,
        **(
            {"lease_kind": "vehicle", "vehicle_asset": row, "monthly_payment": Decimal(payment)}
            | over
        ),
    )
