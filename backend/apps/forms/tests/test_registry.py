"""
Tests for the form registry.

The registry provides a single dispatch point mapping form_type strings
to generator classes, enabling dynamic form generation without hardcoded
conditional logic in the view layer.

Test Coverage:
  1. get_all_form_types() returns exactly 13 entries
  2. All 13 expected form type keys are present
  3. get_generator() with valid form_type returns correct generator class
  4. get_generator() with invalid form_type raises KeyError
  5. All generators have generate() method
  6. All generators have preview() method
  7. Registry values are all classes (not instances)
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.registry import (
    FORM_REGISTRY,
    get_all_form_types,
    get_generator,
)
from apps.forms.services import (
    Form101Generator,
    Form103BGenerator,
    Form106DecGenerator,
    Form106SumGenerator,
    Form107Generator,
    Form121Generator,
    Form122A1Generator,
    ScheduleABGenerator,
    ScheduleCGenerator,
    ScheduleDGenerator,
    ScheduleEFGenerator,
    ScheduleIGenerator,
    ScheduleJGenerator,
)
from apps.intake.models import DebtorInfo, IntakeSession

User = get_user_model()

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    """Create test user for session ownership."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def district(db):
    """Create test district with Chapter 7 filing fee."""
    return District.objects.create(
        code="ILND",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def session(user, district):
    """Create minimal intake session."""
    return IntakeSession.objects.create(
        user=user,
        district=district,
    )


@pytest.fixture
def session_with_debtor(session):
    """Create session with debtor info (required by most generators)."""
    DebtorInfo.objects.create(
        session=session,
        first_name="John",
        last_name="Doe",
        middle_name="Q",
        ssn="123-45-6789",
        date_of_birth=date(1980, 1, 1),
        phone="555-0100",
        email="john.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


# ── Registry Structure Tests ──────────────────────────────────────────


class TestRegistryStructure:
    """Test the registry data structure and basic operations."""

    def test_get_all_form_types_returns_13_entries(self):
        """
        Verify get_all_form_types() returns exactly 13 entries.

        DigniFi MVP supports 14 forms total (7 Official Forms + 7 Schedules),
        but 13 are in the registry (Schedule G/H combined as schedule_e_f).
        """
        form_types = get_all_form_types()
        assert len(form_types) == 13

    def test_all_expected_form_types_present(self):
        """Verify all 13 expected form type keys exist in registry."""
        expected_form_types = [
            "form_101",
            "form_103b",
            "form_106dec",
            "form_106sum",
            "form_107",
            "form_121",
            "form_122a1",
            "schedule_a_b",
            "schedule_c",
            "schedule_d",
            "schedule_e_f",
            "schedule_i",
            "schedule_j",
        ]

        actual_form_types = get_all_form_types()

        # Check all expected types are present
        for form_type in expected_form_types:
            assert (
                form_type in actual_form_types
            ), f"Missing form type: {form_type}"

        # Check no unexpected types
        for form_type in actual_form_types:
            assert (
                form_type in expected_form_types
            ), f"Unexpected form type: {form_type}"

    def test_registry_values_are_classes_not_instances(self):
        """Verify all registry values are classes, not instantiated objects."""
        for form_type, generator_cls in FORM_REGISTRY.items():
            assert isinstance(
                generator_cls, type
            ), f"{form_type} maps to instance, not class"

    def test_registry_values_are_correct_generator_classes(self):
        """Verify each form_type maps to the expected generator class."""
        expected_mappings = {
            "form_101": Form101Generator,
            "form_103b": Form103BGenerator,
            "form_106dec": Form106DecGenerator,
            "form_106sum": Form106SumGenerator,
            "form_107": Form107Generator,
            "form_121": Form121Generator,
            "form_122a1": Form122A1Generator,
            "schedule_a_b": ScheduleABGenerator,
            "schedule_c": ScheduleCGenerator,
            "schedule_d": ScheduleDGenerator,
            "schedule_e_f": ScheduleEFGenerator,
            "schedule_i": ScheduleIGenerator,
            "schedule_j": ScheduleJGenerator,
        }

        for form_type, expected_class in expected_mappings.items():
            actual_class = FORM_REGISTRY[form_type]
            assert (
                actual_class is expected_class
            ), f"{form_type} maps to {actual_class}, expected {expected_class}"


# ── get_generator() Tests ─────────────────────────────────────────────


@pytest.mark.django_db
class TestGetGenerator:
    """Test the get_generator() dispatch function."""

    def test_get_generator_with_valid_form_type_returns_instance(
        self, session_with_debtor
    ):
        """
        Verify get_generator() with valid form_type returns correct generator.

        Tests Form 101 (Voluntary Petition) as representative case.
        """
        generator = get_generator("form_101", session_with_debtor)

        assert isinstance(generator, Form101Generator)
        assert generator.intake_session == session_with_debtor

    def test_get_generator_with_invalid_form_type_raises_key_error(
        self, session_with_debtor
    ):
        """
        Verify get_generator() with invalid form_type raises KeyError.

        Invalid form types should fail fast with KeyError (not ValueError).
        """
        with pytest.raises(KeyError):
            get_generator("invalid_form_type", session_with_debtor)

    def test_get_generator_for_all_13_form_types(self, session_with_debtor):
        """Verify get_generator() works for all 13 registered form types."""
        expected_instances = {
            "form_101": Form101Generator,
            "form_103b": Form103BGenerator,
            "form_106dec": Form106DecGenerator,
            "form_106sum": Form106SumGenerator,
            "form_107": Form107Generator,
            "form_121": Form121Generator,
            "form_122a1": Form122A1Generator,
            "schedule_a_b": ScheduleABGenerator,
            "schedule_c": ScheduleCGenerator,
            "schedule_d": ScheduleDGenerator,
            "schedule_e_f": ScheduleEFGenerator,
            "schedule_i": ScheduleIGenerator,
            "schedule_j": ScheduleJGenerator,
        }

        for form_type, expected_class in expected_instances.items():
            generator = get_generator(form_type, session_with_debtor)
            assert isinstance(
                generator, expected_class
            ), f"{form_type} returned wrong instance type"

    def test_get_generator_returns_new_instance_each_call(
        self, session_with_debtor
    ):
        """
        Verify get_generator() returns new instances, not singletons.

        Each call should instantiate a fresh generator (stateless design).
        """
        generator1 = get_generator("form_101", session_with_debtor)
        generator2 = get_generator("form_101", session_with_debtor)

        assert generator1 is not generator2


# ── Generator Interface Tests ─────────────────────────────────────────


@pytest.mark.django_db
class TestGeneratorInterface:
    """Test that all generators implement required interface."""

    def test_all_generators_have_generate_method(self, session_with_debtor):
        """
        Verify all 13 generators have a generate() method.

        The generate() method is the primary interface for form production.
        """
        for form_type in get_all_form_types():
            generator = get_generator(form_type, session_with_debtor)
            assert hasattr(
                generator, "generate"
            ), f"{form_type} generator lacks generate() method"
            assert callable(
                generator.generate
            ), f"{form_type} generate is not callable"

    def test_all_generators_have_preview_method(self, session_with_debtor):
        """
        Verify all 13 generators have a preview() method.

        The preview() method enables user review before PDF generation.
        """
        for form_type in get_all_form_types():
            generator = get_generator(form_type, session_with_debtor)
            assert hasattr(
                generator, "preview"
            ), f"{form_type} generator lacks preview() method"
            assert callable(
                generator.preview
            ), f"{form_type} preview is not callable"

    def test_form_101_generator_methods_return_dict(
        self, session_with_debtor
    ):
        """
        Verify Form 101 generate() and preview() return dict structures.

        Tests representative generator to ensure proper return types.
        Other generators tested via test_form_*_generator.py files.
        """
        generator = get_generator("form_101", session_with_debtor)

        # Test generate() returns dict
        form_data = generator.generate()
        assert isinstance(
            form_data, dict
        ), "generate() should return dict structure"
        assert "debtor_name" in form_data
        assert "case_type" in form_data

        # Test preview() returns dict
        preview_data = generator.preview()
        assert isinstance(
            preview_data, dict
        ), "preview() should return dict structure"


# ── Edge Cases & Error Handling ───────────────────────────────────────


@pytest.mark.django_db
class TestRegistryEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_all_form_types_returns_list_not_dict_keys(self):
        """Verify get_all_form_types() returns list, not dict_keys view."""
        form_types = get_all_form_types()
        assert isinstance(form_types, list)

    def test_get_all_form_types_returns_consistent_order(self):
        """
        Verify get_all_form_types() returns consistent order.

        Python 3.7+ dicts maintain insertion order, so this should be stable.
        Helps ensure predictable filing order for generated forms.
        """
        first_call = get_all_form_types()
        second_call = get_all_form_types()
        assert first_call == second_call

    def test_registry_form_types_match_get_all_form_types(self):
        """Verify FORM_REGISTRY keys match get_all_form_types() output."""
        registry_keys = list(FORM_REGISTRY.keys())
        function_output = get_all_form_types()
        assert registry_keys == function_output

    @pytest.mark.parametrize(
        "invalid_form_type",
        [
            "form_999",  # Non-existent form number
            "FORM_101",  # Wrong case
            "form101",  # Missing underscore
            "",  # Empty string
            "schedule_g_h",  # Old naming (now schedule_e_f)
            None,  # None value (also raises KeyError in dict lookup)
        ],
    )
    def test_get_generator_rejects_invalid_form_types(
        self, session_with_debtor, invalid_form_type
    ):
        """
        Verify get_generator() rejects various invalid form type patterns.

        Parameterized test covers common error cases.
        """
        # All invalid form types raise KeyError from dict lookup
        with pytest.raises(KeyError):
            get_generator(invalid_form_type, session_with_debtor)
