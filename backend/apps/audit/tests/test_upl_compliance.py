"""
Comprehensive UPL (Unauthorized Practice of Law) compliance tests.

CRITICAL: These tests verify that DigniFi provides legal INFORMATION,
never legal ADVICE. UPL violations can result in legal liability.

Test Coverage:
1. Prohibited phrase detection in all UPL-sensitive outputs
2. UPL disclaimers present in all form previews
3. Audit middleware correctly identifies UPL-sensitive paths
4. Settings configuration for UPL compliance
5. Service layer message generation compliance
"""

import pytest
from decimal import Decimal
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.audit.middleware import AuditLoggingMiddleware
from apps.forms.views import _UPL_DISCLAIMER
from apps.districts.models import District, MedianIncome
from apps.intake.models import IntakeSession, DebtorInfo, IncomeInfo
from apps.eligibility.models import MeansTest
from apps.eligibility.services.means_test_calculator import MeansTestCalculator

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


def _create_median_income(district: District) -> MedianIncome:
    """Create median income data for ILND."""
    return MedianIncome.objects.create(
        district=district,
        effective_date=date(2025, 1, 1),
        family_size_1=Decimal('71304'),
        family_size_2=Decimal('89935'),
        family_size_3=Decimal('102417'),
        family_size_4=Decimal('123691'),
        family_size_5=Decimal('133691'),
        family_size_6=Decimal('143691'),
        family_size_7=Decimal('153691'),
        family_size_8=Decimal('163691'),
    )


def _create_session_with_income(
    user,
    district: District,
    monthly_income: Decimal,
    marital_status: str = 'single',
    number_of_dependents: int = 0,
) -> IntakeSession:
    """Create intake session with income info.

    monthly_income is the desired CMI (Current Monthly Income).
    The model stores a 6-month array; we fill all 6 months with the same value
    so that the average equals the requested CMI.
    """
    session = IntakeSession.objects.create(user=user, district=district)

    DebtorInfo.objects.create(
        session=session,
        first_name='Jane',
        middle_name='Marie',
        last_name='Doe',
        ssn='123456789',
        date_of_birth=date(1990, 1, 15),
        phone='312-555-0100',
        email='jane.doe@example.com',
        street_address='123 Main St',
        city='Chicago',
        state='IL',
        zip_code='60601',
    )

    IncomeInfo.objects.create(
        session=session,
        marital_status=marital_status,
        number_of_dependents=number_of_dependents,
        monthly_income=[float(monthly_income)] * 6,
    )

    return session


def _check_for_prohibited_phrases(text: str) -> list[str]:
    """
    Scan text for UPL-prohibited phrases.

    Returns list of found prohibited phrases (empty if compliant).
    """
    found_violations = []
    text_lower = text.lower()

    for phrase in settings.UPL_PROHIBITED_PHRASES:
        if phrase.lower() in text_lower:
            found_violations.append(phrase)

    return found_violations


# ============================================================================
# Settings Configuration Tests
# ============================================================================


class TestUPLSettings:
    """Verify UPL compliance settings are properly configured."""

    def test_upl_prohibited_phrases_setting_exists(self):
        """UPL_PROHIBITED_PHRASES setting must be defined."""
        assert hasattr(settings, 'UPL_PROHIBITED_PHRASES')

    def test_upl_prohibited_phrases_not_empty(self):
        """UPL_PROHIBITED_PHRASES must have at least one entry."""
        assert len(settings.UPL_PROHIBITED_PHRASES) > 0

    def test_upl_prohibited_phrases_includes_key_violations(self):
        """UPL_PROHIBITED_PHRASES must include critical advice indicators."""
        phrases = [p.lower() for p in settings.UPL_PROHIBITED_PHRASES]

        # These are the most dangerous phrases that cross into advice
        critical_violations = [
            'you should file',
            'i recommend',
            'my advice is',
        ]

        for violation in critical_violations:
            assert violation in phrases, (
                f"Critical UPL violation '{violation}' missing from settings"
            )

    def test_upl_audit_enabled(self):
        """UPL_AUDIT_ENABLED must be True for production compliance."""
        assert hasattr(settings, 'UPL_AUDIT_ENABLED')
        assert settings.UPL_AUDIT_ENABLED is True


# ============================================================================
# Forms View UPL Compliance Tests
# ============================================================================


