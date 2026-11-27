"""
The answers records the step 4 namespaces read (spec §7, §14.2).

`petition.`, `schedule_i.` and `affairs.` each name a key of one record's
`get_answers()`. Forms step 4a registers the namespaces with nothing bound and no record
behind them, so a session without the record reads blank (a scalar) or empty (a row list):
never 0.00 and never a default, since blank means the filer has not answered.
"""

import re
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

ANSWER_NAMESPACES = ("petition.", "schedule_i.", "affairs.")

# The session's related name for each record. `affairs.` is by line: Form 107's lines 1 to 12
# are the financial affairs record's, 13 to 28 the property affairs record's (§7.4).
RECORD_OF_NAMESPACE = {
    "petition.": "petition_answers",
    "schedule_i.": "schedule_i_answers",
}

# A step the wizard doesn't have yet; each leaves this tuple when its PR adds the step to
# frontend/src/constants/wizardSteps.ts.
NEW_STEP_KEYS = ("last_few_years_1", "last_few_years_2")

# No leading zero: `l05_` is not how §7.4 spells line 5.
_AFFAIRS_LINE = re.compile(r"l([1-9]\d*)_")

# Every key of PetitionAnswers (§7.1) with the wizard step that asks it.
PETITION_STEP_OF_KEY = {
    **dict.fromkeys(
        (
            "name_suffix",
            "other_names_answer",
            "itin_answer",
            "itin",
            "other_ssn_answer",
            "other_ssn",
            "ein",
            "mailing_answer",
            "mailing_street",
            "mailing_po_box",
            "mailing_city",
            "mailing_state",
            "mailing_zip",
            "venue_choice",
            "venue_reason",
            "prior_bankruptcy_answer",
            "pending_case_answer",
            "sole_proprietor_answer",
            "business_name",
            "business_street",
            "business_city",
            "business_state",
            "business_zip",
            "business_kind",
            "other_names",
            "other_business_names",
            "prior_cases",
            "pending_cases",
        ),
        "debtor_info",
    ),
    **dict.fromkeys(
        (
            "hazard_answer",
            "hazard_what",
            "hazard_why",
            "hazard_street",
            "hazard_city",
            "hazard_state",
            "hazard_zip",
        ),
        "assets",
    ),
    **dict.fromkeys(
        (
            "debt_nature",
            "debt_nature_text",
            "disabled_veteran",
            "debts_on_duty",
            "reservist",
            "called_to_duty",
            "duty_category",
            "duty_released_on",
            "duty_ended_on",
        ),
        "debts",
    ),
    **dict.fromkeys(
        (
            "rents_residence",
            "eviction_judgment",
            "landlord_name",
            "landlord_street",
            "landlord_city",
            "landlord_state",
            "landlord_zip",
        ),
        "contracts",
    ),
    **dict.fromkeys(
        (
            "credit_counseling",
            "exigent_text",
            "not_required_reason",
            "aware_consequences",
            "aware_fraud",
            "paid_preparer",
            "preparer_name",
        ),
        "review",
    ),
}

# Form 101A's landlord block (4b2-R2): the one pair of answers that puts the form in the packet
# is a rent Yes and an eviction Yes, never the eviction answer alone (a rent No keeps a stale one).
LANDLORD_KEYS = (
    "landlord_name",
    "landlord_street",
    "landlord_city",
    "landlord_state",
    "landlord_zip",
)


def evicted_renter(answers: dict) -> bool:
    return answers.get("rents_residence") == "yes" and answers.get("eviction_judgment") == "yes"


def landlord_missing(answers: dict) -> bool:
    """True only under the pair, when any landlord key is not a non-blank string."""
    if not evicted_renter(answers):
        return False
    return any(
        not (isinstance(answers.get(key), str) and answers[key].strip()) for key in LANDLORD_KEYS
    )


def is_nine_digits(value) -> bool:
    # 0-9 only: \d would also count other scripts' digits, which the forms' font can't print
    return isinstance(value, str) and len(re.sub(r"[^0-9]", "", value)) == 9


def is_itin(value) -> bool:
    """An ITIN is nine digits whose first digit is 9 (PF2-U2)."""
    return is_nine_digits(value) and re.sub(r"[^0-9]", "", value)[0] == "9"


def is_mm_dd_yyyy(value) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        return False
    try:
        datetime.strptime(value, "%m/%d/%Y")
    except ValueError:
        return False
    return True


