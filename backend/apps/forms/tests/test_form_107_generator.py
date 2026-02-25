"""Tests for Form 107 (Statement of Financial Affairs for Individuals) generator."""

import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import DebtInfo, DebtorInfo, IncomeInfo, IntakeSession
from apps.forms.services.form_107_generator import (
    Form107Generator,
    QUESTION_TEXTS,
    TOTAL_QUESTIONS,
    ZERO,
    _build_all_questions,
    _build_creditor_payments_question,
    _build_debtor_name,
    _build_form_107_data,
    _build_income_question,
    _build_placeholder_question,
    _build_question,
    _compute_annual_income_from_monthly,
    _compute_total_monthly_income,
    _extract_creditor_payments,
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


def _create_session(user, district: District) -> IntakeSession:
    return IntakeSession.objects.create(user=user, district=district)


def _create_debtor_info(
    session: IntakeSession,
    first_name: str = 'Jane',
    last_name: str = 'Doe',
    middle_name: str = '',
) -> DebtorInfo:
    return DebtorInfo.objects.create(
        session=session,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        ssn='123-45-6789',
        date_of_birth='1990-01-15',
        phone='312-555-0100',
        email='jane.doe@example.com',
        street_address='123 Main St',
        city='Chicago',
        state='IL',
        zip_code='60601',
    )


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
    creditor_name: str = 'Test Creditor',
    debt_type: str = 'credit_card',
    monthly_payment: Decimal = None,
    account_number: str = '',
) -> DebtInfo:
    return DebtInfo.objects.create(
        session=session,
        creditor_name=creditor_name,
        debt_type=debt_type,
        amount_owed=amount,
        monthly_payment=monthly_payment,
        consumer_business_classification='consumer',
        account_number=account_number,
    )


# -- Pure function tests (no database) --

class TestBuildQuestion:
    """Unit tests for _build_question helper."""

    def test_populated_question(self):
        result = _build_question(
            question_number=1,
            has_data=True,
            response='Yes',
            details=[{'source': 'Employment'}],
        )
        assert result['question_number'] == 1
        assert result['has_data'] is True
        assert result['response'] == 'Yes'
        assert result['details'] == [{'source': 'Employment'}]
        assert result['question_text'] == QUESTION_TEXTS[1]

    def test_placeholder_question(self):
        result = _build_question(
            question_number=4,
            has_data=False,
            response='N/A',
        )
        assert result['question_number'] == 4
        assert result['has_data'] is False
        assert result['response'] == 'N/A'
        assert result['details'] == []
        assert result['question_text'] == QUESTION_TEXTS[4]

    def test_details_default_empty_list(self):
        result = _build_question(question_number=5, has_data=False, response='No')
        assert result['details'] == []


class TestComputeAnnualIncome:
    """Unit tests for income computation helpers."""

    def test_annual_from_uniform_income(self):
        # $3000/mo average * 12 = $36,000
        assert _compute_annual_income_from_monthly(
            [3000, 3000, 3000, 3000, 3000, 3000]
        ) == Decimal('36000.00')

    def test_annual_from_varying_income(self):
        # (2000 + 3000 + 2500 + 3500 + 2000 + 3000) / 6 = 2666.67 * 12 = 32000.04
        result = _compute_annual_income_from_monthly(
            [2000, 3000, 2500, 3500, 2000, 3000]
        )
        assert result == Decimal('32000.04')

    def test_annual_from_empty_list(self):
        assert _compute_annual_income_from_monthly([]) == ZERO

    def test_annual_from_zeros(self):
        assert _compute_annual_income_from_monthly(
            [0, 0, 0, 0, 0, 0]
        ) == ZERO

    def test_monthly_average(self):
        assert _compute_total_monthly_income(
            [3000, 3000, 3000, 3000, 3000, 3000]
        ) == Decimal('3000.00')

    def test_monthly_average_empty(self):
        assert _compute_total_monthly_income([]) == ZERO


