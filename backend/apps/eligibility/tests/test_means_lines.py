"""Every line of Form 122A-2 follows the form's own arithmetic from the filer's answers and the
official tables, and the result says only what that arithmetic gives."""

import pickle
from dataclasses import replace
from decimal import Decimal, InvalidOperation, localcontext

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
    debt_lines,
    is_spouse_ref,
    line_30_cap,
    plan_product,
    rebuttal_figure,
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
    five_percent=(D("30"), D("53"), D("64"), D("76")),
    five_percent_extra=D("14"),
    education_per_child=D("214.58"),
    chapter_13_unsecured_limit=D("526700"),
    chapter_13_secured_limit=D("1580125"),
    multipliers={"ilnd": D("6.9")},
    presumption_low=LOW,
    presumption_high=HIGH,
)

CRV = Vehicle(ref="asset-1", name="Honda CR-V EX 2021", leased=False, claimed=True)
KESTREL = SecuredDebt(
    ref="debt-1",
    creditor="Kestrel Auto Finance",
    secured_by="asset-1",
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
    spouse_vehicles_answer="no",
    spouse_loans_answer="no",
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


def test_a_39d_in_none_of_the_bands_raises_instead_of_reading_as_a_presumption():
    # NaN sits below, inside and above no band once InvalidOperation no longer raises
    with localcontext() as context:
        context.traps[InvalidOperation] = False
        with pytest.raises(ValueError) as refused:
            compare(D("NaN"), None, LOW, HIGH)
    assert "NaN" not in str(refused.value)


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
            ref=f"debt-{number}",
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
        (
            {"line_36_answer": None},
            {"36_answer", "36_payment", "36_multiplier", "36", "37", "38", "39d"},
        ),
        ({"line_36_payment": None}, {"36_payment", "36", "37", "39d"}),
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
        ref="debt-2",
        creditor="Demo Mortgage Co",
        secured_by=None,
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
    # TABLES holds 220 with no cents, so only line 14's own rounding prints it to the cent
    assert lines["14"].as_tuple().exponent == -2
    skipped = ("12", "13_vehicle_1", "13_vehicle_2", "13a", "13b", "13c", "13d", "13e", "13f")
    assert all(lines[key] is SKIPPED for key in skipped)
    assert lines["24"] == D("9548.00")


def test_a_vehicle_owned_outright_and_claimed_takes_line_12_and_no_slot():
    lines = figures(replace(PRIYA, vehicles=(CRV,), secured_debts=()))
    assert lines["11"] == 1 and lines["12"] == D("334.00") and lines["14"] is SKIPPED
    assert lines["13a"] is SKIPPED and lines["13_vehicle_1"] is SKIPPED


def test_a_leased_vehicle_takes_13a_whole_and_its_lease_is_deducted_nowhere():
    leased = replace(CRV, leased=True)
    lines = figures(replace(PRIYA, vehicles=(leased,), secured_debts=()))
    assert lines["13a"] == D("703.00") and lines["13b"] == D("0.00")
    assert lines["13c"] == D("703.00")


def three_vehicles(**changes):
    vehicles = tuple(
        replace(CRV, ref=f"asset-{number}", name=f"Demo vehicle {number}") for number in (1, 2, 3)
    )
    debts = tuple(
        replace(
            KESTREL,
            ref=f"debt-{number}",
            creditor=f"Demo lender {number}",
            secured_by=f"asset-{number}",
            property=f"Demo vehicle {number}",
        )
        for number in (1, 2, 3)
    )
    return replace(PRIYA, vehicles=vehicles, secured_debts=debts, **changes)


def test_a_third_claimed_vehicle_with_a_loan_goes_to_33d_and_line_12_takes_two_cars():
    lines = work_out(three_vehicles(vehicle_choice=("asset-1", "asset-2")), TABLES)
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


@pytest.mark.parametrize(
    "choice",
    [("asset-1", "asset-1"), ("asset-1", "asset-99")],
    ids=["one_car_twice", "not_a_candidate"],
)
def test_a_vehicle_choice_of_one_car_twice_or_a_car_not_listed_leaves_the_slots_missing(choice):
    # One car in both slots would take the ownership standard twice and lower 39d
    lines = work_out(three_vehicles(vehicle_choice=choice), TABLES)
    slots = ("13_vehicle_1", "13_vehicle_2", "13a", "13b", "13c", "13d", "13e", "13f", "33d")
    assert all(lines.lines[key] is MISSING for key in slots)
    assert lines.outcome == CANNOT_WORK_OUT


def test_a_vehicle_loan_above_the_ownership_standard_floors_13c_and_13f_at_zero():
    # Unfloored, 13c or 13f would go below zero and line 24 would drop, raising 39d
    big = replace(KESTREL, monthly_payment=D("800.00"), payments_left=60)
    first = figures(replace(PRIYA, secured_debts=(big,)))
    assert (first["13a"], first["13b"], first["13c"]) == (D("703.00"), D("800.00"), D("0.00"))
    assert first["24"] == D("9662.00")

    three = three_vehicles(vehicle_choice=("asset-1", "asset-2"))
    one, two, other = three.secured_debts
    second_big = replace(two, monthly_payment=D("800.00"), payments_left=60)
    second = figures(replace(three, secured_debts=(one, second_big, other)))
    assert (second["13d"], second["13e"], second["13f"]) == (D("703.00"), D("800.00"), D("0.00"))
    assert second["24"] == D("10421.50")


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


LINE_25_KEYS = ("25_answer", "25_health", "25_disability", "25_hsa", "25", "25_spends", "25_actual")


@pytest.mark.parametrize(
    "change, keys",
    [
        *(({f"line_{n}": OptIn(None)}, (str(n),)) for n in (15, 22, 26, 27, 28, 29, 30, 31)),
        ({"line_25": HealthInsurance(None)}, LINE_25_KEYS),
    ],
)
def test_an_opt_in_with_no_answer_leaves_its_line_and_the_result_blank_not_declined(change, keys):
    # Read as declined, the deduction would add zero and raise 39d toward a presumption
    lines = work_out(replace(PRIYA, **change), TABLES)
    assert all(lines.lines[key] is MISSING for key in keys)
    assert lines.outcome == CANNOT_WORK_OUT


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
        ref="debt-2",
        creditor="Demo Mortgage Co",
        secured_by=None,
        on_home=True,
        property="Demo house",
        monthly_payment=D("900.00"),
        payments_left=60,
        payment_changes="no",
        necessary_for_support="yes",
        cure=D("1200.00"),
    )
    other = replace(
        KESTREL, secured_by=None, necessary_for_support="yes", cure=D("60.00"), ref="debt-3"
    )
    car = replace(
        KESTREL,
        creditor="Demo Car Lender",
        necessary_for_support="yes",
        cure=D("120.00"),
        ref="debt-4",
    )
    # Given in neither line 33's order (9b, 13b, then 33d) nor its reverse
    debts = (other, home, car)
    lines = work_out(replace(PRIYA, line_34_answer="yes", secured_debts=debts), TABLES)
    assert [(row.label, row.amount) for row in lines.rows["34"]] == [
        ("Demo Mortgage Co", D("20.00")),
        ("Demo Car Lender", D("2.00")),
        ("Kestrel Auto Finance", D("1.00")),
    ]
    assert lines.lines["34"] == D("23.00")


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
    other = replace(KESTREL, secured_by=None, taxes_or_insurance="yes")
    unanswered = replace(KESTREL, ref="debt-2", secured_by=None)
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
        (
            lambda a: replace(PRIYA, secured_debts=(replace(KESTREL, payment_changes=a),)),
            "payment_changes",
        ),
        (lambda a: replace(PRIYA, line_43_answer=a), "line 43's answer"),
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


