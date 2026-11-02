"""Round-trip tests for Form 122A-1 schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District, MedianIncome
from apps.eligibility.cmi import IncomeNotSplit
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.registry import packet
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.tests.test_derivations import SPOUSE_AT_HOME, TEN_SOURCES
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household, answer_income_detail

User = get_user_model()

# Box → what it prints with TEN_SOURCES (wages 1, overtime 2, tips 4, interest 8,
# pension 16, Social Security 32, unemployment 64, child support 128, alimony 256,
# other 512).
LINE_BY_SOURCE = {  # TEN_SOURCES with interest at 8.00, the list answered []
    "Debto1.Quest2.0": "7.00",  # line 2: wages, overtime and tips
    "Debto1.Quest3": "256.00",  # line 3: alimony
    "Debto1.Quest4": "128.00",  # line 4: child support
    "Debto1.Quest5A": "0.00",
    "Debto1.Quest5B": "0.00",
    "Debto1.Quest5C": "0.00",
    "Debto1.Quest6A": "0.00",
    "Debto1.Quest6B": "0.00",
    "Debto1.Quest6C": "0.00",
    "Debto1.Quest7": "8.00",  # line 7: interest, dividends, and royalties
    "Debto1.Quest8.0": "64.00",  # line 8: unemployment
    "Debto1.Quest9": "16.00",  # line 9: pension
    "terrorism If necessary list other sources on a separate page and put the total below 1": (
        "Other income"
    ),  # line 10: the source
    "Debto1.Quest10A": "512.00",  # line 10: its amount
}
NEVER_ASKED = {
    "Debto1.Quest8A",
    "Debto1.Quest10B",
    "Debto1.Quest10C",
    "terrorism If necessary list other sources on a separate page and put the total below 2",
}

# Household rows as stored. Y, Y: lives with the filer, and claimed or supported.
SON_8 = {"relationship": "son", "age": 8, "lives_with_you": True, "claimed_or_supported": True}
DAUGHTER_5 = {
    "relationship": "daughter",
    "age": 5,
    "lives_with_you": True,
    "claimed_or_supported": True,
}
DAUGHTER_19_ELSEWHERE = {  # N, Y
    "relationship": "daughter",
    "age": 19,
    "lives_with_you": False,
    "claimed_or_supported": True,
}
ROOMMATE_29 = {  # Y, N
    "relationship": "roommate",
    "age": 29,
    "lives_with_you": True,
    "claimed_or_supported": False,
}
LINE_10_SOURCE = (
    "terrorism If necessary list other sources on a separate page and put the total below 1"
)
# Priya's spouse (3e1 spec §11): wages, the other nine typed $0.
SPOUSE_WAGES_ONLY = {
    **dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00")),
    "monthly_gross_wages": Decimal("1800.00"),
}


def answer_income_step(session, marital_status, spouse_income=None, **amounts):
    IncomeInfo.objects.create(session=session, **amounts)
    members = [] if marital_status == "not_married" else [SPOUSE_AT_HOME]
    answer_household(
        session, marital_status=marital_status, members=members, spouse_income=spouse_income
    )


def _household_list(session, rows):
    """Replace the session's household list with these rows."""
    session.household.store_members([dict(r) for r in rows])
    session.household.save()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema122a1", password="pass")
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
    IncomeInfo.objects.create(
        session=session,
        monthly_gross_wages=Decimal("2000.00"),
        marital_status="not_married",
    )
    answer_household(session)
    return session


@pytest.fixture
def median_income(session):
    # ILND's 2025 medians, one per household size.
    return MedianIncome.objects.create(
        district=session.district,
        effective_date=date(2025, 11, 1),
        family_size_1=Decimal("71304.00"),
        family_size_2=Decimal("91526.00"),
        family_size_3=Decimal("110712.00"),
        family_size_4=Decimal("134366.00"),
        family_size_5=Decimal("145466.00"),
        family_size_6=Decimal("156566.00"),
        family_size_7=Decimal("167666.00"),
        family_size_8=Decimal("178766.00"),
        family_size_additional=Decimal("11100.00"),
    )


