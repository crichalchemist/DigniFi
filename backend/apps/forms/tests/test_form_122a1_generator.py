"""Tests for Form 122A-1 (Chapter 7 Statement of Current Monthly Income) generator."""

import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District, MedianIncome
from apps.intake.models import DebtInfo, IncomeInfo, IntakeSession
from apps.forms.services.form_122a1_generator import (
    Form122A1Generator,
    MSG_FAIL_ABOVE_MEDIAN,
    MSG_NOT_APPLICABLE,
    MSG_PASS_BELOW_MEDIAN,
    _build_form_122a1_data,
    _calculate_percentage,
    _compute_cmi,
    _compute_debt_classification,
)

User = get_user_model()


# -- Fixtures --

def _create_ilnd_district() -> District:
    """Create ILND district fixture."""
    return District.objects.create(
        code='ilnd',
        name='Northern District of Illinois',
        state='IL',
        court_name='U.S. Bankruptcy Court, Northern District of Illinois',
        pro_se_efiling_allowed=False,
        filing_fee_chapter_7=Decimal('338.00'),
    )


def _create_median_income(district: District) -> MedianIncome:
    """Create ILND 2025 median income fixture."""
    return MedianIncome.objects.create(
        district=district,
        effective_date='2025-01-01',
        family_size_1=Decimal('71304.00'),
        family_size_2=Decimal('88797.00'),
        family_size_3=Decimal('105252.00'),
        family_size_4=Decimal('119868.00'),
        family_size_5=Decimal('133392.00'),
        family_size_6=Decimal('146916.00'),
        family_size_7=Decimal('160440.00'),
        family_size_8=Decimal('178766.00'),
        family_size_additional=Decimal('9900.00'),
    )


def _create_session(user, district: District) -> IntakeSession:
    return IntakeSession.objects.create(user=user, district=district)


def _create_income_info(
    session: IntakeSession,
    monthly_income: list,
    marital_status: str = 'single',
    number_of_dependents: int = 0,
) -> IncomeInfo:
    return IncomeInfo.objects.create(
        session=session,
        marital_status=marital_status,
        number_of_dependents=number_of_dependents,
        monthly_income=monthly_income,
    )


def _create_debt(
    session: IntakeSession,
    amount: Decimal,
    classification: str = 'consumer',
    creditor_name: str = 'Test Creditor',
    debt_type: str = 'credit_card',
) -> DebtInfo:
    return DebtInfo.objects.create(
        session=session,
        creditor_name=creditor_name,
        debt_type=debt_type,
        amount_owed=amount,
        consumer_business_classification=classification,
    )


# -- Pure function tests (no database) --

class TestComputeCMI:
    """Unit tests for the _compute_cmi helper."""

    def test_all_zeros(self):
        assert _compute_cmi([0, 0, 0, 0, 0, 0]) == Decimal('0.00')

    def test_uniform_income(self):
        assert _compute_cmi([5942, 5942, 5942, 5942, 5942, 5942]) == Decimal('5942.00')

    def test_varying_income(self):
        # (3000 + 3200 + 2800 + 3100 + 3000 + 3050) / 6 = 3025.00
        assert _compute_cmi([3000, 3200, 2800, 3100, 3000, 3050]) == Decimal('3025.00')

    def test_empty_list(self):
        assert _compute_cmi([]) == Decimal('0.00')

    def test_rounding(self):
        # 6001 / 6 = 1000.1666... -> 1000.17
        assert _compute_cmi([1000, 1000, 1000, 1000, 1000, 1001]) == Decimal('1000.17')


class TestCalculatePercentage:
    """Unit tests for the _calculate_percentage helper."""

    def test_zero_whole(self):
        assert _calculate_percentage(Decimal('100'), Decimal('0')) == Decimal('0.00')

    def test_full_percentage(self):
        assert _calculate_percentage(Decimal('500'), Decimal('500')) == Decimal('100.00')

    def test_half_percentage(self):
        assert _calculate_percentage(Decimal('250'), Decimal('500')) == Decimal('50.00')


