"""Contract and codebtor rows save every answer they are given (forms 3c3, Task 3).

Business intent: Schedules G and H print what the filer typed, so a half-filled row must save
(a filer mid-way through an address loses nothing), a nameless stored row keeps its id, and a
link to another filer's property, debt or contract is never kept or echoed.
"""

import json
from decimal import Decimal

import pytest

from apps.intake.models import AssetInfo, Codebtor, DebtInfo, ExecutoryContract


def _url(session, endpoint):
    return f"/api/intake/sessions/{session.pk}/{endpoint}/"


def _car(session):
    return AssetInfo.objects.create(
        session=session,
        asset_type="vehicle",
        ab_line="3",
        description="Demo car",
        current_value=Decimal("5000.00"),
        amount_owed=Decimal("0.00"),
    )


def _debt(session, name="Demo Card Services"):
    return DebtInfo.objects.create(
        session=session,
        creditor_name=name,
        debt_type="credit_card",
        amount_owed=Decimal("500.00"),
    )


ADDRESS = {"street_address": "1 Demo Street", "city": "Chicago", "state": "IL", "zip_code": "60601"}


def _only(model, session):
    return model.objects.filter(session=session).order_by("id").last()


def test_a_contract_with_an_address_and_no_name_saves_in_the_list(filer):
    client, session = filer

    response = client.put(_url(session, "contracts"), [{**ADDRESS, "state": "il"}], format="json")

    assert response.status_code == 200, response.content
    assert response.data[0]["counterparty_name"] == ""
    assert response.data[0]["contract_type"] == ""
    assert response.data[0]["state"] == "IL"
    stored = _only(ExecutoryContract, session)
    assert stored.street_address == "1 Demo Street"
    assert stored.outside_us is False


def test_clearing_a_stored_contracts_name_keeps_its_id(filer):
    client, session = filer
    stored = ExecutoryContract.objects.create(
        session=session, counterparty_name="Oak Street Apartments", contract_type="lease"
    )

    response = client.put(
        _url(session, "contracts"),
        [{"id": stored.pk, "counterparty_name": "", "contract_type": "lease"}],
        format="json",
    )

    assert response.status_code == 200, response.content
    assert response.data[0]["id"] == stored.pk
    assert ExecutoryContract.objects.filter(session=session).count() == 1
    stored.refresh_from_db()
    assert stored.counterparty_name == ""


def test_a_codebtor_with_an_address_and_no_name_saves_in_the_list(filer):
    client, session = filer

    response = client.put(
        _url(session, "codebtors"),
        [{**ADDRESS, "street_2": "Unit 4", "outside_us": False}],
        format="json",
    )

    assert response.status_code == 200, response.content
    assert response.data[0]["name"] == ""
    assert response.data[0]["relationship"] == ""
    assert response.data[0]["street_2"] == "Unit 4"


def test_an_address_ticked_outside_the_us_saves_with_no_state_or_zip(filer):
    client, session = filer

    response = client.put(
        _url(session, "codebtors"),
        [
            {
                "name": "Demo Person",
                "street_address": "9 Demo Road",
                "city": "Leeds, United Kingdom",
                "outside_us": True,
            }
        ],
        format="json",
    )

    assert response.status_code == 200, response.content
    stored = _only(Codebtor, session)
    assert stored.state == ""
    assert stored.zip_code == ""
    assert stored.outside_us is True


def test_a_new_contract_and_codebtor_store_no_type_or_relationship_unless_sent(filer):
    client, session = filer

    client.put(_url(session, "contracts"), [{"counterparty_name": "Metro Gym"}], format="json")
    assert _only(ExecutoryContract, session).contract_type == ""
    client.put(
        _url(session, "contracts"),
        [{"counterparty_name": "Metro Gym", "contract_type": "lease"}],
        format="json",
    )
    assert _only(ExecutoryContract, session).contract_type == "lease"

    client.put(_url(session, "codebtors"), [{"name": "Demo Person"}], format="json")
    assert _only(Codebtor, session).relationship == ""
    client.put(
        _url(session, "codebtors"),
        [{"name": "Demo Person", "relationship": "friend"}],
        format="json",
    )
    assert _only(Codebtor, session).relationship == "friend"

    no_type = client.post(
        _url(session, "contracts"), {"counterparty_name": "Metro Gym"}, format="json"
    )
    assert no_type.status_code == 400
    assert "contract_type" in no_type.data

    only_a_name = client.post(_url(session, "codebtors"), {"name": "Demo Person"}, format="json")
    assert only_a_name.status_code == 201
    assert _only(Codebtor, session).relationship == ""