@pytest.mark.django_db
class TestForm122A1Schema:
    def test_schema_loads(self):
        schema = load_schema("form_122a1")
        assert schema.form_type == "form_122a1"

    def test_all_fields_have_valid_source(self):
        schema = load_schema("form_122a1")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, session_with_income):
        field_map = resolve(load_schema("form_122a1"), session_with_income)
        assert "Bankruptcy District Information" in field_map
        assert "12B" in field_map  # annualized CMI

    def test_cmi_calculation(self, session_with_income):
        field_map = resolve(load_schema("form_122a1"), session_with_income)
        # 2000 wages = 2000 CMI, annualized = 24000
        assert field_map["12B"] == "24000.00"

    def test_empty_session_is_asked_for_income_by_source(self, session):
        # Lines 11 to 13 are CMI, and a filer who gave no income has none (spec §5.5).
        with pytest.raises(IncomeNotSplit):
            resolve(load_schema("form_122a1"), session)

    def test_each_income_source_prints_on_the_122a1_line_that_asks_for_it(self, session):
        # A distinct power of two per source, so a box that reads the wrong source, or
        # adds one too many, prints a different figure (step 2 spec §5.5's table).
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
        answer_household(session)

        field_map = resolve(load_schema("form_122a1"), session)

        assert {box: field_map.get(box) for box in LINE_BY_SOURCE} == LINE_BY_SOURCE
        # Social Security is left out of current monthly income, so no line shows it.
        assert "32.00" not in field_map.values()

    def test_lines_122a1_never_asks_print_nothing(self, session):
        # Line 8's second box, line 10's second row and its totals: blank, never 0.00 (B2).
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
        answer_household(session)

        field_map = resolve(load_schema("form_122a1"), session)

        assert sorted(NEVER_ASKED & field_map.keys()) == []

    def test_line_13_counts_the_filer_and_everyone_living_with_them(self, session_with_income):
        # Two children at home count; a daughter of 19 the filer supports elsewhere doesn't.
        # There is no Your Information step, so no old household-size box to read.
        _household_list(session_with_income, [SON_8, DAUGHTER_5, DAUGHTER_19_ELSEWHERE])

        field_map = resolve(load_schema("form_122a1"), session_with_income)

        assert field_map["13B"] == "3"

    def test_line_11_prints_monthly_income_and_only_line_12b_multiplies_it_by_12(self, session):
        # Line 11 adds lines 2-10 for the month in Column A and in the total box, whose
        # second widget is line 12a's copy; line 12b is the year (step 2 spec §6.1, C1).
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
        answer_household(session)

        field_map = resolve(load_schema("form_122a1"), session)

        # Every source but Social Security's 32.00: 1023.00 - 32.00.
        printed = (field_map.get("Debto1.Quest11"), field_map.get("Quest11"), field_map.get("12B"))
        assert printed == ("991.00", "991.00", "11892.00")

    def test_13b_and_13c_read_the_same_count(self, session_with_income, median_income):
        # DIG-51: line 13 must print the median the means test used. The son and the roommate
        # live with the filer, so line 13 is 3; line 5, the son alone, is 2, whose median
        # would be 91,526.00.
        DebtorInfo.objects.create(
            session=session_with_income,
            first_name="Maria",
            last_name="Torres",
            ssn="900-11-0001",  # IRS-reserved range: synthetic
            date_of_birth=date(1988, 6, 15),
            state="IL",
        )
        _household_list(session_with_income, [SON_8, ROOMMATE_29])
        MeansTestCalculator(session_with_income).calculate()

        field_map = resolve(load_schema("form_122a1"), session_with_income)

        printed = (field_map.get("13A"), field_map.get("13B"), field_map.get("13C"))
        assert printed == ("IL", "3", "110712.00")

    def test_line_13_median_and_the_result_wait_for_the_eligibility_check(
        self, session_with_income
    ):
        # Before the means test runs there is no median to print and nothing to compare.
        field_map = resolve(load_schema("form_122a1"), session_with_income)

        assert sorted({"13C", "14a", "CheckBox1"} & field_map.keys()) == []

    @pytest.mark.parametrize(
        "monthly_wages,line_14,page_1,form_122a2_applies",
        [
            # Exactly the median ($71,304 a year) is below it (DIG-136).
            ("5942.00", "/12b less or equal to 13", "/No Abuse", False),
            ("5942.01", "/12b more than 13", "/Presumption of abuse applies", True),
        ],
        ids=["at_the_median", "one_cent_over"],
    )
    def test_the_result_ticks_agree_with_whether_form_122a2_is_in_the_packet(
        self, session, median_income, monthly_wages, line_14, page_1, form_122a2_applies
    ):
        # Line 14 and the page-1 result follow the form's own instruction (Q5, DIG-65), by
        # the one comparison that decides the packet, so they never disagree at the median.
        IncomeInfo.objects.create(
            session=session,
            monthly_gross_wages=Decimal(monthly_wages),
            marital_status="not_married",
        )
        answer_household(session)
        MeansTestCalculator(session).calculate()

        field_map = resolve(load_schema("form_122a1"), session)

        assert (field_map.get("14a"), field_map.get("CheckBox1")) == (line_14, page_1)
        assert ("form_122a2" in packet(session)) is form_122a2_applies

    @pytest.mark.parametrize(
        "answer,line_1,spouse_box",
        [
            ("not_married", "/Not married", None),
            ("married_spouse_filing", "/Maried and filing", None),  # the template's own spelling
            ("married_together", "/Married but not filing", "/together"),
            ("married_separately", "/Married but not filing", "/separately"),
        ],
    )
    def test_line_1_ticks_the_box_for_each_marriage_answer(
        self, session, answer, line_1, spouse_box
    ):
        answer_income_step(
            session,
            answer,
            {"monthly_gross_wages": Decimal("100.00")},
            monthly_gross_wages=Decimal("2000.00"),
        )
        field_map = resolve(load_schema("form_122a1"), session)
        assert (field_map.get("CheckBox3"), field_map.get("CheckBox3A")) == (line_1, spouse_box)

    @pytest.mark.parametrize(
        "answer,column_b,line_11",
        [
            (
                "married_together",
                {
                    "Debto2.Quest2.0": "1800.00",
                    "Debto2.Quest3": "0.00",
                    "Debto2.Quest2.2": "0.00",
                    "Debto2.Quest5A": "0.00",
                    "Debto2.Quest5B": "0.00",
                    "Debto2.Quest5C": "0.00",
                    "Debto2.Quest6A": "0.00",
                    "Debto2.Quest6B": "0.00",
                    "Debto2.Quest6C": "0.00",
                    "Debto2.Quest7": "0.00",
                    "Debto2.Quest8.0": "0.00",
                    "Debto2.Quest9": "0.00",
                    "Debto2.Quest10A": "0.00",
                    "Debto2.Quest11": "1800.00",
                },
                "13800.00",
            ),
            ("married_separately", {}, "12000.00"),
        ],
    )
    def test_column_b_prints_the_spouses_figures_only_for_a_spouse_at_home(
        self, session, answer, column_b, line_11
    ):
        answer_income_step(
            session, answer, SPOUSE_WAGES_ONLY, monthly_gross_wages=Decimal("12000.00")
        )
        field_map = resolve(load_schema("form_122a1"), session)
        assert {b: v for b, v in field_map.items() if b.startswith("Debto2.")} == column_b
        assert (field_map["Debto1.Quest11"], field_map["Quest11"], field_map["12B"]) == (
            "12000.00",
            line_11,
            f"{Decimal(line_11) * 12:.2f}",
        )


