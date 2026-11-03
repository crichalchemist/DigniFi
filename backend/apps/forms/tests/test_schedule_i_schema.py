"""Round-trip tests for Schedule I schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.derivations import DERIVATIONS
from apps.forms.services.fill_resolver import resolve
from apps.forms.tests.test_derivations import SPOUSE_AT_HOME as SPOUSE_AT_HOME_ROW
from apps.forms.tests.test_derivations import TEN_SOURCES
from apps.forms.tests.test_form_122a1_schema import (
    LINE_10_SOURCE,
    SPOUSE_WAGES_ONLY,
    answer_income_step,
)
from apps.forms.tests.test_form_122a1_schema import LINE_BY_SOURCE as FORM_122A1_LINE_BY_SOURCE
from apps.intake.models import DebtorInfo, Household, IncomeInfo, IntakeSession, SpouseIncome
from apps.intake.tests.builders import answer_household

User = get_user_model()

# Box → what it prints with TEN_SOURCES (wages 1, overtime 2, tips 4, interest 8,
# pension 16, Social Security 32, unemployment 64, child support 128, alimony 256,
# other 512).
LINE_BY_SOURCE = {
    "Amount 2 Debtor 1": "5.00",  # line 2: wages and tips
    "Amount 3 Debtor 1": "2.00",  # line 3: overtime
    "Amount 8a Debtor 1": "0.00",  # 8a: no business or rental property listed
    "Amount 8b Debtor 1": "8.00",  # 8b: interest and dividends
    "Amount 8c Debtor 1": "384.00",  # 8c: child support and alimony
    "Amount 8d Debtor 1": "64.00",  # 8d: unemployment
    "Amount 8e Debtor 1": "32.00",  # 8e: Social Security
    "Amount 8f Debtor 1": "0.00",  # 8f: assistance answered No
    "Amount 8g Debtor 1": "16.00",  # 8g: pension
    "Other income 8h": "Other income",  # 8h: what the other income is
    "Amount 8h Debtor 1": "512.00",  # 8h: its amount
}
LINE_TOTALS = {
    "Amount 4 Debtor 1": "7.00",  # line 4: line 2 + line 3
    "Amount 4 Debtor 1a": "7.00",  # line 4's copy at the top of page 2
    "Amount 6 Debtor 1": "0.00",  # line 6: every deduction blank but 5a, typed $0
    "Amount 7 Debtor 1": "7.00",  # line 7: line 4 less line 6
    "Amount 9 Debtor 1": "1016.00",  # line 9: 8a + 8b + ... + 8h
}
DEDUCTION_BOXES = tuple(f"Amount 5{x} Debtor 1" for x in "abcdefgh")
NEVER_ASKED = {"Supplemental income date"}  # lines 11 and 13 and the Debtor 2 header are unbound
# Schedule I's combined monthly income and every box that copies it: all ten sources,
# Social Security included (step 2 spec §6.1, C1), 1 + 2 + 4 + ... + 512.
COMBINED_INCOME = {
    ("schedule_i", "Amount 10 Debtor 1"): "1023.00",  # line 10: line 7 + line 9
    (
        "schedule_i",
        "Amount 10",
    ): "1023.00",  # line 10's total: Debtor 1 + a spouse at home, none here
    ("schedule_i", "Amount 12"): "1023.00",  # line 12: line 10 + line 11, never asked
    ("form_106sum", "4"): "1023.00",  # copies Schedule I line 12
    ("schedule_j", "23a"): "1023.00",  # copies Schedule I line 12
    # Current monthly income leaves Social Security (32) out.
    ("form_122a1", "Quest11"): "991.00",  # 122A-1 line 11
    ("form_106sum", "8"): "991.00",  # copies 122A-1 line 11
}
INCOME_LINES = {"Amount 10 Debtor 1", "Amount 10", "Amount 12", *LINE_BY_SOURCE, *LINE_TOTALS}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemasi", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_income(session):
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        middle_name="",
        last_name="Doe",
        ssn="123-45-6789",
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(
        session=session,
        monthly_gross_wages=Decimal("2000.00"),
        marital_status="not_married",
    )
    answer_household(session)
    return session


@pytest.mark.django_db
class TestScheduleISchema:
    def test_resolver_produces_output(self, session_with_income):
        field_map = resolve(load_schema("schedule_i"), session_with_income)
        assert "Bankruptcy District Information" in field_map
        assert "Debtor 1" in field_map
        assert "Jane Doe" in field_map["Debtor 1"]
        assert "Amount 12" in field_map

    def test_each_income_source_prints_on_its_own_line(self, session):
        # A distinct power of two per source, so a box that reads the wrong source, or
        # adds one too many, prints a different figure (step 2 spec §5.5's table, §7.7).
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
        answer_household(session)

        schedule_i = resolve(load_schema("schedule_i"), session)
        form_122a1 = resolve(load_schema("form_122a1"), session)

        assert {box: schedule_i.get(box) for box in LINE_BY_SOURCE} == LINE_BY_SOURCE
        assert {
            box: form_122a1.get(box) for box in FORM_122A1_LINE_BY_SOURCE
        } == FORM_122A1_LINE_BY_SOURCE
        # Social Security is Schedule I income (8e), but never current monthly income.
        assert [box for box, value in schedule_i.items() if value == "32.00"] == [
            "Amount 8e Debtor 1"
        ]
        assert "32.00" not in form_122a1.values()

    def test_lines_4_7_and_9_add_the_lines_the_form_names(self, session):
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
        answer_household(session)

        field_map = resolve(load_schema("schedule_i"), session)

        assert {box: field_map.get(box) for box in LINE_TOTALS} == LINE_TOTALS

    def test_lines_schedule_i_never_asks_about_print_nothing(self, session):
        # A Chapter 13 supplement's date is the one box left that Schedule I never asks.
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
        answer_household(session)

        field_map = resolve(load_schema("schedule_i"), session)

        assert sorted(NEVER_ASKED & field_map.keys()) == []

    def test_combined_monthly_income_counts_social_security_wherever_it_is_copied(self, session):
        # Schedule I line 12 is all of the filer's income; current monthly income is not
        # (11 U.S.C. § 101(10A)(B)). Each form prints the one its line asks for.
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
        answer_household(session)

        forms = {form_type for form_type, _ in COMBINED_INCOME}
        printed = {form_type: resolve(load_schema(form_type), session) for form_type in forms}

        assert {
            (form_type, box): printed[form_type].get(box) for form_type, box in COMBINED_INCOME
        } == COMBINED_INCOME

    @pytest.mark.parametrize("stray_spouse_row", [False, True])
    def test_income_lines_print_blank_with_no_income_row(self, session, stray_spouse_row):
        # A row with nothing given prints 0.00 (§9.6); the Income step's gap refuses those forms
        # before anything prints (CLAUDE.md "Forms need a completed intake").
        if stray_spouse_row:
            SpouseIncome.objects.create(session=session, monthly_gross_wages=Decimal("1800.00"))
        else:
            household = Household(session=session)
            household.store_members([])
            household.save()
        schedule_i = resolve(load_schema("schedule_i"), session)
        assert sorted(INCOME_LINES & schedule_i.keys()) == []
        if not stray_spouse_row:
            # Schedule J needs the household list, which only this variant answered.
            assert resolve(load_schema("schedule_j"), session).get("23a") is None
        if stray_spouse_row:
            assert schedule_i["Bankruptcy District Information"] == "Northern District of Illinois"
            assert (
                sorted(b for b in schedule_i if b.startswith("Amount") or b == "Other income 8h")
                == []
            )

    def test_schedule_i_column_2_prints_the_spouses_income_for_a_spouse_at_home(self, session):
        answer_income_step(
            session, "married_together", SPOUSE_WAGES_ONLY, monthly_gross_wages=Decimal("12000.00")
        )
        schedule_i = resolve(load_schema("schedule_i"), session)
        form_106sum = resolve(load_schema("form_106sum"), session)
        schedule_j = resolve(load_schema("schedule_j"), session)

        wage_boxes = (
            "Amount 2 Debtor 2",
            "Amount 4 Debtor 2",
            "Amount 4 Debtor 2a",
            "Amount 7 Debtor 2",
            "Amount 10 Debtor 2",
        )
        zero_boxes = (
            *(f"Amount {n} Debtor 2" for n in ("3", "8a", "8b", "8c", "8d", "8e", "8f")),
            *(f"Amount {n} Debtor 2" for n in ("8g", "8h", "9", "6")),
            *(f"Amount 5{x} Debtor 2" for x in "abcdefgh"),
        )
        assert {b: schedule_i.get(b) for b in wage_boxes} == dict.fromkeys(wage_boxes, "1800.00")
        assert {b: schedule_i.get(b) for b in zero_boxes} == dict.fromkeys(zero_boxes, "0.00")
        assert schedule_i["Amount 10 Debtor 1"] == "12000.00"
        assert (
            schedule_i["Amount 10"],
            schedule_i["Amount 12"],
            form_106sum["4"],
            schedule_j["23a"],
        ) == ("13800.00",) * 4

    @pytest.mark.parametrize("answer", ["not_married", "married_separately"])
    def test_a_filer_with_no_spouse_at_home_gets_a_blank_column_2(self, session, answer):
        answer_income_step(
            session, answer, SPOUSE_WAGES_ONLY, monthly_gross_wages=Decimal("12000.00")
        )
        field_map = resolve(load_schema("schedule_i"), session)
        assert sorted(b for b in field_map if "Debtor 2" in b) == []
        assert (
            field_map["Amount 10 Debtor 1"],
            field_map["Amount 10"],
            field_map["Amount 12"],
        ) == ("12000.00",) * 3

    @pytest.mark.parametrize("spouse_income", [{"monthly_gross_wages": Decimal("0.00")}, {}])
    def test_a_spouse_at_home_prints_0_00_on_every_asked_line_left_blank(
        self, session, spouse_income
    ):
        # A blank column counts as zero in the total, which still prints (step 2 spec §6.1).
        answer_income_step(
            session,
            "married_together",
            spouse_income,
            monthly_gross_wages=Decimal("12000.00"),
        )
        schedule_i = resolve(load_schema("schedule_i"), session)
        printed = {b: v for b, v in schedule_i.items() if "Debtor 2" in b}
        assert printed and set(printed.values()) == {"0.00"}
        assert (
            schedule_i["Amount 10 Debtor 1"],
            schedule_i["Amount 10"],
            schedule_i["Amount 12"],
        ) == ("12000.00",) * 3
        if not spouse_income:
            return  # a spouse with nothing given has no CMI, so 122A-1 refuses
        assert {"Amount 2 Debtor 2", "Amount 7 Debtor 2", "Amount 8b Debtor 2"} <= printed.keys()
        form_122a1 = resolve(load_schema("form_122a1"), session)
        assert {b: v for b, v in form_122a1.items() if b.startswith("Debto2.")} == {
            **dict.fromkeys(
                [
                    "Debto2.Quest2.0",
                    "Debto2.Quest3",
                    "Debto2.Quest2.2",
                    "Debto2.Quest5A",
                    "Debto2.Quest5B",
                    "Debto2.Quest5C",
                    "Debto2.Quest6A",
                    "Debto2.Quest6B",
                    "Debto2.Quest6C",
                    "Debto2.Quest7",
                    "Debto2.Quest8.0",
                    "Debto2.Quest9",
                    "Debto2.Quest10A",
                    "Debto2.Quest11",
                ],
                "0.00",
            ),
        }

    @pytest.mark.parametrize(
        "answer,filer_other,spouse_other,named",
        [
            ("not_married", "512.00", None, "Other income"),
            ("married_together", "0.00", "50.00", "Other income"),
            ("married_separately", "0.00", "50.00", None),
            ("married_together", "0.00", "0.00", None),
        ],
    )
    def test_line_10s_description_names_other_income_from_either_column(
        self, session, answer, filer_other, spouse_other, named
    ):
        answer_income_step(
            session,
            answer,
            {
                "monthly_gross_wages": Decimal("1.00"),
                "monthly_other_income": None if spouse_other is None else Decimal(spouse_other),
            },
            monthly_gross_wages=Decimal("12000.00"),
            monthly_other_income=Decimal(filer_other),
        )
        form_122a1 = resolve(load_schema("form_122a1"), session)
        schedule_i = resolve(load_schema("schedule_i"), session)
        assert (form_122a1.get(LINE_10_SOURCE), schedule_i.get("Other income 8h")) == (named, named)


# ---------------------------------------------------------------------------
# 3e2 Task 12: deductions, take-home pay, 8a, 8b and 8f (spec §4.4-4.6, §9.1, §9.6, §11)
# ---------------------------------------------------------------------------


def _printed(session, form="schedule_i"):
    return resolve(load_schema(form), session)


def _entry(kind, gross, expenses, current_gross=None, current_expenses=None):
    return {
        "kind": kind,
        "description": kind,
        "gross": gross,
        "expenses": expenses,
        "current_gross": current_gross,
        "current_expenses": current_expenses,
    }


def _filer(session, **amounts):
    IncomeInfo.objects.create(session=session, **amounts)


def _resave(row, **columns):
    for column, value in columns.items():
        setattr(row, column, value)
    row.save()


@pytest.mark.django_db
class TestScheduleIDeductionsAndAssistance:
    def test_take_home_pay_is_gross_less_the_deductions_on_schedule_i_106sum_and_schedule_j(
        self, session
    ):
        _filer(session, monthly_gross_wages=Decimal("3200.00"))
        answer_household(session, payroll_tax=Decimal("400.00"))
        schedule_i = _printed(session)
        assert {b: schedule_i[b] for b in DEDUCTION_BOXES} == {
            "Amount 5a Debtor 1": "400.00",
            **dict.fromkeys(DEDUCTION_BOXES[1:], "0.00"),
        }
        assert (
            schedule_i["Amount 6 Debtor 1"],
            schedule_i["Amount 7 Debtor 1"],
            schedule_i["Amount 10 Debtor 1"],
            schedule_i["Amount 12"],
            _printed(session, "form_106sum")["4"],
            _printed(session, "schedule_j")["23a"],
        ) == ("400.00", "2800.00", "2800.00", "2800.00", "2800.00", "2800.00")

    def test_deductions_larger_than_pay_print_take_home_pay_below_zero(self, session):
        _filer(session, monthly_gross_wages=Decimal("100.00"))
        answer_household(session, payroll_tax=Decimal("150.00"))
        assert _printed(session)["Amount 7 Debtor 1"] == "-50.00"

    def test_other_deductions_are_named_only_while_5h_is_above_zero(self, session):
        _filer(session, monthly_gross_wages=Decimal("1000.00"))
        answer_household(session)
        row = session.income_info
        _resave(row, payroll_other=Decimal("25.00"), payroll_other_specify="Parking")
        assert _printed(session)["Other deductions 5h"] == "Parking"
        _resave(row, payroll_other=Decimal("0.00"))
        assert "Other deductions 5h" not in _printed(session)

    def test_schedule_i_prints_income_that_is_now_different_while_122a1_keeps_the_average(
        self, session
    ):
        _filer(session, monthly_gross_wages=Decimal("3000.00"))
        answer_household(session, income_now_different="yes")
        _resave(session.income_info, current_monthly_gross_wages=Decimal("3600.00"))
        schedule_i = _printed(session)
        assert (
            schedule_i["Amount 2 Debtor 1"],
            schedule_i["Amount 3 Debtor 1"],
            schedule_i["Amount 8b Debtor 1"],
        ) == ("3600.00", "0.00", "0.00")
        form_122a1 = _printed(session, "form_122a1")
        assert (form_122a1["Debto1.Quest2.0"], form_122a1["Debto1.Quest11"]) == (
            "3000.00",
            "3000.00",
        )

    def test_schedule_i_reads_the_averages_when_the_answer_moved_back_to_no(self, session):
        _filer(session, monthly_gross_wages=Decimal("3000.00"))
        answer_household(session, income_now_different="yes")
        _resave(
            session.income_info,
            current_monthly_gross_wages=Decimal("3600.00"),
            income_now_different="no",
        )
        assert _printed(session)["Amount 2 Debtor 1"] == "3000.00"

    def test_8f_prints_cash_and_noncash_assistance_and_never_changes_cmi(self, session):
        _filer(session, monthly_gross_wages=Decimal("3000.00"))
        answer_household(session, assistance_answer="yes")
        _resave(
            session.income_info,
            cash_assistance_kind="TANF",
            cash_assistance_amount=Decimal("200.00"),
            noncash_assistance_kind="SNAP (food stamps)",
            noncash_assistance_value=Decimal("350.00"),
        )
        fm = _printed(session)
        assert (fm["Amount 8f Debtor 1"], fm["Assistance 8f@2:T36"]) == (
            "550.00",
            "TANF; SNAP (food stamps)",
        )
        assert DERIVATIONS["filer_cmi"](session) == "3000.00"
        assert "Assistance 8f" not in fm  # untagged: line 11's widget (T49) is never filled

    def test_an_unknown_noncash_value_prints_blank_with_its_kind(self, session):
        _filer(session, monthly_gross_wages=Decimal("3000.00"))
        answer_household(session, assistance_answer="yes")
        _resave(session.income_info, noncash_assistance_kind="Housing subsidy")
        fm = _printed(session)
        assert "Amount 8f Debtor 1" not in fm
        assert fm["Assistance 8f@2:T36"] == "Housing subsidy"

    def test_a_kind_typed_under_yes_then_answered_no_prints_0_00_and_a_blank_specify(self, session):
        _filer(session, monthly_gross_wages=Decimal("3000.00"))
        answer_household(session, assistance_answer="no")
        _resave(
            session.income_info,
            cash_assistance_kind="TANF",
            cash_assistance_amount=Decimal("200.00"),
        )
        fm = _printed(session)
        assert fm["Amount 8f Debtor 1"] == "0.00"
        assert "Assistance 8f@2:T36" not in fm

    def test_a_business_loss_never_lowers_rental_income_on_8a(self, session):
        _filer(session)
        answer_household(
            session,
            business_and_rental=[
                _entry("business", "600.00", "1100.00"),
                _entry("rental", "900.00", "200.00"),
            ],
        )
        assert _printed(session)["Amount 8a Debtor 1"] == "700.00"

    def test_the_8h_words_follow_the_figures_schedule_i_uses(self, session):
        _filer(session, monthly_other_income=Decimal("0.00"))
        answer_household(session, income_now_different="yes")
        row = session.income_info
        _resave(row, current_monthly_other_income=Decimal("300.00"))
        fm = _printed(session)
        assert (fm["Amount 8h Debtor 1"], fm["Other income 8h"]) == ("300.00", "Other income")
        assert DERIVATIONS["other_income_label"](session) == ""
        _resave(
            row,
            monthly_other_income=Decimal("300.00"),
            current_monthly_other_income=Decimal("0.00"),
        )
        fm = _printed(session)
        assert fm["Amount 8h Debtor 1"] == "0.00"
        assert "Other income 8h" not in fm
        assert DERIVATIONS["other_income_label"](session) == "Other income"

    def test_schedule_i_column_2_prints_the_spouses_deductions_and_take_home_pay(self, session):
        _filer(session, monthly_gross_wages=Decimal("12000.00"))
        answer_household(
            session,
            marital_status="married_together",
            members=[SPOUSE_AT_HOME_ROW],
            spouse_income=SPOUSE_WAGES_ONLY,
            payroll_tax=Decimal("250.00"),
        )
        fm = _printed(session)
        assert (
            fm["Amount 5a Debtor 2"],
            fm["Amount 6 Debtor 2"],
            fm["Amount 7 Debtor 2"],
            fm["Amount 10 Debtor 2"],
        ) == ("250.00", "250.00", "1550.00", "1550.00")

    def test_a_spouse_column_stays_blank_for_a_filer_living_apart(self, session):
        _filer(session, monthly_gross_wages=Decimal("12000.00"))
        answer_household(
            session,
            marital_status="married_separately",
            members=[SPOUSE_AT_HOME_ROW],
            spouse_income=SPOUSE_WAGES_ONLY,
            payroll_tax=Decimal("250.00"),
        )
        _resave(
            session.spouse_income,
            assistance_answer="yes",
            cash_assistance_kind="TANF",
            cash_assistance_amount=Decimal("100.00"),
        )
        fm = _printed(session)
        assert sorted(b for b in fm if "Debtor 2" in b) == []
        assert (
            "Assistance 8f@2:T36" not in fm
        )  # the filer answered No; the spouse's kind isn't read
