"""The 122A-2 page's read and save. The answers are not intake data: nothing here reopens a
completed intake."""

import copy
from collections.abc import Mapping
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.districts.dated_tables import NoTableInForce, fill_date
from apps.districts.means_standards import NoMeansTestTable, section_104_in_force
from apps.eligibility.cmi import counted_spouse_income, income_step_gaps, is_above_median
from apps.eligibility.means_inputs import (
    _lives_in,
    _payments_left,
    _vehicles,
    counted_debts,
    open_debts,
    page_answers,
    read_inputs,
    read_tables,
    vehicle_rows,
)
from apps.eligibility.means_lines import (
    MeansTableKeyMissing,
    debt_lines,
    line_30_cap,
    plan_product,
    work_out,
)
from apps.eligibility.models import MeansTest
from apps.eligibility.services import MeansTestCalculator
from apps.forms.services.means_fit import LIST_ANSWERS, merge_row_errors, shown_box_refusals
from apps.intake import polish
from apps.intake.asset_lines import exemption_item_name, ordered_assets
from apps.intake.claim_rows import claim_rows
from apps.intake.locking import lock_session
from apps.intake.means_test import PER_DEBT_KEYS, PROPERTY_CHOICES, means_test_gaps
from apps.intake.models import IntakeSession, MeansTestAnswers, SecuredDebtAnswers

# Fixed sentences for a 400. The first three name a row that has gone: the page finds them in a
# body by their words and reads itself again, so copy.ts holds each (MEANS_NOT_*, pinned by
# test_means_test_copy.py). The last, and the serializer's NOT_IN_THIS_SAVE, are a plain save
# failure and have no twin.
NOT_A_COUNTED_DEBT = "This isn't one of your secured debts."
NOT_A_LINE_11_VEHICLE = "This isn't one of the vehicles on line 11."
NOT_AN_OPEN_DEBT = "This isn't one of the debts on your Amounts Owed step not listed as secured."
DEBT_NAMED_TWICE = "Each debt on your Amounts Owed step can be named by one loan only."

CENT = Decimal("0.01")
SIXTY_OR_MORE = "60_or_more"
_AMOUNT_KEYS = (
    "line_15_amount",
    *(f"line_{n}" for n in (16, 17, 18, 19, 20, 21, 23)),
    "line_22_amount",
    "line_25_health",
    "line_25_disability",
    "line_25_hsa",
    "line_25_actual",
    *(f"line_{n}_amount" for n in range(26, 32)),
    "line_36_payment",
)
_LOAN_AMOUNT_KEYS = ("payment", "total_60_months", "cure")
_DEBT_AMOUNT_KEYS = ("total_60_months", "cure")

# Schedule I line -> IncomeDetail column (R6); Schedule J line -> ExpenseInfo column.
_SCHEDULE_I = {
    "5a": "payroll_tax",
    "5b": "payroll_mandatory_retirement",
    "5d": "payroll_retirement_loan",
    "5e": "payroll_insurance",
    "5f": "payroll_support",
    "5g": "payroll_union_dues",
}
_SCHEDULE_J = {
    "7": "food_and_groceries",
    "8": "childcare",
    "9": "clothing",
    "11": "medical_expenses",
    "14": "charitable_contributions",
    "15c": "vehicle_insurance",
    "15d": "insurance_not_deducted",
    "16": "taxes_not_deducted",
    "18": "child_support_paid",
}


def _two(amount) -> str:
    return str(Decimal(str(amount)).quantize(CENT))


def _two_or_none(amount) -> str | None:
    return None if amount is None else _two(amount)


def _left(text):
    """A stored payments-left text as the API gives it: an integer or "60_or_more"."""
    return SIXTY_OR_MORE if text == SIXTY_OR_MORE else _payments_left(text)


def _answers_for_page(session) -> dict:
    out = page_answers(session, keep_hidden=True)
    for key in _AMOUNT_KEYS:
        out[key] = _two_or_none(out[key])
    for row in out["line_3_rows"]:
        row["amount"] = _two_or_none(row.get("amount"))
    for row in out["line_43_circumstances"]:
        row["amount"] = _two_or_none(row.get("amount"))
    for loan in out["spouse_loans"]:
        for key in _LOAN_AMOUNT_KEYS:
            if key in loan:
                loan[key] = _two_or_none(loan[key])
        if "payments_left" in loan and loan["payments_left"] is not None:
            loan["payments_left"] = _left(loan["payments_left"])
    return out


