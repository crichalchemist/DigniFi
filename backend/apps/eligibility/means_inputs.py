"""The session's side of Form 122A-2: what the filer gave DigniFi, and the tables in force.

`read_inputs` fills a `MeansInputs` from the intake and reads the page's answers, so nothing is
worked out from a Schedule I or J figure. `read_tables` turns the two dated
sets into the calculator's `MeansTables`. This module imports nothing from `apps.forms` or
`apps.eligibility.services`.
"""

from datetime import date
from decimal import Decimal

from apps.districts.dated_tables import fill_date
from apps.districts.means_standards import (
    MEANS_STANDARDS_TABLE,
    SECTION_104_TABLE,
    means_standards_in_force,
    section_104_in_force,
)
from apps.eligibility.cmi import household_cmi, household_members
from apps.eligibility.means_lines import (
    HealthInsurance,
    MeansInputs,
    MeansTableKeyMissing,
    MeansTables,
    OptIn,
    SecuredDebt,
    Vehicle,
)
from apps.intake.asset_lines import exemption_item_name, ordered_assets
from apps.intake.claim_rows import claim_rows
from apps.intake.claims import ordered_debts
from apps.intake.means_test import PER_DEBT_KEYS, PROPERTY_CHOICES, normalized_answers

VEHICLE_LINE = "3"
OTHER_VEHICLE_LINE = "4"
_HOME_LINES = ("1", OTHER_VEHICLE_LINE)


def _age_on(born: date, day: date) -> int:
    """Whole years between, less one when the birthday hasn't come by `day`."""
    before_birthday = (day.month, day.day) < (born.month, born.day)
    return day.year - born.year - (1 if before_birthday else 0)


def _ages(session) -> tuple[int | None, ...]:
    """The filer, then each household row claimed or supported, in list order."""
    debtor = getattr(session, "debtor_info", None)
    filer = None if debtor is None else _age_on(debtor.date_of_birth, fill_date())
    # DRAFT: counsel C-22 (line 5 counts the rows claimed or supported, as count_exemptions does)
    counted = (
        member.get("age")
        for member in household_members(session)
        if member.get("claimed_or_supported") is True
    )
    return (filer, *counted)


def _is_vehicle(row) -> bool:
    if row.ab_line == VEHICLE_LINE:
        return True
    return row.ab_line == OTHER_VEHICLE_LINE and row.get_details().get("lives_here") != "yes"


def _lives_in(row) -> bool:
    return row.ab_line in _HOME_LINES and row.get_details().get("lives_here") == "yes"


def vehicle_rows(session) -> list:
    """The A/B rows Form 122A-2 counts as vehicles, in `ordered_assets` order."""
    return [row for row in ordered_assets(session) if _is_vehicle(row)]


def counted_debts(session) -> list:
    """The confirmed secured debts the reader counts and the page asks about."""
    return [
        debt for debt in ordered_debts(list(session.debts.confirmed())) if debt.is_secured is True
    ]


def open_debts(session) -> list:
    """The confirmed debts Amounts Owed doesn't list as secured."""
    return [
        debt
        for debt in ordered_debts(list(session.debts.confirmed()))
        if debt.is_secured is not True
    ]


def page_answers(session) -> dict:
    """The stored page answers, a reference to a row that has gone read as unanswered."""
    record = getattr(session, "means_test_answers", None)
    stored = {} if record is None else record.get_answers()
    return normalized_answers(
        stored,
        {f"asset-{row.pk}" for row in vehicle_rows(session)},
        {debt.pk for debt in open_debts(session)},
    )


def _decimal(amount) -> Decimal | None:
    """A stored amount as a Decimal; None stays None (a typed "0.00" is an answer)."""
    return None if amount is None else Decimal(amount)


def _payments_left(text) -> int | None:
    if text is None:
        return None
    return 60 if text == "60_or_more" else int(text)


def _flag(answer) -> bool | None:
    return None if answer is None else answer == "yes"


def _opt_in(answers, name) -> OptIn | None:
    answer = answers[f"{name}_answer"]
    if answer is None:
        return None
    return OptIn(answer, _decimal(answers[f"{name}_amount"]))


def _vehicles(session, rows, claims) -> tuple[Vehicle, ...]:
    """`rows` is `vehicle_rows(session)`; `claims` the stored `vehicle_claims` ({} for none)."""
    # DRAFT: counsel C-28 (a vehicle lease takes a slot, and its payment is on no line)
    leased = {
        contract.vehicle_asset_id
        for contract in session.executory_contracts.all()
        if contract.contract_type == "lease" and contract.lease_kind == "vehicle"
    }
    return tuple(
        Vehicle(
            ref=f"asset-{row.pk}",
            name=exemption_item_name(row),
            leased=row.pk in leased,
            claimed=_flag(claims.get(f"asset-{row.pk}")),
        )
        for row in rows
    )


