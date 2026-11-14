"""Every line of Form 122A-2 follows the form's own arithmetic from the filer's answers and the
official tables, and the result says only what that arithmetic gives."""

import pickle
from dataclasses import replace
from decimal import Decimal

import pytest

from apps.eligibility.means_lines import (
    AT_OR_BELOW_MEDIAN,
    CANNOT_WORK_OUT,
    LINE_KEYS,
    MISSING,
    NO_PRESUMPTION,
    OUTCOMES,
    PRESUMPTION,
    ROW_KEYS,
    SKIPPED,
    HealthInsurance,
    MeansInputs,
    MeansRow,
    MeansTableKeyMissing,
    MeansTables,
    OptIn,
    SecuredDebt,
    Vehicle,
    compare,
    work_out,
)

D = Decimal
LOW, HIGH = D("10275.00"), D("17150.00")

TABLES = MeansTables(
    national=(D("867"), D("1558"), D("1857"), D("2176")),
    national_extra=D("397"),
    health_under_65=D("90"),
    health_65_or_older=D("163"),
    housing={
        "Cook": (
            (D("691"), D("1608")),
            (D("811"), D("1889")),
            (D("855"), D("1990")),
            (D("953"), D("2219")),
            (D("968"), D("2255")),
        ),
        "LaSalle": (
            (D("622"), D("990")),
            (D("730"), D("1163")),
            (D("769"), D("1226")),
            (D("858"), D("1366")),
            (D("871"), D("1389")),
        ),
    },
    areas={"Cook": "chicago", "LaSalle": "midwest"},
    operating={"chicago": (D("334"), D("668")), "midwest": (D("263"), D("526"))},
    ownership_one_car=D("703"),
    public_transport=D("220"),
    multipliers={"ilnd": D("6.9")},
    presumption_low=LOW,
    presumption_high=HIGH,
)

CRV = Vehicle(asset_id=1, name="Honda CR-V EX 2021", financed=True, leased=False, claimed=True)
KESTREL = SecuredDebt(
    debt_id=1,
    creditor="Kestrel Auto Finance",
    asset_id=1,
    on_home=False,
    property="Honda CR-V EX 2021",
    monthly_payment=D("450.00"),
    payments_left=37,
    payment_changes="no",
)
NO = OptIn("no")
PRIYA = MeansInputs(
    line_1=D("13800.00"),
    marital_status="married_together",
    ages=(43, 45, 10, 7),
    county="Cook",
    district="ilnd",
    vehicles=(CRV,),
    secured_debts=(KESTREL,),
    line_35_past_due=D("3000.00"),
    line_41a=D("57000.00"),
    line_3_answer="yes",
    line_3_rows=(("His payroll taxes withheld from his pay", D("250.00")),),
    line_15=NO,
    line_16=D("2300.00"),
    line_17=D("0.00"),
    line_18=D("120.00"),
    line_19=D("0.00"),
    line_20=D("0.00"),
    line_21=D("1200.00"),
    line_22=NO,
    line_23=D("0.00"),
    line_25=HealthInsurance("yes", D("620.00"), D("180.00"), D("0.00"), "yes"),
    line_26=NO,
    line_27=NO,
    line_28=NO,
    line_29=NO,
    line_30=NO,
    line_31=OptIn("yes", D("50.00")),
    line_34_answer="no",
    line_36_answer="yes",
    line_36_payment=D("1400.00"),
    line_43_answer="no",
)