class TestBuildForm122A1Data:
    """Unit tests for the pure _build_form_122a1_data helper."""

    def test_zero_income_below_median(self):
        """$0 income is always below median -> passes."""
        debt_class = {
            'consumer_percentage': Decimal('100.00'),
            'business_percentage': Decimal('0.00'),
            'consumer_total': Decimal('10000.00'),
            'business_total': Decimal('0.00'),
            'grand_total': Decimal('10000.00'),
        }
        result = _build_form_122a1_data(
            debt_classification=debt_class,
            monthly_income=[0, 0, 0, 0, 0, 0],
            household_size=1,
            median_income_annual=Decimal('71304.00'),
        )
        assert result['passes_means_test'] is True
        assert result['below_median'] is True
        assert result['current_monthly_income'] == Decimal('0.00')
        assert result['annualized_income'] == Decimal('0.00')
        assert result['result_message'] == MSG_PASS_BELOW_MEDIAN

    def test_business_debts_not_applicable(self):
        """Primarily business debts -> means test not applicable -> passes."""
        debt_class = {
            'consumer_percentage': Decimal('30.00'),
            'business_percentage': Decimal('70.00'),
            'consumer_total': Decimal('3000.00'),
            'business_total': Decimal('7000.00'),
            'grand_total': Decimal('10000.00'),
        }
        result = _build_form_122a1_data(
            debt_classification=debt_class,
            monthly_income=[10000, 10000, 10000, 10000, 10000, 10000],
            household_size=1,
            median_income_annual=Decimal('71304.00'),
        )
        assert result['is_applicable'] is False
        assert result['passes_means_test'] is True
        assert result['result_message'] == MSG_NOT_APPLICABLE

    def test_above_median_fails(self):
        """Income above median with consumer debts -> fails."""
        debt_class = {
            'consumer_percentage': Decimal('80.00'),
            'business_percentage': Decimal('20.00'),
            'consumer_total': Decimal('8000.00'),
            'business_total': Decimal('2000.00'),
            'grand_total': Decimal('10000.00'),
        }
        # $8000/mo * 12 = $96,000 > $71,304
        result = _build_form_122a1_data(
            debt_classification=debt_class,
            monthly_income=[8000, 8000, 8000, 8000, 8000, 8000],
            household_size=1,
            median_income_annual=Decimal('71304.00'),
        )
        assert result['is_applicable'] is True
        assert result['below_median'] is False
        assert result['passes_means_test'] is False
        assert result['result_message'] == MSG_FAIL_ABOVE_MEDIAN

    def test_annualized_income_calculation(self):
        """Annualized income = CMI * 12."""
        debt_class = {
            'consumer_percentage': Decimal('100.00'),
            'business_percentage': Decimal('0.00'),
            'consumer_total': Decimal('5000.00'),
            'business_total': Decimal('0.00'),
            'grand_total': Decimal('5000.00'),
        }
        result = _build_form_122a1_data(
            debt_classification=debt_class,
            monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
            household_size=1,
            median_income_annual=Decimal('71304.00'),
        )
        assert result['current_monthly_income'] == Decimal('3000.00')
        assert result['annualized_income'] == Decimal('36000.00')

    def test_median_monthly_computed(self):
        """Monthly median = annual median / 12."""
        debt_class = {
            'consumer_percentage': Decimal('100.00'),
            'business_percentage': Decimal('0.00'),
            'consumer_total': Decimal('5000.00'),
            'business_total': Decimal('0.00'),
            'grand_total': Decimal('5000.00'),
        }
        result = _build_form_122a1_data(
            debt_classification=debt_class,
            monthly_income=[0, 0, 0, 0, 0, 0],
            household_size=1,
            median_income_annual=Decimal('71304.00'),
        )
        # 71304 / 12 = 5942.00
        assert result['median_income_monthly'] == Decimal('5942.00')

    def test_exactly_at_median_fails(self):
        """Income exactly at median does NOT pass (must be strictly below)."""
        annual = Decimal('71304.00')
        monthly = (annual / Decimal('12')).quantize(Decimal('0.01'))
        debt_class = {
            'consumer_percentage': Decimal('100.00'),
            'business_percentage': Decimal('0.00'),
            'consumer_total': Decimal('5000.00'),
            'business_total': Decimal('0.00'),
            'grand_total': Decimal('5000.00'),
        }
        result = _build_form_122a1_data(
            debt_classification=debt_class,
            monthly_income=[float(monthly)] * 6,
            household_size=1,
            median_income_annual=annual,
        )
        assert result['passes_means_test'] is False
        assert result['below_median'] is False

    def test_fifty_fifty_debts_means_test_applies(self):
        """Exactly 50% consumer / 50% business -> means test does NOT apply.

        The threshold is >50% consumer. At exactly 50%, consumer debts
        do not exceed business debts, so the means test does not apply.
        """
        debt_class = {
            'consumer_percentage': Decimal('50.00'),
            'business_percentage': Decimal('50.00'),
            'consumer_total': Decimal('5000.00'),
            'business_total': Decimal('5000.00'),
            'grand_total': Decimal('10000.00'),
        }
        result = _build_form_122a1_data(
            debt_classification=debt_class,
            monthly_income=[10000, 10000, 10000, 10000, 10000, 10000],
            household_size=1,
            median_income_annual=Decimal('71304.00'),
        )
        assert result['is_applicable'] is False
        assert result['passes_means_test'] is True