class TestExtractCreditorPayments:
    """Unit tests for creditor payment extraction (uses mock-like objects)."""

    def test_no_debts(self):
        assert _extract_creditor_payments([]) == []

    def test_debt_without_monthly_payment(self):
        """Debts with no monthly_payment are excluded."""

        class MockDebt:
            monthly_payment = None
            creditor_name = 'Visa'
            debt_type = 'credit_card'
            account_number = '1234'

        assert _extract_creditor_payments([MockDebt()]) == []

    def test_debt_with_zero_payment(self):
        """Debts with $0 monthly_payment are excluded."""

        class MockDebt:
            monthly_payment = Decimal('0.00')
            creditor_name = 'Visa'
            debt_type = 'credit_card'
            account_number = '1234'

        assert _extract_creditor_payments([MockDebt()]) == []

    def test_debt_with_positive_payment(self):
        """Debts with positive monthly_payment are included."""

        class MockDebt:
            monthly_payment = Decimal('150.00')
            creditor_name = 'Chase Visa'
            debt_type = 'credit_card'
            account_number = '4111222233334444'

        result = _extract_creditor_payments([MockDebt()])
        assert len(result) == 1
        assert result[0]['creditor_name'] == 'Chase Visa'
        assert result[0]['amount'] == Decimal('150.00')
        assert result[0]['account_number_last4'] == '4444'

    def test_short_account_number(self):
        """Account numbers shorter than 4 chars returned as-is."""

        class MockDebt:
            monthly_payment = Decimal('50.00')
            creditor_name = 'Local Store'
            debt_type = 'other'
            account_number = '99'

        result = _extract_creditor_payments([MockDebt()])
        assert result[0]['account_number_last4'] == '99'


class TestBuildAllQuestions:
    """Unit tests for the question assembly function."""

    def test_always_returns_25_questions(self):
        questions, _, _ = _build_all_questions(
            monthly_income=[],
            debts=[],
        )
        assert len(questions) == TOTAL_QUESTIONS

    def test_question_numbering_sequential(self):
        questions, _, _ = _build_all_questions(
            monthly_income=[],
            debts=[],
        )
        numbers = [q['question_number'] for q in questions]
        assert numbers == list(range(1, TOTAL_QUESTIONS + 1))

    def test_questions_with_data_count_no_income_no_debts(self):
        """Q1 and Q3 are always marked has_data=True (populated from models)."""
        _, with_data, needing_input = _build_all_questions(
            monthly_income=[],
            debts=[],
        )
        assert with_data == 2
        assert needing_input == 23

    def test_questions_with_data_count_with_income(self):
        _, with_data, _ = _build_all_questions(
            monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
            debts=[],
        )
        # Q1 and Q3 are always has_data=True
        assert with_data == 2


class TestBuildForm107Data:
    """Unit tests for the complete form data builder."""

    def test_form_type(self):
        result = _build_form_107_data(
            debtor_name='Jane Doe',
            monthly_income=[],
            debts=[],
        )
        assert result['form_type'] == 'form_107'

    def test_debtor_name_included(self):
        result = _build_form_107_data(
            debtor_name='Jane Marie Doe',
            monthly_income=[],
            debts=[],
        )
        assert result['debtor_name'] == 'Jane Marie Doe'

    def test_case_number_empty(self):
        result = _build_form_107_data(
            debtor_name='Test',
            monthly_income=[],
            debts=[],
        )
        assert result['case_number'] == ''

    def test_total_questions_always_25(self):
        result = _build_form_107_data(
            debtor_name='Test',
            monthly_income=[],
            debts=[],
        )
        assert result['total_questions'] == 25


class TestBuildDebtorName:
    """Unit tests for debtor name construction."""

    def test_none_debtor_info(self):
        assert _build_debtor_name(None) == ''

    def test_no_middle_name(self):
        class MockDebtor:
            first_name = 'Jane'
            middle_name = ''
            last_name = 'Doe'

        assert _build_debtor_name(MockDebtor()) == 'Jane Doe'

    def test_with_middle_name(self):
        class MockDebtor:
            first_name = 'Jane'
            middle_name = 'Marie'
            last_name = 'Doe'

        assert _build_debtor_name(MockDebtor()) == 'Jane Marie Doe'