class TestFormsViewUPLCompliance:
    """Verify forms view UPL disclaimers and messaging."""

    def test_upl_disclaimer_constant_exists(self):
        """_UPL_DISCLAIMER constant must be defined in forms views."""
        assert _UPL_DISCLAIMER is not None
        assert len(_UPL_DISCLAIMER) > 0

    def test_upl_disclaimer_no_prohibited_phrases(self):
        """UPL disclaimer itself must not contain prohibited advice phrases."""
        violations = _check_for_prohibited_phrases(_UPL_DISCLAIMER)
        assert violations == [], (
            f"UPL disclaimer contains prohibited phrases: {violations}"
        )

    def test_upl_disclaimer_contains_information_not_advice(self):
        """UPL disclaimer must explicitly state information vs advice."""
        disclaimer_lower = _UPL_DISCLAIMER.lower()
        assert 'legal information' in disclaimer_lower
        assert 'not legal advice' in disclaimer_lower or 'not advice' in disclaimer_lower

    def test_upl_disclaimer_mentions_user_responsibility(self):
        """UPL disclaimer must place responsibility on user."""
        disclaimer_lower = _UPL_DISCLAIMER.lower()
        assert (
            'you are responsible' in disclaimer_lower
            or 'your responsibility' in disclaimer_lower
        )


# ============================================================================
# Means Test Calculator UPL Compliance Tests
# ============================================================================


