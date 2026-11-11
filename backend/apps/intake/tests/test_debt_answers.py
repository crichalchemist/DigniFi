"""A debt row saves every answer it carries (forms 3c3, Task 2).

Business intent: a filer's half-finished Amounts Owed row must save, a link to
property must never reach another session, and an account number must never
come back whole.
"""

from decimal import Decimal

import pytest

from apps.intake.claims import account_last_4
from apps.intake.models import AssetInfo, DebtInfo, IntakeSession

ROW = {"creditor_name": "Demo Bank", "debt_type": "auto_loan", "amount_owed": "4000.00"}


def _patch(client, session, debts):
    return client.patch(f"/api/intake/sessions/{session.pk}/", {"debts": debts}, format="json")


def _car(session):
    return AssetInfo.objects.create(
        session=session,
        asset_type="vehicle",
        ab_line="3",
        description="Demo Sedan",
        current_value=Decimal("5000.00"),
        entire_value=Decimal("5000.00"),
        amount_owed=Decimal("0.00"),
    )


def test_the_api_no_longer_carries_a_priority_label(filer):
    client, session = filer
    response = _patch(
        client,
        session,
        [{**ROW, "debt_type": "student_loan", "priority_classification": "priority"}],
    )
    assert response.status_code == 200
    assert "priority_classification" not in response.data["debts"][0]
    assert session.debts.get().priority_classification == "unsecured"


def test_a_half_filled_debt_saves_with_no_name_and_amount_zero(filer):
    client, session = filer
    response = _patch(client, session, [{"amount_owed": "0", "street_address": "9 Demo Road"}])
    assert response.status_code == 200
    row = response.json()["debts"][0]
    assert row["creditor_name"] == ""
    assert row["debt_type"] == ""
    assert row["amount_owed"] == "0.00"
    assert row["street_address"] == "9 Demo Road"
    assert DebtInfo.objects.get().creditor_name == ""


def test_a_negative_amount_is_refused_on_the_session_save_and_the_per_item_save(filer):
    client, session = filer
    assert _patch(client, session, [{**ROW, "amount_owed": "-1"}]).status_code == 400
    assert DebtInfo.objects.count() == 0
    response = client.post(
        "/api/intake/debts/",
        {**ROW, "session": session.pk, "amount_owed": "-1"},
        format="json",
    )
    assert response.status_code == 400


def test_a_debt_links_to_its_own_sessions_property(filer):
    client, session = filer
    car = _car(session)
    response = _patch(client, session, [{**ROW, "secured_by": car.pk}])
    assert response.json()["debts"][0]["secured_by"] == car.pk
    got = client.get(f"/api/intake/sessions/{session.pk}/").json()
    assert got["debts"][0]["secured_by"] == car.pk
    assert DebtInfo.objects.get().secured_by_id == car.pk


def test_another_filers_asset_id_links_nothing_and_is_never_echoed(filer, other_session):
    client, session = filer
    foreign = _car(other_session)
    response = _patch(client, session, [{**ROW, "secured_by": foreign.pk}])
    assert response.status_code == 200
    assert response.json()["debts"][0]["secured_by"] is None
    assert DebtInfo.objects.get().secured_by_id is None
    response = _patch(client, session, [{**ROW, "secured_by": 999999}])
    assert response.json()["debts"][0]["secured_by"] is None
    assert DebtInfo.objects.get().secured_by_id is None


def test_a_removed_property_leaves_the_debt_with_no_link(filer):
    client, session = filer
    car = _car(session)
    _patch(client, session, [{**ROW, "secured_by": car.pk}])
    AssetInfo.objects.get(pk=car.pk).delete()
    got = client.get(f"/api/intake/sessions/{session.pk}/").json()
    assert got["debts"][0]["secured_by"] is None
    assert DebtInfo.objects.get().secured_by_id is None


def test_a_property_moved_to_another_session_reads_as_no_link_and_a_resave_clears_it(
    filer, other_session
):
    client, session = filer
    car = _car(session)
    _patch(client, session, [{**ROW, "secured_by": car.pk}])
    AssetInfo.objects.filter(pk=car.pk).update(session=other_session)
    got = client.get(f"/api/intake/sessions/{session.pk}/").json()
    assert got["debts"][0]["secured_by"] is None
    assert DebtInfo.objects.get().secured_by_id == car.pk
    _patch(client, session, [{**ROW, "id": got["debts"][0]["id"], "secured_by": car.pk}])
    assert DebtInfo.objects.get().secured_by_id is None


def test_a_row_that_omits_its_link_keeps_it(filer):
    client, session = filer
    car = _car(session)
    debt_id = _patch(client, session, [{**ROW, "secured_by": car.pk}]).json()["debts"][0]["id"]
    _patch(client, session, [{"id": debt_id, "amount_owed": "10"}])
    assert DebtInfo.objects.get().secured_by_id == car.pk
    _patch(client, session, [{"id": debt_id, "amount_owed": "10", "secured_by": None}])
    assert DebtInfo.objects.get().secured_by_id is None