PRIYA_LINES = {
    "1": D("13800.00"),
    "2": "yes",
    "2_filing": "no",
    "3_answer": "yes",
    "3": D("250.00"),
    "4": D("13550.00"),
    "5": 4,
    "6": D("2176.00"),
    "7a": D("90.00"),
    "7b": 4,
    "7c": D("360.00"),
    "7d": D("163.00"),
    "7e": 0,
    "7f": D("0.00"),
    "7g": D("360.00"),
    "8": D("953.00"),
    "9a": D("2219.00"),
    "9b": D("0.00"),
    "9c": D("2219.00"),
    "11": 1,
    "12": D("334.00"),
    "13_vehicle_1": "Honda CR-V EX 2021",
    "13_vehicle_2": SKIPPED,
    "13a": D("703.00"),
    "13b": D("277.50"),
    "13c": D("425.50"),
    "13d": SKIPPED,
    "13e": SKIPPED,
    "13f": SKIPPED,
    "14": SKIPPED,
    "15": SKIPPED,
    "16": D("2300.00"),
    "17": D("0.00"),
    "18": D("120.00"),
    "19": D("0.00"),
    "20": D("0.00"),
    "21": D("1200.00"),
    "22": SKIPPED,
    "23": D("0.00"),
    "24": D("10087.50"),
    "25_answer": "yes",
    "25_health": D("620.00"),
    "25_disability": D("180.00"),
    "25_hsa": D("0.00"),
    "25": D("800.00"),
    "25_spends": "yes",
    "25_actual": SKIPPED,
    "26": SKIPPED,
    "27": SKIPPED,
    "28": SKIPPED,
    "29": SKIPPED,
    "30": SKIPPED,
    "31": D("50.00"),
    "32": D("850.00"),
    "33a": D("0.00"),
    "33b": D("277.50"),
    "33c": SKIPPED,
    "33d": D("0.00"),
    "33e": D("277.50"),
    "34_answer": "no",
    "34": SKIPPED,
    "35_answer": "yes",
    "35_total": D("3000.00"),
    "35": D("50.00"),
    "36_answer": "yes",
    "36_payment": D("1400.00"),
    "36_multiplier": D("6.9"),
    "36": D("96.60"),
    "37": D("424.10"),
    "38": D("11361.60"),
    "39a": D("13550.00"),
    "39b": D("11361.60"),
    "39c": D("2188.40"),
    "39d": D("131304.00"),
    "40": "2",
    "41a": SKIPPED,
    "41b": SKIPPED,
    "42": SKIPPED,
    "43": "no",
    "page_1": PRESUMPTION,
}


def figures(inputs):
    """Every line of `inputs` worked out against TABLES."""
    return work_out(inputs, TABLES).lines


def test_priyas_122a2_matches_the_hand_worked_figures():
    lines = work_out(PRIYA, TABLES)
    assert dict(lines.lines) == PRIYA_LINES
    assert lines.rows["3"] == (MeansRow("His payroll taxes withheld from his pay", D("250.00")),)
    assert lines.rows["13b"] == (
        MeansRow("Kestrel Auto Finance", D("277.50"), property="Honda CR-V EX 2021"),
    )
    assert all(lines.rows[key] == () for key in ("9b", "13e", "33d", "34"))
    assert lines.outcome == PRESUMPTION


def test_the_record_holds_every_line_the_form_prints():
    lines = work_out(PRIYA, TABLES)
    assert tuple(lines.lines) == LINE_KEYS
    assert tuple(lines.rows) == ROW_KEYS
    assert len(LINE_KEYS) == 80
    assert set(PRIYA_LINES) == set(LINE_KEYS)


def test_the_outcomes_are_the_four_the_app_shows_in_order():
    assert OUTCOMES == (AT_OR_BELOW_MEDIAN, CANNOT_WORK_OUT, NO_PRESUMPTION, PRESUMPTION)
    assert repr(MISSING) == "MISSING" and repr(SKIPPED) == "SKIPPED"
    assert pickle.loads(pickle.dumps(MISSING)) is MISSING


def test_the_comparison_in_the_band_needs_line_41b():
    with pytest.raises(ValueError):
        compare(D("12000.00"), None, LOW, HIGH)


@pytest.mark.parametrize(
    "line_39d, line_40, outcome",
    [
        (D("10274.99"), "1", NO_PRESUMPTION),
        (D("10275.00"), "On", NO_PRESUMPTION),
        (D("17150.00"), "On", NO_PRESUMPTION),
        (D("17150.01"), "2", PRESUMPTION),
        (D("-1.00"), "1", NO_PRESUMPTION),
    ],
)
def test_the_comparison_follows_the_form_at_each_edge(line_39d, line_40, outcome):
    comparison = compare(line_39d, D("99999.00"), LOW, HIGH)
    assert comparison.line_40 == line_40
    assert comparison.line_42 == ("no" if line_40 == "On" else None)
    assert comparison.outcome == outcome


@pytest.mark.parametrize(
    "line_41b, line_42",
    [(D("12000.00"), "yes"), (D("12000.01"), "no"), (D("11999.99"), "yes")],
)
def test_line_42_ticks_yes_at_and_above_line_41b(line_41b, line_42):
    comparison = compare(D("12000.00"), line_41b, LOW, HIGH)
    assert comparison.line_42 == line_42
    assert comparison.outcome == (PRESUMPTION if line_42 == "yes" else NO_PRESUMPTION)