# -- UPL compliance tests --

class TestUPLCompliance:
    """Verify all result messages comply with UPL boundaries."""

    ADVICE_PHRASES = [
        'you should',
        'you qualify',
        'we recommend',
        'you are eligible',
        'i recommend',
        'you must file',
        'you need to file',
    ]

    def test_pass_message_no_advice(self):
        for phrase in self.ADVICE_PHRASES:
            assert phrase not in MSG_PASS_BELOW_MEDIAN.lower()

    def test_not_applicable_message_no_advice(self):
        for phrase in self.ADVICE_PHRASES:
            assert phrase not in MSG_NOT_APPLICABLE.lower()

    def test_fail_message_no_advice(self):
        for phrase in self.ADVICE_PHRASES:
            assert phrase not in MSG_FAIL_ABOVE_MEDIAN.lower()

    def test_pass_message_uses_information_framing(self):
        assert 'based on the information provided' in MSG_PASS_BELOW_MEDIAN.lower()

    def test_not_applicable_message_uses_information_framing(self):
        assert 'based on the information provided' in MSG_NOT_APPLICABLE.lower()

    def test_fail_message_uses_information_framing(self):
        assert 'based on the information provided' in MSG_FAIL_ABOVE_MEDIAN.lower()


# -- Integration tests (database) --