def branch_of(debt_nature: str | None) -> str | None:
    """Form 107 line 6's branch from Form 101 line 16: "consumer" for consumer debts, "other"
    for business debts or neither, None while line 16 holds no answer."""
    if debt_nature == "consumer":
        return "consumer"
    if debt_nature in ("business", "neither"):
        return "other"
    return None


def is_plain_amount(value) -> bool:
    """An amount Form 107 prints: ASCII digits with at most two places, under $10,000,000,000
    (the Schedule I rule). Any other is stored as typed and prints blank (B47, R-12)."""
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9]+(\.[0-9]{1,2})?", value) is not None
        and Decimal(value) < 10**10
    )


def is_last_4(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9]{4}", value) is not None


# Form 107 lines 1 to 12's row cells as FinancialAffairsAnswers stores them (D§3), copied here so
# this module imports no model; test_affairs_cells.py pins the two equal.
_PAYMENT_CELLS = (
    "debt_id",
    "name",
    "street",
    "street_2",
    "city",
    "state",
    "zip",
    "date_1",
    "date_2",
    "date_3",
    "paid",
    "owed",
)
_L5_CELLS = ("source", "amount")
AFFAIRS_LIST_CELLS: dict[str, tuple[str, ...]] = {
    "l2_rows": ("street", "street_2", "city", "state", "zip", "from", "to"),
    "l5_current_rows": _L5_CELLS,
    "l5_last_rows": _L5_CELLS,
    "l5_prior_rows": _L5_CELLS,
    "l6_rows": (
        *_PAYMENT_CELLS,
        "mortgage",
        "car",
        "credit_card",
        "loan",
        "vendors",
        "other",
        "other_text",
    ),
    "l7_rows": (*_PAYMENT_CELLS, "reason"),
    "l8_rows": (*_PAYMENT_CELLS, "reason"),
    "l9_rows": (
        "case_title",
        "case_number",
        "nature",
        "court_name",
        "court_street",
        "court_city",
        "court_state",
        "court_zip",
        "status",
    ),
    "l10_rows": (
        "name",
        "street",
        "street_2",
        "city",
        "state",
        "zip",
        "property",
        "date",
        "value",
        "repossessed",
        "foreclosed",
        "garnished",
        "attached",
    ),
    "l11_rows": (
        "name",
        "street",
        "street_2",
        "city",
        "state",
        "zip",
        "action",
        "date",
        "amount",
        "last_4",
    ),
    "l12_statement": ("text",),
}
# The cells a sheet column prints that no row stores: each is composed from the row's own (D§5.2).
AFFAIRS_COMPUTED_CELLS: dict[str, tuple[str, ...]] = {
    "l2_rows": ("address",),
    "l6_rows": ("name_and_address", "dates", "paid_for"),
    "l7_rows": ("name_and_address", "dates"),
    "l8_rows": ("name_and_address", "dates"),
    "l9_rows": ("court", "case_title_1", "case_title_2"),
    "l10_rows": ("name_and_address", "what_happened"),
    "l11_rows": ("name_and_address",),
}
# The cells that print a dollar amount: the only ones a group's total box may add (R14).
AFFAIRS_MONEY_CELLS = frozenset({"paid", "owed", "amount", "value"})
_TICK_CELLS = frozenset(
    {
        "mortgage",
        "car",
        "credit_card",
        "loan",
        "vendors",
        "other",
        "repossessed",
        "foreclosed",
        "garnished",
        "attached",
    }
)
_DATE_CELLS = frozenset({"from", "to", "date_1", "date_2", "date_3", "date"})
_STATUSES = ("pending", "on_appeal", "concluded")
# The words Form 107 prints beside line 6's and line 10's boxes (the index's option_text), in the
# form's order; test_affairs_cells.py pins each to the template.
PAID_FOR_WORDS: dict[str, str] = {
    "mortgage": "Mortgage",
    "car": "Car",
    "credit_card": "Credit card",
    "loan": "Loan repayment",
    "vendors": "Suppliers or vendors",
    "other": "Other",
}
WHAT_HAPPENED_WORDS: dict[str, str] = {
    "repossessed": "Property was repossessed.",
    "foreclosed": "Property was foreclosed.",
    "garnished": "Property was garnished.",
    "attached": "Property was attached, seized, or levied.",
}
_FORM_107 = "b_107_0425-form.pdf"
_CASE_TITLE_BOX = "Case title1 9a"


