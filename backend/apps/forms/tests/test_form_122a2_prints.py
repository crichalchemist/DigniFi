"""
What Form 122A-2 prints for each answer the page can hold: a declined opt-in blank, a typed $0 as
0.00, a skipped branch blank, totals always.

Business intent: the form is signed under oath, so a box the filer never answered must never
print 0.00 (it would swear to an amount nobody gave), a box the form skips must print nothing,
and the result boxes must say what the calculator worked out, in the box the form's own order
puts it in. Each test builds its session as test_means_hold.py does and reads the baked page,
never the document alone, where a box state is the claim.
"""

# ruff: noqa: F811
from decimal import Decimal

import pytest

from apps.districts.dated_tables import fill_date
from apps.eligibility.means_inputs import read_inputs, read_tables, vehicle_rows
from apps.eligibility.means_lines import NO_PRESUMPTION, PRESUMPTION, work_out
from apps.eligibility.services import MeansTestCalculator
from apps.forms.registry import build_parts
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve_parts
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.forms.tests.test_means_hold import (  # noqa: F401  (fixtures)
    _item_row,
    _marry,
    above,
    district,
    session_with_debtor,
    user,
)
from apps.intake.models import IntakeSession
from apps.intake.tests.builders import (
    answer_asset_lines,
    answer_means_test,
    complete_debt,
    linked_loan,
    linked_row,
)

# 39c on `above` (wages 9,000.00, a household of one, every answer No or 0.00): line 16 steers it.
BASE_39C = Decimal("5524.00")

# Each result box's boxes by position on the template, top to bottom, written out here from the
# index's rects (T3 above T5; T21, T22, T23 down the page; T6 above T7): an inverted `choices`
# map in the schema ticks the other box and fails by tag. Each tag's on-state is what it prints.
PAGE_1 = {"T3": "/No Abuse", "T5": "/Presumption of abuse applies"}
LINE_40 = {"1": ("T21", "/1"), "2": ("T22", "/2"), "between": ("T23", "/On")}
LINE_42 = {"No": ("T6", "/No"), "Yes": ("T7", "/Yes")}


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


def _drawn(session):
    document = build_parts("form_122a2", _fresh(session))
    pdf = PDFFormFiller().fill("form_122a2", document)
    return read_drawn("form_122a2", pdf, document["parts"])


def _printed(drawn, name):
    """What every widget of one name prints: one value, since a name prints one value."""
    values = {w.value for w in drawn if w.full_name == name}
    assert len(values) == 1, (name, values)
    return values.pop()


def _tick(drawn, name):
    """The state of the one box of this name that is ticked, else "/Off"."""
    states = {w.state for w in drawn if w.full_name == name} - {"/Off"}
    assert len(states) <= 1, (name, states)
    return states.pop() if states else "/Off"


def _ticked(drawn, name):
    """{tag: state} of the boxes of this name that are ticked: where the check mark sits."""
    return {w.tag: w.state for w in drawn if w.full_name == name and w.state != "/Off"}


def _steer(session, target):
    """Answer line 16 so line 39c is `target`, and prove it did."""
    answer_means_test(session, line_16=str(BASE_39C - Decimal(target)))
    tables, _ = read_tables(fill_date())
    lines = work_out(read_inputs(_fresh(session)), tables)
    assert lines.lines["39c"] == Decimal(target)


def _claimed_car(session, payment="300.00"):
    """One vehicle on Schedule A/B line 3 with a loan, claimed on line 11."""
    car = linked_row(session, "3", description="Demo car")
    linked_loan(session, car, payment)
    answer_asset_lines(session, yes=("3",))
    return {f"asset-{row.pk}": "yes" for row in vehicle_rows(_fresh(session))}


def test_a_declined_opt_in_prints_blank_and_an_answered_zero_prints_0_00(above):
    answer_means_test(above, line_26_answer="no", line_17="0.00")

    drawn = _drawn(above)

    assert _printed(drawn, "undefined_61") == ""
    assert _printed(drawn, "undefined_49") == "0.00"


