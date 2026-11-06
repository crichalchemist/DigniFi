"""The lines of Schedule A/B (Form 106A/B), in the form's order (3b spec §3).

Pure, with no models. Each line has the part it sits in, the shape of its rows, how many
rows its slots hold and, for a line that asks which kind, its kinds and each kind's slots.
Lines 37 and 46 are gates: the lines after them are shown only under a Yes.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal

WHO = ("only_you", "with_someone")
PROPERTY_KINDS = (
    "single_family",
    "duplex",
    "condo",
    "manufactured",
    "land",
    "investment",
    "timeshare",
    "other",
)
# The words the form prints beside each box, for a row on an attached sheet, which has no box.
WHO_WORDS = {
    "only_you": "Debtor 1 only",
    "with_someone": "At least one of the debtors and another",
}
PROPERTY_KIND_WORDS = {
    "single_family": "Single-family home",
    "duplex": "Duplex or multi-unit building",
    "condo": "Condominium or cooperative",
    "manufactured": "Manufactured or mobile home",
    "land": "Land",
    "investment": "Investment property",
    "timeshare": "Timeshare",
    "other": "Other",
}


@dataclass(frozen=True)
class Line:
    key: str
    part: int
    shape: str
    capacity: int = 1
    kinds: tuple[tuple[str, int], ...] = ()
    gate: str | None = None


def _lines(keys, part, shape, capacity=1, gate=None):
    return [Line(key, part, shape, capacity, gate=gate) for key in keys]


def _range(first, last):
    return [str(n) for n in range(first, last + 1)]


LINES: tuple[Line, ...] = (
    Line("1", 1, "place", 3),
    Line("3", 2, "vehicle", 4),
    Line("4", 2, "vehicle_no_mileage", 2),
    *_lines(_range(6, 14), 3, "item"),
    Line("16", 4, "cash"),
    Line("17", 4, "labelled", kinds=(("checking", 2), ("savings", 2), ("cd", 1), ("other", 4))),
    Line("18", 4, "named", 3),
    Line("19", 4, "named_share", 3),
    Line("20", 4, "named", 3),
    Line(
        "21",
        4,
        "labelled",
        kinds=(
            ("401k", 1),
            ("pension", 1),
            ("ira", 1),
            ("retirement", 1),
            ("keogh", 1),
            ("additional", 2),
        ),
    ),
    Line(
        "22",
        4,
        "labelled",
        kinds=tuple(
            (kind, 1)
            for kind in (
                "electric",
                "gas",
                "heating_oil",
                "security_deposit",
                "prepaid_rent",
                "telephone",
                "water",
                "rented_furniture",
                "other",
            )
        ),
    ),
    Line("23", 4, "named", 3),
    Line("24", 4, "named", 3),
    *_lines(["25", "26", "27"], 4, "item"),
    Line("28", 4, "shared_box", kinds=(("federal", 1), ("state", 1), ("local", 1))),
    Line(
        "29",
        4,
        "shared_box",
        kinds=tuple(
            (kind, 1)
            for kind in (
                "alimony",
                "maintenance",
                "support",
                "divorce_settlement",
                "property_settlement",
            )
        ),
    ),
    Line("30", 4, "item"),
    Line("31", 4, "insurance", 3),
    *_lines(_range(32, 35), 4, "item"),
    Line("37", 5, "gate"),
    *_lines(_range(38, 41), 5, "item", gate="37"),
    Line("42", 5, "named_share", 3, gate="37"),
    Line("43", 5, "item_question", gate="37"),
    Line("44", 5, "named", 6, gate="37"),
    Line("46", 6, "gate"),
    *_lines(_range(47, 51), 6, "item", gate="46"),
    Line("53", 7, "shared_box", 3),
)

LINE_BY_KEY: dict[str, Line] = {line.key: line for line in LINES}
_POSITION = {line.key: index for index, line in enumerate(LINES)}


def shown_lines(answers: dict[str, str]) -> list[Line]:
    """Every line, less those whose gate isn't answered "yes"."""
    return [line for line in LINES if line.gate is None or answers.get(line.gate) == "yes"]


# Session id → its rows, while one_read_of_assets is open. Kept here and not on the session, so
# a session held across a save reads what the save stored.
_ONE_READ: ContextVar[dict | None] = ContextVar("one_read_of_assets", default=None)


@contextmanager
def one_read_of_assets():
    """Within the block, ordered_assets reads each session's rows once: a form's rules each ask."""
    token = _ONE_READ.set({})
    try:
        yield
    finally:
        _ONE_READ.reset(token)


def ordered_assets(session) -> list:
    """The session's rows in catalog order, then id; an old row with no line sorts first.

    Sorted in Python: the line and every value are ciphertext in the table.
    """

    def position(row):
        if row.ab_line is None:
            return -1
        return _POSITION.get(row.ab_line, len(LINES))

    held = _ONE_READ.get()
    if held is not None and session.pk in held:
        return held[session.pk]
    rows = sorted(session.assets.all(), key=lambda row: (position(row), row.pk))
    if held is not None:
        held[session.pk] = rows
    return rows