# The petition record's row lists whose `filed_on` prints only as a real MM/DD/YYYY date (PF2-2).
_DATED_ROW_LISTS = ("prior_cases", "pending_cases")
# The petition record's dates that print only as a real MM/DD/YYYY date (4d-R9).
_DATED_KEYS = ("duty_released_on", "duty_ended_on")


def _unrecognized(binding: str) -> ValueError:
    return ValueError(f"unrecognized binding: {binding!r}")


def _namespace(binding: str) -> str:
    """The answer namespace a binding starts with; a binding outside the three is unrecognized."""
    for prefix in ANSWER_NAMESPACES:
        if binding.startswith(prefix):
            return prefix
    raise _unrecognized(binding)


def _affairs_line(binding: str) -> int:
    """The Form 107 line an `affairs.` key names by its `l<n>_` prefix, 1 to 28."""
    match = _AFFAIRS_LINE.match(binding[len("affairs.") :])
    if match is None or not 1 <= int(match[1]) <= 28:
        raise _unrecognized(binding)
    return int(match[1])


def _text(value) -> str:
    """A stored value as text: null and structure are blank, a typed 0 or False is not."""
    return "" if value is None or isinstance(value, dict | list) else str(value)


def _tick(cell: str) -> Callable[[dict], str]:
    """A box the filer ticked prints through its slot's {"true": state}; anything else is blank."""
    return lambda row: "true" if row.get(cell) == "yes" else ""


def _amount(cell: str) -> Callable[[dict], str]:
    """To the cent when typed as a plain amount ("0" prints 0.00); malformed or blank is blank."""

    def printer(row: dict) -> str:
        value = row.get(cell)
        return str(Decimal(value).quantize(Decimal("0.01"))) if is_plain_amount(value) else ""

    return printer


def _date(cell: str) -> Callable[[dict], str]:
    """Only a real MM/DD/YYYY date; the stored value stays as typed (R-12)."""

    def printer(row: dict) -> str:
        value = row.get(cell)
        return value if is_mm_dd_yyyy(value) else ""

    return printer


def _last_4(cell: str) -> Callable[[dict], str]:
    def printer(row: dict) -> str:
        value = row.get(cell)
        return value if is_last_4(value) else ""

    return printer


def _status(cell: str) -> Callable[[dict], str]:
    def printer(row: dict) -> str:
        value = row.get(cell)
        return value if isinstance(value, str) and value in _STATUSES else ""

    return printer


def _stored(cell: str) -> Callable[[dict], str]:
    return lambda row: _text(row.get(cell))


def _printer(cell: str) -> Callable[[dict], str]:
    """A stored cell's printer, by the kind of answer it holds."""
    if cell in _TICK_CELLS:
        return _tick(cell)
    if cell in AFFAIRS_MONEY_CELLS:
        return _amount(cell)
    if cell in _DATE_CELLS:
        return _date(cell)
    if cell == "last_4":
        return _last_4(cell)
    if cell == "status":
        return _status(cell)
    return _stored(cell)


def _part(row: dict, cell: str) -> str:
    """One part of a composed cell: as stored, its edge spaces trimmed; blank skips it."""
    return _text(row.get(cell)).strip()


def _joined(*parts: str) -> str:
    return ", ".join(part for part in parts if part)


def _city_line(row: dict, city: str, state: str, zip_code: str) -> str:
    """The "City, ST ZIP" line from the parts given, as fill_resolver._entry_text builds it."""
    line = _joined(_part(row, city), _part(row, state))
    return " ".join(part for part in (line, _part(row, zip_code)) if part)


def _address(row: dict) -> str:
    return _joined(
        _part(row, "street"), _part(row, "street_2"), _city_line(row, "city", "state", "zip")
    )


def _name_and_address(row: dict) -> str:
    return _joined(_part(row, "name"), _address(row))


def _court(row: dict) -> str:
    return _joined(
        _part(row, "court_name"),
        _part(row, "court_street"),
        _city_line(row, "court_city", "court_state", "court_zip"),
    )


def _dates(row: dict) -> str:
    return _joined(*(_date(cell)(row) for cell in ("date_1", "date_2", "date_3")))


def _paid_for(row: dict) -> str:
    """The form's words for each ticked box in its order; Other with the filer's words (R-8)."""
    words = []
    for cell, word in PAID_FOR_WORDS.items():
        if row.get(cell) != "yes":
            continue
        other_text = _part(row, "other_text") if cell == "other" else ""
        words.append(f"{word}: {other_text}" if other_text else word)
    return ", ".join(words)


