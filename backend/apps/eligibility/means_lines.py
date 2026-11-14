"""Form 122A-2's lines, worked out from a record of the filer's answers and the official tables.

Pure: standard library only, no models and no settings. The caller hands in `MeansInputs` and
`MeansTables`; `work_out` returns every line the form prints as a figure, `MISSING` (an input it
needs was never given) or `SKIPPED` (the form's own arithmetic doesn't reach the line). The result
is the form's arithmetic and nothing more: a court makes the final decision.

Every money line is quantized to the cent, half-even, and each later line adds the printed figures.
Nothing here carries a county, a district or an answer into an error message.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal


class _Sentinel:
    def __init__(self, name: str):
        self._name = name

    def __repr__(self) -> str:
        return self._name

    def __reduce__(self):
        return self._name


MISSING = _Sentinel("MISSING")
SKIPPED = _Sentinel("SKIPPED")

Value = Decimal | int | str | _Sentinel

AT_OR_BELOW_MEDIAN = "at_or_below_median"
CANNOT_WORK_OUT = "cannot_work_out"
NO_PRESUMPTION = "no_presumption"
PRESUMPTION = "presumption"
OUTCOMES = (AT_OR_BELOW_MEDIAN, CANNOT_WORK_OUT, NO_PRESUMPTION, PRESUMPTION)

LINE_KEYS = (
    "1", "2", "2_filing", "3_answer", "3", "4", "5", "6",
    "7a", "7b", "7c", "7d", "7e", "7f", "7g", "8", "9a", "9b", "9c",
    "11", "12", "13_vehicle_1", "13_vehicle_2",
    "13a", "13b", "13c", "13d", "13e", "13f", "14", "15",
    "16", "17", "18", "19", "20", "21", "22", "23", "24",
    "25_answer", "25_health", "25_disability", "25_hsa", "25", "25_spends", "25_actual",
    "26", "27", "28", "29", "30", "31", "32",
    "33a", "33b", "33c", "33d", "33e", "34_answer", "34",
    "35_answer", "35_total", "35", "36_answer", "36_payment", "36_multiplier", "36",
    "37", "38", "39a", "39b", "39c", "39d", "40", "41a", "41b", "42", "43", "page_1",
)  # fmt: skip
ROW_KEYS = ("3", "9b", "13b", "13e", "33d", "34")

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
MONTHS = Decimal(60)
QUARTER = Decimal("0.25")


class MeansTableKeyMissing(LookupError):
    """A table figure the tables should hold, and don't. `part` names the table, never a filer."""

    def __init__(self, part: str):
        super().__init__(f"The means test tables have no {part} figure for this session.")


# The records that hold filer data print a fixed repr (and so a fixed str): a log line, an
# exception message or an f-string that names one never carries a filer's figures or words.


@dataclass(frozen=True, repr=False)
class OptIn:
    answer: str
    amount: Decimal | None = None

    def __repr__(self) -> str:
        return "OptIn(...)"


@dataclass(frozen=True, repr=False)
class HealthInsurance:
    answer: str
    health: Decimal | None = None
    disability: Decimal | None = None
    hsa: Decimal | None = None
    actually_spends: str | None = None
    actual: Decimal | None = None

    def __repr__(self) -> str:
        return "HealthInsurance(...)"


@dataclass(frozen=True, repr=False)
class Vehicle:
    asset_id: int
    name: str
    financed: bool
    leased: bool
    claimed: bool | None = None

    def __repr__(self) -> str:
        return "Vehicle(asset_id=...)"


@dataclass(frozen=True, repr=False)
class SecuredDebt:
    debt_id: int
    creditor: str
    asset_id: int | None
    on_home: bool
    property: str
    monthly_payment: Decimal | None
    payments_left: int | None = None
    payment_changes: str | None = None
    total_60_months: Decimal | None = None
    taxes_or_insurance: str | None = None
    necessary_for_support: str | None = None
    cure: Decimal | None = None

    def __repr__(self) -> str:
        return "SecuredDebt(debt_id=...)"


