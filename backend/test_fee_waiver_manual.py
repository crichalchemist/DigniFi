#!/usr/bin/env python
"""Manual test script for FeeWaiverApplication model."""

import os
import sys
import django

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

# Run migrations
from django.core.management import call_command
print("Running migrations...")
call_command('migrate', verbosity=0)
print("Migrations complete.\n")

from django.contrib.auth import get_user_model
from apps.intake.models import IntakeSession, FeeWaiverApplication
from apps.districts.models import District

User = get_user_model()


def test_fee_waiver_defaults_to_pending():
    """Test that fee waiver status defaults to pending."""
    print("\n=== Test 1: Fee waiver defaults to pending ===")

    user = User.objects.create_user(username='test1', password='test')
    district, _ = District.objects.get_or_create(
        code='ILND',
        defaults={
            'name': 'Northern District of Illinois',
            'state': 'IL',
            'court_name': 'U.S. Bankruptcy Court for the Northern District of Illinois',
            'pro_se_efiling_allowed': False,
            'filing_fee_chapter_7': 338.00,
        }
    )
    session = IntakeSession.objects.create(user=user, district=district)

    waiver = FeeWaiverApplication.objects.create(
        session=session,
        monthly_income=0.00,
        monthly_expenses=1200.00
    )

    assert waiver.status == 'pending', f"Expected 'pending', got '{waiver.status}'"
    print(f"✓ Status correctly defaults to 'pending': {waiver.status}")
    return True


def test_qualifies_for_waiver_with_zero_income():
    """Test that $0 income automatically qualifies for fee waiver."""
    print("\n=== Test 2: $0 income qualifies for waiver ===")

    user = User.objects.create_user(username='test2', password='test')
    district, _ = District.objects.get_or_create(
        code='ILND',
        defaults={
            'name': 'Northern District of Illinois',
            'state': 'IL',
            'court_name': 'U.S. Bankruptcy Court for the Northern District of Illinois',
            'pro_se_efiling_allowed': False,
            'filing_fee_chapter_7': 338.00,
        }
    )
    session = IntakeSession.objects.create(user=user, district=district)

    waiver = FeeWaiverApplication.objects.create(
        session=session,
        monthly_income=0.00,
        monthly_expenses=1200.00
    )

    threshold = waiver.get_poverty_threshold()
    print(f"Poverty threshold for 1 person: ${threshold}/month")
    print(f"Monthly income: ${waiver.monthly_income}")

    qualifies = waiver.qualifies_for_waiver()
    assert qualifies is True, f"Expected True, got {qualifies}"
    print(f"✓ $0 income correctly qualifies for waiver: {qualifies}")
    return True


def test_qualifies_for_waiver_with_public_benefits():
    """Test that receiving public benefits qualifies for waiver."""
    print("\n=== Test 3: Public benefits qualify for waiver ===")

    user = User.objects.create_user(username='test3', password='test')
    district, _ = District.objects.get_or_create(
        code='ILND',
        defaults={
            'name': 'Northern District of Illinois',
            'state': 'IL',
            'court_name': 'U.S. Bankruptcy Court for the Northern District of Illinois',
            'pro_se_efiling_allowed': False,
            'filing_fee_chapter_7': 338.00,
        }
    )
    session = IntakeSession.objects.create(user=user, district=district)

    waiver = FeeWaiverApplication.objects.create(
        session=session,
        monthly_income=800.00,
        monthly_expenses=1200.00,
        receives_public_benefits=True,
        benefit_types=['SNAP', 'Medicaid']
    )

    print(f"Monthly income: ${waiver.monthly_income}")
    print(f"Receives benefits: {waiver.receives_public_benefits}")
    print(f"Benefit types: {waiver.benefit_types}")

    qualifies = waiver.qualifies_for_waiver()
    assert qualifies is True, f"Expected True, got {qualifies}"
    print(f"✓ Public benefits correctly qualifies for waiver: {qualifies}")
    return True


def test_poverty_threshold_calculation():
    """Test poverty threshold calculation for various household sizes."""
    print("\n=== Test 4: Poverty threshold calculation ===")

    district, _ = District.objects.get_or_create(
        code='ILND',
        defaults={
            'name': 'Northern District of Illinois',
            'state': 'IL',
            'court_name': 'U.S. Bankruptcy Court for the Northern District of Illinois',
            'pro_se_efiling_allowed': False,
            'filing_fee_chapter_7': 338.00,
        }
    )

    test_cases = [
        (1, 1882.50),   # (15060 * 1.5) / 12
        (2, 2555.00),   # ((15060 + 5380) * 1.5) / 12
        (3, 3227.50),   # ((15060 + 5380*2) * 1.5) / 12
        (4, 3900.00),   # ((15060 + 5380*3) * 1.5) / 12
    ]

    for i, (household_size, expected_threshold) in enumerate(test_cases):
        user = User.objects.create_user(username=f'test4_{i}', password='test')
        session = IntakeSession.objects.create(user=user, district=district)

        waiver = FeeWaiverApplication.objects.create(
            session=session,
            household_size=household_size,
            monthly_income=0.00,
            monthly_expenses=1200.00
        )

        threshold = waiver.get_poverty_threshold()
        print(f"Household size {household_size}: ${threshold}/month (expected ${expected_threshold})")

        assert float(threshold) == expected_threshold, \
            f"Expected ${expected_threshold}, got ${threshold}"

    print("✓ All poverty threshold calculations correct")
    return True


def test_does_not_qualify_above_threshold():
    """Test that income above threshold does not qualify."""
    print("\n=== Test 5: Income above threshold does not qualify ===")

    user = User.objects.create_user(username='test5', password='test')
    district, _ = District.objects.get_or_create(
        code='ILND',
        defaults={
            'name': 'Northern District of Illinois',
            'state': 'IL',
            'court_name': 'U.S. Bankruptcy Court for the Northern District of Illinois',
            'pro_se_efiling_allowed': False,
            'filing_fee_chapter_7': 338.00,
        }
    )
    session = IntakeSession.objects.create(user=user, district=district)

    waiver = FeeWaiverApplication.objects.create(
        session=session,
        household_size=1,
        monthly_income=2000.00,  # Above $1,882.50 threshold
        monthly_expenses=1200.00,
        receives_public_benefits=False
    )

    threshold = waiver.get_poverty_threshold()
    print(f"Poverty threshold: ${threshold}/month")
    print(f"Monthly income: ${waiver.monthly_income}")

    qualifies = waiver.qualifies_for_waiver()
    assert qualifies is False, f"Expected False, got {qualifies}"
    print(f"✓ Income above threshold correctly does not qualify: {qualifies}")
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("RUNNING MANUAL TESTS FOR FeeWaiverApplication MODEL")
    print("="*60)

    tests = [
        test_fee_waiver_defaults_to_pending,
        test_qualifies_for_waiver_with_zero_income,
        test_qualifies_for_waiver_with_public_benefits,
        test_poverty_threshold_calculation,
        test_does_not_qualify_above_threshold,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
