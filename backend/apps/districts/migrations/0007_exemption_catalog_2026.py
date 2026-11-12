"""Load the Illinois and federal exemption laws as P.A. 104-120 left them (effective 2026-01-01)."""

from datetime import date

from django.db import migrations

# Kept here, not imported, because a migration must keep running the code it shipped with.
ILGA = "https://www.ilga.gov/legislation/ilcs/fulltext.asp?DocName="
ACT = "https://www.ilga.gov/documents/legislation/publicacts/104/PDF/104-0120.pdf"
S_12_1001 = ILGA + "073500050K12-1001"
CORNELL = "https://www.law.cornell.edu/uscode/text/"

CATALOG_2026 = {
    "effective_date": date(2026, 1, 1),
    # Open-ended: a new public act, not a calendar date, replaces the list.
    "valid_through": None,
    "source_url": ACT,
}

TIME_RULE = (
    "The right to a payment is exempt for at most 2 years after the right accrues. "
    "Property traced to the payment is exempt for at most 5 years after the payment accrues, "
    "and only up to its amount."
)

# (key, jurisdiction, citation, limit_text, source_url); position = index + 1.
# DRAFT: counsel C-8: the limit sentences (spec §5.1, B15)
LAWS_2026 = [
    ("il_40_5_4_135", "illinois", "40 ILCS 5/4-135", "", ILGA + "004000050K4-135"),
    ("il_215_5_238", "illinois", "215 ILCS 5/238", "", ILGA + "021500050K238"),
    ("il_305_5_11_3", "illinois", "305 ILCS 5/11-3", "", ILGA + "030500050K11-3"),
    (
        "il_735_5_12_901",
        "illinois",
        "735 ILCS 5/12-901",
        "Up to $50,000 for each person. When 2 or more people own the home, each is limited to "
        "their share of $100,000, by percentage of ownership.",
        ILGA + "073500050K12-901",
    ),
    (
        "il_735_5_12_1001_a",
        "illinois",
        "735 ILCS 5/12-1001(a)",
        "No total limit. A creditor may ask the court to take any one item with a resale value "
        "over $5,000, unless another part of this section exempts it. One piece of jewelry is "
        "exempt up to $5,000.",
        S_12_1001,
    ),
    ("il_735_5_12_1001_b", "illinois", "735 ILCS 5/12-1001(b)", "Up to $4,000.", S_12_1001),
    (
        "il_735_5_12_1001_c",
        "illinois",
        "735 ILCS 5/12-1001(c)",
        "Up to $3,600 in one motor vehicle.",
        S_12_1001,
    ),
    ("il_735_5_12_1001_d", "illinois", "735 ILCS 5/12-1001(d)", "Up to $2,250.", S_12_1001),
    ("il_735_5_12_1001_e", "illinois", "735 ILCS 5/12-1001(e)", "", S_12_1001),
    ("il_735_5_12_1001_f", "illinois", "735 ILCS 5/12-1001(f)", "", S_12_1001),
    ("il_735_5_12_1001_g1", "illinois", "735 ILCS 5/12-1001(g)(1)", "", S_12_1001),
    ("il_735_5_12_1001_g2", "illinois", "735 ILCS 5/12-1001(g)(2)", "", S_12_1001),
    ("il_735_5_12_1001_g3", "illinois", "735 ILCS 5/12-1001(g)(3)", "", S_12_1001),
    (
        "il_735_5_12_1001_g4",
        "illinois",
        "735 ILCS 5/12-1001(g)(4)",
        "Only what the person and their dependents reasonably need to live on.",
        S_12_1001,
    ),
    ("il_735_5_12_1001_h1", "illinois", "735 ILCS 5/12-1001(h)(1)", TIME_RULE, S_12_1001),
    (
        "il_735_5_12_1001_h2",
        "illinois",
        "735 ILCS 5/12-1001(h)(2)",
        "Only what the person reasonably needs to live on. " + TIME_RULE,
        S_12_1001,
    ),
    (
        "il_735_5_12_1001_h3",
        "illinois",
        "735 ILCS 5/12-1001(h)(3)",
        "Only what the person and their dependents reasonably need to live on. " + TIME_RULE,
        S_12_1001,
    ),
    (
        "il_735_5_12_1001_h4",
        "illinois",
        "735 ILCS 5/12-1001(h)(4)",
        "Up to $22,500. " + TIME_RULE,
        S_12_1001,
    ),
    ("il_735_5_12_1001_h5", "illinois", "735 ILCS 5/12-1001(h)(5)", TIME_RULE, S_12_1001),
    ("il_735_5_12_1001_i", "illinois", "735 ILCS 5/12-1001(i)", "", S_12_1001),
    ("il_735_5_12_1006", "illinois", "735 ILCS 5/12-1006", "", ILGA + "073500050K12-1006"),
    ("il_820_305_21", "illinois", "820 ILCS 305/21", "", ILGA + "082003050K21"),
    ("us_11_522_b3c", "federal", "11 U.S.C. § 522(b)(3)(C)", "", CORNELL + "11/522"),
    ("us_38_5301", "federal", "38 U.S.C. § 5301", "", CORNELL + "38/5301"),
    ("us_42_407", "federal", "42 U.S.C. § 407", "", CORNELL + "42/407"),
]


def load_2026(apps, schema_editor):
    catalog = apps.get_model("districts", "ExemptionCatalog").objects.create(**CATALOG_2026)
    apps.get_model("districts", "ExemptionLaw").objects.bulk_create(
        [
            apps.get_model("districts", "ExemptionLaw")(
                catalog=catalog,
                position=position,
                key=key,
                jurisdiction=jurisdiction,
                citation=citation,
                limit_text=limit_text,
                source_url=source_url,
            )
            for position, (key, jurisdiction, citation, limit_text, source_url) in enumerate(
                LAWS_2026, start=1
            )
        ]
    )


def unload_2026(apps, schema_editor):
    # The laws go with their catalog (CASCADE).
    apps.get_model("districts", "ExemptionCatalog").objects.filter(
        effective_date=CATALOG_2026["effective_date"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("districts", "0006_exemption_catalog"),
    ]

    operations = [
        migrations.RunPython(load_2026, unload_2026),
    ]