@pytest.mark.parametrize(
    "line_1, line_39d, line_40, outcome, line_39c",
    [
        (D("11782.84"), D("10274.40"), "1", NO_PRESUMPTION, D("171.24")),
        (D("11782.85"), D("10275.00"), "On", NO_PRESUMPTION, D("171.25")),
        (D("11897.43"), D("17149.80"), "On", PRESUMPTION, D("285.83")),
        (D("11897.44"), D("17150.40"), "2", PRESUMPTION, D("285.84")),
    ],
)
def test_each_band_edge_is_crossed_through_the_forms_arithmetic(
    line_1, line_39d, line_40, outcome, line_39c
):
    lines = work_out(replace(PRIYA, line_1=line_1), TABLES)
    assert lines.lines["39b"] == D("11361.60") and lines.lines["3"] == D("250.00")
    assert lines.lines["39c"] == line_39c
    assert lines.lines["39d"] == line_39d
    assert lines.lines["40"] == line_40
    assert lines.outcome == outcome
    if line_40 == "On":
        assert lines.lines["41b"] == D("14250.00")


def test_each_line_rounds_half_even_and_later_lines_add_the_printed_figures():
    two_debts = tuple(
        replace(
            KESTREL,
            debt_id=number,
            payment_changes="yes",
            total_60_months=D("1.50"),
        )
        for number in (1, 2)
    )
    lines = work_out(replace(PRIYA, secured_debts=two_debts), TABLES)
    assert [row.amount for row in lines.rows["13b"]] == [D("0.02"), D("0.02")]
    assert lines.lines["13b"] == D("0.04")
    assert figures(replace(PRIYA, line_36_payment=D("25.00")))["36"] == D("1.72")
    in_band = figures(replace(PRIYA, line_1=D("11811.60"), line_41a=D("10.10")))
    assert in_band["39d"] == D("12000.00")
    assert in_band["41b"] == D("2.52")


@pytest.mark.parametrize(
    "change, missing",
    [
        ({"line_16": None}, {"16", "24", "38", "39b", "39c", "39d", "40", "page_1"}),
        ({"county": None}, {"8", "9a", "9c", "12", "24"}),
        ({"ages": (43, None, 10, 7)}, {"7b", "7c", "7e", "7f", "7g", "24"}),
        (
            {"vehicles": (replace(CRV, claimed=None),)},
            {"11", "12", "13a", "13b", "13c", "33b", "33d"},
        ),
        (
            {"secured_debts": (replace(KESTREL, payments_left=None),)},
            {"13b", "13c", "33b", "33e", "37"},
        ),
        ({"line_35_past_due": None}, {"35_answer", "35_total", "35", "37"}),
        ({"line_3_answer": None}, {"3_answer", "3", "4", "39a", "39c", "39d"}),
    ],
)
def test_a_missing_input_leaves_its_line_and_the_result_blank(change, missing):
    lines = work_out(replace(PRIYA, **change), TABLES)
    assert missing <= {key for key, value in lines.lines.items() if value is MISSING}
    assert lines.outcome == CANNOT_WORK_OUT


def test_a_row_with_a_missing_average_stays_in_its_list_with_that_amount():
    lines = work_out(replace(PRIYA, secured_debts=(replace(KESTREL, payments_left=None),)), TABLES)
    assert lines.rows["13b"] == (
        MeansRow("Kestrel Auto Finance", MISSING, property="Honda CR-V EX 2021"),
    )


def test_a_household_with_no_people_in_it_is_not_worked_out_from_a_table_column():
    lines = figures(replace(PRIYA, ages=()))
    assert lines["5"] == 0
    assert all(lines[key] is MISSING for key in ("6", "8", "9a", "9c", "24"))


def test_a_mortgage_above_the_housing_standard_floors_9c_at_zero():
    mortgage = SecuredDebt(
        debt_id=2,
        creditor="Demo Mortgage Co",
        asset_id=None,
        on_home=True,
        property="Demo house",
        monthly_payment=D("3000.00"),
        payments_left=60,
        payment_changes="no",
    )
    lines = work_out(replace(PRIYA, secured_debts=(mortgage, KESTREL)), TABLES)
    assert lines.lines["9b"] == D("3000.00") and lines.lines["9c"] == D("0.00")
    assert lines.rows["9b"] == (MeansRow("Demo Mortgage Co", D("3000.00"), property="Demo house"),)
    assert lines.lines["33a"] == D("3000.00")
    assert lines.lines["24"] == D("7868.50") and lines.lines["33e"] == D("3277.50")