class TestBuildIncomeQuestion:
    """Unit tests for Q1 builder."""

    def test_with_income(self):
        result = _build_income_question([3000, 3000, 3000, 3000, 3000, 3000])
        assert result['question_number'] == 1
        assert result['has_data'] is True
        assert result['response'] == 'Yes'
        assert len(result['details']) == 1
        assert result['details'][0]['annualized'] == '36000.00'

    def test_zero_income(self):
        result = _build_income_question([0, 0, 0, 0, 0, 0])
        assert result['response'] == 'No'
        assert result['details'] == []

    def test_empty_income(self):
        result = _build_income_question([])
        assert result['response'] == 'No'
        assert result['details'] == []


class TestBuildCreditorPaymentsQuestion:
    """Unit tests for Q3 builder."""

    def test_no_debts(self):
        result = _build_creditor_payments_question([])
        assert result['question_number'] == 3
        assert result['has_data'] is True
        assert result['response'] == 'No'
        assert result['details'] == []


class TestPlaceholderQuestion:
    """Unit tests for placeholder question builder."""

    def test_placeholder_structure(self):
        result = _build_placeholder_question(7)
        assert result['question_number'] == 7
        assert result['has_data'] is False
        assert result['response'] == 'N/A'
        assert result['details'] == []
        assert result['question_text'] == QUESTION_TEXTS[7]


# -- Integration tests (database) --