def rows_on(rows: list, key: str, kind: str | None = None) -> list:
    """The rows on one line, and of one kind when a kind is given, in the order given."""
    on_line = [row for row in rows if row.ab_line == key]
    if kind is None:
        return on_line
    return [row for row in on_line if row.get_details().get("kind") == kind]


def rows_under_gate(rows: list, gate: str) -> list:
    """The rows on the lines a gate shows; none is how the form reads the gate's No."""
    keys = {line.key for line in LINES if line.gate == gate}
    return [row for row in rows if row.ab_line in keys]


def printed_answer(rows: list, key: str) -> str:
    """The Yes or No a line's box prints, read from the rows (3b spec §8.1); "" when a gate hid it.

    A gate says Yes with a row under it. Complete has refused any row that disagrees with the
    stored answers by the time a form prints.
    """
    line = LINE_BY_KEY[key]
    if line.shape == "gate":
        return "yes" if rows_under_gate(rows, key) else "no"
    if line.gate is not None and not rows_under_gate(rows, line.gate):
        return ""
    return "yes" if rows_on(rows, key) else "no"


def part_total(rows: list, part: int) -> Decimal:
    """The sum of `current_value` over the rows on the lines of one Part; a null counts as zero."""
    keys = {line.key for line in LINES if line.part == part}
    return sum((row.current_value or Decimal(0) for row in rows if row.ab_line in keys), Decimal(0))


class AssetStepGap(Exception):
    """One thing the Assets step still lacks, in the filer's words (3b spec §7).

    The forms views answer it with a 422 and this `step`, as they answer an IncomeStepGap.
    """

    step = "assets"


def _blank(text) -> bool:
    return not (text or "").strip()


def _value_given(row, figure: str, flag: str) -> bool:
    """A value counts as given with a figure (a $0 included) or its "I don't know" flag."""
    return getattr(row, figure) is not None or bool(row.get_details().get(flag))


def _row_is_complete(line: Line, row) -> bool:
    details = row.get_details()
    has_text = not _blank(row.description)
    has_value = _value_given(row, "current_value", "value_unknown")
    shape = line.shape
    if shape == "cash":
        return has_value
    if shape in ("place", "vehicle", "vehicle_no_mileage"):
        if not (has_value and _value_given(row, "entire_value", "entire_unknown")):
            return False
        if not details.get("who"):
            return False
        if shape == "place":
            kinds = details.get("property_kinds") or []
            return (
                not _blank(details.get("street"))
                and bool(kinds)
                and ("other" not in kinds or not _blank(details.get("other_kind")))
            )
        return not _blank(details.get("make"))
    if shape == "item_question":
        answer = details.get("has_personal_info")
        return answer is not None and (answer is False or has_text) and has_value
    if line.kinds and not details.get("kind"):
        return False
    if shape == "named_share" and details.get("percent") is None:
        return False
    return has_text and has_value


def _row_name(row) -> str:
    """What the filer knows a row by, in the order Review names it."""
    details = row.get_details()
    return (
        (row.description or "").strip()
        or (details.get("street") or "").strip()
        or (details.get("make") or "").strip()
        or "one item"
    )


def asset_step_gaps(session) -> list[AssetStepGap]:
    """What Complete and the forms refuse on the Assets step, in the form's order (3b spec §7).

    Reads `session.assets` and `session.asset_lines`; a session with no answers row has every
    shown line unanswered.
    """
    gaps: list[AssetStepGap] = []
    rows = ordered_assets(session)
    for row in rows:
        if row.ab_line not in LINE_BY_KEY:
            gaps.append(AssetStepGap(f'Pick a line on the Assets step for "{_row_name(row)}".'))

    answers_row = getattr(session, "asset_lines", None)
    answers = answers_row.get_answers() if answers_row is not None else {}
    shown = {line.key for line in shown_lines(answers)}
    for line in LINES:
        key = line.key
        on_line = rows_on(rows, key)
        if key not in shown:
            if on_line:
                gaps.append(
                    AssetStepGap(
                        f"Line {key} is under line {line.gate}, which isn't answered Yes. "
                        f"Remove what line {key} lists, or answer line {line.gate} Yes."
                    )
                )
            continue
        answer = answers.get(key)
        if answer not in ("yes", "no"):
            gaps.append(AssetStepGap(f"Line {key} on the Assets step needs a Yes or No."))
            continue
        if line.shape == "gate":
            if on_line:
                gaps.append(AssetStepGap(f"Line {key} takes no items. Remove what it lists."))
            under = [other.key for other in LINES if other.gate == key]
            if answer == "yes" and all(answers.get(other) == "no" for other in under):
                gaps.append(
                    AssetStepGap(
                        f"Line {key} says Yes, but every line under it says No. Change one of them."
                    )
                )
            continue
        if answer == "yes" and not on_line:
            gaps.append(
                AssetStepGap(f"Line {key} says Yes. Add what you have, or change it to No.")
            )
        elif answer == "no" and on_line:
            gaps.append(
                AssetStepGap(
                    f"Line {key} says No, but it still lists something. Remove it, or change the answer to Yes."
                )
            )
        if answer == "yes":
            for row in on_line:
                if not _row_is_complete(line, row):
                    gaps.append(
                        AssetStepGap(
                            f'Line {key} needs more about "{_row_name(row)}" on the Assets step.'
                        )
                    )
    return gaps
