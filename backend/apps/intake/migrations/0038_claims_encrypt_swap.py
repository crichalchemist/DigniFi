"""Drop the plaintext debt, contract and codebtor columns and take their names (3c2 spec
section 6.1, step 3)."""

from django.db import migrations

COLUMNS = {
    "debtinfo": [
        "creditor_name",
        "monthly_payment",
        "notes",
        "collateral_description",
        "date_incurred",
    ],
    "executorycontract": ["counterparty_name", "description"],
    "codebtor": ["name", "street_address", "city", "state", "zip_code", "relationship"],
}


def _swap():
    operations = []
    for model_name, names in COLUMNS.items():
        for name in names:
            operations.append(migrations.RemoveField(model_name=model_name, name=name))
        for name in names:
            operations.append(
                migrations.RenameField(
                    model_name=model_name, old_name=f"{name}_encrypted", new_name=name
                )
            )
    return operations


class Migration(migrations.Migration):
    dependencies = [
        ("intake", "0037_claims_encrypt_copy"),
    ]

    operations = _swap()
