"""Schedules D, E/F, G and H are the filer's sworn lists: their names, addresses, collateral and
dates are stored as ciphertext (3c spec section 6.1)."""

from decimal import Decimal

import pytest
from django.db import connection

from apps.intake.models import Codebtor, DebtInfo, ExecutoryContract

CIPHERTEXT = "gAAAAA"  # every Fernet token starts so

DEBT_COLUMNS = [
    "creditor_name",
    "monthly_payment",
    "notes",
    "collateral_description",
    "date_incurred",
]
CONTRACT_COLUMNS = ["counterparty_name", "description"]
CODEBTOR_COLUMNS = ["name", "street_address", "city", "state", "zip_code", "relationship"]


def _raw(table, columns, pk):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {', '.join(columns)} FROM {table} WHERE id = %s", [pk])
        return cursor.fetchone()


def test_every_debt_contract_and_codebtor_column_is_stored_as_ciphertext(filer):
    # Schedules D, E/F, G and H are the filer's sworn lists: names, addresses, collateral and
    # dates are filer data and must never sit in the table as plaintext (3c spec §6.1).
    client, session = filer
    response = client.patch(
        f"/api/intake/sessions/{session.pk}/",
        {
            "debts": [
                {
                    "creditor_name": "Prairie Card Services",
                    "debt_type": "credit_card",
                    "amount_owed": "1200.00",
                    "monthly_payment": "75.00",
                    "notes": "Opened in 2019",
                    "collateral_description": "2015 Honda Civic",
                }
            ]
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    contracts = client.put(
        f"/api/intake/sessions/{session.pk}/contracts/",
        [
            {
                "counterparty_name": "Oak Street Apartments",
                "contract_type": "lease",
                "description": "Apartment lease",
            }
        ],
        format="json",
    )
    assert contracts.status_code == 200, contracts.content
    codebtors = client.put(
        f"/api/intake/sessions/{session.pk}/codebtors/",
        [
            {
                "name": "Sam Doe",
                "street_address": "12 Elm St",
                "city": "Chicago",
                "state": "IL",
                "zip_code": "60601",
                "relationship": "relative",
            }
        ],
        format="json",
    )
    assert codebtors.status_code == 200, codebtors.content
    debt = DebtInfo.objects.get(session=session)
    debt.date_incurred = "2019–2025"  # the API doesn't take it yet
    debt.save()
    contract = ExecutoryContract.objects.get(session=session)
    codebtor = Codebtor.objects.get(session=session)

    typed = {
        "debt_info": (
            debt.pk,
            DEBT_COLUMNS,
            ["Prairie Card Services", "75.00", "Opened in 2019", "2015 Honda Civic", "2019–2025"],
        ),
        "executory_contracts": (
            contract.pk,
            CONTRACT_COLUMNS,
            ["Oak Street Apartments", "Apartment lease"],
        ),
        "codebtors": (
            codebtor.pk,
            CODEBTOR_COLUMNS,
            ["Sam Doe", "12 Elm St", "Chicago", "IL", "60601", "relative"],
        ),
    }
    for table, (pk, columns, plaintexts) in typed.items():
        raw = _raw(table, columns, pk)
        assert all(str(value).startswith(CIPHERTEXT) for value in raw), table
        # Full typed strings only: a short word can occur by chance in base64 ciphertext.
        for value in raw:
            for plaintext in plaintexts:
                if len(plaintext) > 4:
                    assert plaintext not in str(value), (table, plaintext)

    debt.refresh_from_db()
    assert debt.monthly_payment == Decimal("75.00")
    assert debt.date_incurred == "2019–2025"
    assert (debt.creditor_name, debt.notes, debt.collateral_description) == (
        "Prairie Card Services",
        "Opened in 2019",
        "2015 Honda Civic",
    )
    contract.refresh_from_db()
    assert (contract.counterparty_name, contract.description) == (
        "Oak Street Apartments",
        "Apartment lease",
    )
    codebtor.refresh_from_db()
    assert (codebtor.name, codebtor.street_address, codebtor.city) == (
        "Sam Doe",
        "12 Elm St",
        "Chicago",
    )
    assert (codebtor.state, codebtor.zip_code, codebtor.relationship) == ("IL", "60601", "relative")


def test_a_monthly_payment_below_zero_is_refused_and_a_cleared_one_is_emptied(filer):
    client, session = filer
    url = f"/api/intake/sessions/{session.pk}/"
    refused = client.patch(
        url,
        {
            "debts": [
                {
                    "creditor_name": "Prairie Card Services",
                    "debt_type": "credit_card",
                    "amount_owed": "1200.00",
                    "monthly_payment": "-5.00",
                }
            ]
        },
        format="json",
    )
    assert refused.status_code == 400
    assert not DebtInfo.objects.filter(session=session).exists()

    debt = DebtInfo.objects.create(
        session=session,
        creditor_name="Prairie Card Services",
        debt_type="credit_card",
        amount_owed=Decimal("1200.00"),
        monthly_payment=Decimal("75.00"),
    )
    cleared = client.patch(
        url, {"debts": [{"id": debt.pk, "monthly_payment": None}]}, format="json"
    )
    assert cleared.status_code == 200, cleared.content
    debt.refresh_from_db()
    assert debt.monthly_payment is None


@pytest.mark.parametrize(
    ("endpoint", "row"),
    [
        ("codebtors", {"name": "Lee Park", "state": "ILL"}),
        ("codebtors", {"name": "L" * 256}),
        ("codebtors", {"name": "Lee Park", "city": "C" * 101}),
        ("codebtors", {"name": "Lee Park", "relationship": "cousin"}),
        ("contracts", {"counterparty_name": "O" * 256, "contract_type": "lease"}),
    ],
)
def test_a_contract_or_codebtor_value_wider_than_its_old_column_is_refused(filer, endpoint, row):
    # Undoing the migration must never meet a value wider than the old column.
    client, session = filer
    response = client.put(f"/api/intake/sessions/{session.pk}/{endpoint}/", [row], format="json")
    assert response.status_code == 400
    assert not ExecutoryContract.objects.filter(session=session).exists()
    assert not Codebtor.objects.filter(session=session).exists()


@pytest.mark.parametrize("path", ["session_patch", "debt_viewset"])
@pytest.mark.parametrize(
    "wide",
    [{"creditor_name": "P" * 256}, {"monthly_payment": "12345678901"}],
)
def test_a_debt_wider_than_its_old_column_is_refused_on_every_debt_write_path(filer, path, wide):
    # Undoing the migration must never meet a value wider than the old column.
    client, session = filer
    row = {
        "creditor_name": "Prairie Card Services",
        "debt_type": "credit_card",
        "amount_owed": "1200.00",
    } | wide
    if path == "session_patch":
        response = client.patch(
            f"/api/intake/sessions/{session.pk}/", {"debts": [row]}, format="json"
        )
    else:
        response = client.post("/api/intake/debts/", {**row, "session": session.pk}, format="json")
    assert response.status_code == 400
    assert not DebtInfo.objects.filter(session=session).exists()