def _secured_debts(rows, debts) -> tuple[SecuredDebt, ...]:
    by_id = {row.pk: row for row in rows}
    out = []
    for debt in debts:
        linked = by_id.get(debt.secured_by_id)
        answers = getattr(debt, "means_answers", None)
        given = {name: getattr(answers, name, None) for name in PER_DEBT_KEYS}
        out.append(
            SecuredDebt(
                ref=f"debt-{debt.pk}",
                creditor=debt.creditor_name,
                secured_by=None if linked is None else f"asset-{linked.pk}",
                on_home=linked is not None and _lives_in(linked),
                property="" if linked is None else exemption_item_name(linked),
                monthly_payment=debt.monthly_payment,
                payments_left=_payments_left(given["payments_left"]),
                payment_changes=given["payment_changes"],
                total_60_months=given["total_60_months"],
                taxes_or_insurance=given["taxes_or_insurance"],
                necessary_for_support=given["necessary_for_support"],
                cure=given["cure"],
            )
        )
    return tuple(out)


def _spouse_vehicles(answers) -> tuple[Vehicle, ...]:
    if answers["spouse_vehicles_answer"] != "yes":
        return ()
    return tuple(
        Vehicle(
            ref=row["ref"],
            name=row.get("description") or "",
            leased=_flag(row.get("leased")),
            claimed=_flag(row.get("claimed")),
        )
        for row in answers["spouse_vehicles"]
    )


def _spouse_loans(answers, open_by_id, names) -> tuple[SecuredDebt, ...]:
    """The spouse's loans, `names` mapping a vehicle ref to its name."""
    if answers["spouse_loans_answer"] != "yes":
        return ()
    out = []
    for loan in answers["spouse_loans"]:
        debt = open_by_id.get(loan.get("debt"))
        secured_by = loan.get("secured_by")
        names_vehicle = secured_by not in (None, *PROPERTY_CHOICES)
        on_list = loan.get("on_amounts_owed")
        placed = secured_by is not None and (
            on_list == "no" or (on_list == "yes" and debt is not None)
        )
        out.append(
            SecuredDebt(
                ref=loan["ref"],
                creditor=debt.creditor_name if debt is not None else loan.get("creditor") or "",
                secured_by=secured_by if names_vehicle else None,
                on_home=secured_by == "home",
                property=names[secured_by] if names_vehicle else loan.get("property") or "",
                monthly_payment=_decimal(loan.get("payment")),
                payments_left=_payments_left(loan.get("payments_left")),
                payment_changes=loan.get("payment_changes"),
                total_60_months=_decimal(loan.get("total_60_months")),
                taxes_or_insurance=loan.get("taxes_or_insurance"),
                necessary_for_support=loan.get("necessary_for_support"),
                cure=_decimal(loan.get("cure")),
                placed=placed,
            )
        )
    return tuple(out)


def _line_35(priority_rows) -> Decimal | None:
    """Past-due amounts of the priority debts; None while one is unanswered."""
    amounts = [row.debt.past_due_amount for row in priority_rows]
    if any(amount is None for amount in amounts):
        return None
    return sum(amounts, Decimal("0.00"))


def read_inputs(session) -> MeansInputs:
    """What Form 122A-2 reads from the intake and the page's answers (the spouse's only under
    `married_together`).

    Raises:
        IncomeNotSplit, IncomeStepGap: the Income step's own gaps, from `household_cmi` and
            `household_members`.
    """
    rows = ordered_assets(session)
    claims = claim_rows(session)
    answers = page_answers(session)
    together = session.income_info.marital_status == "married_together"
    vehicles = _vehicles(session, vehicle_rows(session), answers["vehicle_claims"])
    spouse_vehicles = _spouse_vehicles(answers) if together else ()
    debts = _secured_debts(rows, counted_debts(session))
    spouse_loans = ()
    if together:
        names = {vehicle.ref: vehicle.name for vehicle in (*vehicles, *spouse_vehicles)}
        by_id = {debt.pk: debt for debt in open_debts(session)}
        spouse_loans = _spouse_loans(answers, by_id, names)
    first, second = answers["vehicle_choice"]
    household = getattr(session, "household", None)
    health = answers["line_25_answer"]
    return MeansInputs(
        line_1=household_cmi(session),
        marital_status=session.income_info.marital_status,
        ages=_ages(session),
        county=None if household is None else household.county,
        district=session.district.code.lower(),
        vehicles=(*vehicles, *spouse_vehicles),
        secured_debts=(*debts, *spouse_loans),
        line_35_past_due=_line_35(claims.priority),
        # DRAFT: counsel C-23 (line 41a is Schedule E/F Part 2 alone, 106Sum line 3b)
        line_41a=sum((row.debt.amount_owed for row in claims.unsecured), Decimal("0.00")),
        vehicle_choice=(first, second) if first is not None and second is not None else None,
        spouse_vehicles_answer=answers["spouse_vehicles_answer"] if together else None,
        spouse_loans_answer=answers["spouse_loans_answer"] if together else None,
        line_3_answer=answers["line_3_answer"],
        line_3_rows=tuple(
            (row.get("purpose") or "", _decimal(row.get("amount")))
            for row in answers["line_3_rows"]
        ),
        line_15=_opt_in(answers, "line_15"),
        line_16=_decimal(answers["line_16"]),
        line_17=_decimal(answers["line_17"]),
        line_18=_decimal(answers["line_18"]),
        line_19=_decimal(answers["line_19"]),
        line_20=_decimal(answers["line_20"]),
        line_21=_decimal(answers["line_21"]),
        line_22=_opt_in(answers, "line_22"),
        line_23=_decimal(answers["line_23"]),
        line_25=(
            None
            if health is None
            else HealthInsurance(
                health,
                health=_decimal(answers["line_25_health"]),
                disability=_decimal(answers["line_25_disability"]),
                hsa=_decimal(answers["line_25_hsa"]),
                actually_spends=answers["line_25_spends"],
                actual=_decimal(answers["line_25_actual"]),
            )
        ),
        line_26=_opt_in(answers, "line_26"),
        line_27=_opt_in(answers, "line_27"),
        line_28=_opt_in(answers, "line_28"),
        line_29=_opt_in(answers, "line_29"),
        line_30=_opt_in(answers, "line_30"),
        line_31=_opt_in(answers, "line_31"),
        line_34_answer=answers["line_34_answer"],
        line_36_answer=answers["line_36_answer"],
        line_36_payment=_decimal(answers["line_36_payment"]),
        line_43_answer=answers["line_43_answer"],
    )