def _parties(client, session, debt_id, parties):
    body = {"id": debt_id, "amount_owed": "1", "notice_parties": parties}
    return _patch(client, session, [body]).json()["debts"][0]["notice_parties"]


def test_a_notice_party_keeps_its_id_and_a_removed_ones_id_is_never_reused(filer):
    client, session = filer
    parties = [{"name": "Demo Collections"}, {"name": "Demo Law Office"}]
    reply = _patch(client, session, [{**ROW, "notice_parties": parties}]).json()["debts"][0]
    assert [p["id"] for p in reply["notice_parties"]] == [1, 2]
    debt_id = reply["id"]
    kept = _parties(client, session, debt_id, [{"id": 2, "name": "Demo Law Office"}])
    assert [p["id"] for p in kept] == [2]
    _parties(client, session, debt_id, [])
    fresh = _parties(client, session, debt_id, [{"name": "Demo Agency"}])
    assert fresh[0]["id"] >= 3


def test_an_eleventh_notice_party_is_refused(filer):
    client, session = filer
    ten = [{"name": f"Demo Party {i}"} for i in range(10)]
    reply = _patch(client, session, [{**ROW, "notice_parties": ten}])
    assert reply.status_code == 200
    debt_id = reply.json()["debts"][0]["id"]
    eleven = [{"name": f"Demo Party {i}"} for i in range(11)]
    body = {"id": debt_id, "amount_owed": "1", "notice_parties": eleven}
    assert _patch(client, session, [body]).status_code == 400
    assert len(DebtInfo.objects.get().get_notice_parties()) == 10


def test_a_notice_party_id_that_is_not_a_whole_number_is_refused(filer):
    client, session = filer
    for bad in ("one", True, [1], {"a": 1}):
        body = {**ROW, "notice_parties": [{"id": bad, "name": "Demo Collections"}]}
        assert _patch(client, session, [body]).status_code == 400


def test_an_unknown_lien_kind_or_status_is_refused(filer):
    client, session = filer
    assert _patch(client, session, [{**ROW, "lien": {"kinds": ["mortgage"]}}]).status_code == 400
    assert _patch(client, session, [{**ROW, "claim_status": ["contested"]}]).status_code == 400
    lien = {"kinds": ["other", "agreement", "agreement"], "other": "Demo lien"}
    row = _patch(
        client, session, [{**ROW, "lien": lien, "claim_status": ["disputed", "contingent"]}]
    ).json()["debts"][0]
    assert row["lien"] == {"kinds": ["agreement", "other"], "other": "Demo lien"}
    assert row["claim_status"] == ["contingent", "disputed"]
    debt_id = row["id"]
    body = {"id": debt_id, "amount_owed": "1", "claim_status": []}
    assert _patch(client, session, [body]).json()["debts"][0]["claim_status"] == []
    omitted = {"id": debt_id, "amount_owed": "1"}
    assert _patch(client, session, [omitted]).json()["debts"][0]["claim_status"] == []


def test_a_claim_status_nobody_answered_stays_unanswered(filer):
    client, session = filer
    assert _patch(client, session, [ROW]).json()["debts"][0]["claim_status"] is None


def test_a_state_typed_in_lower_case_saves_in_capitals(filer):
    client, session = filer
    row = _patch(client, session, [{**ROW, "state": "il"}]).json()["debts"][0]
    assert row["state"] == "IL"


def test_a_one_letter_state_saves_so_one_row_never_refuses_the_list(filer):
    client, session = filer
    row = _patch(client, session, [{**ROW, "state": "I"}])
    assert row.status_code == 200
    assert row.json()["debts"][0]["state"] == "I"
    assert _patch(client, session, [{**ROW, "state": "ILL"}]).status_code == 400


def test_only_the_last_four_digits_of_an_account_number_are_readable(filer):
    assert account_last_4("4111 1111 1111 0042") == "0042"
    assert account_last_4("12") == "12"
    assert account_last_4(None) == ""
    assert account_last_4("ABC-") == ""
    client, session = filer
    number = "4111111111110042"
    response = _patch(client, session, [{**ROW, "account_number": number}])
    row = response.json()["debts"][0]
    assert row["account_last_4"] == "0042"
    assert "account_number" not in row
    text = response.content.decode()
    assert number not in text
    assert not any(number[i : i + 5] in text for i in range(len(number) - 4))


def test_a_date_longer_than_the_box_prints_is_refused(filer):
    client, session = filer
    assert _patch(client, session, [{**ROW, "date_incurred": "01/2020-06/2021"}]).status_code == 200
    too_long = {**ROW, "date_incurred": "01/2020-06/20211"}
    assert _patch(client, session, [too_long]).status_code == 400
    assert _patch(client, session, [{**ROW, "date_incurred": None}]).status_code == 200
    assert _patch(client, session, [{**ROW, "date_incurred": ""}]).status_code == 200


def test_the_per_item_debt_save_ignores_a_link(filer):
    client, session = filer
    car = _car(session)
    response = client.post(
        "/api/intake/debts/", {**ROW, "session": session.pk, "secured_by": car.pk}, format="json"
    )
    assert response.status_code == 201
    assert DebtInfo.objects.get().secured_by_id is None


