"""
Comprehensive tests for MeansTestCalculator service.

Tests cover:
- Below-median income (passes means test)
- Above-median income (outcome cannot_work_out until the 122A-2 answers exist)
- At-median income (edge case: counts as below the median, DIG-136), and CMI rounded to the cent
- All household sizes (1-8), counted from the household list
- No fee-waiver verdict at any income: the result and its details carry none (3f spec §9)
- Missing income_info raises ValueError
- None session raises ValueError
- A total saved before income was stored by source is never read (IncomeNotSplit)
- No sentence in the reply: no message key, and every string is a code, a name or a figure
- Recalculation idempotency (calculate twice, only 1 MeansTest record)
"""

import json
import re
from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.districts.models import District, MedianIncome
from apps.eligibility.cmi import IncomeNotSplit
from apps.eligibility.models import MeansTest
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.registry import (
    PreconditionMissing,
    build_field_values,
    packet,
)
from apps.forms.services.derivations import DERIVATIONS
from apps.intake.models import (
    DebtorInfo,
    ExpenseInfo,
    Household,
    IncomeInfo,
    IntakeSession,
    PetitionAnswers,
    SpouseIncome,
)
from apps.intake.tests.builders import (
    DEBT_NATURE_DEFAULTS,
    answer_household,
    answer_income_detail,
)

User = get_user_model()


@pytest.fixture
def user():
    """Create test user."""
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def district():
    """Create test district with ILND data."""
    return District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court for the Northern District of Illinois",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def median_income(district):
    """
    Create median income record with real ILND 2025 data.

    Family sizes 1-8:
    - 1: $71,304
    - 2: $91,526
    - 3: $110,712
    - 4: $134,366
    - 5: $145,466
    - 6: $156,566
    - 7: $167,666
    - 8: $178,766
    """
    return MedianIncome.objects.create(
        district=district,
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


@pytest.fixture
def session(user, district):
    """Create intake session, whose household list answers that no one else lives there, and
    whose debts are mainly consumer debts with both military questions No (the builders' step 6
    defaults, 4d), so an above-median result here waits on Form 122A-2's answers, not on line 16.
    """
    s = IntakeSession.objects.create(
        user=user,
        district=district,
        status="in_progress",
        current_step=2,
    )
    household = Household(session=s, county="Cook")
    household.store_members([])
    household.save()
    PetitionAnswers.objects.create(session=s, answers=json.dumps(dict(DEBT_NATURE_DEFAULTS)))
    return s


# Household rows as stored: each lives with the filer and is claimed or supported.
CHILD = {"relationship": "son", "age": 8, "lives_with_you": True, "claimed_or_supported": True}
SPOUSE = {
    "relationship": "spouse",
    "age": 40,
    "lives_with_you": True,
    "claimed_or_supported": True,
    "spouse_is_dependent": False,
}


def _income(**fields):
    """An IncomeInfo row with the four 3e2 answers given, so no Income step gap is open."""
    row = IncomeInfo.objects.create(**fields)
    answer_income_detail(row)
    return row


def _household_list(session, rows):
    """Replace the session's household list with these rows."""
    session.household.store_members([dict(r) for r in rows])
    session.household.save()


@pytest.mark.django_db
class TestMeansTestCalculatorInitialization:
    """Tests for MeansTestCalculator initialization and validation."""

    def test_raises_value_error_on_none_session(self):
        """Test that None session raises ValueError."""
        with pytest.raises(ValueError, match="IntakeSession is required"):
            MeansTestCalculator(None)

    def test_raises_value_error_on_missing_income_info(self, session):
        """Test that session without income_info raises ValueError."""
        with pytest.raises(
            ValueError,
            match="IntakeSession must have income_info before calculating means test",
        ):
            MeansTestCalculator(session)

    def test_initializes_successfully_with_income_info(self, session):
        """Test successful initialization with income_info."""
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("5000.00"),
        )

        calculator = MeansTestCalculator(session)
        assert calculator.intake_session == session
        assert calculator.district == session.district


