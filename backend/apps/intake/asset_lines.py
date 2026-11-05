"""The lines of Schedule A/B (Form 106A/B), in the form's order (3b spec §3).

Pure, with no models. Each line has the part it sits in, the shape of its rows, how many
rows its slots hold and, for a line that asks which kind, its kinds and each kind's slots.
Lines 37 and 46 are gates: the lines after them are shown only under a Yes.
"""

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


def ordered_assets(session) -> list:
    """The session's rows in catalog order, then id; an old row with no line sorts first.

    Sorted in Python: the line and every value are ciphertext in the table.
    """

    def position(row):
        if row.ab_line is None:
            return -1
        return _POSITION.get(row.ab_line, len(LINES))

    return sorted(session.assets.all(), key=lambda row: (position(row), row.pk))


def rows_on(rows: list, key: str, kind: str | None = None) -> list:
    """The rows on one line, and of one kind when a kind is given, in the order given."""
    on_line = [row for row in rows if row.ab_line == key]
    if kind is None:
        return on_line
    return [row for row in on_line if row.get_details().get("kind") == kind]


def part_total(rows: list, part: int) -> Decimal:
    """The sum of `current_value` over the rows on the lines of one Part; a null counts as zero."""
    keys = {line.key for line in LINES if line.part == part}
    return sum((row.current_value or Decimal(0) for row in rows if row.ab_line in keys), Decimal(0))