def test_the_per_item_debt_save_ignores_a_lien_a_status_and_notice_parties(filer):
    client, session = filer
    response = client.post(
        "/api/intake/debts/",
        {
            **ROW,
            "session": session.pk,
            "lien": {"kinds": ["agreement"], "other": ""},
            "claim_status": ["disputed"],
            "notice_parties": [{"name": "Demo Collections"}],
        },
        format="json",
    )
    assert response.status_code == 201
    debt = DebtInfo.objects.get()
    assert (debt.lien, debt.claim_status, debt.notice_parties) == (None, None, None)
    assert client.get(f"/api/intake/sessions/{session.pk}/").status_code == 200
    response = client.patch(
        f"/api/intake/debts/{debt.pk}/", {"lien": {"kinds": ["agreement"]}}, format="json"
    )
    assert response.status_code == 200
    assert DebtInfo.objects.get().lien is None
    assert client.get(f"/api/intake/sessions/{session.pk}/").status_code == 200


@pytest.mark.parametrize("missing", ["creditor_name", "debt_type"])
def test_the_per_item_debt_save_still_requires_a_name_and_a_type(filer, missing):
    client, session = filer
    body = {**ROW, "session": session.pk}
    del body[missing]
    assert client.post("/api/intake/debts/", body, format="json").status_code == 400


def test_a_session_created_with_a_debt_stores_its_answers_readably(filer):
    client, session = filer
    elsewhere = IntakeSession.objects.create(user=session.user, district=session.district)
    foreign = _car(elsewhere)
    debt = {
        **ROW,
        "session": session.pk,  # the nested serializer requires it on create; it is ignored
        "lien": {"kinds": ["agreement"], "other": ""},
        "claim_status": ["disputed"],
        "notice_parties": [{"name": "Demo Collections"}],
        "secured_by": foreign.pk,
    }
    body = {"district": session.district_id, "current_step": 1, "debts": [debt]}
    created = client.post("/api/intake/sessions/", body, format="json")
    assert created.status_code == 201, created.content
    new_id = created.data["session"]["id"]
    got = client.get(f"/api/intake/sessions/{new_id}/")
    assert got.status_code == 200
    row = got.json()["debts"][0]
    assert row["lien"] == {"kinds": ["agreement"], "other": ""}
    assert row["claim_status"] == ["disputed"]
    assert isinstance(row["notice_parties"][0]["id"], int)
    assert row["notice_parties"][0]["name"] == "Demo Collections"
    assert row["secured_by"] is None


PRIORITY = {
    "priority_answer": "taxes",
    "priority_other": "",
    "priority_amount": "3000.00",
    "nonpriority_amount": None,
    "past_due_amount": "0.00",
}


def test_the_priority_answers_save_and_come_back_on_the_session_save(filer):
    client, session = filer
    response = _patch(client, session, [{**ROW, "debt_type": "other", **PRIORITY}])
    assert response.status_code == 200
    sent = response.data["debts"][0]
    assert {key: sent[key] for key in PRIORITY} == PRIORITY
    debt = session.debts.get()
    assert debt.priority_answer == "taxes"
    assert debt.past_due_amount == Decimal("0.00")
    assert debt.nonpriority_amount is None


def test_the_per_item_save_takes_the_priority_answers(filer):
    client, session = filer
    response = client.post(
        "/api/intake/debts/",
        {**ROW, "session": session.pk, "priority_answer": "not_sure"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["priority_answer"] == "not_sure"


@pytest.mark.parametrize("answer", ["", "priority", "yes"])
def test_an_unknown_priority_answer_is_refused(filer, answer):
    client, session = filer
    assert _patch(client, session, [{**ROW, "priority_answer": answer}]).status_code == 400
    per_item = {**ROW, "session": session.pk, "priority_answer": answer}
    assert client.post("/api/intake/debts/", per_item, format="json").status_code == 400


@pytest.mark.parametrize("field", ["priority_amount", "nonpriority_amount", "past_due_amount"])
@pytest.mark.parametrize("value", ["-1", "12345678901.00"])
def test_a_negative_or_too_wide_priority_figure_is_refused(filer, field, value):
    client, session = filer
    assert _patch(client, session, [{**ROW, field: value}]).status_code == 400
    per_item = {**ROW, "session": session.pk, field: value}
    assert client.post("/api/intake/debts/", per_item, format="json").status_code == 400
    assert not session.debts.exists()


def test_other_words_longer_than_the_box_takes_are_refused(filer):
    client, session = filer
    too_long = {**ROW, "priority_answer": "other", "priority_other": "x" * 101}
    assert _patch(client, session, [too_long]).status_code == 400
    fits = {**too_long, "priority_other": "x" * 100}
    assert _patch(client, session, [fits]).status_code == 200


def test_a_debt_saved_without_the_priority_answers_reads_them_as_unanswered(filer):
    client, session = filer
    assert _patch(client, session, [ROW]).status_code == 200
    debt = client.get(f"/api/intake/sessions/{session.pk}/").data["debts"][0]
    assert [debt[key] for key in PRIORITY] == [None] * 5