@pytest.mark.django_db
class TestForm107Generator:
    """Form 107 generator integration tests."""

    def test_full_session_data(self):
        """Test with debtor, income, and debts populated."""
        user = User.objects.create_user(username='test_full', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session, first_name='Jane', last_name='Doe')
        _create_income_info(session, [4000, 4000, 4000, 4000, 4000, 4000])
        _create_debt(
            session, Decimal('5000.00'),
            creditor_name='Chase', monthly_payment=Decimal('200.00'),
        )

        result = Form107Generator(session).generate()

        assert result['debtor_name'] == 'Jane Doe'
        assert result['form_type'] == 'form_107'
        assert result['total_questions'] == 25
        assert len(result['questions']) == 25
        assert result['questions_with_data'] == 2

    def test_zero_income_session(self):
        """Test with $0 income reports No for Q1."""
        user = User.objects.create_user(username='test_zero_inc', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_income_info(session, [0, 0, 0, 0, 0, 0])

        result = Form107Generator(session).generate()

        q1 = result['questions'][0]
        assert q1['question_number'] == 1
        assert q1['response'] == 'No'
        assert q1['details'] == []

    def test_no_debts(self):
        """Test with no debts reports No for Q3."""
        user = User.objects.create_user(username='test_no_debts', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_income_info(session, [2000, 2000, 2000, 2000, 2000, 2000])

        result = Form107Generator(session).generate()

        q3 = result['questions'][2]
        assert q3['question_number'] == 3
        assert q3['response'] == 'No'
        assert q3['details'] == []

    def test_no_debtor_info_graceful(self):
        """Test graceful degradation when debtor info is missing."""
        user = User.objects.create_user(username='test_no_debtor', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form107Generator(session).generate()

        assert result['debtor_name'] == ''
        assert result['total_questions'] == 25
        assert len(result['questions']) == 25

    def test_question_count_always_25(self):
        """Question count is always 25 regardless of data."""
        user = User.objects.create_user(username='test_count', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form107Generator(session).generate()

        assert result['total_questions'] == 25
        assert len(result['questions']) == 25
        assert result['questions_with_data'] + result['questions_needing_input'] == 25

    def test_questions_with_data_reflects_populated(self):
        """questions_with_data should be 2 (Q1 and Q3 always populated)."""
        user = User.objects.create_user(username='test_data_count', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_income_info(session, [5000, 5000, 5000, 5000, 5000, 5000])

        result = Form107Generator(session).generate()

        assert result['questions_with_data'] == 2
        assert result['questions_needing_input'] == 23

    def test_preview_matches_generate(self):
        """Preview returns identical data to generate."""
        user = User.objects.create_user(username='test_preview', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)
        _create_income_info(session, [3000, 3000, 3000, 3000, 3000, 3000])
        _create_debt(
            session, Decimal('8000.00'),
            monthly_payment=Decimal('100.00'),
        )

        generator = Form107Generator(session)
        assert generator.preview() == generator.generate()

    def test_employment_income_populates_q1(self):
        """Q1 should contain income details when income is present."""
        user = User.objects.create_user(username='test_q1', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_income_info(session, [4500, 4500, 4500, 4500, 4500, 4500])

        result = Form107Generator(session).generate()

        q1 = result['questions'][0]
        assert q1['question_number'] == 1
        assert q1['response'] == 'Yes'
        assert q1['has_data'] is True
        assert len(q1['details']) == 1
        assert q1['details'][0]['annualized'] == '54000.00'
        assert q1['details'][0]['monthly_average'] == '4500.00'

    def test_creditor_payments_populate_q3(self):
        """Q3 should list creditors with active monthly payments."""
        user = User.objects.create_user(username='test_q3', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debt(
            session, Decimal('3000.00'),
            creditor_name='Chase Visa',
            monthly_payment=Decimal('150.00'),
            account_number='4111222233334444',
        )
        _create_debt(
            session, Decimal('1500.00'),
            creditor_name='Discover',
            monthly_payment=Decimal('75.00'),
            account_number='6011',
        )
        # Debt with no monthly payment should not appear
        _create_debt(
            session, Decimal('500.00'),
            creditor_name='Collections Agency',
        )

        result = Form107Generator(session).generate()

        q3 = result['questions'][2]
        assert q3['question_number'] == 3
        assert q3['response'] == 'Yes'
        assert len(q3['details']) == 2

        creditor_names = {d['creditor_name'] for d in q3['details']}
        assert 'Chase Visa' in creditor_names
        assert 'Discover' in creditor_names
        assert 'Collections Agency' not in creditor_names

    def test_debtor_name_from_debtor_info(self):
        """Debtor name should come from DebtorInfo model."""
        user = User.objects.create_user(username='test_name', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(
            session,
            first_name='Maria',
            last_name='Garcia',
            middle_name='Elena',
        )

        result = Form107Generator(session).generate()

        assert result['debtor_name'] == 'Maria Elena Garcia'

    def test_debtor_name_without_middle(self):
        """Debtor name without middle name."""
        user = User.objects.create_user(username='test_name2', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session, first_name='John', last_name='Smith')

        result = Form107Generator(session).generate()

        assert result['debtor_name'] == 'John Smith'

    def test_placeholder_questions_structure(self):
        """Placeholder questions (not Q1 or Q3) should have N/A response."""
        user = User.objects.create_user(username='test_placeholder', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form107Generator(session).generate()

        # Q2 is a placeholder
        q2 = result['questions'][1]
        assert q2['question_number'] == 2
        assert q2['has_data'] is False
        assert q2['response'] == 'N/A'
        assert q2['details'] == []

        # Q25 is a placeholder
        q25 = result['questions'][24]
        assert q25['question_number'] == 25
        assert q25['has_data'] is False
        assert q25['response'] == 'N/A'

    def test_missing_income_info_graceful(self):
        """Missing IncomeInfo should result in Q1 response 'No'."""
        user = User.objects.create_user(username='test_no_income', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form107Generator(session).generate()

        q1 = result['questions'][0]
        assert q1['response'] == 'No'
        assert q1['details'] == []

    def test_all_question_texts_present(self):
        """Every question should have non-empty question_text."""
        user = User.objects.create_user(username='test_texts', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form107Generator(session).generate()

        for q in result['questions']:
            assert q['question_text'] != '', (
                f"Q{q['question_number']} has empty question_text"
            )
