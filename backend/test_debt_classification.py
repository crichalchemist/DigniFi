#!/usr/bin/env python
"""Quick validation test for DebtInfo classification fields."""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

from django.contrib.auth import get_user_model
from apps.intake.models import DebtInfo, IntakeSession
from apps.districts.models import District

User = get_user_model()


def test_debt_classification():
    """Test consumer/business debt classification fields."""
    print("\n" + "="*70)
    print("Testing DebtInfo Consumer/Business Classification Fields")
    print("="*70)

    # Create test user
    user = User.objects.create_user(username='testuser', password='testpass123')
    print(f"✓ Created test user: {user.username}")

    # Get district
    district = District.objects.first()
    if not district:
        print("✗ No district found - skipping test (run fixtures first)")
        return False
    print(f"✓ Found district: {district.name}")

    # Create intake session
    session = IntakeSession.objects.create(user=user, district=district)
    print(f"✓ Created intake session: {session.id}")

    # Test 1: consumer_business_classification defaults to consumer
    print("\nTest 1: Default consumer classification")
    debt1 = DebtInfo.objects.create(
        session=session,
        creditor_name="Test Creditor",
        amount_owed=1000.00,
        debt_type="credit_card",
    )
    assert debt1.consumer_business_classification == "consumer", \
        f"Expected 'consumer', got '{debt1.consumer_business_classification}'"
    print(f"  ✓ Debt defaults to consumer classification")
    print(f"  ✓ __str__: {debt1}")

    # Test 2: Can mark debt as business
    print("\nTest 2: Business debt classification")
    debt2 = DebtInfo.objects.create(
        session=session,
        creditor_name="Business Vendor",
        amount_owed=5000.00,
        debt_type="other",
        consumer_business_classification="business",
    )
    assert debt2.consumer_business_classification == "business", \
        f"Expected 'business', got '{debt2.consumer_business_classification}'"
    print(f"  ✓ Can mark debt as business")
    print(f"  ✓ __str__: {debt2}")

    # Test 3: Secured debt with collateral
    print("\nTest 3: Secured debt with collateral")
    debt3 = DebtInfo.objects.create(
        session=session,
        creditor_name="Auto Lender",
        amount_owed=15000.00,
        debt_type="auto_loan",
        is_secured=True,
        collateral_description="2020 Honda Civic VIN: 1HGBH41JXMN109186",
    )
    assert debt3.is_secured is True, "Expected is_secured=True"
    assert debt3.collateral_description == "2020 Honda Civic VIN: 1HGBH41JXMN109186"
    print(f"  ✓ Secured debt with collateral")
    print(f"  ✓ Collateral: {debt3.collateral_description}")

    # Test 4: Priority debt
    print("\nTest 4: Priority unsecured debt")
    debt4 = DebtInfo.objects.create(
        session=session,
        creditor_name="IRS",
        amount_owed=8000.00,
        debt_type="other",
        is_priority=True,
    )
    assert debt4.is_priority is True, "Expected is_priority=True"
    print(f"  ✓ Priority debt flag works")

    # Test 5: Debt status flags
    print("\nTest 5: Debt status flags (contingent, unliquidated, disputed)")
    debt5 = DebtInfo.objects.create(
        session=session,
        creditor_name="Lawsuit Plaintiff",
        amount_owed=25000.00,
        debt_type="other",
        is_contingent=False,
        is_unliquidated=True,
        is_disputed=True,
    )
    assert debt5.is_contingent is False
    assert debt5.is_unliquidated is True
    assert debt5.is_disputed is True
    print(f"  ✓ Contingent: {debt5.is_contingent}")
    print(f"  ✓ Unliquidated: {debt5.is_unliquidated}")
    print(f"  ✓ Disputed: {debt5.is_disputed}")

    # Test 6: Date incurred
    print("\nTest 6: Date incurred tracking")
    from datetime import date
    debt6 = DebtInfo.objects.create(
        session=session,
        creditor_name="Old Creditor",
        amount_owed=3000.00,
        debt_type="credit_card",
        date_incurred=date(2023, 6, 15),
    )
    assert debt6.date_incurred == date(2023, 6, 15)
    print(f"  ✓ Date incurred: {debt6.date_incurred}")

    print("\n" + "="*70)
    print("ALL TESTS PASSED ✓")
    print("="*70 + "\n")

    # Cleanup
    user.delete()

    return True


if __name__ == '__main__':
    try:
        success = test_debt_classification()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