def test_each_branch_the_form_skips_prints_blank(above):
    claims = _claimed_car(above)
    answer_means_test(above, vehicle_claims=claims)

    drawn = _drawn(above)

    # the guards: a claimed car with a loan takes its slot, so line 11 is 1 and line 12 prints
    assert _tick(drawn, "CheckBox6") == "/1"
    assert _printed(drawn, "Quest12") != ""
    assert _printed(drawn, "Quest13B Total amount for vehicle 1") == "300.00"
    # line 14 is for a filer with no vehicle; no Vehicle 2 leaves lines 13d to 13f empty
    assert _printed(drawn, "Quest14") == ""
    assert _printed(drawn, "Quest13D") == ""
    assert _printed(drawn, "Quest13F") == ""
    vehicle_2 = [w for w in drawn if w.full_name.startswith("Quest13E.")]
    assert vehicle_2
    assert {w.value for w in vehicle_2} == {""}
    # line 2 outside married_together: no spouse box ticked, no row, and line 3's total is 0.00
    assert _tick(drawn, "CheckBox4") == "/Off"
    for name in ("Quest3A", "Quest3A1", "Quest3B", "Quest3B1", "Quest3C", "Quest3C1"):
        assert _printed(drawn, name) == "", name
    assert _printed(drawn, "Quest3") == "0.00"


def test_line_34_prints_a_row_only_for_a_yes_with_a_cure_above_zero(above):
    cured = _item_row(above, "Demo Lender A")
    zero = _item_row(above, "Demo Lender B")
    declined = _item_row(above, "Demo Lender C")
    answer_means_test(
        above,
        line_34_answer="yes",
        debts={
            cured.pk: {"necessary_for_support": "yes", "cure": "600.00"},
            zero.pk: {"necessary_for_support": "yes", "cure": "0.00"},
            declined.pk: {"necessary_for_support": "no"},
        },
    )

    drawn = _drawn(above)

    assert _printed(drawn, "undefined_81") == "Demo Lender A"
    assert _printed(drawn, "secures the debt") != ""
    assert _printed(drawn, "undefined_82") == "600.00"
    assert _printed(drawn, "undefined_83") == "10.00"
    for name in (f"undefined_{n}" for n in range(84, 92)):
        assert _printed(drawn, name) == "", name
    assert _printed(drawn, "undefined_92") == "10.00"


def test_line_3s_total_prints_0_00_under_line_2s_no(above):
    answer_means_test(above)

    drawn = _drawn(above)

    assert _tick(drawn, "CheckBox3") == "/No"
    assert _printed(drawn, "Quest3") == "0.00"


def test_a_negative_39c_prints_with_a_minus_sign_and_ticks_box_1(above):
    _steer(above, "-476.00")

    drawn = _drawn(above)

    assert _printed(drawn, "undefined_107").startswith("-")
    assert _printed(drawn, "undefined_107") == "-476.00"
    assert _tick(drawn, "CheckBox14") == "/1"
    assert _tick(drawn, "CheckBox1") == "/No Abuse"


@pytest.mark.parametrize(
    ("target_39c", "printed"),
    [("200.00", True), ("2188.40", False), ("171.24", False)],
    ids=["39d 12,000.00 prints", "39d 131,304.00 blank", "39d 10,274.40 blank"],
)
def test_lines_41a_to_42_print_only_in_the_middle_band(above, target_39c, printed):
    complete_debt(above, amount_owed=Decimal("60000.00"))
    _steer(above, target_39c)

    drawn = _drawn(above)

    assert _printed(drawn, "undefined_110") == ("60000.00" if printed else "")
    assert _printed(drawn, "undefined_111") == ("15000.00" if printed else "")
    assert _tick(drawn, "CheckBox15") == ("/No" if printed else "/Off")


def test_line_25s_total_prints_in_both_boxes(above):
    # without line_25_spends the total is MISSING and prints blank
    answer_means_test(
        above,
        line_25_answer="yes",
        line_25_health="300.00",
        line_25_disability="200.00",
        line_25_hsa="300.00",
        line_25_spends="yes",
    )

    drawn = _drawn(above)

    assert [w.value for w in drawn if w.full_name == "2_2"] == ["800.00", "800.00"]


# (39c, unsecured debt, the page-1 box, line 40's box, line 42's box), §7.11's cases. 39d is 60
# times 39c, so only multiples of 0.60 exist and 17,150.00 itself is unreachable.
BAND_CASES = [
    ("171.24", None, "T3", "1", None),
    ("171.25", "100000.00", "T3", "between", "No"),
    ("200.00", "60000.00", "T3", "between", "No"),
    ("250.00", "60000.00", "T5", "between", "Yes"),
    ("200.00", "20000.00", "T5", "between", "Yes"),
    ("285.83", "100000.00", "T3", "between", "No"),
    ("285.84", None, "T5", "2", None),
]