@dataclass(frozen=True, repr=False)
class MeansInputs:
    line_1: Decimal | None
    marital_status: str | None
    ages: tuple[int | None, ...] | None
    county: str | None
    district: str
    vehicles: tuple[Vehicle, ...]
    secured_debts: tuple[SecuredDebt, ...]
    line_35_past_due: Decimal | None
    line_41a: Decimal
    vehicle_choice: tuple[int, int] | None = None
    line_3_answer: str | None = None
    line_3_rows: tuple[tuple[str, Decimal], ...] = ()
    line_15: OptIn | None = None
    line_16: Decimal | None = None
    line_17: Decimal | None = None
    line_18: Decimal | None = None
    line_19: Decimal | None = None
    line_20: Decimal | None = None
    line_21: Decimal | None = None
    line_22: OptIn | None = None
    line_23: Decimal | None = None
    line_25: HealthInsurance | None = None
    line_26: OptIn | None = None
    line_27: OptIn | None = None
    line_28: OptIn | None = None
    line_29: OptIn | None = None
    line_30: OptIn | None = None
    line_31: OptIn | None = None
    line_34_answer: str | None = None
    line_36_answer: str | None = None
    line_36_payment: Decimal | None = None
    line_43_answer: str | None = None

    def __repr__(self) -> str:
        return "MeansInputs(...)"


@dataclass(frozen=True)
class MeansTables:
    national: tuple[Decimal, Decimal, Decimal, Decimal]
    national_extra: Decimal
    health_under_65: Decimal
    health_65_or_older: Decimal
    housing: Mapping[str, tuple[tuple[Decimal, Decimal], ...]]
    areas: Mapping[str, str]
    operating: Mapping[str, tuple[Decimal, Decimal]]
    ownership_one_car: Decimal
    public_transport: Decimal
    multipliers: Mapping[str, Decimal]
    presumption_low: Decimal
    presumption_high: Decimal


@dataclass(frozen=True, repr=False)
class MeansRow:
    label: str
    amount: Decimal | _Sentinel
    property: str = ""
    flag: str | None = None
    cure: Decimal | None = None

    def __repr__(self) -> str:
        return "MeansRow(...)"


@dataclass(frozen=True)
class Comparison:
    line_40: str
    line_42: str | None
    outcome: str


@dataclass(frozen=True, repr=False)
class MeansLines:
    lines: Mapping[str, Value]
    rows: Mapping[str, tuple[MeansRow, ...]]
    outcome: str

    def __repr__(self) -> str:
        return "MeansLines(outcome=...)"


def _money(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_EVEN)


def _given(amount: Decimal | None) -> Decimal | _Sentinel:
    return MISSING if amount is None else _money(amount)


def _add(*values: Value) -> Decimal | _Sentinel:
    """The sum of the printed figures: a MISSING one makes it MISSING, a SKIPPED one adds zero."""
    if any(value is MISSING for value in values):
        return MISSING
    return _money(sum((v for v in values if v is not SKIPPED), ZERO))


def _minus(first: Value, second: Value) -> Decimal | _Sentinel:
    if first is MISSING or second is MISSING:
        return MISSING
    return _money(first - second)


def _minus_floored(first: Value, second: Value) -> Decimal | _Sentinel:
    difference = _minus(first, second)
    return difference if difference is MISSING else max(difference, ZERO)


def _yes_no(answer: str | None, field: str) -> str | None:
    """The answer when it is yes, no or None; anything else raises, naming the field only."""
    if answer is not None and answer not in ("yes", "no"):
        raise ValueError(f"{field} must be yes or no.")
    return answer


def _opt_in(opt_in: OptIn | None, field: str) -> Decimal | _Sentinel:
    """The line's amount under yes, SKIPPED under no, and MISSING while it is unanswered."""
    if opt_in is None:
        return MISSING
    answer = _yes_no(opt_in.answer, f"{field}'s answer")
    if answer is None:
        return MISSING
    if answer == "yes":
        return _given(opt_in.amount)
    return SKIPPED


