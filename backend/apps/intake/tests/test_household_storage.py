"""The household list and the county are stored encrypted, with stable ids (3e1 spec §4).

Business intent: each form counts the list its own way, so a row keeps exactly the answers the
filer gave. A missing answer saves, for Complete to name; only a value no answer can have is
refused. Ids are never reused, so the wizard can pair each row it sent with its id.
"""

from decimal import Decimal

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.districts.counties import ILND_COUNTIES
from apps.districts.models import District
from apps.intake.models import Household, IntakeSession
from apps.users.models import User

ROW_KEYS = ["id", "relationship", "age", "lives_with_you", "claimed_or_supported"]
SON = {"relationship": "son", "age": 8, "lives_with_you": True, "claimed_or_supported": True}
DAUGHTER = {**SON, "relationship": "daughter", "age": 5}
ROOMMATE = {**SON, "relationship": "roommate", "age": 29, "claimed_or_supported": False}
UNANSWERED = dict.fromkeys(["age", "lives_with_you", "claimed_or_supported"])


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
    client = APIClient()
    client.force_authenticate(user=user)
    return client, IntakeSession.objects.create(user=user, district=district)


def _url(session):
    return f"/api/intake/sessions/{session.pk}/"


def _save(client, session, household):
    return client.patch(_url(session), {"household": household}, format="json")


def _members(client, session, rows):
    """Save the list and return it as the reply gives it."""
    response = _save(client, session, {"members": rows})
    assert response.status_code == 200, response.data
    return response.data["household"]["members"]


def _ids(rows):
    return [row["id"] for row in rows]


def test_a_household_county_and_list_are_stored_as_ciphertext(filer):
    client, session = filer
    _save(client, session, {"county": "Cook", "members": [ROOMMATE]})
    household = Household.objects.get(session=session)
    with connection.cursor() as cursor:
        cursor.execute("SELECT county, members FROM household WHERE id = %s", [household.pk])
        county, members = cursor.fetchone()
    assert "Cook" not in county and "roommate" not in members
    assert household.county == "Cook"
    assert household.get_members()[0]["relationship"] == "roommate"


def test_each_new_row_gets_the_next_id_and_ids_are_never_reused(filer):
    client, session = filer
    first = _members(client, session, [SON, DAUGHTER, ROOMMATE])
    assert _ids(first) == [1, 2, 3]
    # The daughter is removed and a grandchild added: the new row gets 4, never 2.
    second = _members(client, session, [first[0], first[2], {"relationship": "grandchild"}])
    assert _ids(second) == [1, 3, 4]
    assert _ids(Household.objects.get(session=session).get_members()) == [1, 3, 4]


def test_a_sent_row_with_one_of_the_lists_ids_replaces_the_stored_row_whole(filer):
    client, session = filer
    [stored] = _members(client, session, [SON])
    # Unlike an asset or a debt row, an answer the row leaves out isn't kept.
    [replaced] = _members(client, session, [{"id": stored["id"], "relationship": "daughter"}])
    assert replaced == {"id": stored["id"], "relationship": "daughter", **UNANSWERED}


def test_a_row_with_an_id_the_list_doesnt_hold_gets_a_new_one(filer):
    client, session = filer
    _members(client, session, [SON, DAUGHTER, ROOMMATE])
    assert _ids(_members(client, session, [{**SON, "id": 99}])) == [4]


def test_an_id_sent_twice_keeps_it_only_once(filer):
    client, session = filer
    _members(client, session, [SON, DAUGHTER, ROOMMATE])
    twice = _members(client, session, [{**SON, "id": 1}, {**DAUGHTER, "id": 1}])
    assert [(r["id"], r["relationship"]) for r in twice] == [(1, "son"), (4, "daughter")]


def test_the_reply_lists_rows_in_the_order_sent_each_with_its_id(filer):
    client, session = filer
    son, daughter = _members(client, session, [SON, DAUGHTER])
    reply = _members(client, session, [daughter, ROOMMATE, son])
    assert [(r["id"], r["relationship"]) for r in reply] == [
        (2, "daughter"),
        (3, "roommate"),
        (1, "son"),
    ]
    assert client.get(_url(session)).data["household"]["members"] == reply