def test_a_renter_has_no_9b_rows_and_9c_is_the_standard():
    lines = work_out(PRIYA, TABLES)
    assert lines.rows["9b"] == ()
    assert lines.lines["9b"] == D("0.00") and lines.lines["9c"] == D("2219.00")


def test_with_no_vehicle_line_14_takes_public_transportation_and_12_to_13f_are_skipped():
    lines = figures(replace(PRIYA, vehicles=(), secured_debts=()))
    assert lines["11"] == 0 and lines["14"] == D("220.00") and lines["15"] is SKIPPED
    skipped = ("12", "13_vehicle_1", "13_vehicle_2", "13a", "13b", "13c", "13d", "13e", "13f")
    assert all(lines[key] is SKIPPED for key in skipped)
    assert lines["24"] == D("9548.00")


def test_a_vehicle_owned_outright_and_claimed_takes_line_12_and_no_slot():
    outright = replace(CRV, financed=False, leased=False)
    lines = figures(replace(PRIYA, vehicles=(outright,), secured_debts=()))
    assert lines["11"] == 1 and lines["12"] == D("334.00") and lines["14"] is SKIPPED
    assert lines["13a"] is SKIPPED and lines["13_vehicle_1"] is SKIPPED


def test_a_leased_vehicle_takes_13a_whole_and_its_lease_is_deducted_nowhere():
    leased = replace(CRV, financed=False, leased=True)
    lines = figures(replace(PRIYA, vehicles=(leased,), secured_debts=()))
    assert lines["13a"] == D("703.00") and lines["13b"] == D("0.00")
    assert lines["13c"] == D("703.00")


def three_vehicles(**changes):
    vehicles = tuple(
        replace(CRV, asset_id=number, name=f"Demo vehicle {number}") for number in (1, 2, 3)
    )
    debts = tuple(
        replace(
            KESTREL,
            debt_id=number,
            creditor=f"Demo lender {number}",
            asset_id=number,
            property=f"Demo vehicle {number}",
        )
        for number in (1, 2, 3)
    )
    return replace(PRIYA, vehicles=vehicles, secured_debts=debts, **changes)


def test_a_third_claimed_vehicle_with_a_loan_goes_to_33d_and_line_12_takes_two_cars():
    lines = work_out(three_vehicles(vehicle_choice=(1, 2)), TABLES)
    assert lines.lines["11"] == 3 and lines.lines["12"] == D("668.00")
    assert lines.lines["13_vehicle_1"] == "Demo vehicle 1"
    assert lines.lines["13_vehicle_2"] == "Demo vehicle 2"
    assert [row.label for row in lines.rows["33d"]] == ["Demo lender 3"]
    assert [row.label for row in lines.rows["13e"]] == ["Demo lender 2"]
    assert lines.lines["33d"] == D("277.50")
    assert lines.lines["13d"] == D("703.00") and lines.lines["13f"] == D("425.50")
    assert lines.lines["33c"] == D("277.50")
    assert lines.lines["24"] == D("10847.00") and lines.lines["33e"] == D("832.50")


def test_three_financed_vehicles_with_no_choice_leave_the_slots_missing():
    lines = work_out(three_vehicles(), TABLES)
    assert lines.lines["11"] == 3 and lines.lines["12"] == D("668.00")
    slots = ("13_vehicle_1", "13_vehicle_2", "13a", "13b", "13c", "13d", "13e", "13f", "33d")
    assert all(lines.lines[key] is MISSING for key in slots)
    assert lines.rows["13b"] == () and lines.rows["33d"] == ()
    assert lines.outcome == CANNOT_WORK_OUT


def test_a_household_of_six_adds_two_people_and_takes_the_five_or_more_housing_column():
    lines = figures(replace(PRIYA, ages=(43, 45, 10, 7, 5, 3)))
    assert lines["5"] == 6 and lines["6"] == D("2970.00")
    assert lines["8"] == D("968.00") and lines["9a"] == D("2255.00")