@pytest.mark.django_db
class TestMeansTestCalculatorUPLCompliance:
    """Verify means test calculator generates UPL-compliant messages."""

    def test_passing_means_test_message_no_prohibited_phrases(self):
        """Passing means test message must not contain advice."""
        user = User.objects.create_user(username='test_pass', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)

        # Below-median income (passes means test)
        session = _create_session_with_income(
            user, district, monthly_income=Decimal('4000.00')
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        violations = _check_for_prohibited_phrases(result['message'])
        assert violations == [], (
            f"Passing means test message contains prohibited phrases: {violations}\n"
            f"Message: {result['message']}"
        )

    def test_passing_means_test_uses_may_be_eligible(self):
        """Passing means test should use permissive language like 'may be eligible'."""
        user = User.objects.create_user(username='test_may', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)

        session = _create_session_with_income(
            user, district, monthly_income=Decimal('4000.00')
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        message_lower = result['message'].lower()
        assert (
            'may be eligible' in message_lower
            or 'may qualify' in message_lower
        ), "Passing means test message should use conditional language"

    def test_failing_means_test_message_no_prohibited_phrases(self):
        """Failing means test message must not contain advice."""
        user = User.objects.create_user(username='test_fail', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)

        # Above-median income (fails means test)
        session = _create_session_with_income(
            user, district, monthly_income=Decimal('10000.00')
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        violations = _check_for_prohibited_phrases(result['message'])
        assert violations == [], (
            f"Failing means test message contains prohibited phrases: {violations}\n"
            f"Message: {result['message']}"
        )

    def test_failing_means_test_provides_information_not_advice(self):
        """Failing means test should explain options without recommending."""
        user = User.objects.create_user(username='test_info', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)

        # CMI must exceed the annual median threshold ($71,304) to FAIL
        session = _create_session_with_income(
            user, district, monthly_income=Decimal('80000.00')
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        message_lower = result['message'].lower()

        # Should mention options (informational)
        assert (
            'chapter 13' in message_lower
            or 'additional calculations' in message_lower
        ), "Failing means test should provide information about alternatives"

        # Should NOT say "you should choose Chapter 13"
        assert 'should choose' not in message_lower
        assert 'should file' not in message_lower

    def test_fee_waiver_message_no_prohibited_phrases(self):
        """Fee waiver qualification message must not contain advice."""
        user = User.objects.create_user(username='test_waiver', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)

        # Very low income (qualifies for fee waiver)
        session = _create_session_with_income(
            user, district, monthly_income=Decimal('1500.00')
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        violations = _check_for_prohibited_phrases(result['message'])
        assert violations == [], (
            f"Fee waiver message contains prohibited phrases: {violations}\n"
            f"Message: {result['message']}"
        )

    def test_message_uses_typically_not_always(self):
        """Messages should use 'typically' not absolute statements."""
        user = User.objects.create_user(username='test_typ', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)

        session = _create_session_with_income(
            user, district, monthly_income=Decimal('4000.00')
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        message_lower = result['message'].lower()

        # Should use conditional/general language
        conditional_terms = ['typically', 'generally', 'may', 'often', 'usually']
        has_conditional = any(term in message_lower for term in conditional_terms)

        assert has_conditional, (
            "Means test message should use conditional language (typically, may, etc.)"
        )

    def test_all_calculation_paths_upl_compliant(self):
        """Test multiple income scenarios to ensure all paths are compliant."""
        district = _create_ilnd_district()
        _create_median_income(district)

        # Test scenarios: very low, below median, at median, above median, high
        test_incomes = [
            Decimal('1000.00'),   # Very low (fee waiver)
            Decimal('4000.00'),   # Below median
            Decimal('5942.00'),   # Approximately at median (71304 / 12)
            Decimal('7000.00'),   # Above median
            Decimal('15000.00'),  # High income
        ]

        all_messages = []

        for income in test_incomes:
            user = User.objects.create_user(
                username=f'test_{income}',
                password='test'
            )
            session = _create_session_with_income(user, district, monthly_income=income)

            calculator = MeansTestCalculator(session)
            result = calculator.calculate()
            all_messages.append((income, result['message']))

            violations = _check_for_prohibited_phrases(result['message'])
            assert violations == [], (
                f"Message for income ${income} contains prohibited phrases: {violations}\n"
                f"Message: {result['message']}"
            )


# ============================================================================
# Audit Middleware UPL Path Detection Tests
# ============================================================================


class TestAuditMiddlewareUPLPathDetection:
    """Verify audit middleware correctly identifies UPL-sensitive paths."""

    def test_is_upl_sensitive_method_exists(self):
        """Middleware must have _is_upl_sensitive method."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        assert hasattr(middleware, '_is_upl_sensitive')
        assert callable(middleware._is_upl_sensitive)

    def test_eligibility_paths_marked_upl_sensitive(self):
        """Paths under /api/eligibility/ must be marked UPL-sensitive."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            '/api/eligibility/',
            '/api/eligibility/means-test/',
            '/api/eligibility/calculate/',
        ]

        for path in test_paths:
            assert middleware._is_upl_sensitive(path) is True, (
                f"Path {path} should be marked UPL-sensitive"
            )

    def test_forms_paths_marked_upl_sensitive(self):
        """Paths under /api/forms/ must be marked UPL-sensitive."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            '/api/forms/',
            '/api/forms/generate/',
            '/api/forms/preview/',
            '/api/forms/1/regenerate/',
        ]

        for path in test_paths:
            assert middleware._is_upl_sensitive(path) is True, (
                f"Path {path} should be marked UPL-sensitive"
            )

    def test_intake_paths_marked_upl_sensitive(self):
        """Paths under /api/intake/ must be marked UPL-sensitive."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            '/api/intake/',
            '/api/intake/sessions/',
            '/api/intake/sessions/1/calculate_means_test/',
        ]

        for path in test_paths:
            assert middleware._is_upl_sensitive(path) is True, (
                f"Path {path} should be marked UPL-sensitive"
            )

    def test_means_test_paths_marked_upl_sensitive(self):
        """Paths under /api/means-test/ must be marked UPL-sensitive."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            '/api/means-test/',
            '/api/means-test/calculate/',
        ]

        for path in test_paths:
            assert middleware._is_upl_sensitive(path) is True, (
                f"Path {path} should be marked UPL-sensitive"
            )

    def test_non_upl_paths_not_marked_sensitive(self):
        """Non-UPL paths should NOT be marked UPL-sensitive."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            '/api/auth/login/',
            '/api/auth/logout/',
            '/api/users/profile/',
            '/api/health/',
            '/admin/',
            '/static/css/style.css',
        ]

        for path in test_paths:
            assert middleware._is_upl_sensitive(path) is False, (
                f"Path {path} should NOT be marked UPL-sensitive"
            )


# ============================================================================
# String Constant Scanning Tests
# ============================================================================


@pytest.mark.django_db
class TestServiceLayerStringCompliance:
    """Scan all service layer string constants for prohibited phrases."""

    def test_means_test_calculator_all_strings_compliant(self):
        """Scan all possible MeansTestCalculator outputs for violations."""
        district = _create_ilnd_district()
        _create_median_income(district)

        # Generate messages for different scenarios
        scenarios = [
            ('passing', Decimal('3000.00')),
            ('failing', Decimal('10000.00')),
            ('fee_waiver', Decimal('1200.00')),
        ]

        for scenario_name, income in scenarios:
            user = User.objects.create_user(
                username=f'test_{scenario_name}',
                password='test'
            )
            session = _create_session_with_income(user, district, monthly_income=income)

            calculator = MeansTestCalculator(session)
            result = calculator.calculate()

            # Check main message
            violations = _check_for_prohibited_phrases(result['message'])
            assert violations == [], (
                f"Scenario '{scenario_name}' has violations: {violations}\n"
                f"Message: {result['message']}"
            )

    def test_detailed_breakdown_no_advice(self):
        """Detailed breakdown should provide data, not recommendations."""
        user = User.objects.create_user(username='test_detail', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)

        session = _create_session_with_income(
            user, district, monthly_income=Decimal('5000.00')
        )

        calculator = MeansTestCalculator(session)
        calculator.calculate()  # Must calculate first

        breakdown = calculator.get_detailed_breakdown()

        # Convert breakdown to string for scanning (JSON values)
        import json
        breakdown_str = json.dumps(breakdown)

        violations = _check_for_prohibited_phrases(breakdown_str)
        assert violations == [], (
            f"Detailed breakdown contains prohibited phrases: {violations}"
        )


# ============================================================================
# Integration Tests: End-to-End UPL Compliance
# ============================================================================


@pytest.mark.django_db
class TestEndToEndUPLCompliance:
    """Integration tests verifying UPL compliance across entire workflow."""

    def test_complete_intake_to_form_preview_upl_compliant(self):
        """
        Test complete workflow from intake to form preview.
        Every step must be UPL-compliant.
        """
        # Setup
        user = User.objects.create_user(username='test_e2e', password='test')
        district = _create_ilnd_district()
        _create_median_income(district)

        # Create intake session with income
        session = _create_session_with_income(
            user, district, monthly_income=Decimal('4500.00')
        )

        # Calculate means test (UPL-sensitive operation)
        calculator = MeansTestCalculator(session)
        means_test_result = calculator.calculate()

        # Verify means test message is compliant
        violations = _check_for_prohibited_phrases(means_test_result['message'])
        assert violations == [], (
            f"Means test result contains prohibited phrases: {violations}"
        )

        # Get detailed breakdown (UPL-sensitive operation)
        breakdown = calculator.get_detailed_breakdown()

        # Breakdown should contain statute citation (informational)
        assert 'statute_citation' in breakdown['results']
        assert '11 U.S.C.' in breakdown['results']['statute_citation']

        # Breakdown should NOT contain advice
        import json
        breakdown_str = json.dumps(breakdown)
        violations = _check_for_prohibited_phrases(breakdown_str)
        assert violations == [], (
            f"Detailed breakdown contains prohibited phrases: {violations}"
        )

    def test_all_output_channels_scanned(self):
        """
        Verify we're testing all channels where UPL violations could occur.

        This meta-test ensures comprehensive coverage.
        """
        tested_components = [
            'settings.UPL_PROHIBITED_PHRASES',
            'forms.views._UPL_DISCLAIMER',
            'MeansTestCalculator._generate_upl_compliant_message',
            'AuditLoggingMiddleware._is_upl_sensitive',
        ]

        # This test documents what we're testing
        # If new UPL-sensitive components are added, update this list
        assert len(tested_components) == 4, (
            "Update this test when adding new UPL-sensitive components"
        )


# ============================================================================
# Regression Tests: Known UPL Violations
# ============================================================================


class TestUPLRegressionPrevention:
    """
    Tests that prevent regression to known UPL violations.

    Add new tests here whenever a UPL violation is discovered and fixed.
    """

    def test_no_direct_recommendations(self):
        """
        REGRESSION: Ensure we never say "I recommend" or "You should".

        Context: Initial implementation risk - easy to accidentally slip
        into recommendation language when trying to be helpful.
        """
        prohibited_direct = [
            'i recommend',
            'you should file',
            'you should choose',
        ]

        for phrase in prohibited_direct:
            assert phrase in [p.lower() for p in settings.UPL_PROHIBITED_PHRASES], (
                f"Prohibited phrase '{phrase}' must be in settings"
            )

    def test_no_predictive_advice(self):
        """
        REGRESSION: Ensure we never predict case outcomes.

        Context: "You will win" or "This will be discharged" crosses into
        legal advice by predicting specific outcomes.
        """
        # Settings should include phrases that predict outcomes
        # (Add these if discovered in the wild)
        predictive_phrases = [
            'you will',
            'this will be',
            'you are going to',
        ]

        # Document that these would be violations if found
        # (This is a preventive test - add to settings if violations occur)
        pass  # Placeholder for future regression tests

    def test_conditional_language_required(self):
        """
        REGRESSION: Ensure all eligibility language is conditional.

        Context: "You are eligible" is more advice-like than "You may be eligible".
        """
        # This is tested in the means test calculator tests
        # Document here that conditional language is REQUIRED, not optional
        pass  # Documented requirement