@pytest.mark.parametrize(("target_39c", "unsecured", "page_1", "line_40", "line_42"), BAND_CASES)
def test_the_printed_boxes_agree_with_the_in_app_outcome_for_every_band_case(
    above, target_39c, unsecured, page_1, line_40, line_42
):
    if unsecured is not None:
        complete_debt(above, amount_owed=Decimal(unsecured))
    _steer(above, target_39c)

    drawn = _drawn(above)

    assert _ticked(drawn, "CheckBox1") == {page_1: PAGE_1[page_1]}
    assert _ticked(drawn, "CheckBox14") == dict([LINE_40[line_40]])
    assert _ticked(drawn, "CheckBox15") == ({} if line_42 is None else dict([LINE_42[line_42]]))
    printed = NO_PRESUMPTION if page_1 == "T3" else PRESUMPTION
    assert MeansTestCalculator(_fresh(above)).calculate()["outcome"] == printed
    tables, _ = read_tables(fill_date())
    assert work_out(read_inputs(_fresh(above)), tables).outcome == printed


# Every key the page asks for a figure, the override that leaves it unanswered, and the one box
# it prints in: 28 cases (R1). An opt-in is two keys, its answer and its amount.
UNANSWERED = (
    [
        ("line_15_answer", {"line_15_answer": None}, "Quest15"),
        ("line_15_amount", {"line_15_amount": None}, "Quest15"),
    ]
    + [
        (f"line_{n}", {f"line_{n}": None}, f"undefined_{48 + n - 16}")
        for n in (16, 17, 18, 19, 20, 21)
    ]
    + [
        ("line_22_answer", {"line_22_answer": None}, "undefined_54"),
        ("line_22_amount", {"line_22_amount": None}, "undefined_54"),
        ("line_23", {"line_23": None}, "undefined_55"),
        ("line_25_health", {"line_25_health": None}, "undefined_57"),
        ("line_25_disability", {"line_25_disability": None}, "undefined_58"),
        ("line_25_hsa", {"line_25_hsa": None}, "1_2"),
    ]
    + [
        (f"line_{n}_{part}", {f"line_{n}_{part}": None}, f"undefined_{61 + n - 26}")
        for n in range(26, 32)
        for part in ("answer", "amount")
    ]
    + [
        ("line_36_payment", {"line_36_payment": None}, "undefined_97"),
        (
            "line_3_amount",
            {"line_3_rows": [{"purpose": "Demo purpose", "amount": None}]},
            "Quest3A1",
        ),
    ]
)


def _every_asked_box_typed():
    """Every asked figure typed as 0.00, every opt-in Yes, line 25 spent, line 3 one row."""
    answers = {}
    for n in (15, 22, 26, 27, 28, 29, 30, 31):
        answers[f"line_{n}_answer"] = "yes"
        answers[f"line_{n}_amount"] = "0.00"
    answers |= {
        "line_25_answer": "yes",
        "line_25_health": "0.00",
        "line_25_disability": "0.00",
        "line_25_hsa": "0.00",
        "line_25_spends": "yes",
        "line_36_answer": "yes",
        "line_36_payment": "0.00",
        "line_3_answer": "yes",
        "line_3_rows": [{"purpose": "Demo purpose", "amount": "0.00"}],
    }
    return answers


@pytest.fixture
def typed(above):
    """A married filer with one claimed car, every asked box typed as 0.00."""
    claims = _claimed_car(above)
    _marry(above)
    answers = _every_asked_box_typed()
    answer_means_test(above, vehicle_claims=claims, **answers)
    return above, claims, answers


def test_an_answered_zero_prints_0_00_in_every_asked_box(typed):
    # the baseline that keeps the next test from passing on boxes that print blank anyway
    above, _, _ = typed

    values = build_parts("form_122a2", _fresh(above))["parts"][0]["values"]

    assert {box: values.get(box) for _, _, box in UNANSWERED} == {
        box: "0.00" for _, _, box in UNANSWERED
    }


@pytest.mark.parametrize(
    ("override", "box"), [pytest.param(o, b, id=key) for key, o, b in UNANSWERED]
)
def test_no_asked_box_prints_without_an_answer(typed, override, box):
    above, claims, answers = typed
    answer_means_test(above, vehicle_claims=claims, **{**answers, **override})

    # below the gate, which refuses the unanswered line before any box is read
    document = resolve_parts(load_schema("form_122a2"), _fresh(above))
    values = document["parts"][0]["values"]

    assert values.get(box, "") == ""
