"""The session's side of Form 122A-2: what the filer gave DigniFi, and the tables in force.

`read_inputs` fills a `MeansInputs` from the intake and leaves every answer the 3h2 page will ask
as None, so nothing is worked out from a Schedule I or J figure. `read_tables` turns the two dated
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
from apps.eligibility.means_lines import MeansInputs, MeansTables, SecuredDebt, Vehicle
from apps.intake.asset_lines import exemption_item_name, ordered_assets
from apps.intake.claim_rows import claim_rows
from apps.intake.claims import ordered_debts

VEHICLE_LINE = "3"
VEHICLE_LINE_NO_MILEAGE = "4"
_HOME_LINES = ("1", VEHICLE_LINE_NO_MILEAGE)


def _age_on(born: date, day: date) -> int:
    """Whole years between, less one when the birthday hasn't come by `day`."""
    before_birthday = (day.month, day.day) < (born.month, born.day)
    return day.year - born.year - (1 if before_birthday else 0)


def _ages(session) -> tuple[int | None, ...]:
    """The filer, then each household row claimed or supported, in list order."""
    debtor = getattr(session, "debtor_info", None)
    filer = None if debtor is None else _age_on(debtor.date_of_birth, fill_date())
    counted = (
        member.get("age")
        for member in household_members(session)
        if member.get("claimed_or_supported") is True
    )
    return (filer, *counted)


def _is_vehicle(row) -> bool:
    if row.ab_line == VEHICLE_LINE:
        return True
    return row.ab_line == VEHICLE_LINE_NO_MILEAGE and row.get_details().get("lives_here") != "yes"


def _lives_in(row) -> bool:
    return row.ab_line in _HOME_LINES and row.get_details().get("lives_here") == "yes"


def _vehicles(session, rows, debts) -> tuple[Vehicle, ...]:
    financed = {debt.secured_by_id for debt in debts}
    leased = {
        contract.vehicle_asset_id
        for contract in session.executory_contracts.all()
        if contract.contract_type == "lease" and contract.lease_kind == "vehicle"
    }
    return tuple(
        Vehicle(
            asset_id=row.pk,
            name=exemption_item_name(row),
            financed=row.pk in financed,
            leased=row.pk in leased,
        )
        for row in rows
        if _is_vehicle(row)
    )


def _secured_debts(rows, debts) -> tuple[SecuredDebt, ...]:
    by_id = {row.pk: row for row in rows}
    out = []
    for debt in debts:
        linked = by_id.get(debt.secured_by_id)
        out.append(
            SecuredDebt(
                debt_id=debt.pk,
                creditor=debt.creditor_name,
                asset_id=None if linked is None else linked.pk,
                on_home=linked is not None and _lives_in(linked),
                property="" if linked is None else exemption_item_name(linked),
                monthly_payment=debt.monthly_payment,
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
    """What Form 122A-2 can read from the intake today; the page's answers stay None.

    Raises:
        IncomeNotSplit, IncomeStepGap: the Income step's own gaps, from `household_cmi` and
            `household_members`.
    """
    rows = ordered_assets(session)
    claims = claim_rows(session)
    debts = [
        debt for debt in ordered_debts(list(session.debts.confirmed())) if debt.is_secured is True
    ]
    household = getattr(session, "household", None)
    return MeansInputs(
        line_1=household_cmi(session),
        marital_status=session.income_info.marital_status,
        ages=_ages(session),
        county=None if household is None else household.county,
        district=session.district.code.lower(),
        vehicles=_vehicles(session, rows, debts),
        secured_debts=_secured_debts(rows, debts),
        line_35_past_due=_line_35(claims.priority),
        line_41a=sum((row.debt.amount_owed for row in claims.unsecured), Decimal("0.00")),
    )


def _by_size(figures, kind: str, key: str | None = None) -> dict:
    return {f.size: f.amount for f in figures if f.kind == kind and (key is None or f.key == key)}


def _one(figures, kind: str, key: str = "", size: int = 0) -> Decimal:
    return _by_size(figures, kind, key)[size]


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
    """
    standards = means_standards_in_force(on)
    section_104 = section_104_in_force(on)
    figures = list(standards.figures.all())
    counties = {f.key for f in figures if f.kind in ("housing_operating", "housing_mortgage")}
    housing = {}
    for county in sorted(counties):
        operating = _by_size(figures, "housing_operating", county)
        mortgage = _by_size(figures, "housing_mortgage", county)
        housing[county] = tuple((operating[n], mortgage[n]) for n in range(1, 6))
    operating_cars = {f.key for f in figures if f.kind == "operating"}
    tables = MeansTables(
        national=tuple(_by_size(figures, "national")[n] for n in range(1, 5)),
        national_extra=_one(figures, "national_extra"),
        health_under_65=_one(figures, "health", "under_65"),
        health_65_or_older=_one(figures, "health", "65_or_older"),
        housing=housing,
        areas={area.county: area.area for area in standards.areas.all()},
        operating={
            area: (
                _one(figures, "operating", area, 1),
                _one(figures, "operating", area, 2),
            )
            for area in sorted(operating_cars)
        },
        ownership_one_car=_one(figures, "ownership", size=1),
        public_transport=_one(figures, "public_transport"),
        multipliers={f.key: f.amount for f in figures if f.kind == "multiplier"},
        presumption_low=section_104.presumption_low,
        presumption_high=section_104.presumption_high,
    )
    return tables, [
        _used(MEANS_STANDARDS_TABLE, standards),
        _used(SECTION_104_TABLE, section_104),
    ]