@pytest.mark.django_db
class TestForm122A1Generator:
    """Form 122A-1 generator integration tests."""

    def test_zero_income_passes(self):
        """$0 income across 6 months -> below median -> passes."""
        user = User.objects.create_user(username='test_zero', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session(user, district)
        _create_income_info(session, [0, 0, 0, 0, 0, 0])
        _create_debt(session, Decimal('10000.00'), 'consumer')

        result = Form122A1Generator(session).generate()

        assert result['passes_means_test'] is True
        assert result['below_median'] is True
        assert result['current_monthly_income'] == Decimal('0.00')
        assert result['annualized_income'] == Decimal('0.00')
        assert result['is_applicable'] is True

    def test_primarily_business_debts_not_applicable(self):
        """Over 50% business debts -> means test not applicable -> passes."""
        user = User.objects.create_user(username='test_biz', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session(user, district)
        _create_income_info(session, [10000, 10000, 10000, 10000, 10000, 10000])
        _create_debt(session, Decimal('3000.00'), 'consumer')
        _create_debt(session, Decimal('7000.00'), 'business', creditor_name='Biz Loan')

        result = Form122A1Generator(session).generate()

        assert result['is_applicable'] is False
        assert result['passes_means_test'] is True
        assert result['result_message'] == MSG_NOT_APPLICABLE
        assert result['consumer_debt_percentage'] == Decimal('30.00')
        assert result['business_debt_percentage'] == Decimal('70.00')

    def test_income_above_median_fails(self):
        """Income above median with consumer debts -> fails means test."""
        user = User.objects.create_user(username='test_high', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session(user, district)
        # $8000/mo * 12 = $96,000 > $71,304 median for 1 person
        _create_income_info(session, [8000, 8000, 8000, 8000, 8000, 8000])
        _create_debt(session, Decimal('15000.00'), 'consumer')

        result = Form122A1Generator(session).generate()

        assert result['passes_means_test'] is False
        assert result['below_median'] is False
        assert result['is_applicable'] is True
        assert result['current_monthly_income'] == Decimal('8000.00')
        assert result['annualized_income'] == Decimal('96000.00')

    def test_income_below_median_passes(self):
        """Income below median -> passes means test."""
        user = User.objects.create_user(username='test_low', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session(user, district)
        # $4000/mo * 12 = $48,000 < $71,304
        _create_income_info(session, [4000, 4000, 4000, 4000, 4000, 4000])
        _create_debt(session, Decimal('20000.00'), 'consumer')

        result = Form122A1Generator(session).generate()

        assert result['passes_means_test'] is True
        assert result['below_median'] is True
        assert result['result_message'] == MSG_PASS_BELOW_MEDIAN

    def test_consumer_debt_percentage_calculation(self):
        """Verify consumer/business debt percentage calculation."""
        user = User.objects.create_user(username='test_pct', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session(user, district)
        _create_income_info(session, [3000, 3000, 3000, 3000, 3000, 3000])
        _create_debt(session, Decimal('6000.00'), 'consumer')
        _create_debt(session, Decimal('4000.00'), 'business', creditor_name='Biz')

        result = Form122A1Generator(session).generate()

        assert result['consumer_debt_percentage'] == Decimal('60.00')
        assert result['business_debt_percentage'] == Decimal('40.00')
        assert result['is_applicable'] is True

    def test_missing_income_defaults_to_zeros(self):
        """Session without IncomeInfo returns graceful zero defaults."""
        user = User.objects.create_user(username='test_miss', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session(user, district)
        _create_debt(session, Decimal('5000.00'), 'consumer')

        result = Form122A1Generator(session).generate()

        assert result['current_monthly_income'] == Decimal('0.00')
        assert result['annualized_income'] == Decimal('0.00')
        assert result['monthly_income_history'] == [0, 0, 0, 0, 0, 0]
        assert result['passes_means_test'] is True
        assert result['household_size'] == 1

    def test_no_debts_not_applicable(self):
        """No debts -> 0% consumer -> means test not applicable."""
        user = User.objects.create_user(username='test_nodebt', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session(user, district)
        _create_income_info(session, [5000, 5000, 5000, 5000, 5000, 5000])

        result = Form122A1Generator(session).generate()

        assert result['consumer_debt_percentage'] == Decimal('0.00')
        assert result['is_applicable'] is False
        assert result['passes_means_test'] is True

    def test_household_size_with_dependents(self):
        """Household size includes debtor + spouse + dependents."""
        user = User.objects.create_user(username='test_fam', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session(user, district)
        _create_income_info(
            session,
            [4000, 4000, 4000, 4000, 4000, 4000],
            marital_status='married_joint',
            number_of_dependents=2,
        )
        _create_debt(session, Decimal('10000.00'), 'consumer')

        result = Form122A1Generator(session).generate()

        # 1 (debtor) + 1 (spouse) + 2 (dependents) = 4
        assert result['household_size'] == 4
        # Median for family of 4 = $119,868
        assert result['median_income_annual'] == Decimal('119868.00')
        # $48,000 < $119,868 -> passes
        assert result['passes_means_test'] is True

    def test_missing_median_income_graceful(self):
        """No MedianIncome record -> median defaults to $0 -> fails if has income."""
        user = User.objects.create_user(username='test_nomed', password='test')
        district = _create_ilnd_district()
        # No median income record created
        session = _create_session(user, district)
        _create_income_info(session, [3000, 3000, 3000, 3000, 3000, 3000])
        _create_debt(session, Decimal('5000.00'), 'consumer')

        result = Form122A1Generator(session).generate()

        assert result['median_income_annual'] == Decimal('0.00')
        assert result['median_income_monthly'] == Decimal('0.00')
        # $36,000 >= $0 -> fails (no median data means we cannot confirm below)
        assert result['passes_means_test'] is False

    def test_preview_matches_generate(self):
        """Preview returns identical data to generate."""
        user = User.objects.create_user(username='test_prev', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session(user, district)
        _create_income_info(session, [2000, 2000, 2000, 2000, 2000, 2000])
        _create_debt(session, Decimal('8000.00'), 'consumer')

        generator = Form122A1Generator(session)
        assert generator.preview() == generator.generate()