@pytest.mark.django_db
class TestBelowMedianIncomePassesMeansTest:
    """Tests for below-median income scenarios (passes means test)."""

    def test_below_median_single_no_dependents(self, session, median_income):
        """Test single filer, no dependents, below median passes means test."""
        # Median for family size 1: $71,304/year = $5,942/month
        # Below median: $5,000/month
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("5000.00"),
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["passes_means_test"] is True
        assert result["cmi"] == Decimal("5000.00")
        assert result["median_income_threshold"] == Decimal("71304.00")
        assert result["family_size"] == 1

    def test_a_spouse_at_home_counts_in_the_household(self, session, median_income):
        """A filer living with their spouse is a household of two."""
        # Median for family size 2: $91,526/year = $7,627.17/month
        # Below median: $7,000/month, and the spouse typed $0
        _income(
            session=session,
            marital_status="married_together",
            monthly_gross_wages=Decimal("7000.00"),
        )
        answer_income_detail(
            SpouseIncome.objects.create(session=session, monthly_gross_wages=Decimal("0.00"))
        )
        _household_list(session, [SPOUSE])

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["passes_means_test"] is True
        assert result["cmi"] == Decimal("7000.00")
        assert result["median_income_threshold"] == Decimal("91526.00")
        assert result["family_size"] == 2  # Filer + spouse

    def test_two_children_at_home_make_a_household_of_three(self, session, median_income):
        """Two children living with the filer make a household of three."""
        # Median for family size 3: $110,712/year = $9,226/month
        # Below median: $8,500/month
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("8500.00"),
        )
        _household_list(session, [CHILD, CHILD])

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["passes_means_test"] is True
        assert result["cmi"] == Decimal("8500.00")
        assert result["median_income_threshold"] == Decimal("110712.00")
        assert result["family_size"] == 3  # Filer + 2 children


@pytest.mark.django_db
class TestAboveMedianIncomeCannotBeWorkedOutYet:
    """An above-median filer's result is cannot_work_out until the 122A-2 answers exist."""

    def test_above_median_single_filer_is_cannot_work_out_until_the_122a2_answers_exist(
        self, session, median_income
    ):
        """A single filer above the median meets cannot_work_out and no passes/fails verdict."""
        # Median for family size 1: $71,304/year
        # Above median: $80,000/month average
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("80000.00"),
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["outcome"] == "cannot_work_out"
        assert result["passes_means_test"] is None
        assert result["cmi"] == Decimal("80000.00")
        assert result["median_income_threshold"] == Decimal("71304.00")
        assert result["family_size"] == 1
        # It waits on the 122A-2 page's answers (the tables were read), not on Amounts Owed
        assert result["details"]["open_on"] is None
        assert [t["name"] for t in result["details"]["tables"]] == [
            "IRS expense standards",
            "Bankruptcy Code dollar amounts",
        ]

    def test_the_replies_say_when_the_result_waits_on_amounts_owed(self, session, median_income):
        # 4d-R27: the calculate reply carries open_on, "debts" while line 16 is open above the
        # median and null once the result waits on Form 122A-2's own answers.
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("80000.00"),
        )
        assert MeansTestCalculator(session).calculate()["open_on"] is None

        record = session.petition_answers
        record.merge({"debt_nature": None, "disabled_veteran": None, "reservist": None})
        record.save()
        assert "debt_nature" not in record.get_answers()
        waiting = MeansTestCalculator(IntakeSession.objects.get(pk=session.pk)).calculate()

        assert (waiting["outcome"], waiting["open_on"]) == ("cannot_work_out", "debts")

    def test_a_spouse_living_apart_isnt_counted_but_children_at_home_are(
        self, session, median_income
    ):
        """Line 13 counts who lives with the filer: two children at home, not a spouse apart."""
        # Median for family size 3: $110,712/year
        # Above median: $140,000/month
        _income(
            session=session,
            marital_status="married_separately",
            monthly_gross_wages=Decimal("140000.00"),
        )
        spouse_apart = {
            **SPOUSE,
            "lives_with_you": False,
            "claimed_or_supported": False,
            "spouse_is_dependent": False,
        }
        _household_list(session, [spouse_apart, CHILD, CHILD])

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["outcome"] == "cannot_work_out"
        assert result["passes_means_test"] is None
        assert result["cmi"] == Decimal("140000.00")
        assert result["median_income_threshold"] == Decimal("110712.00")
        assert result["family_size"] == 3  # Filer + 2 children at home