def _average(debt: SecuredDebt) -> Decimal | _Sentinel:
    """The debt's 60-month average, rounded to the cent; MISSING while its inputs are."""
    changes = _yes_no(debt.payment_changes, "payment_changes")
    if changes == "yes" and debt.total_60_months is not None:
        return _money(debt.total_60_months / MONTHS)
    if changes == "no" and debt.payments_left is not None and debt.monthly_payment is not None:
        return _money(min(debt.payments_left, 60) * debt.monthly_payment / MONTHS)
    return MISSING


def _row(debt: SecuredDebt, with_flag: bool = False) -> MeansRow:
    return MeansRow(
        debt.creditor,
        _average(debt),
        property=debt.property,
        flag=debt.taxes_or_insurance if with_flag else None,
    )


def _check_county(inputs: MeansInputs, tables: MeansTables) -> None:
    county = inputs.county
    if county is None:
        return
    if county not in tables.housing:
        raise MeansTableKeyMissing("housing")
    if county not in tables.areas:
        raise MeansTableKeyMissing("area")
    if tables.areas[county] not in tables.operating:
        raise MeansTableKeyMissing("operating")


def _lines_1_to_4(inputs: MeansInputs) -> tuple[dict[str, Value], tuple[MeansRow, ...]]:
    marital = inputs.marital_status
    rows: tuple[MeansRow, ...] = ()
    if marital is None:
        two = two_filing = three_answer = three = MISSING
    elif marital == "married_together":
        two, two_filing = "yes", "no"
        three_answer = _yes_no(inputs.line_3_answer, "line 3's answer") or MISSING
        if three_answer == "yes":
            rows = tuple(
                MeansRow(purpose, _money(amount)) for purpose, amount in inputs.line_3_rows
            )
        three = MISSING if three_answer is MISSING else _add(*(row.amount for row in rows))
    else:
        two, two_filing, three_answer, three = "no", SKIPPED, SKIPPED, ZERO
    line_1 = _given(inputs.line_1)
    values = {
        "1": line_1,
        "2": two,
        "2_filing": two_filing,
        "3_answer": three_answer,
        "3": three,
        "4": _minus(line_1, three),
    }
    return values, rows


def _lines_5_to_9a(inputs: MeansInputs, tables: MeansTables) -> dict[str, Value]:
    ages = inputs.ages
    people = None if ages is None else len(ages)
    counted = people is not None and people >= 1
    if not counted:
        line_6 = MISSING
    elif people <= 4:
        line_6 = _money(tables.national[people - 1])
    else:
        line_6 = _money(tables.national[3] + (people - 4) * tables.national_extra)
    if ages is None or None in ages:
        seven = dict.fromkeys(("7b", "7c", "7e", "7f", "7g"), MISSING)
    else:
        under = sum(1 for age in ages if age < 65)
        older = len(ages) - under
        seven_c = _money(tables.health_under_65 * under)
        seven_f = _money(tables.health_65_or_older * older)
        seven = {
            "7b": under,
            "7c": seven_c,
            "7e": older,
            "7f": seven_f,
            "7g": _add(seven_c, seven_f),
        }
    if counted and inputs.county is not None:
        insurance_and_operating, mortgage_or_rent = tables.housing[inputs.county][
            min(people, 5) - 1
        ]
        line_8, line_9a = _money(insurance_and_operating), _money(mortgage_or_rent)
    else:
        line_8 = line_9a = MISSING
    return {
        "5": MISSING if people is None else people,
        "6": line_6,
        "7a": _money(tables.health_under_65),
        "7b": seven["7b"],
        "7c": seven["7c"],
        "7d": _money(tables.health_65_or_older),
        "7e": seven["7e"],
        "7f": seven["7f"],
        "7g": seven["7g"],
        "8": line_8,
        "9a": line_9a,
    }