def test_a_person_turning_65_moves_one_person_from_7b_to_7e():
    younger = figures(replace(PRIYA, ages=(64,)))
    older = figures(replace(PRIYA, ages=(65,)))
    assert (younger["7b"], younger["7e"], younger["7f"]) == (1, 0, D("0.00"))
    assert (older["7b"], older["7e"], older["7f"]) == (0, 1, D("163.00"))
    assert older["7c"] == D("0.00")


def test_a_midwest_county_takes_the_midwest_operating_cost():
    assert figures(replace(PRIYA, county="LaSalle"))["12"] == D("263.00")


def test_a_filer_not_married_fills_line_3_with_zero():
    lines = work_out(replace(PRIYA, marital_status="not_married"), TABLES)
    assert lines.lines["2"] == "no"
    assert lines.lines["2_filing"] is SKIPPED and lines.lines["3_answer"] is SKIPPED
    assert lines.lines["3"] == D("0.00") and lines.rows["3"] == ()
    assert lines.lines["4"] == lines.lines["1"]


def test_a_married_filer_living_together_answering_no_fills_line_3_with_zero():
    lines = work_out(replace(PRIYA, line_3_answer="no"), TABLES)
    assert (lines.lines["2"], lines.lines["2_filing"]) == ("yes", "no")
    assert lines.lines["3"] == D("0.00") and lines.rows["3"] == ()


def test_an_unanswered_marriage_leaves_lines_2_to_4_missing():
    lines = figures(replace(PRIYA, marital_status=None))
    assert all(lines[key] is MISSING for key in ("2", "2_filing", "3_answer", "3", "4"))


def test_seven_b_and_seven_e_always_add_up_to_line_5():
    lines = figures(replace(PRIYA, ages=(70, 64, 66, 10)))
    assert lines["7b"] == 2 and lines["7e"] == 2 and lines["7b"] + lines["7e"] == lines["5"]
    assert lines["7c"] == D("180.00") and lines["7f"] == D("326.00")
    assert lines["7g"] == D("506.00")


def test_a_negative_39c_prints_negative_and_reads_as_below_the_lower_figure():
    lines = work_out(replace(PRIYA, line_1=D("5000.00")), TABLES)
    assert lines.lines["39c"] == D("-6611.60") and lines.lines["39d"] == D("-396696.00")
    assert lines.lines["40"] == "1" and lines.outcome == NO_PRESUMPTION


def test_the_middle_band_decides_on_line_42():
    in_band = replace(PRIYA, line_1=D("11811.60"))
    yes = work_out(replace(in_band, line_41a=D("48000.00")), TABLES)
    assert yes.lines["39d"] == D("12000.00") and yes.lines["41b"] == D("12000.00")
    assert (yes.lines["40"], yes.lines["42"], yes.outcome) == ("On", "yes", PRESUMPTION)
    assert yes.lines["page_1"] == PRESUMPTION and yes.lines["43"] == "no"
    no = work_out(replace(in_band, line_41a=D("48000.04")), TABLES)
    assert (no.lines["42"], no.outcome, no.lines["page_1"]) == (
        "no",
        NO_PRESUMPTION,
        NO_PRESUMPTION,
    )
    assert no.lines["43"] is SKIPPED


def test_the_lines_the_form_skips_are_skipped_and_add_zero():
    skipped = work_out(replace(PRIYA, line_35_past_due=D("0.00"), line_36_answer="no"), TABLES)
    assert skipped.lines["34"] is SKIPPED and skipped.lines["34_answer"] == "no"
    assert skipped.lines["35_answer"] == "no"
    assert skipped.lines["35_total"] is SKIPPED and skipped.lines["35"] is SKIPPED
    assert all(skipped.lines[k] is SKIPPED for k in ("36_payment", "36_multiplier", "36"))
    assert skipped.lines["37"] == skipped.lines["33e"] == D("277.50")
    assert all(skipped.lines[key] is SKIPPED for key in ("41a", "41b", "42"))
    below = figures(replace(PRIYA, line_1=D("5000.00")))
    assert below["40"] == "1" and below["43"] is SKIPPED
    assert all(below[key] is SKIPPED for key in ("41a", "41b", "42"))


def test_an_opt_in_adds_its_amount_under_yes_and_nothing_under_no():
    yes = figures(replace(PRIYA, line_27=OptIn("yes", D("10.00"))))
    assert yes["27"] == D("10.00") and yes["32"] == D("860.00")
    assert figures(replace(PRIYA, line_27=None))["27"] is MISSING
    assert figures(replace(PRIYA, line_27=OptIn("yes")))["27"] is MISSING