@pytest.mark.django_db
class TestAtMedianIncomeEdgeCase:
    """Income exactly at the median counts as below it (DIG-136), in the means test and the
    packet alike: Form 122A-1 line 14a reads "less than or equal to"."""

    def test_filer_exactly_at_median_passes_and_is_told_at_or_below_the_median(
        self, session, median_income
    ):
        # Median for family size 1: $71,304/year
        # At median: $5,942/month annualizes to exactly $71,304/year
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("5942.00"),
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["passes_means_test"] is True
        # § 707(b)(7) reads "equal to or less than": at the median is not above it (W-1)
        assert result["outcome"] == "at_or_below_median"
        assert result["cmi"] == Decimal("5942.00")
        assert result["median_income_threshold"] == Decimal("71304.00")
        assert "form_122a2" not in packet(session)

    def test_one_cent_over_median_is_above_median(self, session, median_income):
        # $5,942.01/month annualizes to $71,304.12/year, over the $71,304 median
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("5942.01"),
        )

        result = MeansTestCalculator(session).calculate()

        assert result["outcome"] == "cannot_work_out"
        assert result["passes_means_test"] is None
        assert "form_122a2" in packet(session)

    def test_fractional_cent_cmi_rounds_before_the_median_comparison(self, session, median_income):
        # Stored amounts are whole cents, so a fraction of a cent can only come from arithmetic
        # on unsaved amounts, as here. Rounded half-even, $5,942.005 is $5,942.00, exactly the
        # median a month. Unrounded it is $71,304.06 a year, and rounded half up $5,942.01:
        # both above the median, while 122A-1 would print $5,942.00. The verdict, the packet
        # and the printed CMI must agree on one figure.
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("5942.005"),
        )

        result = MeansTestCalculator(session).calculate()

        assert result["cmi"] == Decimal("5942.00")
        assert result["passes_means_test"] is True
        assert "form_122a2" not in packet(session)
        assert DERIVATIONS["cmi"](session) == "5942.00"
        assert DERIVATIONS["line12b_annualized_cmi"](session) == "71304.00"


@pytest.mark.django_db
class TestAllHouseholdSizes:
    """The median is looked up by line 13's count: the filer and everyone living with them."""

    @pytest.mark.parametrize(
        "size,median",
        [
            (1, "71304.00"),
            (2, "91526.00"),
            (3, "110712.00"),
            (4, "134366.00"),
            (5, "145466.00"),
            (6, "156566.00"),
            (7, "167666.00"),
            (8, "178766.00"),
        ],
    )
    def test_the_median_is_for_the_filer_and_everyone_living_with_them(
        self, session, median_income, size, median
    ):
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("5000.00"),
        )
        _household_list(session, [CHILD] * (size - 1))

        result = MeansTestCalculator(session).calculate()

        assert (result["family_size"], result["median_income_threshold"]) == (
            size,
            Decimal(median),
        )


@pytest.mark.django_db
class TestNoFeeWaiverVerdict:
    """The means test answers § 707(b) only. Whether the fee is waived is the court's, under
    § 1930(f), and the filing-fee page shows its 150% figure as information (3f spec §6.2, §9).
    The old 60%-of-median flag was never that test, so no income gets a fee-waiver verdict."""

    @pytest.mark.parametrize("wages", ["0.00", "1500.00", "3000.00", "3565.20", "4166.67"])
    def test_no_income_gets_a_fee_waiver_verdict_from_the_means_test(
        self, session, median_income, wages
    ):
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal(wages),
        )
        calculator = MeansTestCalculator(session)

        result = calculator.calculate()

        assert result["cmi"] == Decimal(wages)
        assert result["passes_means_test"] is True  # every figure is under the $5,942 median
        assert "qualifies_for_fee_waiver" not in result
        assert "qualifies_fee_waiver" not in result["details"]
        assert result["outcome"] == "at_or_below_median"
        assert "message" not in result

    def test_a_means_test_row_stores_no_fee_waiver_verdict(self):
        assert "qualifies_for_fee_waiver" not in {f.name for f in MeansTest._meta.get_fields()}