def _vehicle_slots(inputs: MeansInputs):
    """Vehicle 1 and Vehicle 2, each a Vehicle or None for an empty slot, or MISSING."""
    if any(vehicle.claimed is None for vehicle in inputs.vehicles):
        return MISSING
    # DRAFT: counsel C-28 (a leased vehicle takes a slot; 13a prints whole, nothing on 13b)
    candidates = [v for v in inputs.vehicles if v.claimed and (v.financed or v.leased)]
    if len(candidates) <= 2:
        return tuple((candidates + [None, None])[:2])
    if inputs.vehicle_choice is None:
        return MISSING
    by_asset = {vehicle.asset_id: vehicle for vehicle in candidates}
    first, second = (by_asset.get(asset_id) for asset_id in inputs.vehicle_choice)
    if first is None or second is None or first is second:
        return MISSING
    return first, second


def _group_debts(inputs: MeansInputs, slots) -> tuple[dict[str, list[SecuredDebt]], bool]:
    """Each counted debt to its group (9b, 13b, 13e or 33d), and whether any waits on the slots."""
    groups: dict[str, list[SecuredDebt]] = {"9b": [], "13b": [], "13e": [], "33d": []}
    vehicle_assets = {vehicle.asset_id for vehicle in inputs.vehicles}
    waiting = False
    for debt in inputs.secured_debts:
        if debt.on_home:
            groups["9b"].append(debt)
        elif slots is MISSING and debt.asset_id in vehicle_assets:
            waiting = True
        elif (
            slots is not MISSING
            and debt.asset_id is not None
            and debt.asset_id == _slot_asset(slots[0])
        ):
            groups["13b"].append(debt)
        elif (
            slots is not MISSING
            and debt.asset_id is not None
            and debt.asset_id == _slot_asset(slots[1])
        ):
            groups["13e"].append(debt)
        else:
            groups["33d"].append(debt)
    return groups, waiting


def _slot_asset(vehicle: Vehicle | None) -> int | None:
    return None if vehicle is None else vehicle.asset_id


def _vehicle_lines(
    inputs: MeansInputs, tables: MeansTables, slots, rows: dict[str, tuple[MeansRow, ...]]
) -> dict[str, Value]:
    if any(vehicle.claimed is None for vehicle in inputs.vehicles):
        count = MISSING
    else:
        count = sum(1 for vehicle in inputs.vehicles if vehicle.claimed)
    if count is MISSING:
        line_12 = line_14 = MISSING
    else:
        line_14 = _money(tables.public_transport) if count == 0 else SKIPPED
        if count == 0:
            line_12 = SKIPPED
        elif inputs.county is None:
            line_12 = MISSING
        else:
            one_car, two_cars = tables.operating[tables.areas[inputs.county]]
            line_12 = _money(one_car if count == 1 else two_cars)
    if count is MISSING:
        line_15 = MISSING
    elif count == 0:
        line_15 = SKIPPED
    else:
        line_15 = _opt_in(inputs.line_15, "line 15")
    values: dict[str, Value] = {"11": count, "12": line_12, "14": line_14, "15": line_15}
    for number, (name_key, standard_key, debts_key, net_key) in enumerate(
        (("13_vehicle_1", "13a", "13b", "13c"), ("13_vehicle_2", "13d", "13e", "13f"))
    ):
        if slots is MISSING:
            values.update(dict.fromkeys((name_key, standard_key, debts_key, net_key), MISSING))
        elif slots[number] is None:
            values.update(dict.fromkeys((name_key, standard_key, debts_key, net_key), SKIPPED))
        else:
            standard = _money(tables.ownership_one_car)
            debts_total = _add(*(row.amount for row in rows[debts_key]))
            values[name_key] = slots[number].name
            values[standard_key] = standard
            values[debts_key] = debts_total
            values[net_key] = _minus_floored(standard, debts_total)
    return values


