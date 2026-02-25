"""Tests for Form 121 (Your Statement About Your Social Security Numbers) generator."""

import pytest
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import DebtorInfo, IntakeSession
from apps.forms.services.form_121_generator import (
    Form121Generator,
    Form121GenerationError,
    _format_ssn,
    _extract_last_four,
    _mask_ssn,
    _build_full_name,
    _build_form_121_data,
    _build_preview_data,
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
    ssn: str = '123456789',
    first_name: str = 'Jane',
    middle_name: str = 'Marie',
    last_name: str = 'Doe',
) -> DebtorInfo:
    """Create DebtorInfo with the given identity fields."""
    return DebtorInfo.objects.create(
        session=session,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        ssn=ssn,
        date_of_birth=date(1990, 1, 15),
        phone='312-555-0100',
        email='jane.doe@example.com',
        street_address='123 Main St',
        city='Chicago',
        state='IL',
        zip_code='60601',
    )


# -- Pure function tests (no database) --


class TestFormatSSN:
    """Unit tests for the pure _format_ssn helper."""

    def test_raw_nine_digits(self):
        """Bare 9-digit string formats to XXX-XX-XXXX."""
        assert _format_ssn('123456789') == '123-45-6789'

    def test_already_formatted(self):
        """Already-formatted SSN passes through unchanged."""
        assert _format_ssn('987-65-4321') == '987-65-4321'

    def test_strips_whitespace(self):
        """Leading and trailing whitespace is removed before formatting."""
        assert _format_ssn('  123456789  ') == '123-45-6789'

    def test_invalid_length_raises(self):
        """Non-conforming input raises ValueError with clear message."""
        with pytest.raises(ValueError, match='Invalid SSN format'):
            _format_ssn('12345')

    def test_letters_raise(self):
        """Alphabetic characters are rejected."""
        with pytest.raises(ValueError, match='Invalid SSN format'):
            _format_ssn('12345678a')

    def test_partial_dashes_raise(self):
        """Partially formatted SSN (missing digits) is rejected."""
        with pytest.raises(ValueError, match='Invalid SSN format'):
            _format_ssn('123-45-678')


class TestExtractLastFour:
    """Unit tests for the pure _extract_last_four helper."""

    def test_returns_last_four_digits(self):
        """Extracts the final 4 characters from a formatted SSN."""
        assert _extract_last_four('123-45-6789') == '6789'

    def test_different_ssn(self):
        """Works for any valid formatted SSN."""
        assert _extract_last_four('999-88-7777') == '7777'


class TestMaskSSN:
    """Unit tests for the pure _mask_ssn helper."""

    def test_masks_first_five_digits(self):
        """Replaces first 5 digits with asterisks, preserving last 4."""
        assert _mask_ssn('123-45-6789') == '***-**-6789'

    def test_mask_preserves_last_four(self):
        """Last 4 digits are always visible in the masked output."""
        masked = _mask_ssn('987-65-4321')
        assert masked.endswith('4321')
        assert masked.startswith('***-**-')


class TestBuildFullName:
    """Unit tests for the pure _build_full_name helper."""

    def test_all_three_parts(self):
        """First, middle, and last names are space-joined."""
        assert _build_full_name('Jane', 'Marie', 'Doe') == 'Jane Marie Doe'

    def test_empty_middle_name(self):
        """Empty middle name is collapsed (no double space)."""
        assert _build_full_name('Jane', '', 'Doe') == 'Jane Doe'

    def test_all_empty(self):
        """All-empty input yields empty string."""
        assert _build_full_name('', '', '') == ''


class TestBuildForm121Data:
    """Unit tests for the pure _build_form_121_data helper."""

    def test_filed_separately_always_true(self):
        """Form 121 is always filed separately (sealed)."""
        result = _build_form_121_data(
            debtor_name='Jane Doe',
            ssn_full='123-45-6789',
            ssn_last_four='6789',
        )
        assert result['filed_separately'] is True

    def test_case_number_empty_by_default(self):
        """Case number starts empty (court assigns it after filing)."""
        result = _build_form_121_data(
            debtor_name='Jane Doe',
            ssn_full='123-45-6789',
            ssn_last_four='6789',
        )
        assert result['case_number'] == ''

    def test_includes_full_ssn(self):
        """generate output includes the unmasked SSN for sealed filing."""
        result = _build_form_121_data(
            debtor_name='Jane Doe',
            ssn_full='123-45-6789',
            ssn_last_four='6789',
        )
        assert result['ssn_full'] == '123-45-6789'

    def test_has_previous_ssn_defaults_false(self):
        """has_previous_ssn defaults to False."""
        result = _build_form_121_data(
            debtor_name='Jane Doe',
            ssn_full='123-45-6789',
            ssn_last_four='6789',
        )
        assert result['has_previous_ssn'] is False
        assert result['previous_ssn'] is None

    def test_previous_ssn_when_provided(self):
        """Previous SSN is included when debtor had a different number."""
        result = _build_form_121_data(
            debtor_name='Jane Doe',
            ssn_full='123-45-6789',
            ssn_last_four='6789',
            has_previous_ssn=True,
            previous_ssn='111-22-3333',
        )
        assert result['has_previous_ssn'] is True
        assert result['previous_ssn'] == '111-22-3333'