@pytest.mark.django_db
class TestTotalSavedBeforeIncomeBySource:
    """The six-month total saved before step 2 is never read, whatever its shape."""

    @pytest.mark.parametrize(
        "months",
        [[5000] * 6, [5000] * 3, [5000] * 8, [], "not a list"],
        ids=["six_months", "three_months", "eight_months", "empty", "not_a_list"],
    )
    def test_income_not_split_by_source_is_refused(self, session, median_income, months):
        _income(
            session=session,
            marital_status="not_married",
            monthly_income=months if isinstance(months, str) else json.dumps(months),
        )

        calculator = MeansTestCalculator(session)

        with pytest.raises(
            IncomeNotSplit, match="^Enter your income by source on the Income step.$"
        ):
            calculator.calculate()


def _every_string(value):
    """Every string in a reply, keys included, through nested dicts and lists."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _every_string(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _every_string(item)


# What a string in the reply may be: a key, a code, a table name, a date, a URL, an amount
# as a string, the statute citation, or empty.
_ALLOWED_STRINGS = re.compile(
    r"^$|^[a-z0-9_]+$|^-?\d+(\.\d+)?$|^\d{4}-\d{2}-\d{2}([T ][0-9:.+\-Z]+)?$|^https?://\S+$"
)
_TABLE_NAMES_AND_CITATION = {
    "Census median income",
    "IRS expense standards",
    "Bankruptcy Code dollar amounts",
    "11 U.S.C. § 707(b)",
}


@pytest.mark.django_db
class TestTheReplyCarriesNoSentence:
    """No sentence leaves the server (R12): the browser composes the outcome's words, so the
    UPL scan of those words is the frontend's. What the reply holds is codes and figures."""

    @pytest.mark.parametrize("wages", ["5000.00", "80000.00"])
    def test_the_reply_holds_no_message_and_no_sentence(self, session, median_income, wages):
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal(wages),
        )

        result = MeansTestCalculator(session).calculate()

        assert "message" not in result
        for text in _every_string(result):
            assert text in _TABLE_NAMES_AND_CITATION or _ALLOWED_STRINGS.match(text), text
            for phrase in settings.UPL_PROHIBITED_PHRASES:
                assert phrase.lower() not in text.lower()


@pytest.mark.django_db
class TestRecalculationIdempotency:
    """Tests for recalculation idempotency (calculate twice, only 1 MeansTest record)."""

    def test_calculate_twice_creates_only_one_means_test_record(self, session, median_income):
        """Test that calling calculate() twice on same session creates only 1 MeansTest."""
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("5000.00"),
        )

        calculator = MeansTestCalculator(session)

        # First calculation
        result1 = calculator.calculate()
        means_test_id_1 = result1["means_test_id"]

        # Second calculation
        result2 = calculator.calculate()
        means_test_id_2 = result2["means_test_id"]

        # Should be same MeansTest record
        assert means_test_id_1 == means_test_id_2

        # Verify only 1 MeansTest record exists
        assert MeansTest.objects.filter(session=session).count() == 1

    def test_recalculation_updates_existing_means_test(self, session, median_income):
        """Test that recalculation updates existing MeansTest record with new data."""
        income_info = _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("5000.00"),
        )

        calculator = MeansTestCalculator(session)

        # First calculation: below median
        result1 = calculator.calculate()
        assert result1["passes_means_test"] is True

        # Update income to above median
        income_info.monthly_gross_wages = Decimal("80000.00")
        income_info.save()

        # Recalculate with new data
        result2 = calculator.calculate()

        # Still above the median: cannot_work_out, no passes/fails verdict
        assert result2["outcome"] == "cannot_work_out"
        assert result2["passes_means_test"] is None
        assert result2["cmi"] == Decimal("80000.00")

        # Still only 1 MeansTest record
        assert MeansTest.objects.filter(session=session).count() == 1

    def test_recalculation_updates_district_if_changed(self, session, median_income):
        """Test that recalculation updates district if session district changes."""
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("5000.00"),
        )

        calculator = MeansTestCalculator(session)

        # First calculation
        calculator.calculate()

        # Create new district and update session
        new_district = District.objects.create(
            code="ilcd",
            name="Central District of Illinois",
            state="IL",
            court_name="U.S. Bankruptcy Court for the Central District of Illinois",
            filing_fee_chapter_7=Decimal("338.00"),
        )

        # Create median income for new district
        MedianIncome.objects.create(
            district=new_district,
            effective_date=date(2025, 11, 1),
            family_size_1=Decimal("65000.00"),  # Different median
            family_size_2=Decimal("85000.00"),
            family_size_3=Decimal("100000.00"),
            family_size_4=Decimal("120000.00"),
            family_size_5=Decimal("130000.00"),
            family_size_6=Decimal("140000.00"),
            family_size_7=Decimal("150000.00"),
            family_size_8=Decimal("160000.00"),
            family_size_additional=Decimal("10000.00"),
        )

        session.district = new_district
        session.save()

        # Recalculate with new district
        calculator2 = MeansTestCalculator(session)
        result2 = calculator2.calculate()

        # Should use new district's median
        assert result2["median_income_threshold"] == Decimal("65000.00")

        # Still only 1 MeansTest record
        assert MeansTest.objects.filter(session=session).count() == 1

        # MeansTest should reference new district
        means_test = MeansTest.objects.get(session=session)
        assert means_test.district == new_district


