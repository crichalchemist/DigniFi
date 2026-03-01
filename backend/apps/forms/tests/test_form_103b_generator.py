"""Tests for Form 103B (Application to Have the Chapter 7 Filing Fee Waived) generator."""

import pytest
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    FeeWaiverApplication,
    IntakeSession,
)
from apps.forms.services.form_103b_generator import (
    Form103BGenerator,
    Form103BGenerationError,
    _build_debtor_name,
    _build_form_103b_data,
    _compute_cash_and_bank_balances,
    _compute_total_debt,
    _compute_total_property_value,
    _determine_qualification_basis,
    _get_result_message,
    BASIS_BENEFITS,
    BASIS_INCOME,
    BASIS_NONE,
    MSG_QUALIFIES_BENEFITS,
    MSG_QUALIFIES_INCOME,
)

User = get_user_model()


# -- Lightweight stubs for pure function tests (no DB) --


@dataclass(frozen=True)
class _StubDebtorInfo:
    first_name: str
    middle_name: str
    last_name: str


@dataclass(frozen=True)
class _StubAsset:
    asset_type: str
    current_value: Decimal


@dataclass(frozen=True)
class _StubDebt:
    amount_owed: Decimal


@dataclass(frozen=True)
class _StubFeeWaiver:
    """Minimal stub matching FeeWaiverApplication interface for pure tests."""
    monthly_income: Decimal
    receives_public_benefits: bool
    household_size: int = 1

    # HHS poverty guidelines constants (mirrored from model)
    POVERTY_BASE_2024 = Decimal('15060')
    POVERTY_INCREMENT = Decimal('5380')
    POVERTY_MULTIPLIER = Decimal('1.5')
    MONTHS_PER_YEAR = Decimal('12')

    def get_poverty_threshold(self) -> Decimal:
        annual = self.POVERTY_BASE_2024 + (self.POVERTY_INCREMENT * (self.household_size - 1))
        return (annual * self.POVERTY_MULTIPLIER) / self.MONTHS_PER_YEAR


# -- DB fixture helpers --


def _create_ilnd_district() -> District:
    """Create ILND district fixture for tests."""
    return District.objects.create(
        code='ilnd',
        name='Northern District of Illinois',
        state='IL',
        court_name='U.S. Bankruptcy Court, Northern District of Illinois',
        pro_se_efiling_allowed=False,
        filing_fee_chapter_7=Decimal('338.00'),
    )


def _create_session(user, district: District) -> IntakeSession:
    return IntakeSession.objects.create(user=user, district=district)


def _create_debtor_info(
    session: IntakeSession,
    first_name: str = 'Jane',
    middle_name: str = '',
    last_name: str = 'Doe',
) -> DebtorInfo:
    return DebtorInfo.objects.create(
        session=session,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        ssn='123456789',
        date_of_birth=date(1990, 1, 15),
        phone='312-555-0100',
        email='jane.doe@example.com',
        street_address='123 Main St',
        city='Chicago',
        state='IL',
        zip_code='60601',
    )


def _create_fee_waiver(
    session: IntakeSession,
    monthly_income: Decimal = Decimal('0.00'),
    monthly_expenses: Decimal = Decimal('850.00'),
    household_size: int = 1,
    receives_public_benefits: bool = False,
    benefit_types: Optional[list[str]] = None,
) -> FeeWaiverApplication:
    return FeeWaiverApplication.objects.create(
        session=session,
        household_size=household_size,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        receives_public_benefits=receives_public_benefits,
        benefit_types=benefit_types or [],
        cannot_pay_full=True,
        cannot_pay_installments=True,
    )


def _create_asset(
    session: IntakeSession,
    asset_type: str = 'bank_account',
    description: str = 'Checking account',
    current_value: Decimal = Decimal('150.00'),
    amount_owed: Decimal = Decimal('0.00'),
) -> AssetInfo:
    return AssetInfo.objects.create(
        session=session,
        asset_type=asset_type,
        description=description,
        current_value=current_value,
        amount_owed=amount_owed,
    )


def _create_debt(
    session: IntakeSession,
    creditor_name: str = 'Medical Center',
    amount_owed: Decimal = Decimal('5000.00'),
    debt_type: str = 'medical',
) -> DebtInfo:
    return DebtInfo.objects.create(
        session=session,
        creditor_name=creditor_name,
        amount_owed=amount_owed,
        debt_type=debt_type,
    )


# ============================================================
# Pure function tests (no DB)
# ============================================================


class TestBuildDebtorName:
    """Unit tests for _build_debtor_name."""

    def test_first_and_last_only(self):
        stub = _StubDebtorInfo('Jane', '', 'Doe')
        assert _build_debtor_name(stub) == 'Jane Doe'

    def test_with_middle_name(self):
        stub = _StubDebtorInfo('Jane', 'Marie', 'Doe')
        assert _build_debtor_name(stub) == 'Jane Marie Doe'

    def test_all_empty(self):
        stub = _StubDebtorInfo('', '', '')
        assert _build_debtor_name(stub) == ''