class TestBuildPreviewData:
    """Unit tests for the pure _build_preview_data helper."""

    def test_preview_uses_masked_ssn(self):
        """Preview output contains masked SSN, never the full number."""
        result = _build_preview_data(
            debtor_name='Jane Doe',
            ssn_masked='***-**-6789',
            ssn_last_four='6789',
        )
        assert result['ssn_display'] == '***-**-6789'
        assert 'ssn_full' not in result

    def test_preview_filed_separately_true(self):
        """Preview also reflects the sealed-filing flag."""
        result = _build_preview_data(
            debtor_name='Jane Doe',
            ssn_masked='***-**-6789',
            ssn_last_four='6789',
        )
        assert result['filed_separately'] is True

    def test_preview_masks_previous_ssn(self):
        """Previous SSN display is fully masked in preview."""
        result = _build_preview_data(
            debtor_name='Jane Doe',
            ssn_masked='***-**-6789',
            ssn_last_four='6789',
            has_previous_ssn=True,
        )
        assert result['previous_ssn_display'] == '***-**-****'

    def test_preview_no_previous_ssn(self):
        """When no previous SSN, display field is None."""
        result = _build_preview_data(
            debtor_name='Jane Doe',
            ssn_masked='***-**-6789',
            ssn_last_four='6789',
            has_previous_ssn=False,
        )
        assert result['previous_ssn_display'] is None


# -- Integration tests (database) --


@pytest.mark.django_db
class TestForm121Generator:
    """Form 121 SSN disclosure generator integration tests."""

    def test_generate_returns_full_ssn(self):
        """generate() includes unmasked SSN for the sealed court filing."""
        user = User.objects.create_user(username='test_gen', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session, ssn='123456789')

        result = Form121Generator(session).generate()

        assert result['ssn_full'] == '123-45-6789'
        assert result['ssn_last_four'] == '6789'

    def test_generate_debtor_name(self):
        """generate() assembles the full legal name from debtor info."""
        user = User.objects.create_user(username='test_name', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(
            session,
            first_name='John',
            middle_name='Alexander',
            last_name='Smith',
        )

        result = Form121Generator(session).generate()

        assert result['debtor_name'] == 'John Alexander Smith'

    def test_generate_without_middle_name(self):
        """Full name collapses cleanly when middle name is blank."""
        user = User.objects.create_user(username='test_no_mid', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(
            session,
            first_name='Jane',
            middle_name='',
            last_name='Doe',
        )

        result = Form121Generator(session).generate()

        assert result['debtor_name'] == 'Jane Doe'

    def test_generate_filed_separately_always_true(self):
        """Form 121 is always filed separately regardless of inputs."""
        user = User.objects.create_user(username='test_sealed', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)

        result = Form121Generator(session).generate()

        assert result['filed_separately'] is True

    def test_missing_debtor_info_raises(self):
        """Form 121 cannot be generated without DebtorInfo (SSN required)."""
        user = User.objects.create_user(username='test_miss', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        # No DebtorInfo created

        with pytest.raises(Form121GenerationError, match='DebtorInfo is required'):
            Form121Generator(session).generate()

    def test_missing_debtor_info_raises_on_preview(self):
        """preview() also raises when DebtorInfo is absent."""
        user = User.objects.create_user(username='test_miss_prev', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        with pytest.raises(Form121GenerationError, match='DebtorInfo is required'):
            Form121Generator(session).preview()

    def test_preview_masks_ssn(self):
        """preview() never exposes the full SSN — only masked version."""
        user = User.objects.create_user(username='test_prev', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session, ssn='987654321')

        result = Form121Generator(session).preview()

        preview_data = result['data']
        assert preview_data['ssn_display'] == '***-**-4321'
        assert preview_data['ssn_last_four'] == '4321'
        assert 'ssn_full' not in preview_data

    def test_preview_includes_form_metadata(self):
        """preview() wraps data with form type, name, and UPL disclaimer."""
        user = User.objects.create_user(username='test_meta', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session)

        result = Form121Generator(session).preview()

        assert result['form_type'] == 'form_121'
        assert result['preview'] is True
        assert 'under seal' in result['upl_disclaimer']

    def test_preview_and_generate_diverge_on_ssn(self):
        """preview() masks while generate() reveals — the core security contract."""
        user = User.objects.create_user(username='test_diverge', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session, ssn='555667788')

        generator = Form121Generator(session)

        gen_result = generator.generate()
        prev_result = generator.preview()

        # generate() has full SSN
        assert gen_result['ssn_full'] == '555-66-7788'

        # preview() has masked SSN, no full SSN
        assert prev_result['data']['ssn_display'] == '***-**-7788'
        assert 'ssn_full' not in prev_result['data']

    def test_formatted_ssn_input(self):
        """SSN already in XXX-XX-XXXX format is handled correctly."""
        user = User.objects.create_user(username='test_fmt', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_debtor_info(session, ssn='111-22-3333')

        result = Form121Generator(session).generate()

        assert result['ssn_full'] == '111-22-3333'
        assert result['ssn_last_four'] == '3333'