def test_only_the_spouses_row_carries_spouse_is_dependent(filer):
    client, session = filer
    spouse, son = _members(
        client,
        session,
        [
            {"relationship": "spouse", "age": 45, "spouse_is_dependent": False},
            {**SON, "spouse_is_dependent": None},  # a null on another row counts as absent
        ],
    )
    assert list(spouse) == [*ROW_KEYS, "spouse_is_dependent"]
    assert spouse["spouse_is_dependent"] is False
    assert list(son) == ROW_KEYS


@pytest.mark.parametrize(
    "members",
    [
        [{"relationship": "cousin", "age": 30}],
        [{"relationship": "son", "age": -1}],
        [{"relationship": "parent", "age": 121}],
        [{"relationship": "son", "age": 7.5}],
        [{"relationship": "spouse", "age": 45}, {"relationship": "spouse", "age": 44}],
        [{**SON, "spouse_is_dependent": False}],
        [SON] * 21,
    ],
    ids=[
        "unknown_relationship",
        "age_below_0",
        "age_above_120",
        "age_not_whole",
        "second_spouse",
        "spouse_question_on_a_son",
        "a_21st_row",
    ],
)
def test_a_value_no_answer_can_have_is_refused(filer, members):
    client, session = filer
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")

    response = _save(client, session, {"members": members})

    assert response.status_code == 400
    assert "members" in response.data["household"]
    assert IntakeSession.objects.get(pk=session.pk).status == "completed"  # nothing reopens
    assert not Household.objects.filter(session=session).exists()


def test_a_missing_answer_saves(filer):
    client, session = filer
    spouse, unknown = _members(client, session, [{"relationship": "spouse"}, {"age": 9}])
    assert spouse == {"id": 1, "relationship": "spouse", **UNANSWERED, "spouse_is_dependent": None}
    assert unknown == {"id": 2, "relationship": None, **UNANSWERED, "age": 9}
    assert list(spouse) == [*ROW_KEYS, "spouse_is_dependent"]
    assert list(unknown) == ROW_KEYS


def test_the_edges_of_each_limit_save(filer):
    client, session = filer
    edges = [{"relationship": "parent", "age": 120}, {"relationship": "son", "age": 0}]
    assert len(_members(client, session, edges + [ROOMMATE] * 18)) == 20


def test_a_county_outside_the_district_is_refused(filer):
    client, session = filer
    # The statute's spelling of a district county, not the one stored.
    assert _save(client, session, {"county": "Du Page"}).status_code == 400
    assert not Household.objects.filter(session=session).exists()
    assert _save(client, session, {"county": "DuPage"}).data["household"]["county"] == "DuPage"


def test_each_county_carries_its_division():
    # 3c prints the division on the List of Creditors' heading (3e1 spec §6, 28 U.S.C. § 93(a)).
    western = [
        "Boone",
        "Carroll",
        "DeKalb",
        "Jo Daviess",
        "Lee",
        "McHenry",
        "Ogle",
        "Stephenson",
        "Whiteside",
        "Winnebago",
    ]
    eastern = ["Cook", "DuPage", "Grundy", "Kane", "Kendall", "Lake", "LaSalle", "Will"]
    assert sorted(c for c, d in ILND_COUNTIES.items() if d == "Western") == sorted(western)
    assert sorted(c for c, d in ILND_COUNTIES.items() if d == "Eastern") == sorted(eastern)
    assert len(ILND_COUNTIES) == 18  # no county outside the two divisions


def test_a_household_patch_updates_only_the_keys_sent(filer):
    client, session = filer
    assert client.get(_url(session)).data["household"] is None

    first = _save(client, session, {"county": "Cook"}).data["household"]
    assert (first["county"], first["members"]) == ("Cook", None)
    _members(client, session, [SON])
    kept = _save(client, session, {"county": "Kane"}).data["household"]

    assert kept["county"] == "Kane"
    assert [row["relationship"] for row in kept["members"]] == ["son"]


def test_a_new_session_can_carry_its_county(filer):
    client, session = filer
    body = {"district": session.district_id, "current_step": 1, "household": {"county": "Cook"}}
    created = client.post("/api/intake/sessions/", body, format="json")
    assert created.status_code == 201
    assert Household.objects.get(session_id=created.data["session"]["id"]).county == "Cook"