@pytest.mark.parametrize(
    ("field", "line", "amount"),
    [
        ("line_17", "17", D("11.11")),
        ("line_19", "19", D("22.22")),
        ("line_20", "20", D("33.33")),
        ("line_23", "23", D("44.44")),
    ],
)
def test_each_of_lines_17_19_20_and_23_adds_its_own_amount_to_line_24(field, line, amount):
    base = figures(PRIYA)["24"]
    lines = figures(replace(PRIYA, **{field: amount}))
    assert lines[line] == amount
    assert lines["24"] == base + amount


def test_no_record_shows_a_creditor_property_county_or_amount_in_a_log_line():
    car = replace(CRV, name="Demo Property Car")
    debt = replace(
        KESTREL,
        creditor="Demo Creditor",
        property="Demo Property Car",
        monthly_payment=D("123456.78"),
    )
    opt_in = OptIn("yes", D("123456.78"))
    health = HealthInsurance("yes", D("123456.78"), D("0.00"), D("0.00"), "yes")
    inputs = replace(PRIYA, vehicles=(car,), secured_debts=(debt,), line_31=opt_in, line_25=health)
    lines = work_out(inputs, TABLES)
    (row,) = lines.rows["13b"]
    assert row.label == "Demo Creditor"

    for record in (car, debt, opt_in, health, inputs, row, lines):
        for text in (repr(record), str(record)):
            for secret in ("Demo Creditor", "Demo Property Car", "Cook", "123456.78"):
                assert secret not in text, type(record).__name__
    assert repr(car) == "Vehicle(ref=asset-1)" and repr(debt) == "SecuredDebt(ref=debt-1)"