def _line_25(health: HealthInsurance | None) -> dict[str, Value]:
    keys = ("25_answer", "25_health", "25_disability", "25_hsa", "25", "25_spends", "25_actual")
    if health is None:
        return dict.fromkeys(keys, MISSING)
    answer = _yes_no(health.answer, "line 25's answer")
    if answer is None:
        return dict.fromkeys(keys, MISSING)
    if answer == "no":
        return dict.fromkeys(keys, SKIPPED)
    amounts = (_given(health.health), _given(health.disability), _given(health.hsa))
    spends_answer = _yes_no(health.actually_spends, "line 25's actually-spends answer")
    if spends_answer is None:
        spends = actual = MISSING
    elif spends_answer == "no":
        spends, actual = "no", _given(health.actual)
    else:
        spends, actual = "yes", SKIPPED
    return {
        "25_answer": "yes",
        "25_health": amounts[0],
        "25_disability": amounts[1],
        "25_hsa": amounts[2],
        "25": _add(*amounts),
        "25_spends": spends,
        "25_actual": actual,
    }


def _line_34(
    inputs: MeansInputs, groups: dict[str, list[SecuredDebt]], waiting: bool
) -> tuple[dict[str, Value], tuple[MeansRow, ...]]:
    answer = _yes_no(inputs.line_34_answer, "line 34's answer")
    if answer is None:
        return {"34_answer": MISSING, "34": MISSING}, ()
    if answer != "yes":
        return {"34_answer": answer, "34": SKIPPED}, ()
    rows: list[MeansRow] = []
    unanswered = waiting
    for key in ("9b", "13b", "13e", "33d"):
        for debt in groups[key]:
            necessary = _yes_no(debt.necessary_for_support, "necessary_for_support")
            if necessary is None:
                unanswered = True
            elif necessary == "yes":
                if debt.cure is None:
                    unanswered = True
                elif debt.cure > ZERO:
                    cure = _money(debt.cure)
                    rows.append(
                        MeansRow(
                            debt.creditor,
                            _money(cure / MONTHS),
                            property=debt.property,
                            cure=cure,
                        )
                    )
    total = MISSING if unanswered else _add(*(row.amount for row in rows))
    return {"34_answer": "yes", "34": total}, tuple(rows)


def _lines_35_and_36(inputs: MeansInputs, tables: MeansTables) -> dict[str, Value]:
    past_due = inputs.line_35_past_due
    if past_due is None:
        thirty_five = dict.fromkeys(("35_answer", "35_total", "35"), MISSING)
    elif past_due > ZERO:
        total = _money(past_due)
        thirty_five = {"35_answer": "yes", "35_total": total, "35": _money(total / MONTHS)}
    else:
        thirty_five = {"35_answer": "no", "35_total": SKIPPED, "35": SKIPPED}
    answer = _yes_no(inputs.line_36_answer, "line 36's answer")
    if answer is None:
        thirty_six = dict.fromkeys(("36_answer", "36_payment", "36_multiplier", "36"), MISSING)
    elif answer == "yes":
        if inputs.district not in tables.multipliers:
            raise MeansTableKeyMissing("multiplier")
        multiplier = tables.multipliers[inputs.district]
        payment = _given(inputs.line_36_payment)
        thirty_six = {
            "36_answer": "yes",
            "36_payment": payment,
            "36_multiplier": multiplier,
            "36": MISSING if payment is MISSING else _money(payment * multiplier / 100),
        }
    else:
        thirty_six = {
            "36_answer": answer,
            "36_payment": SKIPPED,
            "36_multiplier": SKIPPED,
            "36": SKIPPED,
        }
    return {**thirty_five, **thirty_six}


# DRAFT: counsel C-5 (a 39d of exactly the upper figure is in the band, as the form reads)
def _in_band(line_39d: Decimal, low: Decimal, high: Decimal) -> bool:
    """Whether line 39d sits in the middle band; both edges are in it."""
    return low <= line_39d <= high


def compare(line_39d: Decimal, line_41b: Decimal | None, low: Decimal, high: Decimal) -> Comparison:
    """Line 40's three boxes and, in the middle band, line 42; both edges are in the band.

    A 39d in none of the three bands raises rather than reading as any box.
    """
    if line_39d < low:
        return Comparison("1", None, NO_PRESUMPTION)
    if _in_band(line_39d, low, high):
        if line_41b is None:
            raise ValueError("Line 41b is needed to compare line 39d in the middle band.")
        if line_39d >= line_41b:
            return Comparison("On", "yes", PRESUMPTION)
        return Comparison("On", "no", NO_PRESUMPTION)
    if line_39d > high:
        return Comparison("2", None, PRESUMPTION)
    raise ValueError("Line 39d falls in none of line 40's bands.")


