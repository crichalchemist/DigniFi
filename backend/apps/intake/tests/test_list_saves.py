"""Continue on the Contracts and Codebtors steps saves the whole list by id (DIG-147).

Business intent: Schedules G and H, and their yes/no answers, are read from these lists, and
the filer signs them under penalty of perjury. Each Continue sends the list the step shows:
a row carrying one of this session's ids updates in place, any other row is created, and a
stored row the list left out is deleted. So saving twice never lists one contract twice, a
removed row never lingers, one bad row saves nothing, and a row can only ever change the
filer's own session.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import Codebtor, ExecutoryContract, IntakeSession
from apps.users.models import User

# Each list's model, its name field and three rows a filer might enter.
LISTS = {
    "contracts": (
        ExecutoryContract,
        "counterparty_name",
        [
            {
                "counterparty_name": "Oak Street Apartments",
                "contract_type": "lease",
                "description": "Apartment lease",
            },
            {"counterparty_name": "Metro Gym", "contract_type": "contract", "description": ""},
            {"counterparty_name": "Lakeview Storage", "contract_type": "other", "description": ""},
        ],
    ),
    "codebtors": (
        Codebtor,
        "name",
        [
            {"name": "Sam Doe", "relationship": "relative", "city": "Chicago", "state": "IL"},
            {"name": "Ana Ruiz", "relationship": "friend"},
            {"name": "Lee Park", "relationship": "former_spouse", "zip_code": "60601"},
        ],
    ),
}


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


def _list_url(session, endpoint):
    return f"/api/intake/sessions/{session.pk}/{endpoint}/"


def _save_twice_as_the_wizard_does(client, session, endpoint):
    """Continue, then Continue again with the rows the first save returned, one renamed."""
    model, name, rows = LISTS[endpoint]
    url = _list_url(session, endpoint)

    first = client.put(url, rows[:2], format="json")
    assert first.status_code == 200
    first_ids = [row["id"] for row in first.data]

    again = [dict(row) for row in first.data]
    again[0][name] = "Renamed Party"
    second = client.put(url, again, format="json")

    assert second.status_code == 200
    assert [row["id"] for row in second.data] == first_ids
    stored = model.objects.filter(session=session).order_by("id")
    assert list(stored.values_list("pk", flat=True)) == first_ids
    assert [getattr(row, name) for row in stored] == ["Renamed Party", rows[1][name]]


def test_second_save_does_not_duplicate_codebtors(filer):
    client, session = filer
    _save_twice_as_the_wizard_does(client, session, "codebtors")


def test_second_save_does_not_duplicate_contracts(filer):
    client, session = filer
    _save_twice_as_the_wizard_does(client, session, "contracts")


@pytest.mark.parametrize("endpoint", ["contracts", "codebtors"])
def test_saving_a_list_keeps_sent_rows_adds_new_ones_and_drops_removed_ones(filer, endpoint):
    client, session = filer
    model, name, rows = LISTS[endpoint]
    kept = model.objects.create(session=session, **rows[0])
    removed = model.objects.create(session=session, **rows[1])

    response = client.put(
        _list_url(session, endpoint), [{"id": kept.pk, **rows[0]}, rows[2]], format="json"
    )

    assert response.status_code == 200
    stored = {getattr(row, name): row for row in model.objects.filter(session=session)}
    assert set(stored) == {rows[0][name], rows[2][name]}
    assert stored[rows[0][name]].pk == kept.pk
    assert not model.objects.filter(pk=removed.pk).exists()
    assert [row[name] for row in response.data] == [rows[0][name], rows[2][name]]


@pytest.mark.parametrize("endpoint", ["contracts", "codebtors"])
def test_removing_every_row_leaves_none_stored_and_reopens_the_intake(filer, endpoint):
    # An empty list means the filer said none: a removed last lease or codebtor must not
    # stay stored and print on Schedule G or H.
    client, session = filer
    model, _, rows = LISTS[endpoint]
    model.objects.create(session=session, **rows[0])
    model.objects.create(session=session, **rows[1])
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")

    response = client.put(_list_url(session, endpoint), [], format="json")

    assert response.status_code == 200
    assert response.data == []
    assert not model.objects.filter(session=session).exists()
    assert IntakeSession.objects.get(pk=session.pk).status == "in_progress"


@pytest.mark.parametrize(
    "endpoint,bad_row",
    [
        ("contracts", {"counterparty_name": "", "contract_type": "lease"}),
        ("codebtors", {"name": "Lee Park", "zip_code": "60601-1234-99"}),
    ],
)
def test_a_list_with_one_bad_row_saves_nothing(filer, endpoint, bad_row):
    client, session = filer
    model, name, rows = LISTS[endpoint]
    stored = model.objects.create(session=session, **rows[0])
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")

    response = client.put(
        _list_url(session, endpoint),
        [{"id": stored.pk, **rows[0], name: "Renamed Party"}, rows[1], bad_row],
        format="json",
    )

    assert response.status_code == 400
    assert list(model.objects.filter(session=session)) == [stored]
    stored.refresh_from_db()
    assert getattr(stored, name) == rows[0][name]
    assert IntakeSession.objects.get(pk=session.pk).status == "completed"


@pytest.mark.parametrize("endpoint", ["contracts", "codebtors"])
def test_a_list_row_carrying_another_users_row_id_never_changes_that_row(
    filer, other_session, endpoint
):
    client, session = filer
    model, name, rows = LISTS[endpoint]
    theirs = model.objects.create(session=other_session, **rows[0])

    response = client.put(
        _list_url(session, endpoint), [{"id": theirs.pk, **rows[1]}], format="json"
    )

    assert response.status_code == 200
    theirs.refresh_from_db()
    assert theirs.session_id == other_session.pk
    assert getattr(theirs, name) == rows[0][name]
    mine = model.objects.get(session=session)
    assert mine.pk != theirs.pk
    assert getattr(mine, name) == rows[1][name]


@pytest.mark.parametrize("endpoint", ["contracts", "codebtors"])
def test_filer_cannot_save_a_list_onto_another_users_intake(filer, other_session, endpoint):
    client, _ = filer
    _, _, rows = LISTS[endpoint]

    response = client.put(_list_url(other_session, endpoint), rows[:1], format="json")

    assert response.status_code == 404
    assert not LISTS[endpoint][0].objects.filter(session=other_session).exists()