def _debt_rows(session) -> list[dict]:
    by_id = {row.pk: row for row in ordered_assets(session)}
    out = []
    for debt in counted_debts(session):
        linked = by_id.get(debt.secured_by_id)
        stored = getattr(debt, "means_answers", None)
        given = {key: getattr(stored, key, None) for key in PER_DEBT_KEYS}
        out.append(
            {
                "id": debt.pk,
                "ref": f"debt-{debt.pk}",
                "creditor": debt.creditor_name,
                "property": (
                    debt.collateral_description if linked is None else exemption_item_name(linked)
                ),
                "monthly_payment": _two_or_none(debt.monthly_payment),
                "secured_by": None if linked is None else f"asset-{linked.pk}",
                "on_home": linked is not None and _lives_in(linked),
                "payments_left": (
                    None if given["payments_left"] is None else _left(given["payments_left"])
                ),
                "payment_changes": given["payment_changes"],
                "total_60_months": _two_or_none(given["total_60_months"]),
                "taxes_or_insurance": given["taxes_or_insurance"],
                "necessary_for_support": given["necessary_for_support"],
                "cure": _two_or_none(given["cure"]),
            }
        )
    return out


def _schedule_figures(row, columns, *, above_zero: bool) -> dict:
    out = {}
    for line, column in columns.items():
        value = getattr(row, column)
        if value is None or (above_zero and value <= 0):
            continue
        out[line] = _two(value)
    return out


def _figure(value) -> str | None:
    return _two(value) if isinstance(value, Decimal) else None


def _information(session, answers) -> tuple[dict | None, str | None]:
    try:
        tables, _ = read_tables(fill_date())
    except NoMeansTestTable:
        return None, "no_table"
    inputs = read_inputs(session)
    lines = work_out(inputs, tables).lines
    people = lines["5"] if isinstance(lines["5"], int) else None
    spouse = counted_spouse_income(session)
    expenses = getattr(session, "expense_info", None)
    section_104 = section_104_in_force(fill_date())
    claims = claim_rows(session)
    zero = Decimal("0.00")
    code = session.district.code.lower()
    if code not in tables.multipliers:
        raise MeansTableKeyMissing("multiplier")
    multiplier = tables.multipliers[code]
    payment = answers["line_36_payment"]
    product = None
    if answers["line_36_answer"] == "yes" and payment is not None:
        product = _two(plan_product(Decimal(payment), multiplier))
    return {
        "schedule_i": {
            "you": _schedule_figures(session.income_info, _SCHEDULE_I, above_zero=False),
            "spouse": (
                None if spouse is None else _schedule_figures(spouse, _SCHEDULE_I, above_zero=False)
            ),
        },
        "schedule_j": (
            {} if expenses is None else _schedule_figures(expenses, _SCHEDULE_J, above_zero=True)
        ),
        "line_7g": _figure(lines["7g"]),
        "line_8": _figure(lines["8"]),
        # what the filer entered as past due (the total), not the ÷ 60 figure line 35 prints
        "line_35": _figure(lines["35_total"]),
        "line_39c": _figure(lines["39c"]),
        "line_15_cap": _two(tables.public_transport),
        "line_29_per_child": _two(tables.education_per_child),
        "line_30_people": people,
        "line_30_cap": None if people is None else _two(line_30_cap(tables, people)),
        "spouse_cmi": _two_or_none(inputs.spouse_cmi),
        "limits": {
            "effective_date": section_104.effective_date.isoformat(),
            "unsecured": _two(section_104.chapter_13_unsecured_limit),
            "secured": _two(section_104.chapter_13_secured_limit),
        },
        "totals": {
            "unsecured": _two(
                sum(
                    (row.debt.amount_owed for row in (*claims.priority, *claims.unsecured)),
                    zero,
                )
            ),
            "secured": _two(sum((row.debt.amount_owed for row in claims.secured), zero)),
        },
        "multiplier": f"{multiplier.normalize():f}",
        "line_36_product": product,
    }, None


