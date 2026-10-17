"""Saving the Assets and Amounts Owed steps updates rows in place (DIG-21, DIG-37).

Business intent: the wizard sends back the rows it loaded. A row must keep what the
browser never receives (the encrypted account number, the link to the scanned bill),
a corrected amount must save instead of crashing, and a nested row can only ever
change the filer's own session.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents.models import DocumentType, UploadedDocument
from apps.intake.models import AssetInfo, DebtInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def district(db):
    return District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def filer(district):
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


@pytest.fixture
def other_session(district):
    other = User.objects.create_user(username="other", password="pw")
    return IntakeSession.objects.create(user=other, district=district)


def _scanned_car_loan(session):
    bill = UploadedDocument.objects.create(
        session=session,
        uploaded_by=session.user,
        document_type=DocumentType.CREDITOR_BILL,
        file="bill.pdf",
        original_filename="Ally_bill.pdf",
        file_size=100,
        mime_type="application/pdf",
    )
    return DebtInfo.objects.create(
        session=session,
        creditor_name="Ally Auto",
        debt_type="auto_loan",
        priority_classification="secured",
        account_number="4111222233334444",
        amount_owed=Decimal("500.00"),
        is_secured=True,
        source_document=bill,
        is_draft=True,
    )


def _checking_account(session):
    return AssetInfo.objects.create(
        session=session,
        asset_type="bank_account",
        description="Checking",
        current_value=Decimal("800.00"),
        amount_owed=Decimal("0.00"),
        account_number="998877",
        financial_institution="First Bank",
    )


def _session_url(session):
    return f"/api/intake/sessions/{session.pk}/"


def _rows_as_received(client, session, key):
    """The nested rows exactly as the wizard receives them from GET."""
    response = client.get(_session_url(session))
    assert response.status_code == 200
    return [dict(row) for row in response.data[key]]


def test_filer_can_correct_the_amount_on_a_debt_loaded_from_the_server(filer):
    client, session = filer
    debt = _scanned_car_loan(session)
    [row] = _rows_as_received(client, session, "debts")
    row["amount_owed"] = "650.00"

    response = client.patch(_session_url(session), {"debts": [row]}, format="json")

    assert response.status_code == 200
    saved = DebtInfo.objects.get(session=session)
    assert saved.pk == debt.pk
    assert saved.amount_owed == Decimal("650.00")


def test_filer_can_correct_the_value_of_an_asset_loaded_from_the_server(filer):
    client, session = filer
    asset = _checking_account(session)
    [row] = _rows_as_received(client, session, "assets")
    row["current_value"] = "950.00"

    response = client.patch(_session_url(session), {"assets": [row]}, format="json")

    assert response.status_code == 200
    saved = AssetInfo.objects.get(session=session)
    assert saved.pk == asset.pk
    assert saved.current_value == Decimal("950.00")


def test_resaving_a_session_exactly_as_received_keeps_amounts_account_numbers_and_scan_links(
    filer,
):
    client, session = filer
    debt = _scanned_car_loan(session)
    asset = _checking_account(session)
    received = client.get(_session_url(session)).data

    response = client.patch(
        _session_url(session),
        {"debts": received["debts"], "assets": received["assets"]},
        format="json",
    )

    assert response.status_code == 200
    kept_debt = DebtInfo.objects.get(session=session)
    assert kept_debt.pk == debt.pk
    assert kept_debt.amount_owed == Decimal("500.00")
    assert kept_debt.account_number == "4111222233334444"
    assert kept_debt.source_document_id == debt.source_document_id
    assert kept_debt.is_secured is True
    kept_asset = AssetInfo.objects.get(session=session)
    assert kept_asset.pk == asset.pk
    assert kept_asset.current_value == Decimal("800.00")
    assert kept_asset.amount_owed == Decimal("0.00")
    assert kept_asset.account_number == "998877"


def test_saving_amounts_owed_keeps_sent_rows_adds_new_ones_and_drops_removed_ones(filer):
    client, session = filer
    kept = DebtInfo.objects.create(
        session=session,
        creditor_name="Kept Card",
        debt_type="credit_card",
        amount_owed=Decimal("100.00"),
        account_number="1111",
    )
    removed = DebtInfo.objects.create(
        session=session,
        creditor_name="Paid Off Clinic",
        debt_type="medical",
        amount_owed=Decimal("50.00"),
    )

    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {"id": kept.pk, "creditor_name": "Kept Card"},
                {"creditor_name": "New Clinic", "debt_type": "medical", "amount_owed": "75.00"},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    rows = {d.creditor_name: d for d in DebtInfo.objects.filter(session=session)}
    assert set(rows) == {"Kept Card", "New Clinic"}
    assert rows["Kept Card"].pk == kept.pk
    assert rows["Kept Card"].account_number == "1111"
    assert rows["New Clinic"].amount_owed == Decimal("75.00")
    assert not DebtInfo.objects.filter(pk=removed.pk).exists()


def test_saving_assets_keeps_sent_rows_adds_new_ones_and_drops_removed_ones(filer):
    client, session = filer
    kept = _checking_account(session)
    removed = AssetInfo.objects.create(
        session=session,
        asset_type="vehicle",
        description="Sold Car",
        current_value=Decimal("3000.00"),
    )

    response = client.patch(
        _session_url(session),
        {
            "assets": [
                {"id": kept.pk, "description": "Checking"},
                {"asset_type": "vehicle", "description": "New Car", "current_value": "4500.00"},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    rows = {a.description: a for a in AssetInfo.objects.filter(session=session)}
    assert set(rows) == {"Checking", "New Car"}
    assert rows["Checking"].pk == kept.pk
    assert rows["Checking"].account_number == "998877"
    assert rows["New Car"].current_value == Decimal("4500.00")
    assert not AssetInfo.objects.filter(pk=removed.pk).exists()


def test_a_nested_row_naming_another_users_session_lands_on_the_owners_session_only(
    filer, other_session
):
    client, session = filer

    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "session": other_session.pk,
                    "creditor_name": "Owner Clinic",
                    "debt_type": "medical",
                    "amount_owed": "75.00",
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert not DebtInfo.objects.filter(session=other_session).exists()
    assert DebtInfo.objects.get(session=session).creditor_name == "Owner Clinic"


def test_a_nested_row_carrying_another_users_row_id_never_changes_that_row(filer, other_session):
    client, session = filer
    their_debt = DebtInfo.objects.create(
        session=other_session,
        creditor_name="Their Bank",
        debt_type="credit_card",
        amount_owed=Decimal("900.00"),
    )

    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "id": their_debt.pk,
                    "creditor_name": "Owner Clinic",
                    "debt_type": "medical",
                    "amount_owed": "75.00",
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    their_debt.refresh_from_db()
    assert their_debt.session_id == other_session.pk
    assert their_debt.creditor_name == "Their Bank"
    assert their_debt.amount_owed == Decimal("900.00")
    own = DebtInfo.objects.get(session=session)
    assert own.creditor_name == "Owner Clinic"
    assert own.pk != their_debt.pk


def _new_debt(name, amount):
    return {"creditor_name": name, "debt_type": "credit_card", "amount_owed": amount}


def test_a_save_hands_back_new_debts_in_the_order_they_were_sent_with_their_ids(filer):
    # The wizard pairs each row it sent with the response row at the same index, so a
    # new row learns its id and keeps it on every later save (DIG-273).
    client, session = filer
    kept = DebtInfo.objects.create(
        session=session, creditor_name="Kept", debt_type="medical", amount_owed=Decimal("40.00")
    )
    sent = [
        _new_debt("First new", "10.00"),
        {"id": kept.pk, **_new_debt("Kept", "40.00")},
        _new_debt("Second new", "900.00"),
        _new_debt("Third new", "5.00"),
        _new_debt("Fourth new", "300.00"),
    ]

    response = client.patch(_session_url(session), {"debts": sent}, format="json")

    assert response.status_code == 200
    assert [row["creditor_name"] for row in response.data["debts"]] == [
        row["creditor_name"] for row in sent
    ]
    assert response.data["debts"][1]["id"] == kept.pk
    stored = {debt.creditor_name: debt.pk for debt in DebtInfo.objects.filter(session=session)}
    assert [row["id"] for row in response.data["debts"]] == [
        stored[row["creditor_name"]] for row in sent
    ]
    assert all(row["is_draft"] is False for row in response.data["debts"])


def test_a_save_hands_back_assets_in_the_order_they_were_sent(filer):
    client, session = filer
    sent = [
        {"asset_type": "vehicle", "description": name, "current_value": value}
        for name, value in [("A", "10.00"), ("B", "7000.00"), ("C", "300.00"), ("D", "55.00")]
    ]

    response = client.patch(_session_url(session), {"assets": sent}, format="json")

    assert [row["description"] for row in response.data["assets"]] == ["A", "B", "C", "D"]
    stored = {a.description: a.pk for a in AssetInfo.objects.filter(session=session)}
    assert [row["id"] for row in response.data["assets"]] == [stored[n] for n in "ABCD"]


def test_a_row_sent_with_another_filers_id_comes_back_at_its_place_with_a_new_id(
    filer, other_session
):
    client, session = filer
    theirs = DebtInfo.objects.create(
        session=other_session,
        creditor_name="Their Bank",
        debt_type="credit_card",
        amount_owed=Decimal("900.00"),
    )
    sent = [
        _new_debt("Mine first", "1.00"),
        {"id": theirs.pk, **_new_debt("Mine second", "75.00")},
        _new_debt("Mine third", "2.00"),
    ]

    response = client.patch(_session_url(session), {"debts": sent}, format="json")

    names = [row["creditor_name"] for row in response.data["debts"]]
    assert names == ["Mine first", "Mine second", "Mine third"]
    assert theirs.pk not in [row["id"] for row in response.data["debts"]]
    assert len({row["id"] for row in response.data["debts"]}) == 3


def test_a_later_read_keeps_model_order_after_a_save_in_sent_order(filer):
    client, session = filer
    sent = [_new_debt(f"Debt {i}", f"{i * 37}.00") for i in range(1, 6)]
    client.patch(_session_url(session), {"debts": sent}, format="json")

    read = client.get(_session_url(session))

    assert [row["id"] for row in read.data["debts"]] == [
        debt.pk for debt in DebtInfo.objects.filter(session=session)
    ]


def test_a_save_carrying_only_assets_leaves_the_debts_in_model_order(filer):
    client, session = filer
    for i in range(1, 6):
        DebtInfo.objects.create(
            session=session,
            creditor_name=f"Debt {i}",
            debt_type="credit_card",
            amount_owed=Decimal(f"{i * 37}.00"),
        )
    sent = [
        {"asset_type": "vehicle", "description": name, "current_value": value}
        for name, value in [("A", "10.00"), ("B", "7000.00"), ("C", "300.00")]
    ]

    response = client.patch(_session_url(session), {"assets": sent}, format="json")

    assert [row["description"] for row in response.data["assets"]] == ["A", "B", "C"]
    assert [row["id"] for row in response.data["debts"]] == [
        debt.pk for debt in DebtInfo.objects.filter(session=session)
    ]


def test_a_stored_debt_left_out_of_the_sent_list_is_deleted_and_not_returned(filer):
    client, session = filer
    left_out = DebtInfo.objects.create(
        session=session, creditor_name="Left out", debt_type="medical", amount_owed=Decimal("40.00")
    )
    sent = [_new_debt("Only new", "10.00")]

    response = client.patch(_session_url(session), {"debts": sent}, format="json")

    assert [row["creditor_name"] for row in response.data["debts"]] == ["Only new"]
    assert not DebtInfo.objects.filter(pk=left_out.pk).exists()