def _entry(kind, gross, expenses, current_gross=None, current_expenses=None):
    return {
        "kind": kind,
        "description": kind,
        "gross": gross,
        "expenses": expenses,
        "current_gross": current_gross,
        "current_expenses": current_expenses,
    }


def _zero_filer(session, **amounts):
    """A filer whose ten sources are $0 except these."""
    IncomeInfo.objects.create(
        session=session, **{**dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00")), **amounts}
    )


@pytest.mark.django_db
class TestLines5And6:
    def test_a_gig_drivers_receipts_and_costs_reach_line_5_and_his_cmi_is_the_net(self, session):
        _zero_filer(session)
        answer_household(
            session,
            business_and_rental=[_entry("business", "4200.00", "830.00")],
        )
        fm = resolve(load_schema("form_122a1"), session)
        assert (fm["Debto1.Quest5A"], fm["Debto1.Quest5B"], fm["Debto1.Quest5C"]) == (
            "4200.00",
            "830.00",
            "3370.00",
        )
        assert fm["Debto1.Quest11"] == "3370.00"

    def test_two_businesses_net_against_each_other_on_line_5(self, session):
        _zero_filer(session)
        answer_household(
            session,
            business_and_rental=[
                _entry("business", "1000.00", "0.00"),
                _entry("business", "600.00", "1100.00"),
            ],
        )
        fm = resolve(load_schema("form_122a1"), session)
        assert (fm["Debto1.Quest5A"], fm["Debto1.Quest5B"], fm["Debto1.Quest5C"]) == (
            "1600.00",
            "1100.00",
            "500.00",
        )

    @pytest.mark.parametrize(
        "kind,boxes", [("business", ("5A", "5B", "5C")), ("rental", ("6A", "6B", "6C"))]
    )
    def test_a_net_below_zero_prints_0_00_beside_the_larger_expenses(self, session, kind, boxes):
        _zero_filer(session, monthly_gross_wages=Decimal("700.00"))
        answer_household(session, business_and_rental=[_entry(kind, "300.00", "900.00")])
        fm = resolve(load_schema("form_122a1"), session)
        assert tuple(fm[f"Debto1.Quest{b}"] for b in boxes) == ("300.00", "900.00", "0.00")
        assert fm["Debto1.Quest11"] == "700.00"

    def test_122a1_keeps_the_averages_net_when_the_current_figures_show_a_loss(self, session):
        _zero_filer(session)
        answer_household(
            session,
            income_now_different="yes",
            business_and_rental=[_entry("business", "1000.00", "400.00", "300.00", "900.00")],
        )
        fm = resolve(load_schema("form_122a1"), session)
        assert fm["Debto1.Quest5C"] == "600.00"
        assert resolve(load_schema("schedule_i"), session)["Amount 8a Debtor 1"] == "0.00"

    def test_a_business_loss_never_lowers_rental_income_and_one_persons_never_the_others(
        self, session
    ):
        _zero_filer(session, monthly_gross_wages=Decimal("100.00"))
        answer_household(
            session,
            marital_status="married_together",
            members=[SPOUSE_AT_HOME],
            spouse_income={"monthly_gross_wages": Decimal("0.00")},
            business_and_rental=[
                _entry("business", "600.00", "1100.00"),
                _entry("rental", "900.00", "200.00"),
            ],
        )
        answer_income_detail(
            session.spouse_income,
            business_and_rental=[_entry("business", "2000.00", "500.00")],
        )
        fm = resolve(load_schema("form_122a1"), session)
        assert (fm["Debto1.Quest5C"], fm["Debto1.Quest6C"], fm["Debto2.Quest5C"]) == (
            "0.00",
            "700.00",
            "1500.00",
        )
        assert fm["Debto1.Quest11"] == "800.00"