def test_line_25_declined_is_skipped_and_actual_spending_is_asked_only_under_no():
    declined = figures(replace(PRIYA, line_25=HealthInsurance("no")))
    assert declined["25"] is SKIPPED and declined["25_actual"] is SKIPPED
    assert declined["32"] == D("50.00")
    unanswered = figures(replace(PRIYA, line_25=None))
    assert unanswered["25"] is MISSING and unanswered["32"] is MISSING
    spends_no = HealthInsurance("yes", D("620.00"), D("180.00"), D("0.00"), "no", D("700.00"))
    assert figures(replace(PRIYA, line_25=spends_no))["25_actual"] == D("700.00")
    undecided = HealthInsurance("yes", D("620.00"), D("180.00"), D("0.00"))
    lines = figures(replace(PRIYA, line_25=undecided))
    assert lines["25_spends"] is MISSING and lines["25_actual"] is MISSING
    assert lines["25"] == D("800.00")


def test_line_34_lists_only_debts_necessary_for_support_with_a_cure():
    needed = replace(KESTREL, necessary_for_support="yes", cure=D("600.00"))
    lines = work_out(replace(PRIYA, line_34_answer="yes", secured_debts=(needed,)), TABLES)
    assert lines.rows["34"] == (
        MeansRow(
            "Kestrel Auto Finance",
            D("10.00"),
            property="Honda CR-V EX 2021",
            cure=D("600.00"),
        ),
    )
    assert lines.lines["34"] == D("10.00") and lines.lines["37"] == D("434.10")
    for answer, cure in (("no", D("600.00")), ("yes", D("0.00"))):
        debt = replace(KESTREL, necessary_for_support=answer, cure=cure)
        lines = work_out(replace(PRIYA, line_34_answer="yes", secured_debts=(debt,)), TABLES)
        assert lines.rows["34"] == () and lines.lines["34"] == D("0.00")


def test_line_34_takes_a_home_loan_from_line_33a():
    home = SecuredDebt(
        debt_id=2,
        creditor="Demo Mortgage Co",
        asset_id=None,
        on_home=True,
        property="Demo house",
        monthly_payment=D("900.00"),
        payments_left=60,
        payment_changes="no",
        necessary_for_support="yes",
        cure=D("1200.00"),
    )
    other = replace(KESTREL, asset_id=None, necessary_for_support="yes", cure=D("60.00"), debt_id=3)
    lines = work_out(replace(PRIYA, line_34_answer="yes", secured_debts=(other, home)), TABLES)
    assert [(row.label, row.amount) for row in lines.rows["34"]] == [
        ("Demo Mortgage Co", D("20.00")),
        ("Kestrel Auto Finance", D("1.00")),
    ]
    assert lines.lines["34"] == D("21.00")


def test_line_34_is_missing_while_a_debt_is_unanswered_or_waits_on_the_vehicle_slots():
    unanswered = replace(PRIYA, line_34_answer="yes")
    assert figures(unanswered)["34"] is MISSING
    waiting = replace(three_vehicles(), line_34_answer="yes")
    assert figures(waiting)["34"] is MISSING
    assert figures(replace(PRIYA, line_34_answer=None))["34"] is MISSING


def test_a_payment_that_changes_uses_the_60_month_total():
    changing = replace(KESTREL, payment_changes="yes", total_60_months=D("16650.00"))
    lines = work_out(replace(PRIYA, secured_debts=(changing,)), TABLES)
    assert lines.lines["13b"] == D("277.50")


def test_a_row_with_a_payment_beyond_sixty_months_counts_sixty():
    long_loan = replace(KESTREL, payments_left=84)
    assert figures(replace(PRIYA, secured_debts=(long_loan,)))["13b"] == D("450.00")


def test_a_33d_row_keeps_the_filers_taxes_or_insurance_answer_and_no_answer_stays_blank():
    other = replace(KESTREL, asset_id=None, taxes_or_insurance="yes")
    unanswered = replace(KESTREL, debt_id=2, asset_id=None)
    lines = work_out(replace(PRIYA, secured_debts=(other, unanswered)), TABLES)
    assert [row.flag for row in lines.rows["33d"]] == ["yes", None]
    assert lines.lines["33d"] == D("555.00") and lines.lines["33e"] == D("555.00")