def work_out(inputs: MeansInputs, tables: MeansTables) -> MeansLines:
    _check_county(inputs, tables)
    values: dict[str, Value] = {}
    income, rows_3 = _lines_1_to_4(inputs)
    values.update(income)
    values.update(_lines_5_to_9a(inputs, tables))

    slots = _vehicle_slots(inputs)
    groups, waiting = _group_debts(inputs, slots)
    rows = {key: tuple(_row(debt, key == "33d") for debt in groups[key]) for key in groups}
    values["9b"] = _add(*(row.amount for row in rows["9b"]))
    values["9c"] = _minus_floored(values["9a"], values["9b"])
    values.update(_vehicle_lines(inputs, tables, slots, rows))

    for key in ("16", "17", "18", "19", "20", "21", "23"):
        values[key] = _given(getattr(inputs, f"line_{key}"))
    values["22"] = _opt_in(inputs.line_22, "line 22")
    values["24"] = _add(
        *(values[key] for key in ("6", "7g", "8", "9c", "12", "13c", "13f", "14", "15")),
        *(values[key] for key in ("16", "17", "18", "19", "20", "21", "22", "23")),
    )

    values.update(_line_25(inputs.line_25))
    for key in ("26", "27", "28", "29", "30", "31"):
        values[key] = _opt_in(getattr(inputs, f"line_{key}"), f"line {key}")
    values["32"] = _add(
        values["25"], *(values[key] for key in ("26", "27", "28", "29", "30", "31"))
    )

    values["33a"] = values["9b"]
    values["33b"] = values["13b"]
    values["33c"] = values["13e"]
    values["33d"] = MISSING if waiting else _add(*(row.amount for row in rows["33d"]))
    values["33e"] = _add(values["33a"], values["33b"], values["33c"], values["33d"])
    line_34, rows_34 = _line_34(inputs, groups, waiting)
    values.update(line_34)
    values.update(_lines_35_and_36(inputs, tables))
    values["37"] = _add(values["33e"], values["34"], values["35"], values["36"])
    values["38"] = _add(values["24"], values["32"], values["37"])

    values["39a"] = values["4"]
    values["39b"] = values["38"]
    values["39c"] = _minus(values["39a"], values["39b"])
    values["39d"] = MISSING if values["39c"] is MISSING else _money(values["39c"] * MONTHS)
    if values["39d"] is MISSING:
        values.update(dict.fromkeys(("40", "41a", "41b", "42", "page_1"), MISSING))
        outcome = CANNOT_WORK_OUT
        reaches_43 = None
    else:
        in_band = _in_band(values["39d"], tables.presumption_low, tables.presumption_high)
        line_41a = _money(inputs.line_41a) if in_band else SKIPPED
        line_41b = _money(line_41a * QUARTER) if in_band else SKIPPED
        comparison = compare(
            values["39d"],
            line_41b if in_band else None,
            tables.presumption_low,
            tables.presumption_high,
        )
        values["40"] = comparison.line_40
        values["41a"] = line_41a
        values["41b"] = line_41b
        values["42"] = SKIPPED if comparison.line_42 is None else comparison.line_42
        values["page_1"] = comparison.outcome
        outcome = comparison.outcome
        reaches_43 = comparison.line_40 == "2" or comparison.line_42 == "yes"
    if reaches_43 is None:
        values["43"] = MISSING
    elif reaches_43:
        answer_43 = _yes_no(inputs.line_43_answer, "line 43's answer")
        values["43"] = MISSING if answer_43 is None else answer_43
    else:
        values["43"] = SKIPPED

    return MeansLines(
        lines={key: values[key] for key in LINE_KEYS},
        rows={
            "3": rows_3,
            "9b": rows["9b"],
            "13b": rows["13b"],
            "13e": rows["13e"],
            "33d": rows["33d"],
            "34": rows_34,
        },
        outcome=outcome,
    )