@pytest.mark.parametrize(
    "rows",
    [(), (("", D("250.00")),), (("   ", D("250.00")),), (("Demo purpose", None),)],
    ids=["no_row", "no_purpose", "spaces_only_purpose", "no_amount"],
)
def test_a_line_3_yes_with_no_row_or_an_unfinished_row_leaves_line_3_missing(rows):
    lines = work_out(replace(PRIYA, line_3_rows=rows), TABLES)
    assert (lines.lines["3"], lines.outcome) == (MISSING, CANNOT_WORK_OUT)


def test_line_15_above_the_public_transportation_amount_is_held_back_and_at_it_counts():
    assert (
        work_out(replace(PRIYA, line_15=OptIn("yes", D("220.01"))), TABLES).lines["15"] is MISSING
    )
    assert work_out(replace(PRIYA, line_15=OptIn("yes", D("220.00"))), TABLES).lines["15"] == D(
        "220.00"
    )


def test_line_30_above_its_cap_is_held_back_and_at_it_counts():
    # Priya's household of 4: 5% of food and clothing is 76.00
    assert work_out(replace(PRIYA, line_30=OptIn("yes", D("76.01"))), TABLES).lines["30"] is MISSING
    assert work_out(replace(PRIYA, line_30=OptIn("yes", D("76.00"))), TABLES).lines["30"] == D(
        "76.00"
    )


def test_line_30_waits_for_line_5():
    ten = OptIn("yes", D("10.00"))
    assert work_out(replace(PRIYA, ages=None, line_30=ten), TABLES).lines["30"] is MISSING
    # line_30_cap(TABLES, 0) would index five_percent[-1], the four-person figure
    assert work_out(replace(PRIYA, ages=(), line_30=ten), TABLES).lines["30"] is MISSING


def test_line_30s_cap_adds_the_extra_figure_past_four_people():
    assert [line_30_cap(TABLES, n) for n in range(1, 7)] == [
        D("30.00"),
        D("53.00"),
        D("64.00"),
        D("76.00"),
        D("90.00"),
        D("104.00"),
    ]


def test_a_spouses_car_counts_like_the_filers():
    spouses_car = replace(CRV, ref="spouse-1")
    spouses_loan = replace(KESTREL, ref="spouse-1", secured_by="spouse-1")
    as_spouses = work_out(
        replace(
            PRIYA,
            vehicles=(spouses_car,),
            secured_debts=(spouses_loan,),
            spouse_vehicles_answer="yes",
            spouse_loans_answer="yes",
        ),
        TABLES,
    )
    for key in ("11", "12", "13_vehicle_1", "13a", "13b", "13c", "33b", "39d"):
        assert as_spouses.lines[key] == PRIYA_LINES[key], key
    # answered No, with no car of her own, the lines read as a household with no vehicle
    none = work_out(replace(PRIYA, vehicles=(), secured_debts=()), TABLES)
    assert (none.lines["11"], none.lines["14"]) == (0, D("220.00"))


def _spouse_loan(**changes):
    loan = SecuredDebt(
        ref="spouse-1",
        creditor="Demo Spouse Lender",
        secured_by=None,
        on_home=False,
        property="",
        monthly_payment=D("100.00"),
        payments_left=12,
        payment_changes="no",
    )
    return replace(loan, **changes)


def _spouse_has_a_loan(*loans, **changes):
    return replace(
        PRIYA,
        vehicles=(),
        secured_debts=loans,
        spouse_vehicles_answer="no",
        spouse_loans_answer="yes",
        **changes,
    )


def test_a_spouses_home_loan_goes_on_9b():
    home = _spouse_loan(
        on_home=True, property="Demo house", monthly_payment=D("900.00"), payments_left=60
    )
    lines = work_out(_spouse_has_a_loan(home), TABLES)
    assert lines.rows["9b"] == (MeansRow("Demo Spouse Lender", D("900.00"), property="Demo house"),)
    assert lines.lines["9b"] == D("900.00") and lines.lines["33a"] == D("900.00")
    assert lines.rows["33d"] == ()


