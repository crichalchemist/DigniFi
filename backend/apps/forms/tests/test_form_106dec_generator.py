"""Tests for Form 106Dec (Declaration About an Individual Debtor's Schedules) generator."""

import pytest
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import IntakeSession, DebtorInfo
from apps.forms.services.form_106dec_generator import (
    Form106DecGenerator,
    _build_debtor_full_name,
    _build_declaration_data,
    _DECLARATION_TEXT,
    _STANDARD_SCHEDULES,
)

User = get_user_model()


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
    last_name: str = 'Doe',
    middle_name: str = '',
) -> DebtorInfo:
    return DebtorInfo.objects.create(
        session=session,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        ssn='123-45-6789',
        date_of_birth=date(1990, 1, 15),
        phone='312-555-0100',
        email='jane.doe@example.com',
        street_address='123 Main St',
        city='Chicago',
        state='IL',
        zip_code='60601',
    )


# --- Pure function tests (no DB) ---


class TestBuildDebtorFullName:
    """Unit tests for _build_debtor_full_name helper."""

    def test_first_and_last_only(self):
        """Full name omits middle when blank."""
        debtor = type('FakeDebtor', (), {
            'first_name': 'Jane',
            'middle_name': '',
            'last_name': 'Doe',
        })()

        assert _build_debtor_full_name(debtor) == 'Jane Doe'

    def test_includes_middle_name(self):
        """Full name includes middle name when present."""
        debtor = type('FakeDebtor', (), {
            'first_name': 'Jane',
            'middle_name': 'Marie',
            'last_name': 'Doe',
        })()

        assert _build_debtor_full_name(debtor) == 'Jane Marie Doe'


class TestBuildDeclarationData:
    """Unit tests for _build_declaration_data pure function."""

    def test_returns_expected_keys(self):
        """Declaration data contains all required form fields."""
        result = _build_declaration_data('Jane Doe', '2026-02-24')
        expected_keys = {
            'debtor_name',
            'case_number',
            'declaration_text',
            'penalty_of_perjury',
            'signature_date',
            'schedules_declared',
        }
        assert set(result.keys()) == expected_keys

    def test_penalty_of_perjury_always_true(self):
        """Perjury declaration flag is always True regardless of inputs."""
        result = _build_declaration_data('', '2026-01-01')
        assert result['penalty_of_perjury'] is True

    def test_case_number_empty(self):
        """Case number is empty string until court assigns one."""
        result = _build_declaration_data('Jane Doe', '2026-02-24')
        assert result['case_number'] == ''

    def test_schedules_declared_complete(self):
        """All standard Chapter 7 schedules are listed."""
        result = _build_declaration_data('Jane Doe', '2026-02-24')
        assert result['schedules_declared'] == ['A/B', 'C', 'D', 'E/F', 'I', 'J', '106Sum']


# --- Integration tests (DB required) ---


@pytest.mark.django_db
class TestForm106DecDebtorName:
    """Declaration includes correct debtor name from DebtorInfo."""

    def test_declaration_includes_debtor_name(self):
        """Generated data reflects the debtor's full name."""
        user = User.objects.create_user(username='test_dec_name', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session, first_name='Jane', last_name='Doe')

        result = Form106DecGenerator(session).generate()

        assert result['debtor_name'] == 'Jane Doe'

    def test_declaration_includes_middle_name(self):
        """Full name incorporates middle name when debtor provides one."""
        user = User.objects.create_user(username='test_dec_middle', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(
            session,
            first_name='John',
            middle_name='Michael',
            last_name='Smith',
        )

        result = Form106DecGenerator(session).generate()

        assert result['debtor_name'] == 'John Michael Smith'


@pytest.mark.django_db
class TestForm106DecPerjury:
    """Penalty of perjury flag is always True."""

    def test_penalty_of_perjury_is_true(self):
        """Declaration always asserts perjury acknowledgment."""
        user = User.objects.create_user(username='test_dec_perjury', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)

        result = Form106DecGenerator(session).generate()

        assert result['penalty_of_perjury'] is True

    def test_penalty_of_perjury_true_without_debtor(self):
        """Perjury flag is True even when debtor info is missing."""
        user = User.objects.create_user(username='test_dec_perj_no_deb', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form106DecGenerator(session).generate()

        assert result['penalty_of_perjury'] is True


@pytest.mark.django_db
class TestForm106DecSchedulesDeclared:
    """Schedules declared list is complete for Chapter 7 filing."""

    def test_schedules_declared_complete(self):
        """All standard schedules are included in declaration."""
        user = User.objects.create_user(username='test_dec_sched', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)

        result = Form106DecGenerator(session).generate()

        assert result['schedules_declared'] == ['A/B', 'C', 'D', 'E/F', 'I', 'J', '106Sum']

    def test_schedules_count(self):
        """Declaration covers exactly 7 schedule types."""
        user = User.objects.create_user(username='test_dec_count', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form106DecGenerator(session).generate()

        assert len(result['schedules_declared']) == 7


@pytest.mark.django_db
class TestForm106DecMissingDebtor:
    """Graceful handling when DebtorInfo does not exist."""

    def test_missing_debtor_returns_empty_name(self):
        """Session without DebtorInfo produces empty debtor_name."""
        user = User.objects.create_user(username='test_dec_no_deb', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form106DecGenerator(session).generate()

        assert result['debtor_name'] == ''

    def test_missing_debtor_still_has_declaration_text(self):
        """Declaration text is present even without debtor info."""
        user = User.objects.create_user(username='test_dec_no_deb_text', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form106DecGenerator(session).generate()

        assert result['declaration_text'] == _DECLARATION_TEXT

    def test_missing_debtor_has_signature_date(self):
        """Signature date is set to today even without debtor info."""
        user = User.objects.create_user(username='test_dec_no_deb_date', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form106DecGenerator(session).generate()

        assert result['signature_date'] == date.today().isoformat()


@pytest.mark.django_db
class TestForm106DecPreview:
    """Preview returns identical output to generate."""

    def test_preview_matches_generate(self):
        """Preview and generate return the same data for review."""
        user = User.objects.create_user(username='test_dec_preview', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)

        generator = Form106DecGenerator(session)

        assert generator.preview() == generator.generate()

    def test_preview_without_debtor_matches_generate(self):
        """Preview and generate are consistent even without debtor info."""
        user = User.objects.create_user(username='test_dec_prev_no_deb', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        generator = Form106DecGenerator(session)

        assert generator.preview() == generator.generate()
