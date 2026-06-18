"""IRS National and Local Standards for means test expense deductions (2024)."""

from decimal import Decimal

NATIONAL_STANDARDS = {
    "food": {
        1: Decimal("713"),
        2: Decimal("904"),
        3: Decimal("1088"),
        4: Decimal("1289"),
        5: Decimal("1453"),
    },
    "health_care_under_65": {
        1: Decimal("73"),
        2: Decimal("146"),
        3: Decimal("146"),
        4: Decimal("146"),
        5: Decimal("146"),
    },
    "health_care_65_plus": {
        1: Decimal("164"),
        2: Decimal("164"),
        3: Decimal("164"),
        4: Decimal("164"),
        5: Decimal("164"),
    },
}

LOCAL_STANDARDS = {
    "ILND": {
        "housing": {
            1: Decimal("1730"),
            2: Decimal("1997"),
            3: Decimal("2049"),
            4: Decimal("2281"),
            5: Decimal("2302"),
        },
        "transport_owned": {1: Decimal("318"), 2: Decimal("636")},
        "transport_operating": Decimal("283"),
    },
}


def get_national_standard(category: str, family_size: int, age_under_65: bool = True) -> Decimal:
    key = category
    if category == "health_care":
        key = "health_care_under_65" if age_under_65 else "health_care_65_plus"
    family_size = min(family_size, 5)
    return NATIONAL_STANDARDS[key][family_size]


def get_local_standard(district_code: str, category: str, family_size: int = 1) -> Decimal | None:
    district = LOCAL_STANDARDS.get(district_code.upper())
    if not district:
        return None
    val = district.get(category)
    if isinstance(val, dict):
        family_size = min(family_size, 5)
        return val.get(family_size)
    return val


def get_housing_standard(district_code: str, family_size: int) -> Decimal | None:
    return get_local_standard(district_code, "housing", family_size)