@pytest.mark.django_db
class TestIncomeFromSeveralSources:
    """CMI adds up every source the filer gave on the Income step."""

    def test_cmi_adds_every_source_the_filer_gave(self, session, median_income):
        # 3000 + 1000 + 1000 = 5000: below the $5,942/month median for one person
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("3000.00"),
            monthly_pension=Decimal("1000.00"),
            monthly_child_support=Decimal("1000.00"),
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["cmi"] == Decimal("5000.00")
        assert result["passes_means_test"] is True


@pytest.mark.django_db
class TestAnnualizedComparison:
    """CMI is monthly; the Census median is annual (11 U.S.C. § 707(b)(7)).

    Regression: the comparison must annualize CMI. Under the old monthly-vs-
    annual comparison, a $10,000/month filer "passed" against a $71,304/year
    median.
    """

    def test_high_monthly_income_is_above_median_after_annualization(self, session, median_income):
        # $10,000/month = $120,000/year > $71,304 median for family of 1
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("10000.00"),
        )

        result = MeansTestCalculator(session).calculate()

        assert result["outcome"] == "cannot_work_out"
        assert result["passes_means_test"] is None
        assert result["details"]["annualized_cmi"] == 120000.00


@pytest.mark.django_db
class TestTheOldHouseholdSizeBox:
    """Step 1's old household-size box is no longer read: the household list sizes the
    median (3e1 spec §4.3)."""

    def test_a_stored_household_size_of_4_is_no_longer_read(self, session, median_income):
        DebtorInfo.objects.create(
            session=session,
            first_name="Test",
            last_name="User",
            ssn="900112222",
            date_of_birth=date(1990, 1, 1),
            phone="3125550142",
            email="test@example.com",
            street_address="1 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
            household_size=4,
        )
        # The household list says no one else lives there: the fixture's []
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal("9000.00"),
        )

        result = MeansTestCalculator(session).calculate()

        # $108,000/year: below the family-of-4 median ($134,366) the old box would have
        # looked up, but above the family-of-1 median ($71,304) the list gives
        assert result["family_size"] == 1
        assert result["median_income_threshold"] == Decimal("71304.00")
        assert result["outcome"] == "cannot_work_out"
        assert result["passes_means_test"] is None