class TestComputeCashAndBankBalances:
    """Unit tests for _compute_cash_and_bank_balances."""

    def test_bank_accounts_only(self):
        """Only bank_account type assets are summed."""
        assets = [
            _StubAsset('bank_account', Decimal('100.00')),
            _StubAsset('vehicle', Decimal('5000.00')),
            _StubAsset('bank_account', Decimal('50.00')),
        ]
        assert _compute_cash_and_bank_balances(assets) == Decimal('150.00')

    def test_no_bank_accounts(self):
        """Non-bank assets contribute zero to bank balances."""
        assets = [
            _StubAsset('vehicle', Decimal('5000.00')),
            _StubAsset('real_property', Decimal('100000.00')),
        ]
        assert _compute_cash_and_bank_balances(assets) == Decimal('0.00')

    def test_empty_list(self):
        assert _compute_cash_and_bank_balances([]) == Decimal('0.00')


class TestComputeTotalPropertyValue:
    """Unit tests for _compute_total_property_value."""

    def test_sums_all_assets(self):
        assets = [
            _StubAsset('bank_account', Decimal('150.00')),
            _StubAsset('vehicle', Decimal('3000.00')),
        ]
        assert _compute_total_property_value(assets) == Decimal('3150.00')

    def test_empty_list(self):
        assert _compute_total_property_value([]) == Decimal('0.00')


class TestComputeTotalDebt:
    """Unit tests for _compute_total_debt."""

    def test_sums_all_debts(self):
        debts = [
            _StubDebt(Decimal('5000.00')),
            _StubDebt(Decimal('10000.00')),
            _StubDebt(Decimal('30000.00')),
        ]
        assert _compute_total_debt(debts) == Decimal('45000.00')

    def test_empty_list(self):
        assert _compute_total_debt([]) == Decimal('0.00')


class TestDetermineQualificationBasis:
    """Unit tests for _determine_qualification_basis."""

    def test_benefits_path(self):
        """Public benefits qualification takes precedence."""
        stub = _StubFeeWaiver(
            monthly_income=Decimal('5000.00'),  # Above poverty line
            receives_public_benefits=True,
        )
        assert _determine_qualification_basis(stub) == BASIS_BENEFITS

    def test_income_path_zero_income(self):
        """$0 income is well below 150% poverty line."""
        stub = _StubFeeWaiver(
            monthly_income=Decimal('0.00'),
            receives_public_benefits=False,
        )
        assert _determine_qualification_basis(stub) == BASIS_INCOME

    def test_income_path_below_threshold(self):
        """Income just below threshold qualifies."""
        stub = _StubFeeWaiver(
            monthly_income=Decimal('1882.00'),  # Just under $1882.50
            receives_public_benefits=False,
        )
        assert _determine_qualification_basis(stub) == BASIS_INCOME

    def test_none_path_above_threshold(self):
        """Income above 150% poverty line, no benefits → does not qualify."""
        stub = _StubFeeWaiver(
            monthly_income=Decimal('3000.00'),
            receives_public_benefits=False,
        )
        assert _determine_qualification_basis(stub) == BASIS_NONE

    def test_income_at_exact_threshold_does_not_qualify(self):
        """Income AT exactly 150% poverty line does NOT qualify (must be below)."""
        # 150% of $15,060 / 12 = $1,882.50 for household of 1
        stub = _StubFeeWaiver(
            monthly_income=Decimal('1882.50'),
            receives_public_benefits=False,
        )
        assert _determine_qualification_basis(stub) == BASIS_NONE


class TestGetResultMessage:
    """Unit tests for _get_result_message."""

    def test_income_message(self):
        msg = _get_result_message(BASIS_INCOME, Decimal('338.00'))
        assert msg == MSG_QUALIFIES_INCOME
        assert 'below 150%' in msg

    def test_benefits_message(self):
        msg = _get_result_message(BASIS_BENEFITS, Decimal('338.00'))
        assert msg == MSG_QUALIFIES_BENEFITS
        assert 'means-tested' in msg

    def test_none_message_includes_fee(self):
        msg = _get_result_message(BASIS_NONE, Decimal('338.00'))
        assert '338.00' in msg
        assert 'installment payments' in msg