def test_a_spouses_other_loan_goes_on_33d():
    other = _spouse_loan(taxes_or_insurance="yes")
    lines = work_out(_spouse_has_a_loan(other), TABLES)
    assert lines.rows["33d"] == (
        MeansRow("Demo Spouse Lender", D("20.00"), property="", flag="yes"),
    )
    assert lines.lines["33d"] == D("20.00")
    needed = replace(other, necessary_for_support="yes", cure=D("600.00"))
    lines = work_out(_spouse_has_a_loan(needed, line_34_answer="yes"), TABLES)
    assert [(row.label, row.amount) for row in lines.rows["34"]] == [
        ("Demo Spouse Lender", D("10.00"))
    ]


def test_a_loan_on_a_third_claimed_vehicle_goes_on_33d_and_a_leased_spouse_vehicle_in_a_slot_takes_13a_whole():
    spouses_car = Vehicle(ref="spouse-1", name="Demo spouse car", leased=True, claimed=True)
    third = replace(CRV, ref="asset-3", name="Demo vehicle 3")
    third_loan = replace(
        KESTREL, ref="debt-3", creditor="Demo lender 3", secured_by="asset-3", property=third.name
    )
    inputs = replace(
        PRIYA,
        vehicles=(CRV, spouses_car, third),
        secured_debts=(KESTREL, third_loan),
        vehicle_choice=("asset-1", "spouse-1"),
        spouse_vehicles_answer="yes",
    )
    lines = work_out(inputs, TABLES)
    assert lines.lines["11"] == 3 and lines.lines["12"] == D("668.00")
    assert lines.lines["13_vehicle_2"] == "Demo spouse car"
    assert (lines.lines["13d"], lines.lines["13e"], lines.lines["13f"]) == (
        D("703.00"),
        D("0.00"),
        D("703.00"),
    )
    assert [row.label for row in lines.rows["33d"]] == ["Demo lender 3"]
    assert lines.rows["13e"] == ()


def test_the_spouses_answers_count_only_under_married_together():
    single = replace(PRIYA, marital_status="not_married")
    unanswered = replace(single, spouse_vehicles_answer=None, spouse_loans_answer=None)
    assert dict(work_out(unanswered, TABLES).lines) == dict(work_out(single, TABLES).lines)
    lines = work_out(unanswered, TABLES)
    assert lines.lines["11"] == 1 and lines.lines["13b"] == D("277.50")
    assert lines.outcome == PRESUMPTION


def test_an_unanswered_spouse_question_leaves_what_it_feeds_missing():
    vehicles = work_out(replace(PRIYA, spouse_vehicles_answer=None), TABLES)
    assert all(vehicles.lines[key] is MISSING for key in ("11", "12", "13a", "14", "15"))
    assert vehicles.outcome == CANNOT_WORK_OUT
    asked = replace(PRIYA, line_34_answer="yes")
    other_loan = replace(KESTREL, secured_by=None, necessary_for_support="no")
    for unknown in ({"spouse_loans_answer": None}, {"spouse_loans_answer": "yes"}):
        lines = work_out(replace(asked, **unknown), TABLES)
        assert all(lines.lines[key] is MISSING for key in ("9b", "13b", "33d", "34")), unknown
        assert lines.outcome == CANNOT_WORK_OUT
        # with Priya's car loan alone, that loan waits on the missing slots and holds 33d and 34
        # by itself; a loan on other property waits on nothing but the loans question
        alone = work_out(
            replace(asked, vehicles=(), secured_debts=(other_loan,), **unknown), TABLES
        )
        assert alone.lines["33d"] is MISSING and alone.lines["34"] is MISSING, unknown
        assert alone.outcome == CANNOT_WORK_OUT
    answered_no = work_out(replace(asked, vehicles=(), secured_debts=(other_loan,)), TABLES)
    assert answered_no.lines["33d"] == D("277.50") and answered_no.lines["34"] == D("0.00")


def test_line_34_answered_no_is_skipped_while_the_loans_are_unknown():
    # No means no rows to ask about, so a loan that waits on the spouse's answers holds nothing
    unplaced = _spouse_loan(on_home=True, placed=False)
    for changes in (
        {"spouse_loans_answer": None},
        {"spouse_loans_answer": "yes", "secured_debts": (KESTREL, unplaced)},
    ):
        lines = work_out(replace(PRIYA, line_34_answer="no", **changes), TABLES)
        assert (lines.lines["34_answer"], lines.lines["34"]) == ("no", SKIPPED), changes