@pytest.fixture
def session_with_above_median_income(user, district, median_income):
    """Create a session with above-median income, whose result is cannot_work_out."""
    s = IntakeSession.objects.create(
        user=user,
        district=district,
        status="in_progress",
        current_step=2,
    )
    DebtorInfo.objects.create(
        session=s,
        first_name="Above",
        last_name="Median",
        ssn="123456789",
        date_of_birth=date(1990, 1, 1),
        phone="3125550001",
        email="above@example.com",
        street_address="1 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
        household_size=1,
    )
    _income(
        session=s,
        marital_status="not_married",
        monthly_gross_wages=Decimal("7000.00"),
    )
    answer_household(s)
    return s


@pytest.mark.django_db
class TestRecalculatingAcrossTheMedian:
    """DIG-128: a recalculation at or below the median replaces an earlier cannot_work_out result."""

    def test_recalculating_below_the_median_gives_at_or_below_median(
        self, session_with_above_median_income
    ):
        session = session_with_above_median_income
        first = MeansTestCalculator(session).calculate()
        assert (first["outcome"], first["passes_means_test"]) == ("cannot_work_out", None)

        session.income_info.monthly_gross_wages = Decimal("5000.00")
        session.income_info.save()
        second = MeansTestCalculator(session).calculate()

        stored = MeansTest.objects.get(session=session)
        assert (second["outcome"], second["details"]["tables"]) == ("at_or_below_median", [])
        assert (stored.outcome, stored.passes_means_test) == ("at_or_below_median", True)


@pytest.mark.django_db
class TestAboveMedianEndToEnd:
    def test_above_median_full_flow(self):
        """Above-median filer: CMI → deductions → disposable → 122A-2 refuses (the hold)."""
        user = User.objects.create_user(username="e2e_above", password="pass")
        district = District.objects.create(
            code="ILND",
            name="Northern District of Illinois",
            state="IL",
            court_name="U.S. Bankruptcy Court",
            filing_fee_chapter_7=Decimal("338"),
        )
        MedianIncome.objects.create(
            district=district,
            effective_date=date(2025, 1, 1),
            family_size_1=Decimal("55000"),
            family_size_2=Decimal("65000"),
            family_size_3=Decimal("75000"),
            family_size_4=Decimal("85000"),
            family_size_5=Decimal("95000"),
            family_size_6=Decimal("105000"),
            family_size_7=Decimal("115000"),
            family_size_8=Decimal("125000"),
            family_size_additional=Decimal("11100"),
        )
        session = IntakeSession.objects.create(user=user, district=district)
        DebtorInfo.objects.create(
            session=session,
            first_name="Above",
            middle_name="",
            last_name="Median",
            ssn="987-65-4321",
            date_of_birth=date(1985, 1, 1),
            phone="312-555-0100",
            email="above@test.com",
            street_address="456 Oak Ave",
            city="Chicago",
            state="IL",
            zip_code="60601",
            household_size=1,
        )
        _income(
            session=session,
            monthly_gross_wages=Decimal("6000.00"),
            marital_status="not_married",
        )
        answer_household(session)
        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal("1500"),
            utilities=Decimal("200"),
            food_and_groceries=Decimal("400"),
        )

        result = MeansTestCalculator(session).calculate()
        assert result["outcome"] == "cannot_work_out"
        assert result["passes_means_test"] is None

        with pytest.raises(
            PreconditionMissing,
            match=re.escape("Enter the amount for line 16. Enter 0 if you have none."),
        ):
            build_field_values("form_122a2", session)


@pytest.mark.django_db
def test_calculation_details_store_the_floored_nets_cmi_added(session, median_income):
    row = _income(
        session=session,
        monthly_gross_wages=Decimal("2000.00"),
        marital_status="not_married",
    )
    answer_household(session)
    row.store_entries(
        [
            {"kind": "business", "description": "Shop", "gross": "500.00", "expenses": "900.00"},
            {"kind": "rental", "description": "Duplex", "gross": "1200.00", "expenses": "200.00"},
        ]
    )
    row.save()

    MeansTestCalculator(session).calculate()

    details = MeansTest.objects.get(session=session).get_calculation_details()
    assert details["business_net"] == "0.00"
    assert details["rental_net"] == "1000.00"
    assert details["spouse_business_net"] is None
    assert details["spouse_rental_net"] is None
    assert details["cmi"] == 3000.0