def means_page(session) -> dict:
    """The page's GET body (also the PUT's reply). Works the means test out again first, for a
    session in any status (R23)."""
    gaps = income_step_gaps(session)
    applies = None
    applies_gap = None
    result = None
    if gaps:
        applies_gap = str(gaps[0])
    else:
        try:
            result = MeansTestCalculator(session).calculate()
        except NoTableInForce as refusal:
            applies_gap = str(refusal)
        else:
            # F12: from this calculation, never a re-read another request may have rewritten
            applies = is_above_median(result["cmi"], result["median_income_threshold"])
    session = IntakeSession.objects.get(pk=session.pk)
    income = getattr(session, "income_info", None)
    answers = _answers_for_page(session)
    information, information_gap = None, None
    lines = None
    gap = None
    if applies:
        information, information_gap = _information(session, answers)
        inputs = read_inputs(session)
        lines = debt_lines(inputs)
        if information_gap is None:
            tables, _ = read_tables(fill_date())
            gap = next(iter(means_test_gaps(inputs, tables, page_answers(session))), None)
    if result is not None:
        outcome, details = result["outcome"], result["details"]
    else:
        # nothing worked out (an Income step gap or no median table): what is stored, if any
        saved = MeansTest.objects.filter(session=session).first()
        outcome = saved.outcome if saved else None
        details = saved.get_calculation_details() if saved else {}
    record = getattr(session, "means_test_answers", None)
    answered_on = None if record is None else record.answered_on()
    return {
        "applies": applies,
        "applies_gap": applies_gap,
        "married_together": getattr(income, "marital_status", None) == "married_together",
        "answers": answers,
        "debts": _debt_rows(session),
        "vehicles": [
            {"ref": vehicle.ref, "name": vehicle.name, "leased": vehicle.leased}
            for vehicle in _vehicles(session, vehicle_rows(session), {})
        ],
        "amounts_owed_loans": [
            {"id": debt.pk, "creditor": debt.creditor_name} for debt in open_debts(session)
        ],
        "debt_lines": lines,
        "debts_answered_on": None if answered_on is None else answered_on.isoformat(),
        "fill_date": fill_date().isoformat(),
        "information": information,
        "information_gap": information_gap,
        "outcome": outcome,
        "family_size": details.get("family_size"),
        "tables_gap": details.get("tables_gap"),
        "gap": gap,
        "polish_available": polish.configured(),
    }


def _jsonable(value):
    if isinstance(value, Decimal):
        return _two(value)
    if isinstance(value, Mapping):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _differs(key: str, stored, sent) -> bool:
    if stored is None or sent is None:
        return (stored is None) != (sent is None)
    if key in ("payment", "total_60_months", "cure"):
        return Decimal(str(stored)) != Decimal(str(sent))
    return stored != sent


def _spouse_rows(record, list_key, rows, merged_refs, new_ids):
    """The sent rows with the ids they keep or are given. Rows replace the stored ones whole.

    A stored ref sent again is kept; any other (a new-<n>, an unknown or no ref) gets a new one,
    and a new-<n> is recorded in `new_ids` for the references that name it (R14).
    """
    kept = []
    for row in rows or []:
        row = copy.deepcopy(dict(row))
        ref = row.get("ref")
        if ref in merged_refs:
            row["ref"] = ref
        else:
            row["ref"] = record.new_spouse_ref(list_key)
            if ref is not None and ref.startswith("new-"):
                new_ids.setdefault(ref, row["ref"])
        kept.append(row)
    return kept