def test_a_lease_row_saves_its_kind_payment_and_owes_now(filer):
    client, session = filer

    response = client.put(
        _url(session, "contracts"),
        [
            {
                "counterparty_name": "Demo Motors",
                "contract_type": "lease",
                "lease_kind": "vehicle",
                "monthly_payment": "389.00",
                "owes_now": "no",
            }
        ],
        format="json",
    )

    assert response.status_code == 200, response.content
    row = response.data[0]
    assert row["monthly_payment"] == "389.00"
    assert row["lease_kind"] == "vehicle"
    assert row["owes_now"] == "no"
    assert row["vehicle_asset"] is None
    assert row["owed_debt"] is None


@pytest.mark.parametrize(
    "bad", [{"monthly_payment": "-1"}, {"lease_kind": "boat"}], ids=["negative", "unknown-kind"]
)
def test_a_negative_or_unknown_lease_answer_refuses_the_whole_list(filer, bad):
    client, session = filer
    stored = ExecutoryContract.objects.create(
        session=session, counterparty_name="Oak Street Apartments", contract_type="lease"
    )

    response = client.put(
        _url(session, "contracts"),
        [
            {"id": stored.pk, "counterparty_name": "Renamed", "contract_type": "lease"},
            {"counterparty_name": "X", **bad},
        ],
        format="json",
    )

    assert response.status_code == 400
    stored.refresh_from_db()
    assert stored.counterparty_name == "Oak Street Apartments"


def test_a_contract_links_its_own_sessions_property_and_debt(filer):
    client, session = filer
    car, debt = _car(session), _debt(session)

    response = client.put(
        _url(session, "contracts"),
        [
            {
                "counterparty_name": "Demo Motors",
                "contract_type": "lease",
                "vehicle_asset": car.pk,
                "owed_debt": debt.pk,
                "owes_now": "yes",
            }
        ],
        format="json",
    )

    assert response.status_code == 200, response.content
    assert response.data[0]["vehicle_asset"] == car.pk
    assert response.data[0]["owed_debt"] == debt.pk
    assert response.data[0]["owes_now"] == "yes"
    stored = _only(ExecutoryContract, session)
    assert (stored.vehicle_asset_id, stored.owed_debt_id) == (car.pk, debt.pk)


def test_another_filers_asset_or_debt_id_links_nothing_on_a_contract(filer, other_session):
    client, session = filer
    theirs_car, theirs_debt = _car(other_session), _debt(other_session)

    response = client.put(
        _url(session, "contracts"),
        [
            {
                "counterparty_name": "Demo Motors",
                "contract_type": "lease",
                "vehicle_asset": theirs_car.pk,
                "owed_debt": theirs_debt.pk,
            }
        ],
        format="json",
    )

    assert response.status_code == 200, response.content
    assert response.data[0]["vehicle_asset"] is None
    assert response.data[0]["owed_debt"] is None
    stored = _only(ExecutoryContract, session)
    assert (stored.vehicle_asset_id, stored.owed_debt_id) == (None, None)


def test_a_contract_link_to_a_row_moved_to_another_intake_reads_as_no_link(filer, other_session):
    client, session = filer
    debt = _debt(session)
    ExecutoryContract.objects.create(
        session=session, counterparty_name="Demo Motors", contract_type="lease", owed_debt=debt
    )
    DebtInfo.objects.filter(pk=debt.pk).update(session=other_session)

    response = client.get(_url(session, "contracts"))

    assert response.status_code == 200
    assert response.data[0]["owed_debt"] is None


def test_a_removed_property_leaves_the_contract_with_no_link(filer):
    client, session = filer
    car = _car(session)
    ExecutoryContract.objects.create(
        session=session, counterparty_name="Demo Motors", contract_type="lease", vehicle_asset=car
    )
    car.delete()

    response = client.get(_url(session, "contracts"))

    assert response.data[0]["vehicle_asset"] is None


def test_a_codebtor_link_to_another_filers_debt_is_dropped_on_save(filer, other_session):
    client, session = filer
    theirs, mine = _debt(other_session), _debt(session)
    contract = ExecutoryContract.objects.create(
        session=session, counterparty_name="Demo Motors", contract_type="lease"
    )
    links = [
        {"kind": "debt", "id": theirs.pk},
        {"kind": "debt", "id": mine.pk},
        {"kind": "debt", "id": mine.pk},
        {"kind": "contract", "id": contract.pk},
    ]

    response = client.put(
        _url(session, "codebtors"), [{"name": "Demo Person", "links": links}], format="json"
    )

    kept = [{"kind": "debt", "id": mine.pk}, {"kind": "contract", "id": contract.pk}]
    assert response.status_code == 200, response.content
    assert response.data[0]["links"] == kept
    assert _only(Codebtor, session).get_links() == kept

    asset_kind = client.put(
        _url(session, "codebtors"),
        [{"name": "Demo Person", "links": [{"kind": "asset", "id": 1}]}],
        format="json",
    )
    assert asset_kind.status_code == 400