class TestBuildForm103bData:
    """Unit tests for _build_form_103b_data pure function."""

    def _make_data(self, **overrides) -> dict[str, any]:
        """Build form data with sensible defaults."""
        defaults = {
            'debtor_name': 'Jane Doe',
            'household_size': 1,
            'monthly_income': Decimal('0.00'),
            'monthly_expenses': Decimal('850.00'),
            'cash_and_bank_balances': Decimal('150.00'),
            'total_property_value': Decimal('2500.00'),
            'total_debt': Decimal('45000.00'),
            'owns_property': True,
            'receives_benefits_or_disability': False,
            'receives_public_benefits': False,
            'benefit_types': [],
            'qualifies_for_waiver': True,
            'qualification_basis': BASIS_INCOME,
            'poverty_threshold_monthly': Decimal('1882.50'),
            'filing_fee': Decimal('338.00'),
            'result_message': MSG_QUALIFIES_INCOME,
            'signature_date': '2026-02-24',
        }
        defaults.update(overrides)
        return _build_form_103b_data(**defaults)

    def test_returns_all_expected_keys(self):
        """Form data contains every required field."""
        data = self._make_data()
        expected_keys = {
            'form_type', 'debtor_name', 'case_number',
            'household_size', 'monthly_income', 'monthly_expenses',
            'net_monthly_income',
            'cash_and_bank_balances', 'total_property_value', 'total_debt',
            'received_money_6_months', 'owns_property',
            'receives_benefits_or_disability',
            'receives_public_benefits', 'benefit_types',
            'penalty_of_perjury', 'signature_date',
            'qualifies_for_waiver', 'qualification_basis',
            'poverty_threshold_monthly', 'filing_fee',
            'result_message',
        }
        assert expected_keys == set(data.keys())

    def test_form_type(self):
        data = self._make_data()
        assert data['form_type'] == 'form_103b'

    def test_net_monthly_income_computed(self):
        """Net income = income - expenses."""
        data = self._make_data(
            monthly_income=Decimal('0.00'),
            monthly_expenses=Decimal('850.00'),
        )
        assert data['net_monthly_income'] == Decimal('-850.00')

    def test_case_number_empty(self):
        data = self._make_data()
        assert data['case_number'] == ''

    def test_penalty_of_perjury_always_true(self):
        data = self._make_data()
        assert data['penalty_of_perjury'] is True

    def test_benefit_types_copied(self):
        """Benefit types list is copied (not a reference to mutable input)."""
        original = ['SNAP', 'Medicaid']
        data = self._make_data(benefit_types=original)
        assert data['benefit_types'] == ['SNAP', 'Medicaid']
        assert data['benefit_types'] is not original


# ============================================================
# Integration tests (database)
# ============================================================