def test_a_loan_the_reader_cant_place_leaves_9b_13b_13e_33d_and_34_missing():
    unplaced = _spouse_loan(on_home=True, placed=False)
    inputs = replace(
        PRIYA, secured_debts=(KESTREL, unplaced), spouse_loans_answer="yes", line_34_answer="yes"
    )
    lines = work_out(inputs, TABLES)
    assert all(lines.lines[key] is MISSING for key in ("9b", "13b", "13e", "33d", "34"))
    assert lines.rows["9b"] == () and lines.outcome == CANNOT_WORK_OUT


def _one_car(ref, **debt_changes):
    spouse = is_spouse_ref(ref)
    answer = "yes" if spouse else "no"
    return replace(
        PRIYA,
        vehicles=(replace(CRV, ref=ref),),
        secured_debts=(
            replace(KESTREL, ref=ref if spouse else "debt-1", secured_by=ref, **debt_changes),
        ),
        spouse_vehicles_answer=answer,
        spouse_loans_answer=answer,
    )


@pytest.mark.parametrize("ref", ["asset-1", "spouse-1"])
def test_a_loan_with_nothing_due_takes_no_slot(ref):
    # H57: a car with 0 payments left and no larger final payment has nothing to deduct, so its
    # slot goes to another car and its loan is a 33d row at 0.00
    nothing_due = work_out(_one_car(ref, payments_left=0, payment_changes="no"), TABLES)
    assert nothing_due.lines["13_vehicle_1"] is SKIPPED and nothing_due.lines["13a"] is SKIPPED
    assert [(row.label, row.amount) for row in nothing_due.rows["33d"]] == [
        ("Kestrel Auto Finance", D("0.00"))
    ]
    assert nothing_due.lines["11"] == 1 and nothing_due.lines["12"] == D("334.00")
    larger_last = _one_car(ref, payments_left=0, payment_changes="yes", total_60_months=D("900.00"))
    assert work_out(larger_last, TABLES).lines["13b"] == D("15.00")
    unanswered = work_out(_one_car(ref, payments_left=None, payment_changes="no"), TABLES)
    assert unanswered.lines["13a"] == D("703.00") and unanswered.lines["13b"] is MISSING


def test_debt_lines_names_each_debts_line_and_none_while_it_waits():
    assert debt_lines(PRIYA) == {"debt-1": "13b"}
    home = replace(KESTREL, ref="debt-2", secured_by=None, on_home=True)
    other = replace(KESTREL, ref="debt-3", secured_by=None)
    unplaced = _spouse_loan(placed=False)
    inputs = replace(PRIYA, secured_debts=(KESTREL, home, other), spouse_loans_answer="yes")
    assert debt_lines(replace(inputs, secured_debts=(*inputs.secured_debts, unplaced))) == {
        "debt-1": None,
        "debt-2": "9b",
        "debt-3": "33d",
        "spouse-1": None,
    }
    # the loans question isn't answered by a spouse loan the filer hasn't added, so the car loan
    # still waits, and the home loan and the other loan keep their lines
    assert debt_lines(inputs) == {"debt-1": None, "debt-2": "9b", "debt-3": "33d"}
    waiting = three_vehicles()
    assert debt_lines(waiting) == {"debt-1": None, "debt-2": None, "debt-3": None}
    chosen = replace(waiting, vehicle_choice=("asset-1", "asset-2"))
    assert debt_lines(chosen) == {"debt-1": "13b", "debt-2": "13e", "debt-3": "33d"}
    assert is_spouse_ref("spouse-1") and not is_spouse_ref("asset-1")


def test_the_plan_payments_product_rounds_half_even():
    assert plan_product(D("25.00"), D("6.9")) == D("1.72")
    assert plan_product(D("35.00"), D("6.9")) == D("2.42")
    assert plan_product(D("1400.00"), D("6.9")) == D("96.60")


@pytest.mark.parametrize(
    "line_39c, amounts, figure",
    [
        (D("2188.40"), [D("400.00")], D("107304.00")),
        (D("2188.40"), [D("400.00"), D("250.00")], D("92304.00")),
        (D("2188.40"), [D("0.00"), D("400.00")], D("107304.00")),
        (D("2188.40"), [D("3000.00")], D("-48696.00")),
        (D("-100.00"), [D("50.00")], D("-9000.00")),
    ],
)
def test_the_rebuttal_figure_is_the_arithmetic_with_line_43s_amounts(line_39c, amounts, figure):
    assert rebuttal_figure(line_39c, amounts) == figure
