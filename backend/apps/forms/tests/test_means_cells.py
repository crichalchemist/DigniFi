"""Every 122A-2 box prints what the calculator holds for it and nothing else: a missing or skipped
line prints blank, never 0.00."""

import re
from dataclasses import replace
from decimal import Decimal

import pytest

from apps.eligibility.means_lines import (
    LINE_KEYS,
    MISSING,
    PRESUMPTION,
    ROW_KEYS,
    SKIPPED,
    MeansLines,
    MeansRow,
)
from apps.eligibility.tests.test_means_lines import PRIYA_LINES
from apps.forms.services import means_fit, text_fit
from apps.forms.services.means_cells import LINE_43_POINTER, means_value

D = Decimal

_TEXT_KEYS = ("13_vehicle_1", "13_vehicle_2")
_COUNT_KEYS = ("5", "7b", "7e", "11")
_ANSWER_KEYS = (
    "2", "2_filing", "3_answer", "25_answer", "25_spends", "34_answer", "35_answer",
    "36_answer", "42", "43",
)  # fmt: skip
_MONEY_KEYS = tuple(
    key
    for key in LINE_KEYS
    if key not in (*_TEXT_KEYS, *_COUNT_KEYS, *_ANSWER_KEYS, "36_multiplier", "40", "page_1")
)

_DEMO_ROW = MeansRow("Demo", D("1.00"), property="Demo", flag="yes", cure=D("1.00"))

# R17: a value in every line and a row in every list, line 43's four rows numbered so the n-th
# pointer and amount can be told apart; Task 5's tier 1 reader test reads it too.
FULL_LINES = MeansLines(
    lines={
        **{key: D("1.00") for key in _MONEY_KEYS},
        **{key: 1 for key in _COUNT_KEYS},
        **{key: "yes" for key in _ANSWER_KEYS},
        "36_multiplier": D("6.9"),
        "40": "On",
        "page_1": PRESUMPTION,
        "13_vehicle_1": "Demo",
        "13_vehicle_2": "Demo",
    },
    rows={
        **{key: (_DEMO_ROW,) for key in ROW_KEYS if key != "43"},
        "43": tuple(MeansRow(f"Demo {n}", D(f"{n}.00")) for n in range(1, 5)),
    },
    outcome=PRESUMPTION,
)

PRIYA = MeansLines(
    lines=PRIYA_LINES,
    rows={
        **{key: () for key in ROW_KEYS},
        "3": (MeansRow("His payroll taxes withheld from his pay", D("250.00")),),
    },
    outcome=PRESUMPTION,
)


def _with_lines(lines: MeansLines, **values) -> MeansLines:
    return replace(lines, lines={**lines.lines, **values})


def _with_rows(lines: MeansLines, **rows) -> MeansLines:
    return replace(lines, rows={**lines.rows, **rows})


@pytest.mark.parametrize(
    ("binding", "printed"),
    [
        ("means.line_2", "yes"),
        ("means.line_2_filing", "no"),
        ("means.line_3", "250.00"),
        ("means.line_11", "1"),
        ("means.line_13_vehicle_1", "Honda CR-V EX 2021"),
        ("means.line_13d", ""),
        ("means.line_36_multiplier", "6.9%"),
        ("means.line_39c", "2188.40"),
        ("means.line_40", "2"),
        ("means.line_42", ""),
        ("means.line_43", "no"),
        ("means.page_1", "presumption"),
    ],
)
def test_every_means_scalar_resolves_to_text_or_blank(binding, printed):
    assert means_value(binding, PRIYA) == printed


@pytest.mark.parametrize("sentinel", [MISSING, SKIPPED], ids=repr)
@pytest.mark.parametrize("key", ["16", "5", "2", "43"])
def test_a_missing_or_skipped_line_prints_blank_never_zero(sentinel, key):
    lines = _with_lines(FULL_LINES, **{key: sentinel})
    assert means_value(f"means.line_{key}", lines) == ""


@pytest.mark.parametrize("key", [key for key in ROW_KEYS if key != "43"])
def test_a_row_whose_amount_the_calculator_couldnt_work_out_prints_blank(key):
    lines = _with_rows(FULL_LINES, **{key: (MeansRow("Demo", MISSING),)})
    words = "purpose" if key == "3" else "creditor"
    assert means_value(f"means.line_{key}[].amount", lines) == [""]
    assert means_value(f"means.line_{key}[].{words}", lines) == ["Demo"]


def test_a_line_43_pointer_or_amount_past_the_last_row_prints_blank():
    lines = _with_rows(FULL_LINES, **{"43": FULL_LINES.rows["43"][:1]})
    assert means_value("means.line_43_pointer_1", lines) == "See line 43.1 on the attached sheet."
    assert means_value("means.line_43_amount_1", lines) == "1.00"
    for n in (2, 3, 4):
        assert means_value(f"means.line_43_pointer_{n}", lines) == ""
        assert means_value(f"means.line_43_amount_{n}", lines) == ""


@pytest.mark.parametrize(("count", "printed"), [(0, "0"), (1, "1"), (2, "2_or_more")])
def test_line_11_prints_0_1_or_2_or_more(count, printed):
    assert means_value("means.line_11", _with_lines(FULL_LINES, **{"11": count})) == printed


@pytest.mark.parametrize("multiplier", [D("6.9"), D("6.90")], ids=str)
def test_the_multiplier_prints_as_the_list_gives_it(multiplier):
    lines = _with_lines(FULL_LINES, **{"36_multiplier": multiplier})
    assert means_value("means.line_36_multiplier", lines) == "6.9%"


@pytest.mark.parametrize(
    "binding", ["means.line_9b[].amout", "means.line_99", "means.line_43_pointer_5"]
)
def test_an_unknown_means_attribute_is_a_value_error(binding):
    with pytest.raises(ValueError, match=re.escape(f"unrecognized binding: {binding!r}")):
        means_value(binding, FULL_LINES)


def test_line_43s_columns_are_equal_length_strings():
    lines = _with_rows(
        FULL_LINES, **{"43": tuple(MeansRow(f"  Demo {n} ", D(f"{n}.00")) for n in range(1, 5))}
    )
    explanations = means_value("means.line_43[].explanation", lines)
    amounts = means_value("means.line_43[].amount", lines)
    assert explanations == ["Demo 1", "Demo 2", "Demo 3", "Demo 4"]
    assert amounts == ["1.00", "2.00", "3.00", "4.00"]
    assert all(isinstance(cell, str) for cell in (*explanations, *amounts))


def test_the_four_pointers_name_the_sheet_rows_that_hold_them():
    sheet_number = "43.{n}"  # the line 43 sheet's number pattern (R14): row n is "43.n"
    for n in range(1, 5):
        pointer = means_value(f"means.line_43_pointer_{n}", FULL_LINES)
        assert sheet_number.format(n=n) in pointer
        assert pointer == LINE_43_POINTER.format(n=n)


def test_the_pointer_fits_its_box_at_10_pt():
    widget = means_fit._widget("undefined_113")
    fitted = text_fit.fit(widget, means_fit.TEMPLATE, "See line 43.1 on the attached sheet.")
    assert fitted is not None
    assert fitted[1] == 10.0
