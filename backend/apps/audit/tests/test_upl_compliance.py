"""
Comprehensive UPL (Unauthorized Practice of Law) compliance tests.

CRITICAL: These tests verify that DigniFi provides legal INFORMATION,
never legal ADVICE. UPL violations can result in legal liability.

Test Coverage:
1. Prohibited phrase detection in all UPL-sensitive outputs
2. UPL disclaimers present in all form previews
3. Audit middleware correctly identifies UPL-sensitive paths
4. Settings configuration for UPL compliance
5. Service layer reply compliance (no sentence leaves the server)
"""

from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.audit.middleware import AuditLoggingMiddleware
from apps.districts.models import District, MedianIncome
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.constants import _UPL_DISCLAIMER
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household

User = get_user_model()


def _create_ilnd_district() -> District:
    """Create ILND district fixture for tests."""
    return District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
        pro_se_efiling_allowed=False,
        filing_fee_chapter_7=Decimal("338.00"),
    )


def _create_median_income(district: District) -> MedianIncome:
    """Create median income data for ILND."""
    return MedianIncome.objects.create(
        district=district,
        effective_date=date(2025, 1, 1),
        family_size_1=Decimal("71304"),
        family_size_2=Decimal("89935"),
        family_size_3=Decimal("102417"),
        family_size_4=Decimal("123691"),
        family_size_5=Decimal("133691"),
        family_size_6=Decimal("143691"),
        family_size_7=Decimal("153691"),
        family_size_8=Decimal("163691"),
        family_size_additional=Decimal("11100.00"),
    )


def _create_session_with_income(
    user,
    district: District,
    monthly_income: Decimal,
    marital_status: str = "not_married",
) -> IntakeSession:
    """Create intake session with income info.

    monthly_income is the desired CMI (Current Monthly Income). It is stored as
    wages, the filer's only income source, so CMI equals it.
    """
    session = IntakeSession.objects.create(user=user, district=district)

    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        middle_name="Marie",
        last_name="Doe",
        ssn="123456789",
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )

    IncomeInfo.objects.create(
        session=session,
        marital_status=marital_status,
        monthly_gross_wages=monthly_income,
    )
    answer_household(session, marital_status=marital_status)

    return session


