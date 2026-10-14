"""Income saved as a $0 total becomes ten $0 amounts (forms step 2 spec §5.5, §7.8).

Before step 2 only the six-month total was stored, and nothing recorded the amount from each
source. A $0 total loses nothing when split: every source was $0. Any other total leaves
the ten amounts empty, so the Income step asks the filer to split it and income forms
refuse until they do. The old total itself is left as it is.
"""

from decimal import Decimal, InvalidOperation

from django.db import migrations

INCOME_SOURCES = [
    "monthly_gross_wages",
    "monthly_overtime",
    "monthly_tips",
    "monthly_rental_income",
    "monthly_pension",
    "monthly_social_security",
    "monthly_unemployment",
    "monthly_child_support",
    "monthly_alimony",
    "monthly_other_income",
]


def _saved_total_is_zero(months) -> bool:
    # No months saved means no total, not a $0 one.
    if not isinstance(months, list) or not months:
        return False
    try:
        return sum(Decimal(str(month)) for month in months) == 0
    except InvalidOperation:
        return False


def split_income_saved_as_zero(apps, schema_editor):
    IncomeInfo = apps.get_model("intake", "IncomeInfo")
    for income in IncomeInfo.objects.all():
        if _saved_total_is_zero(income.monthly_income):
            for field in INCOME_SOURCES:
                setattr(income, field, Decimal("0.00"))
            income.save(update_fields=INCOME_SOURCES)


class Migration(migrations.Migration):

    dependencies = [
        ("intake", "0013_incomeinfo_income_by_source"),
    ]

    operations = [
        migrations.RunPython(split_income_saved_as_zero, migrations.RunPython.noop),
    ]
