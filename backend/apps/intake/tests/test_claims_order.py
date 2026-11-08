"""Schedules D and E/F list claims alphabetically by creditor (DIG-164).

Business intent: the creditor's name is ciphertext in the table, so no database sort can
put debts in the order the court's forms ask for. The order is decided in Python, and
every read of a session's debts must agree on it.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.claims import ordered_debts
from apps.intake.models import DebtInfo, IntakeSession
from apps.intake.views import DebtViewSet
from apps.users.models import User

SIX_NAMES = [
    "Zephyr Card",
    "alder Medical",
    "Émile Dental",
    "Birch Loans",
    "Eagle Credit",
    "chase Bank",
]
SIX_IN_ORDER = [
    "alder Medical",
    "Birch Loans",
    "chase Bank",
    "Eagle Credit",
    "Émile Dental",
    "Zephyr Card",
]


def _row(name, pk):
    return SimpleNamespace(creditor_name=name, pk=pk)


def _names(rows):
    return [row.creditor_name for row in ordered_debts(rows)]


def test_creditors_sort_by_their_letters_ignoring_case_and_accents():
    # D and E/F: "list the claims in alphabetical order according to the creditor's name"
    rows = [
        _row("zephyr Card", 1),
        _row("Émile Dental", 2),
        _row("alder Medical", 3),
        _row("Birch Loans", 4),
        _row("Eagle Credit", 5),
    ]
    assert _names(rows) == [
        "alder Medical",
        "Birch Loans",
        "Eagle Credit",
        "Émile Dental",
        "zephyr Card",
    ]


def test_debts_to_one_creditor_keep_their_order_by_id():
    rows = [_row("Chase", 9), _row("CHASE", 3), _row("Chàse", 5)]
    assert [row.pk for row in ordered_debts(rows)] == [3, 5, 9]


def test_a_name_typed_with_a_leading_space_sorts_by_its_first_letter():
    assert _names([_row(" Zephyr Card", 1), _row("Alder Medical", 2)]) == [
        "Alder Medical",
        " Zephyr Card",
    ]


@pytest.fixture
def filer(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session, user


def _make_debts(session, names):
    return [
        DebtInfo.objects.create(
            session=session,
            creditor_name=name,
            debt_type="credit_card",
            amount_owed=Decimal("100.00"),
        )
        for name in names
    ]


def test_a_session_read_lists_debts_by_creditor_from_their_encrypted_rows(filer):
    # Six names leave a database sort of the ciphertext a 1-in-720 chance of passing.
    client, session, _ = filer
    _make_debts(session, SIX_NAMES)

    response = client.get(f"/api/intake/sessions/{session.pk}/")

    assert [row["creditor_name"] for row in response.data["debts"]] == SIX_IN_ORDER


def test_a_re_save_keeps_the_debts_in_creditor_order(filer):
    client, session, _ = filer
    _make_debts(session, SIX_NAMES)
    url = f"/api/intake/sessions/{session.pk}/"
    rows = [dict(row) for row in client.get(url).data["debts"]]

    client.patch(url, {"debts": rows}, format="json")
    first = [row["creditor_name"] for row in client.get(url).data["debts"]]
    client.patch(url, {"debts": list(reversed(rows))}, format="json")
    second = [row["creditor_name"] for row in client.get(url).data["debts"]]

    assert first == SIX_IN_ORDER
    assert second == SIX_IN_ORDER


def test_the_debts_list_pages_through_rows_in_id_order(filer):
    client, session, user = filer
    _make_debts(session, sorted(SIX_NAMES, reverse=True))

    response = client.get("/api/intake/debts/")

    ids = [row["id"] for row in response.data["results"]]
    assert ids == sorted(ids)
    # Sqlite returns rowid order for an unordered query, so the API check alone can't
    # fail there; an empty order_by is what lets Postgres page rows in any order.
    queryset = DebtViewSet(request=SimpleNamespace(user=user)).get_queryset()
    assert list(queryset.query.order_by) == ["pk"]