def _what_happened(row: dict) -> str:
    # Each of the form's sentences ends in its own period, so they join with a space (R-8).
    return " ".join(word for cell, word in WHAT_HAPPENED_WORDS.items() if row.get(cell) == "yes")


def _case_title_half(index: int) -> Callable[[dict], str]:
    """Line 9's case title across its two boxes: the first takes the whole leading words that
    fit it, the second the rest (R-15)."""

    def printer(row: dict) -> str:
        # Imported here: this module stays a leaf, and explain_split measures through the filler.
        from apps.forms.services.explain_split import split_at_box

        title = _text(row.get("case_title"))
        return split_at_box(title, _FORM_107, _CASE_TITLE_BOX)[index] if title else ""

    return printer


_COMPUTED_PRINTERS: dict[str, Callable[[dict], str]] = {
    "address": _address,
    "name_and_address": _name_and_address,
    "court": _court,
    "dates": _dates,
    "paid_for": _paid_for,
    "what_happened": _what_happened,
    "case_title_1": _case_title_half(0),
    "case_title_2": _case_title_half(1),
}
# Each list's printer of one row, cell by cell, over every stored and computed cell (D§5.2).
AFFAIRS_CELLS: dict[str, dict[str, Callable[[dict], str]]] = {
    key: {
        **{cell: _printer(cell) for cell in cells},
        **{cell: _COMPUTED_PRINTERS[cell] for cell in AFFAIRS_COMPUTED_CELLS.get(key, ())},
    }
    for key, cells in AFFAIRS_LIST_CELLS.items()
}


def affairs_statement(answers: dict) -> list[dict]:
    """Line 12's statement: its non-blank texts, only under line 12's Yes."""
    rows = answers.get("l12_statement")
    if answers.get("l12_answer") != "yes" or not isinstance(rows, list):
        return []
    return [
        {"text": row["text"]}
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("text"), str) and row["text"].strip()
    ]


def record_value(session, binding: str) -> str | list[str]:
    """
    The value of an answers record's key: "<namespace>.<key>" is a str, "<namespace>.<key>[].<attr>"
    a list of str over a row list. Blank or [] when the session has no such record.
    """
    namespace = _namespace(binding)
    key, is_list, attr = binding[len(namespace) :].partition("[].")
    printed_rows = False
    if namespace == "affairs.":
        line = _affairs_line(binding)
        related = "financial_affairs" if line <= 12 else "property_affairs"
        # Lines 1 to 12's rows print through AFFAIRS_CELLS; a list or cell it doesn't know is a
        # defect, refused with or without a record (R-48). Lines 13 to 28 keep the plain read.
        printed_rows = bool(is_list) and line <= 12
        if printed_rows and attr not in AFFAIRS_CELLS.get(key, {}):
            raise _unrecognized(binding)
    else:
        related = RECORD_OF_NAMESPACE[namespace]
    record = getattr(session, related, None)
    if record is None:
        return [] if is_list else ""
    answers = record.get_answers()
    if printed_rows:
        if key == "l12_statement":
            return [row["text"] for row in affairs_statement(answers)]
        rows = answers.get(key)
        if not isinstance(rows, list):
            return []
        printer = AFFAIRS_CELLS[key][attr]
        return [printer(row) if isinstance(row, dict) else "" for row in rows]
    if not is_list:
        value = _text(answers.get(key))
        if namespace == "petition." and key in _DATED_KEYS and value.strip():
            # A date the form can't read prints blank; the stored value stays as typed.
            return value if is_mm_dd_yyyy(value) else ""
        return value
    rows = answers.get(key)
    if not isinstance(rows, list):
        return []
    cells = [_text(row.get(attr)) if isinstance(row, dict) else "" for row in rows]
    if namespace == "petition." and key in _DATED_ROW_LISTS and attr == "filed_on":
        # A date the form can't read prints blank; the stored value stays as typed.
        cells = [c if not c.strip() or is_mm_dd_yyyy(c) else "" for c in cells]
    return cells


def record_step(binding: str) -> str:
    """The wizard step that asks a binding's key (a WIZARD_STEPS key or one of NEW_STEP_KEYS)."""
    namespace = _namespace(binding)
    key = binding[len(namespace) :].partition("[].")[0]
    if namespace == "petition.":
        step = PETITION_STEP_OF_KEY.get(key)
        if step is None:
            raise _unrecognized(binding)
        return step
    if namespace == "schedule_i.":
        return "expense_info" if key.startswith("schedule_j_") else "income_info"
    return "last_few_years_1" if _affairs_line(binding) <= 12 else "last_few_years_2"