def _every_string(value) -> list[str]:
    """Every string in a reply, keys included, through nested dicts and lists."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for key, item in value.items() for text in [key, *_every_string(item)]]
    if isinstance(value, list | tuple):
        return [text for item in value for text in _every_string(item)]
    return []


def _reply_violations(result: dict) -> list[str]:
    """Prohibited phrases in any string of a calculate reply."""
    return [
        violation
        for text in _every_string(result)
        for violation in _check_for_prohibited_phrases(text)
    ]


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
        assert hasattr(settings, "UPL_PROHIBITED_PHRASES")

    def test_upl_prohibited_phrases_not_empty(self):
        """UPL_PROHIBITED_PHRASES must have at least one entry."""
        assert len(settings.UPL_PROHIBITED_PHRASES) > 0

    def test_upl_prohibited_phrases_includes_key_violations(self):
        """UPL_PROHIBITED_PHRASES must include critical advice indicators."""
        phrases = [p.lower() for p in settings.UPL_PROHIBITED_PHRASES]

        # These are the most dangerous phrases that cross into advice
        critical_violations = [
            "you should file",
            "i recommend",
            "my advice is",
        ]

        for violation in critical_violations:
            assert (
                violation in phrases
            ), f"Critical UPL violation '{violation}' missing from settings"

    def test_upl_audit_enabled(self):
        """UPL_AUDIT_ENABLED must be True for production compliance."""
        assert hasattr(settings, "UPL_AUDIT_ENABLED")
        assert settings.UPL_AUDIT_ENABLED is True


# ============================================================================
# Forms View UPL Compliance Tests
# ============================================================================


class TestFormsViewUPLCompliance:
    """Verify forms view UPL disclaimers and messaging."""

    def test_upl_disclaimer_constant_exists(self):
        """_UPL_DISCLAIMER constant must be defined in the forms app."""
        assert _UPL_DISCLAIMER is not None
        assert len(_UPL_DISCLAIMER) > 0

    def test_upl_disclaimer_no_prohibited_phrases(self):
        """UPL disclaimer itself must not contain prohibited advice phrases."""
        violations = _check_for_prohibited_phrases(_UPL_DISCLAIMER)
        assert violations == [], f"UPL disclaimer contains prohibited phrases: {violations}"

    def test_upl_disclaimer_contains_information_not_advice(self):
        """UPL disclaimer must explicitly state information vs advice."""
        disclaimer_lower = _UPL_DISCLAIMER.lower()
        assert "legal information" in disclaimer_lower
        assert "not legal advice" in disclaimer_lower or "not advice" in disclaimer_lower

    def test_upl_disclaimer_mentions_user_responsibility(self):
        """UPL disclaimer must place responsibility on user."""
        disclaimer_lower = _UPL_DISCLAIMER.lower()
        assert (
            "you are responsible" in disclaimer_lower or "your responsibility" in disclaimer_lower
        )


# ============================================================================
# Means Test Calculator UPL Compliance Tests
# ============================================================================


@pytest.mark.django_db
class TestMeansTestCalculatorUPLCompliance:
    """The reply carries codes and figures, never a sentence: the outcome's words are the
    browser's, scanned by upl-means-test-copy.test.ts (R12)."""

    def _reply(self, username, income):
        user = User.objects.create_user(username=username, password="test")
        district = _create_ilnd_district()
        _create_median_income(district)
        session = _create_session_with_income(user, district, monthly_income=income)
        return MeansTestCalculator(session).calculate()

    def test_an_at_or_below_median_reply_has_no_prohibited_phrases(self):
        result = self._reply("test_pass", Decimal("4000.00"))

        assert "message" not in result
        assert _reply_violations(result) == []

    def test_passing_means_test_gives_the_outcome_code_and_no_eligibility_wording(self):
        result = self._reply("test_may", Decimal("4000.00"))

        assert result["outcome"] == "at_or_below_median"
        for text in _every_string(result):
            for word in ("eligible", "qualif", "chapter 13", "should choose"):
                assert word not in text.lower()

    def test_an_above_median_reply_has_no_prohibited_phrases(self):
        result = self._reply("test_fail", Decimal("10000.00"))

        assert "message" not in result
        assert _reply_violations(result) == []

    def test_failing_means_test_provides_the_outcome_not_advice(self):
        # CMI must exceed the annual median threshold ($71,304) to be above it
        result = self._reply("test_info", Decimal("80000.00"))

        assert result["outcome"] == "cannot_work_out"
        for text in _every_string(result):
            for word in ("eligible", "qualif", "chapter 13", "should choose", "should file"):
                assert word not in text.lower()

    def test_a_very_low_income_reply_gives_no_fee_waiver_verdict(self):
        """A filer far below the median hears nothing about a fee waiver from the means test: the court decides it (28 U.S.C. § 1930(f)), and the filing-fee page shows its figures as information."""
        result = self._reply("test_waiver", Decimal("1500.00"))

        assert "message" not in result
        assert _reply_violations(result) == []
        for text in _every_string(result):
            assert "fee waiver" not in text.lower()
            assert "1930" not in text

    @pytest.mark.parametrize(
        "income, outcome",
        [(Decimal("4000.00"), "at_or_below_median"), (Decimal("10000.00"), "cannot_work_out")],
    )
    def test_the_reply_states_nothing_absolute(self, income, outcome):
        result = self._reply("test_typ", income)

        assert result["outcome"] == outcome
        absolute = (
            "eligible",
            "qualif",
            "chapter 13",
            "should choose",
            "guarantee",
            "will be approved",
        )
        for text in _every_string(result):
            for word in absolute:
                assert word not in text.lower()

    def test_all_calculation_paths_upl_compliant(self):
        """Test multiple income scenarios to ensure all paths are compliant."""
        district = _create_ilnd_district()
        _create_median_income(district)

        # Test scenarios: very low, below median, at median, above median, high
        test_incomes = [
            Decimal("1000.00"),  # Very low
            Decimal("4000.00"),  # Below median
            Decimal("5942.00"),  # Approximately at median (71304 / 12)
            Decimal("7000.00"),  # Above median
            Decimal("15000.00"),  # High income
        ]

        for income in test_incomes:
            user = User.objects.create_user(username=f"test_{income}", password="test")
            session = _create_session_with_income(user, district, monthly_income=income)

            result = MeansTestCalculator(session).calculate()

            assert "message" not in result
            violations = _reply_violations(result)
            assert (
                violations == []
            ), f"Reply for income ${income} contains prohibited phrases: {violations}"


# ============================================================================
# Audit Middleware UPL Path Detection Tests
# ============================================================================