@pytest.mark.django_db
class TestForm103BGeneratorIntegration:
    """Form 103B fee waiver generator integration tests."""

    def test_zero_income_qualifies_for_waiver(self):
        """CRITICAL: $0 income user qualifies for fee waiver."""
        user = User.objects.create_user(username='test_zero', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session, monthly_income=Decimal('0.00'))

        result = Form103BGenerator(session).generate()

        assert result['qualifies_for_waiver'] is True
        assert result['qualification_basis'] == BASIS_INCOME
        assert result['monthly_income'] == Decimal('0.00')
        assert result['filing_fee'] == Decimal('338.00')

    def test_income_at_exactly_150_percent_does_not_qualify(self):
        """Income at exactly 150% poverty line does NOT qualify (strict <)."""
        user = User.objects.create_user(username='test_exact', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        # 150% of $15,060 / 12 = $1,882.50
        _create_fee_waiver(session, monthly_income=Decimal('1882.50'))

        result = Form103BGenerator(session).generate()

        assert result['qualifies_for_waiver'] is False
        assert result['qualification_basis'] == BASIS_NONE

    def test_income_just_below_threshold_qualifies(self):
        """Income one cent below threshold qualifies."""
        user = User.objects.create_user(username='test_below', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session, monthly_income=Decimal('1882.49'))

        result = Form103BGenerator(session).generate()

        assert result['qualifies_for_waiver'] is True
        assert result['qualification_basis'] == BASIS_INCOME

    def test_public_benefits_auto_qualifies(self):
        """Public benefits qualification regardless of income."""
        user = User.objects.create_user(username='test_benefits', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(
            session,
            monthly_income=Decimal('3000.00'),  # Above poverty line
            receives_public_benefits=True,
            benefit_types=['SNAP', 'Medicaid'],
        )

        result = Form103BGenerator(session).generate()

        assert result['qualifies_for_waiver'] is True
        assert result['qualification_basis'] == BASIS_BENEFITS
        assert result['benefit_types'] == ['SNAP', 'Medicaid']

    def test_no_fee_waiver_raises_error(self):
        """Missing FeeWaiverApplication raises Form103BGenerationError."""
        user = User.objects.create_user(username='test_no_fw', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        # No FeeWaiverApplication created

        with pytest.raises(Form103BGenerationError, match='FeeWaiverApplication is required'):
            Form103BGenerator(session).generate()

    def test_preview_matches_generate(self):
        """preview() wraps generate() data with form metadata."""
        user = User.objects.create_user(username='test_preview', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session)

        generator = Form103BGenerator(session)
        gen_result = generator.generate()
        prev_result = generator.preview()

        assert prev_result['form_type'] == 'form_103b'
        assert prev_result['preview'] is True
        assert prev_result['data'] == gen_result
        assert 'not legal advice' in prev_result['upl_disclaimer']

    def test_filing_fee_from_district(self):
        """Filing fee comes from the district model, not hardcoded."""
        user = User.objects.create_user(username='test_fee', password='test')
        district = District.objects.create(
            code='TSTD',
            name='Test District',
            state='XX',
            court_name='Test Court',
            pro_se_efiling_allowed=False,
            filing_fee_chapter_7=Decimal('500.00'),  # Non-standard fee
        )
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session)

        result = Form103BGenerator(session).generate()

        assert result['filing_fee'] == Decimal('500.00')

    def test_household_size_4_poverty_threshold(self):
        """Household of 4 uses correct poverty threshold."""
        user = User.objects.create_user(username='test_hh4', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session, household_size=4, monthly_income=Decimal('0.00'))

        result = Form103BGenerator(session).generate()

        # ($15,060 + 3*$5,380) * 1.5 / 12 = ($15,060 + $16,140) * 1.5 / 12
        # = $31,200 * 1.5 / 12 = $46,800 / 12 = $3,900.00
        assert result['poverty_threshold_monthly'] == Decimal('3900.00')
        assert result['qualifies_for_waiver'] is True

    def test_assets_aggregated_correctly(self):
        """Bank balances, total property, and debt computed from related models."""
        user = User.objects.create_user(username='test_assets', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session)

        # Two bank accounts and one vehicle
        _create_asset(session, 'bank_account', 'Checking', Decimal('100.00'))
        _create_asset(session, 'bank_account', 'Savings', Decimal('50.00'))
        _create_asset(session, 'vehicle', '2010 Civic', Decimal('2000.00'))

        # Two debts
        _create_debt(session, 'Hospital A', Decimal('10000.00'))
        _create_debt(session, 'Credit Card', Decimal('5000.00'), 'credit_card')

        result = Form103BGenerator(session).generate()

        assert result['cash_and_bank_balances'] == Decimal('150.00')
        assert result['total_property_value'] == Decimal('2150.00')
        assert result['total_debt'] == Decimal('15000.00')
        assert result['owns_property'] is True

    def test_no_assets_no_debts_graceful(self):
        """Zero assets and debts yield zero values without error."""
        user = User.objects.create_user(username='test_empty', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session)

        result = Form103BGenerator(session).generate()

        assert result['cash_and_bank_balances'] == Decimal('0.00')
        assert result['total_property_value'] == Decimal('0.00')
        assert result['total_debt'] == Decimal('0.00')
        assert result['owns_property'] is False

    def test_missing_debtor_info_graceful(self):
        """Missing DebtorInfo yields empty name (graceful degradation)."""
        user = User.objects.create_user(username='test_no_debtor', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        # No DebtorInfo
        _create_fee_waiver(session)

        result = Form103BGenerator(session).generate()

        assert result['debtor_name'] == ''
        assert result['qualifies_for_waiver'] is True

    def test_signature_date_is_today(self):
        """Signature date is always today's date."""
        user = User.objects.create_user(username='test_date', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session)

        result = Form103BGenerator(session).generate()

        assert result['signature_date'] == date.today().isoformat()

    def test_net_monthly_income_negative_for_zero_income(self):
        """$0 income with expenses yields negative net income."""
        user = User.objects.create_user(username='test_net', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(
            session,
            monthly_income=Decimal('0.00'),
            monthly_expenses=Decimal('850.00'),
        )

        result = Form103BGenerator(session).generate()

        assert result['net_monthly_income'] == Decimal('-850.00')

    def test_result_message_upl_compliant_income(self):
        """Income-qualified result message is UPL-safe."""
        user = User.objects.create_user(username='test_msg_inc', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session, monthly_income=Decimal('0.00'))

        result = Form103BGenerator(session).generate()

        assert 'may be eligible' in result['result_message']
        assert 'should' not in result['result_message'].lower()
        assert 'recommend' not in result['result_message'].lower()

    def test_result_message_upl_compliant_not_qualified(self):
        """Non-qualified message includes fee and installment option."""
        user = User.objects.create_user(username='test_msg_no', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_fee_waiver(session, monthly_income=Decimal('5000.00'))

        result = Form103BGenerator(session).generate()

        assert '338.00' in result['result_message']
        assert 'installment' in result['result_message']