def save_means_answers(session, data: Mapping) -> None:
    """Save the page's answers, `data` being `MeansTestSerializer.validated_data`.

    Under the session's lock, checks every reference against the stored rows before any write,
    then writes the page keys, each debt's own answers and the day the debt answers changed.
    Never reopens a completed intake.
    """
    with transaction.atomic():
        # the view's session carries prefetched assets and debts read before the lock
        session = lock_session(session.pk)
        record = MeansTestAnswers.objects.filter(session=session).first()
        if record is None:
            record = MeansTestAnswers(session=session)
        stored = record.get_answers()

        counted = {debt.pk: debt for debt in counted_debts(session)}
        vehicles = {f"asset-{row.pk}" for row in vehicle_rows(session)}
        open_ids = {debt.pk for debt in open_debts(session)}

        errors: dict = {}
        sent_debts = data.get("debts") or []
        bad = {
            i: {"id": [NOT_A_COUNTED_DEBT]}
            for i, row in enumerate(sent_debts)
            if row["id"] not in counted
        }
        if bad:
            errors["debts"] = bad
        claims = data.get("vehicle_claims") or {}
        bad = {ref: [NOT_A_LINE_11_VEHICLE] for ref in claims if ref not in vehicles}
        if bad:
            errors["vehicle_claims"] = bad

        stored_vehicles = {row.get("ref") for row in stored.get("spouse_vehicles") or []}
        if "spouse_vehicles" in data:
            sent_vehicles = data["spouse_vehicles"] or []
            merged = {
                row["ref"]
                for row in sent_vehicles
                if row.get("ref")
                and (row["ref"] in stored_vehicles or row["ref"].startswith("new-"))
            }
        else:
            merged = stored_vehicles
        nameable = vehicles | merged

        sent_loans = data.get("spouse_loans") or []
        loan_errors: dict = {}
        named: set = set()
        for i, loan in enumerate(sent_loans):
            problems = {}
            debt = loan.get("debt")
            if debt is not None:
                if debt not in open_ids:
                    problems["debt"] = [NOT_AN_OPEN_DEBT]
                elif debt in named:
                    problems["debt"] = [DEBT_NAMED_TWICE]
                named.add(debt)
            secured_by = loan.get("secured_by")
            if secured_by is not None and secured_by not in PROPERTY_CHOICES:
                if secured_by not in nameable:
                    problems["secured_by"] = [NOT_A_LINE_11_VEHICLE]
            if problems:
                loan_errors[i] = problems
        if loan_errors:
            errors["spouse_loans"] = loan_errors
        choice = data.get("vehicle_choice") or []
        if any(ref is not None and ref not in nameable for ref in choice):
            errors["vehicle_choice"] = [NOT_A_LINE_11_VEHICLE]
        # F1: every list this save sends, whole or in half, is measured here, under the answer it
        # will be saved with. The serializer measures line 43's alone: it runs before the lock,
        # so it can't know whether the filer is married together, and line 3 and the spouse's
        # boxes are drawn only then.
        waiting = [key for key, answer in LIST_ANSWERS.items() if key in data or answer in data]
        merged = {**stored, **{key: value for key, value in data.items() if key != "debts"}}
        income = getattr(session, "income_info", None)
        together = getattr(income, "marital_status", None) == "married_together"
        merge_row_errors(errors, shown_box_refusals(merged, waiting, together))
        if errors:
            raise serializers.ValidationError(errors)

        # Did a debt answer change? Compared before anything is written (H34).
        changed = False
        for row in sent_debts:
            old = getattr(counted[row["id"]], "means_answers", None)
            for key in PER_DEBT_KEYS:
                if key in row and _differs(key, getattr(old, key, None), row[key]):
                    changed = True
        if "spouse_loans" in data:
            old_loans = {loan.get("ref"): loan for loan in stored.get("spouse_loans") or []}
            for loan in sent_loans:
                old = old_loans.get(loan.get("ref"), {})
                for key in PER_DEBT_KEYS:
                    if _differs(key, old.get(key), loan.get(key)):
                        changed = True

        page = {key: value for key, value in data.items() if key != "debts"}
        new_vehicle_ids: dict = {}
        if "spouse_vehicles" in data:
            page["spouse_vehicles"] = _spouse_rows(
                record, "spouse_vehicles", data["spouse_vehicles"], stored_vehicles, new_vehicle_ids
            )
        if "spouse_loans" in data:
            stored_loans = {loan.get("ref") for loan in stored.get("spouse_loans") or []}
            rows = _spouse_rows(record, "spouse_loans", sent_loans, stored_loans, {})
            for row in rows:
                row["secured_by"] = new_vehicle_ids.get(
                    row.get("secured_by"), row.get("secured_by")
                )
            page["spouse_loans"] = rows
        if "vehicle_choice" in data and data["vehicle_choice"] is not None:
            page["vehicle_choice"] = [new_vehicle_ids.get(ref, ref) for ref in choice]

        record.merge(_jsonable(page))
        if changed:
            record.debts_answered_on = fill_date().isoformat()
        record.save()

        for row in sent_debts:
            debt = counted[row["id"]]
            answers = getattr(debt, "means_answers", None) or SecuredDebtAnswers(debt=debt)
            for key in PER_DEBT_KEYS:
                if key in row:
                    setattr(answers, key, row[key])
            answers.save()
