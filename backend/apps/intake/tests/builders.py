"""Synthetic household answers for intake, eligibility and forms tests.

Every value here is invented. answer_household's defaults make a session that passes 3e1's new
checks: not married, no one else in the home or supported ([]), and Cook County. The 3e2
defaults answer the other four: income not now different, no business or rental ([]), no other
government assistance, and $0 taken out of pay. answer_household also chooses to pay the filing
fee in full (Form 101 line 8), so a forms test meets no refusal for a missing answer;
payment_choice=None leaves the answer as it is. The claim answers default to no debts, and No on
contracts, codebtors and H line 2.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from types import MappingProxyType

from apps.intake.asset_lines import shown_lines
from apps.intake.models import (
    AssetInfo,
    AssetLineAnswers,
    ClaimAnswers,
    Codebtor,
    DebtInfo,
    ExecutoryContract,
    ExemptionAnswers,
    FilingFee,
    Household,
    SpouseIncome,
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
    line 1 answered, "not claiming" and line 3 No; exemptions=None leaves them alone.
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
    return household


def answer_exemptions(
    session,
    *,
    line_1: str | None = "state_and_federal",
    line_3: str | None = "no",
    line_3_1: str | None = None,
    no_claims: bool = True,
) -> ExemptionAnswers:
    """Store Schedule C's page answers (3g1), through the session's own relation. The defaults
    finish the page: line 1 answered, line 3 No, and "I'm not claiming any property as exempt"."""
    row = getattr(session, "exemption_answers", None) or ExemptionAnswers(session=session)
    row.line_1 = line_1
    row.line_3 = line_3
    row.line_3_1 = line_3_1
    row.no_claims = no_claims
    row.save()
    return row


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
