"""Load the U.S. Trustee's means test standards for cases filed on or after 2026-07-15."""

from datetime import date
from decimal import Decimal

from django.db import migrations

# Kept here, not imported, because a migration must keep running the code it shipped with.
# Read from the U.S. Trustee's pages for cases filed on or after July 15, 2026 (spec Appendix A);
# the Trustee spells LaSalle 'La Salle' and this district 'ILN'.
STANDARDS_2026 = {
    "effective_date": date(2026, 7, 15),
    "valid_through": None,
    "source_url": "https://www.justice.gov/ust/means-testing/20260715",
}
NATIONAL = (867, 1558, 1857, 2176)
NATIONAL_EXTRA = 397  # food, clothing and other items
FIVE_PERCENT = (30, 53, 64, 76)
FIVE_PERCENT_EXTRA = 14  # 5% of food and clothing (line 30's cap)
HEALTH = {"under_65": 90, "65_or_older": 163}  # per person
# county: ((insurance and operating, mortgage or rent) for 1, 2, 3, 4, 5 or more people)
HOUSING = {
    "Cook": ((691, 1608), (811, 1889), (855, 1990), (953, 2219), (968, 2255)),
    "DuPage": ((600, 1854), (704, 2178), (742, 2295), (827, 2559), (841, 2600)),
    "Grundy": ((632, 1449), (743, 1701), (783, 1792), (873, 1998), (887, 2030)),
    "Kane": ((615, 1672), (722, 1964), (761, 2069), (848, 2307), (862, 2344)),
    "Kendall": ((632, 1662), (743, 1951), (783, 2056), (872, 2293), (887, 2330)),
    "Lake": ((614, 1886), (721, 2215), (760, 2334), (848, 2602), (861, 2645)),
    "LaSalle": ((622, 990), (730, 1163), (769, 1226), (858, 1366), (871, 1389)),
    "Will": ((631, 1655), (741, 1944), (780, 2049), (870, 2284), (884, 2321)),
    "Boone": ((561, 1188), (658, 1396), (694, 1470), (773, 1640), (786, 1666)),
    "Carroll": ((638, 741), (749, 871), (790, 917), (880, 1023), (895, 1039)),
    "DeKalb": ((600, 1351), (705, 1587), (743, 1672), (829, 1864), (842, 1894)),
    "Jo Daviess": ((604, 990), (709, 1163), (747, 1226), (833, 1367), (846, 1389)),
    "Lee": ((645, 904), (757, 1062), (798, 1119), (889, 1248), (904, 1268)),
    "McHenry": ((604, 1581), (709, 1857), (747, 1957), (833, 2182), (847, 2217)),
    "Ogle": ((603, 1058), (708, 1243), (746, 1310), (832, 1460), (845, 1484)),
    "Stephenson": ((611, 860), (718, 1010), (757, 1064), (844, 1186), (857, 1206)),
    "Whiteside": ((615, 773), (722, 908), (761, 957), (848, 1068), (862, 1084)),
    "Winnebago": ((579, 977), (680, 1148), (716, 1210), (798, 1349), (811, 1371)),
}
CHICAGO = ("Cook", "DeKalb", "DuPage", "Grundy", "Kane", "Kendall", "Lake", "McHenry", "Will")
# The other nine counties use the Midwest Region figures.
OPERATING = {"chicago": (334, 668), "midwest": (263, 526)}  # one car, two cars
OWNERSHIP = (703, 1406)  # one car, two cars
PUBLIC_TRANSPORT = 220
MULTIPLIERS = {"ilnd": Decimal("6.9")}  # percent; the Trustee's "ILN"

# (kind, key, size, amount)
FIGURES_2026 = (
    [("national", "", size, amount) for size, amount in enumerate(NATIONAL, start=1)]
    + [("national_extra", "", 0, NATIONAL_EXTRA)]
    + [("five_percent", "", size, amount) for size, amount in enumerate(FIVE_PERCENT, start=1)]
    + [("five_percent_extra", "", 0, FIVE_PERCENT_EXTRA)]
    + [("health", key, 0, amount) for key, amount in HEALTH.items()]
    + [
        (kind, county, size, pair[column])
        for county, rows in HOUSING.items()
        for size, pair in enumerate(rows, start=1)
        for kind, column in (("housing_operating", 0), ("housing_mortgage", 1))
    ]
    + [
        ("operating", area, cars, amount)
        for area, amounts in OPERATING.items()
        for cars, amount in enumerate(amounts, start=1)
    ]
    + [("ownership", "", cars, amount) for cars, amount in enumerate(OWNERSHIP, start=1)]
    + [("public_transport", "", 0, PUBLIC_TRANSPORT)]
    + [("multiplier", code, 0, percent) for code, percent in MULTIPLIERS.items()]
)
# (county, area)
AREAS_2026 = [(county, "chicago" if county in CHICAGO else "midwest") for county in HOUSING]


def load_2026(apps, schema_editor):
    standards = apps.get_model("districts", "MeansStandards").objects.create(**STANDARDS_2026)
    figure = apps.get_model("districts", "MeansFigure")
    figure.objects.bulk_create(
        [
            figure(standards=standards, kind=kind, key=key, size=size, amount=amount)
            for kind, key, size, amount in FIGURES_2026
        ]
    )
    area_row = apps.get_model("districts", "MeansArea")
    area_row.objects.bulk_create(
        [area_row(standards=standards, county=county, area=area) for county, area in AREAS_2026]
    )


def unload_2026(apps, schema_editor):
    # The figures and areas go with their set (CASCADE).
    apps.get_model("districts", "MeansStandards").objects.filter(
        effective_date=STANDARDS_2026["effective_date"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("districts", "0009_means_standards"),
    ]

    operations = [
        migrations.RunPython(load_2026, unload_2026),
    ]
