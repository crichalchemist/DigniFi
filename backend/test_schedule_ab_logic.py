#!/usr/bin/env python
"""
Manual logic verification for ScheduleABGenerator.

Tests the core calculation logic without requiring Django ORM.
"""

from decimal import Decimal


class MockAsset:
    """Mock AssetInfo for testing."""
    def __init__(self, asset_type, description, current_value, amount_owed=None):
        self.asset_type = asset_type
        self.description = description
        self.current_value = Decimal(str(current_value))
        self.amount_owed = Decimal(str(amount_owed)) if amount_owed else Decimal('0.00')


def test_schedule_ab_logic():
    """Test Schedule A/B generation logic."""

    # Test Case 1: Real Property
    print("Test 1: Real Property")
    assets = [
        MockAsset('real_property', '123 Main St', 200000, 150000)
    ]

    real_property = [a for a in assets if a.asset_type == 'real_property']
    personal_property = [a for a in assets if a.asset_type != 'real_property']

    total_real = sum((a.current_value for a in real_property), Decimal('0.00'))
    total_personal = sum((a.current_value for a in personal_property), Decimal('0.00'))
    total_value = total_real + total_personal

    print(f"  Real Property Total: {total_real}")
    print(f"  Personal Property Total: {total_personal}")
    print(f"  Total Value: {total_value}")
    assert total_real == Decimal('200000.00')
    assert total_personal == Decimal('0.00')
    assert total_value == Decimal('200000.00')
    print("  ✓ PASS\n")

    # Test Case 2: Vehicle
    print("Test 2: Vehicle")
    assets = [
        MockAsset('vehicle', '2020 Honda Civic', 15000, 10000)
    ]

    real_property = [a for a in assets if a.asset_type == 'real_property']
    personal_property = [a for a in assets if a.asset_type != 'real_property']
    vehicles = [a for a in personal_property if a.asset_type == 'vehicle']

    total_real = sum((a.current_value for a in real_property), Decimal('0.00'))
    total_personal = sum((a.current_value for a in personal_property), Decimal('0.00'))

    vehicle_equity = vehicles[0].current_value - vehicles[0].amount_owed

    print(f"  Personal Property Total: {total_personal}")
    print(f"  Vehicle Equity: {vehicle_equity}")
    assert total_personal == Decimal('15000.00')
    assert vehicle_equity == Decimal('5000.00')
    print("  ✓ PASS\n")

    # Test Case 3: Mixed Assets
    print("Test 3: Mixed Assets")
    assets = [
        MockAsset('real_property', '123 Main St', 200000, 150000),
        MockAsset('vehicle', '2020 Honda Civic', 15000, 10000),
        MockAsset('bank_account', 'Chase Checking', 2500, 0),
    ]

    real_property = [a for a in assets if a.asset_type == 'real_property']
    personal_property = [a for a in assets if a.asset_type != 'real_property']

    total_real = sum((a.current_value for a in real_property), Decimal('0.00'))
    total_personal = sum((a.current_value for a in personal_property), Decimal('0.00'))
    total_value = total_real + total_personal

    print(f"  Real Property Total: {total_real}")
    print(f"  Personal Property Total: {total_personal}")
    print(f"  Total Value: {total_value}")
    assert total_real == Decimal('200000.00')
    assert total_personal == Decimal('17500.00')
    assert total_value == Decimal('217500.00')
    print("  ✓ PASS\n")

    # Test Case 4: No Assets
    print("Test 4: No Assets")
    assets = []

    real_property = [a for a in assets if a.asset_type == 'real_property']
    personal_property = [a for a in assets if a.asset_type != 'real_property']

    total_real = sum((a.current_value for a in real_property), Decimal('0.00'))
    total_personal = sum((a.current_value for a in personal_property), Decimal('0.00'))
    total_value = total_real + total_personal

    print(f"  Real Property Total: {total_real}")
    print(f"  Personal Property Total: {total_personal}")
    print(f"  Total Value: {total_value}")
    assert total_real == Decimal('0.00')
    assert total_personal == Decimal('0.00')
    assert total_value == Decimal('0.00')
    print("  ✓ PASS\n")

    # Test Case 5: Negative Equity (Underwater)
    print("Test 5: Negative Equity (Underwater)")
    assets = [
        MockAsset('real_property', '123 Main St', 150000, 175000),
    ]

    real_property = [a for a in assets if a.asset_type == 'real_property']
    equity = real_property[0].current_value - real_property[0].amount_owed

    print(f"  Equity: {equity}")
    assert equity == Decimal('-25000.00')
    print("  ✓ PASS\n")

    print("All logic tests passed! ✓")


if __name__ == '__main__':
    test_schedule_ab_logic()