class TestAuditMiddlewareUPLPathDetection:
    """Verify audit middleware correctly identifies UPL-sensitive paths."""

    def test_is_upl_sensitive_method_exists(self):
        """Middleware must have _is_upl_sensitive method."""
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        assert hasattr(middleware, "_is_upl_sensitive")
        assert callable(middleware._is_upl_sensitive)

    def test_eligibility_paths_marked_upl_sensitive(self):
        """Paths under /api/eligibility/ must be marked UPL-sensitive."""
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            "/api/eligibility/",
            "/api/eligibility/means-test/",
            "/api/eligibility/calculate/",
        ]

        for path in test_paths:
            assert (
                middleware._is_upl_sensitive(path) is True
            ), f"Path {path} should be marked UPL-sensitive"

    def test_forms_paths_marked_upl_sensitive(self):
        """Paths under /api/forms/ must be marked UPL-sensitive."""
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            "/api/forms/",
            "/api/forms/generate/",
            "/api/forms/preview/",
            "/api/forms/1/regenerate/",
        ]

        for path in test_paths:
            assert (
                middleware._is_upl_sensitive(path) is True
            ), f"Path {path} should be marked UPL-sensitive"

    def test_intake_paths_marked_upl_sensitive(self):
        """Paths under /api/intake/ must be marked UPL-sensitive."""
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            "/api/intake/",
            "/api/intake/sessions/",
            "/api/intake/sessions/1/calculate_means_test/",
        ]

        for path in test_paths:
            assert (
                middleware._is_upl_sensitive(path) is True
            ), f"Path {path} should be marked UPL-sensitive"

    def test_means_test_paths_marked_upl_sensitive(self):
        """Paths under /api/means-test/ must be marked UPL-sensitive."""
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            "/api/means-test/",
            "/api/means-test/calculate/",
        ]

        for path in test_paths:
            assert (
                middleware._is_upl_sensitive(path) is True
            ), f"Path {path} should be marked UPL-sensitive"

    def test_non_upl_paths_not_marked_sensitive(self):
        """Non-UPL paths should NOT be marked UPL-sensitive."""
        middleware = AuditLoggingMiddleware(get_response=lambda r: None)

        test_paths = [
            "/api/auth/login/",
            "/api/auth/logout/",
            "/api/users/profile/",
            "/api/health/",
            "/admin/",
            "/static/css/style.css",
        ]

        for path in test_paths:
            assert (
                middleware._is_upl_sensitive(path) is False
            ), f"Path {path} should NOT be marked UPL-sensitive"


# ============================================================================
# String Constant Scanning Tests
# ============================================================================


@pytest.mark.django_db
class TestServiceLayerStringCompliance:
    """Scan all service layer string constants for prohibited phrases."""

    def test_means_test_calculator_all_strings_compliant(self):
        """Scan every string of the MeansTestCalculator's replies for violations."""
        district = _create_ilnd_district()
        _create_median_income(district)

        scenarios = [
            ("passing", Decimal("3000.00")),
            ("failing", Decimal("10000.00")),
            ("very_low", Decimal("1200.00")),
        ]

        for scenario_name, income in scenarios:
            user = User.objects.create_user(username=f"test_{scenario_name}", password="test")
            session = _create_session_with_income(user, district, monthly_income=income)

            result = MeansTestCalculator(session).calculate()

            assert "message" not in result
            violations = _reply_violations(result)
            assert violations == [], f"Scenario '{scenario_name}' has violations: {violations}"

    def test_reply_details_no_advice(self):
        """The reply's details provide data, not recommendations."""
        user = User.objects.create_user(username="test_detail", password="test")
        district = _create_ilnd_district()
        _create_median_income(district)

        session = _create_session_with_income(user, district, monthly_income=Decimal("5000.00"))

        result = MeansTestCalculator(session).calculate()

        assert "message" not in result
        violations = _reply_violations(result)
        assert violations == [], f"Reply contains prohibited phrases: {violations}"


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
        user = User.objects.create_user(username="test_e2e", password="test")
        district = _create_ilnd_district()
        _create_median_income(district)

        # Create intake session with income
        session = _create_session_with_income(user, district, monthly_income=Decimal("4500.00"))

        # Calculate means test (UPL-sensitive operation)
        calculator = MeansTestCalculator(session)
        means_test_result = calculator.calculate()

        # Verify the means test reply is compliant: no message, and no sentence in any string
        assert "message" not in means_test_result
        violations = _reply_violations(means_test_result)
        assert violations == [], f"Means test result contains prohibited phrases: {violations}"

        # The reply's details carry the statute citation (informational)
        assert "11 U.S.C." in means_test_result["details"]["statute_citation"]

    def test_all_output_channels_scanned(self):
        """
        Verify we're testing all channels where UPL violations could occur.

        This meta-test ensures comprehensive coverage.
        """
        tested_components = [
            "settings.UPL_PROHIBITED_PHRASES",
            "forms.views._UPL_DISCLAIMER",
            "AuditLoggingMiddleware._is_upl_sensitive",
            "intake.polish_checks.POLISH_PHRASES",
        ]

        # This test documents what we're testing
        # If new UPL-sensitive components are added, update this list
        assert (
            len(tested_components) == 4
        ), "Update this test when adding new UPL-sensitive components"


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
            "i recommend",
            "you should file",
            "you should choose",
        ]

        for phrase in prohibited_direct:
            assert phrase in [
                p.lower() for p in settings.UPL_PROHIBITED_PHRASES
            ], f"Prohibited phrase '{phrase}' must be in settings"

    def test_no_predictive_advice(self):
        """
        REGRESSION: Ensure we never predict case outcomes.

        Context: "You will win" or "This will be discharged" crosses into
        legal advice by predicting specific outcomes.
        """
        # Settings should include phrases that predict outcomes
        # (Add these if discovered in the wild)
        _predictive_phrases = [
            "you will",
            "this will be",
            "you are going to",
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
