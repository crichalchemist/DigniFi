"""Tests for IRS National and Local Standards."""

from decimal import Decimal

from apps.eligibility.services.irs_standards import (
    get_housing_standard,
    get_local_standard,
    get_national_standard,
)


def test_national_standard_food_size_1():
    assert get_national_standard("food", 1) == Decimal("713.00")


def test_national_standard_food_size_4():
    assert get_national_standard("food", 4) == Decimal("1289.00")


def test_national_standard_food_caps_at_5():
    assert get_national_standard("food", 5) == Decimal("1453.00")
    assert get_national_standard("food", 8) == Decimal("1453.00")


def test_national_standard_health_under_65():
    assert get_national_standard("health_care", 2, age_under_65=True) == Decimal("146.00")


def test_national_standard_health_over_65():
    assert get_national_standard("health_care", 2, age_under_65=False) == Decimal("164.00")


def test_local_standard_housing_ilnd():
    assert get_local_standard("ILND", "housing", 2) == Decimal("1997.00")


def test_local_standard_transport_owned_one_car():
    assert get_local_standard("ILND", "transport_owned", 1) == Decimal("318.00")


def test_local_standard_transport_operating():
    assert get_local_standard("ILND", "transport_operating") == Decimal("283.00")


def test_housing_standard_returns_none_for_unknown_district():
    assert get_housing_standard("ZZZZ", 1) is None