def test_a_stored_codebtor_link_of_an_unknown_kind_is_dropped_on_read(filer):
    client, session = filer
    mine = _debt(session)
    Codebtor.objects.create(
        session=session,
        name="Demo Person",
        links=json.dumps([{"kind": "other", "id": 1}, {"kind": "debt", "id": mine.pk}]),
    )

    response = client.get(_url(session, "codebtors"))

    assert response.status_code == 200
    assert response.data[0]["links"] == [{"kind": "debt", "id": mine.pk}]


def test_a_codebtor_link_to_another_filers_contract_is_dropped_on_save(filer, other_session):
    client, session = filer
    theirs = ExecutoryContract.objects.create(
        session=other_session, counterparty_name="Demo Gym", contract_type="contract"
    )
    mine = ExecutoryContract.objects.create(
        session=session, counterparty_name="Demo Motors", contract_type="lease"
    )

    response = client.put(
        _url(session, "codebtors"),
        [
            {
                "name": "Demo Person",
                "links": [
                    {"kind": "contract", "id": theirs.pk},
                    {"kind": "contract", "id": mine.pk},
                ],
            }
        ],
        format="json",
    )

    assert response.status_code == 200, response.content
    only_mine = [{"kind": "contract", "id": mine.pk}]
    assert response.data[0]["links"] == only_mine
    assert _only(Codebtor, session).get_links() == only_mine


def test_a_codebtor_link_to_a_removed_debt_is_dropped_on_read(filer):
    client, session = filer
    debt = _debt(session)
    link = [{"kind": "debt", "id": debt.pk}]
    saved = client.put(
        _url(session, "codebtors"), [{"name": "Demo Person", "links": link}], format="json"
    )
    assert saved.data[0]["links"] == link
    debt.delete()

    assert client.get(_url(session, "codebtors")).data[0]["links"] == []

    again = client.put(
        _url(session, "codebtors"),
        [{"id": saved.data[0]["id"], "name": "Demo Person", "links": link}],
        format="json",
    )
    assert again.status_code == 200
    assert _only(Codebtor, session).get_links() == []


def test_the_per_item_paths_ignore_a_link(filer):
    client, session = filer
    mine = _debt(session)

    response = client.post(
        _url(session, "codebtors"),
        {"name": "Demo Person", "links": [{"kind": "debt", "id": mine.pk}]},
        format="json",
    )

    assert response.status_code == 201
    assert _only(Codebtor, session).get_links() == []


def test_the_single_contract_post_ignores_its_links(filer, other_session):
    client, session = filer
    own_car, own_debt = _car(session), _debt(session)
    theirs_car, theirs_debt = _car(other_session), _debt(other_session)

    for car, debt in [(theirs_car, theirs_debt), (own_car, own_debt)]:
        response = client.post(
            _url(session, "contracts"),
            {
                "counterparty_name": "Demo Motors",
                "contract_type": "lease",
                "vehicle_asset": car.pk,
                "owed_debt": debt.pk,
            },
            format="json",
        )

        assert response.status_code == 201, response.content
        assert response.data["vehicle_asset"] is None
        assert response.data["owed_debt"] is None
        stored = _only(ExecutoryContract, session)
        assert (stored.vehicle_asset_id, stored.owed_debt_id) == (None, None)


@pytest.mark.parametrize(
    "endpoint,row",
    [
        ("contracts", {"counterparty_name": "Demo Motors", "contract_type": "lease"}),
        ("codebtors", {"name": "Demo Person"}),
    ],
)
def test_a_row_whose_state_holds_one_letter_or_nothing_saves_the_whole_list(filer, endpoint, row):
    client, session = filer
    model = ExecutoryContract if endpoint == "contracts" else Codebtor

    response = client.put(
        _url(session, endpoint), [{**row, "state": "I"}, dict(row)], format="json"
    )

    assert response.status_code == 200, response.content
    assert [r["state"] for r in response.data] == ["I", ""]
    assert model.objects.filter(session=session).count() == 2

    too_long = client.put(_url(session, endpoint), [{**row, "state": "ILL"}], format="json")
    assert too_long.status_code == 400


def test_clearing_a_stored_codebtors_name_keeps_its_id(filer):
    client, session = filer
    stored = Codebtor.objects.create(session=session, name="Demo Person")

    response = client.put(
        _url(session, "codebtors"),
        [{"id": stored.pk, "name": "", "relationship": "friend"}],
        format="json",
    )

    assert response.status_code == 200, response.content
    assert response.data[0]["id"] == stored.pk
    assert Codebtor.objects.filter(session=session).count() == 1
    stored.refresh_from_db()
    assert stored.name == ""