def _by_size(figures, kind: str, key: str | None = None) -> dict:
    return {f.size: f.amount for f in figures if f.kind == kind and (key is None or f.key == key)}


def _at(sizes: dict, size: int, part: str) -> Decimal:
    """The figure for `size`; a set that lacks it raises, naming the table part and nothing else."""
    if size not in sizes:
        raise MeansTableKeyMissing(part)
    return sizes[size]


def _one(figures, kind: str, part: str, key: str = "", size: int = 0) -> Decimal:
    return _at(_by_size(figures, kind, key), size, part)


def _used(name: str, table) -> dict:
    return {
        "name": name,
        "effective_date": table.effective_date.isoformat(),
        "valid_through": None if table.valid_through is None else table.valid_through.isoformat(),
        "source_url": table.source_url,
    }


def read_tables(on: date | None = None) -> tuple[MeansTables, list[dict]]:
    """The U.S. Trustee set, then the § 104 set, in force on `on` (the fill date by default).

    Raises:
        NoMeansTestTable: either set isn't in force.
        MeansTableKeyMissing: the set in force lacks a figure the calculator reads.
    """
    standards = means_standards_in_force(on)
    section_104 = section_104_in_force(on)
    figures = list(standards.figures.all())
    counties = {f.key for f in figures if f.kind in ("housing_operating", "housing_mortgage")}
    housing = {}
    for county in sorted(counties):
        operating = _by_size(figures, "housing_operating", county)
        mortgage = _by_size(figures, "housing_mortgage", county)
        housing[county] = tuple(
            (_at(operating, n, "housing"), _at(mortgage, n, "housing")) for n in range(1, 6)
        )
    operating_cars = {f.key for f in figures if f.kind == "operating"}
    national = _by_size(figures, "national")
    five_percent = _by_size(figures, "five_percent")
    tables = MeansTables(
        national=tuple(_at(national, n, "national") for n in range(1, 5)),
        national_extra=_one(figures, "national_extra", "national"),
        health_under_65=_one(figures, "health", "health", key="under_65"),
        health_65_or_older=_one(figures, "health", "health", key="65_or_older"),
        housing=housing,
        areas={area.county: area.area for area in standards.areas.all()},
        operating={
            area: (
                _one(figures, "operating", "transport", key=area, size=1),
                _one(figures, "operating", "transport", key=area, size=2),
            )
            for area in sorted(operating_cars)
        },
        ownership_one_car=_one(figures, "ownership", "transport", size=1),
        public_transport=_one(figures, "public_transport", "public_transport"),
        five_percent=tuple(_at(five_percent, n, "five_percent") for n in range(1, 5)),
        five_percent_extra=_one(figures, "five_percent_extra", "five_percent"),
        education_per_child=section_104.education_per_child_monthly,
        chapter_13_unsecured_limit=section_104.chapter_13_unsecured_limit,
        chapter_13_secured_limit=section_104.chapter_13_secured_limit,
        multipliers={f.key: f.amount for f in figures if f.kind == "multiplier"},
        presumption_low=section_104.presumption_low,
        presumption_high=section_104.presumption_high,
    )
    return tables, [
        _used(MEANS_STANDARDS_TABLE, standards),
        _used(SECTION_104_TABLE, section_104),
    ]