def test_line_43_never_changes_a_box_or_the_outcome():
    yes, no = (work_out(replace(PRIYA, line_43_answer=a), TABLES) for a in ("yes", "no"))
    assert {k: v for k, v in yes.lines.items() if k != "43"} == {
        k: v for k, v in no.lines.items() if k != "43"
    }
    assert yes.outcome == no.outcome == PRESUMPTION
    assert figures(replace(PRIYA, line_43_answer=None))["43"] is MISSING


def test_a_county_the_tables_dont_hold_raises_without_naming_it():
    with pytest.raises(MeansTableKeyMissing) as refused:
        work_out(replace(PRIYA, county="Demo County"), TABLES)
    assert "Demo County" not in str(refused.value)


@pytest.mark.parametrize(
    "change, part",
    [
        ({"housing": {}}, "housing"),
        ({"areas": {}}, "area"),
        ({"operating": {}}, "operating"),
    ],
)
def test_each_missing_table_part_is_named_by_its_part(change, part):
    with pytest.raises(MeansTableKeyMissing) as refused:
        work_out(replace(PRIYA, line_16=None), replace(TABLES, **change))
    assert str(refused.value) == f"The means test tables have no {part} figure for this session."


def test_a_missing_county_never_raises():
    assert figures(replace(PRIYA, county=None))["8"] is MISSING


def test_a_district_with_no_multiplier_raises_only_when_line_36_asks_for_it():
    work_out(replace(PRIYA, district="ilcd", line_36_answer="no"), TABLES)
    with pytest.raises(MeansTableKeyMissing) as refused:
        work_out(replace(PRIYA, district="ilcd"), TABLES)
    assert "ilcd" not in str(refused.value)


def test_an_opt_in_yes_on_line_15_or_22_raises_line_24_by_its_amount():
    base = figures(PRIYA)["24"]
    assert figures(replace(PRIYA, line_15=OptIn("yes", D("40.00"))))["24"] == base + D("40.00")
    assert figures(replace(PRIYA, line_22=OptIn("yes", D("15.00"))))["24"] == base + D("15.00")


def test_every_amount_prints_to_the_cent_and_every_count_is_a_whole_number():
    lines = work_out(PRIYA, TABLES).lines
    for key, value in lines.items():
        if isinstance(value, Decimal) and key != "36_multiplier":
            assert value.as_tuple().exponent == -2, key
    for key in ("5", "7b", "7e", "11"):
        assert type(lines[key]) is int, key


def _health(**changes):
    return replace(PRIYA, line_25=replace(PRIYA.line_25, **changes))


def _with_debt(answer):
    debt = replace(KESTREL, necessary_for_support=answer, cure=D("60.00"))
    return replace(PRIYA, line_34_answer="yes", secured_debts=(debt,))


@pytest.mark.parametrize(
    "build, field",
    [
        (lambda a: replace(PRIYA, line_3_answer=a), "line 3's answer"),
        (lambda a: replace(PRIYA, line_15=OptIn(a)), "line 15's answer"),
        (lambda a: replace(PRIYA, line_22=OptIn(a)), "line 22's answer"),
        (lambda a: replace(PRIYA, line_27=OptIn(a)), "line 27's answer"),
        (lambda a: _health(answer=a), "line 25's answer"),
        (lambda a: _health(actually_spends=a), "line 25's actually-spends answer"),
        (lambda a: replace(PRIYA, line_34_answer=a), "line 34's answer"),
        (lambda a: replace(PRIYA, line_36_answer=a), "line 36's answer"),
        (_with_debt, "necessary_for_support"),
    ],
)
@pytest.mark.parametrize("answer", ["Yes", ""])
def test_a_yes_no_answer_that_is_neither_raises_instead_of_reading_as_no(build, field, answer):
    with pytest.raises(ValueError) as refused:
        work_out(build(answer), TABLES)
    assert str(refused.value) == f"{field} must be yes or no."
    assert "Yes" not in str(refused.value)


def test_the_middle_band_is_decided_once_for_line_40_and_lines_41a_and_41b():
    for line_1, in_band in ((D("11782.84"), False), (D("11782.85"), True)):
        lines = work_out(replace(PRIYA, line_1=line_1), TABLES).lines
        assert (lines["40"] == "On") is in_band
        assert (lines["41b"] is not SKIPPED) is in_band
