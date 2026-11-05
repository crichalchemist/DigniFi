"""Saving Schedule A/B rows and the Yes/No answers through the API (3b spec §3.3).

Business intent: a filer who types $0 on a leased car gets $0 back, a value too wide for
the column is refused before it can make every read of the session fail, a figure beats
its "I don't know" flag, and answering a line again after Complete reopens the intake.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import AssetInfo, AssetLineAnswers, IntakeSession
from apps.users.models import User


@pytest.fixture
def filer_session(db):
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
    return client, session


@pytest.fixture
def completed_session(filer_session):
    client, session = filer_session
    session.status = "completed"
    session.save()
    return client, session


def _url(session):
    return f"/api/intake/sessions/{session.pk}/"


def test_zero_is_a_saved_value_and_comes_back_as_zero(filer_session):
    client, session = filer_session
    row = {"ab_line": "3", "current_value": "0.00", "entire_value": "0.00"}
    assert client.patch(_url(session), {"assets": [row]}, format="json").status_code == 200

    asset = client.get(_url(session)).data["assets"][0]
    assert asset["current_value"] == "0.00"
    assert asset["entire_value"] == "0.00"


def test_entire_value_wider_than_the_column_is_a_400(filer_session):
    client, session = filer_session
    row = {"ab_line": "3", "entire_value": "10000000000.00"}

    response = client.patch(_url(session), {"assets": [row]}, format="json")

    assert response.status_code == 400
    assert client.get(_url(session)).status_code == 200
    assert AssetInfo.objects.count() == 0


def test_a_figure_clears_its_unknown_flag(filer_session):
    client, session = filer_session
    row = {"ab_line": "6", "current_value": "5.00", "details": {"value_unknown": True}}
    client.patch(_url(session), {"assets": [row]}, format="json")

    saved = AssetInfo.objects.get()
    assert saved.current_value == Decimal("5.00")
    assert saved.get_details()["value_unknown"] is False


def test_unknown_with_no_figure_keeps_the_flag_and_a_null_value(filer_session):
    client, session = filer_session
    row = {"ab_line": "6", "details": {"value_unknown": True}}
    client.patch(_url(session), {"assets": [row]}, format="json")

    asset = client.get(_url(session)).data["assets"][0]
    assert asset["current_value"] is None
    assert asset["details"]["value_unknown"] is True


def test_a_kind_from_another_line_is_a_400(filer_session):
    client, session = filer_session
    row = {"ab_line": "17", "details": {"kind": "401k"}}

    response = client.patch(_url(session), {"assets": [row]}, format="json")

    assert response.status_code == 400
    assert AssetInfo.objects.count() == 0


def test_a_kind_on_its_own_line_saves(filer_session):
    client, session = filer_session
    row = {"ab_line": "17", "details": {"kind": "savings", "who": "only_you"}}

    assert client.patch(_url(session), {"assets": [row]}, format="json").status_code == 200
    assert AssetInfo.objects.get().get_details() == {"kind": "savings", "who": "only_you"}


def test_percent_is_kept_as_a_string_in_the_details(filer_session):
    client, session = filer_session
    row = {"ab_line": "19", "details": {"percent": "12.50"}}

    client.patch(_url(session), {"assets": [row]}, format="json")

    assert client.get(_url(session)).data["assets"][0]["details"] == {"percent": "12.50"}


def test_a_percent_over_100_is_a_400(filer_session):
    client, session = filer_session
    row = {"ab_line": "19", "details": {"percent": "100.01"}}

    assert client.patch(_url(session), {"assets": [row]}, format="json").status_code == 400


def test_an_unknown_line_or_answer_is_a_400(filer_session):
    client, session = filer_session

    unknown_row = client.patch(
        _url(session), {"assets": [{"ab_line": "99"}]}, format="json"
    ).status_code
    unknown_answer_line = client.patch(
        _url(session), {"asset_lines": {"99": "yes"}}, format="json"
    ).status_code
    unknown_answer = client.patch(
        _url(session), {"asset_lines": {"6": "maybe"}}, format="json"
    ).status_code

    assert (unknown_row, unknown_answer_line, unknown_answer) == (400, 400, 400)


def test_line_answers_set_only_the_keys_sent_and_null_clears_one(filer_session):
    client, session = filer_session
    client.patch(_url(session), {"asset_lines": {"6": "no", "7": "yes"}}, format="json")

    response = client.patch(_url(session), {"asset_lines": {"7": None, "8": "no"}}, format="json")

    assert response.status_code == 200
    assert response.data["asset_lines"] == {"6": "no", "8": "no"}
    assert AssetLineAnswers.objects.get(session=session).get_answers() == {"6": "no", "8": "no"}


def test_the_session_read_has_no_answers_before_any_are_saved(filer_session):
    client, session = filer_session

    assert client.get(_url(session)).data["asset_lines"] == {}


def test_saving_only_line_answers_reopens_a_completed_intake(completed_session):
    client, session = completed_session

    client.patch(_url(session), {"asset_lines": {"6": "no"}}, format="json")

    session.refresh_from_db()
    assert session.status == "in_progress"


def test_a_missing_answer_saves(filer_session):
    client, session = filer_session

    response = client.patch(_url(session), {"assets": [{"ab_line": "6"}]}, format="json")

    assert response.status_code == 200
    assert AssetInfo.objects.count() == 1


def test_per_item_create_without_a_line_is_a_400(filer_session):
    client, session = filer_session

    response = client.post(
        "/api/intake/assets/", {"session": session.pk, "description": "Sofa"}, format="json"
    )

    assert response.status_code == 400
    assert AssetInfo.objects.count() == 0


def test_per_item_create_with_a_line_saves_and_has_no_equity(filer_session):
    client, session = filer_session

    response = client.post(
        "/api/intake/assets/",
        {"session": session.pk, "ab_line": "6", "description": "Sofa", "current_value": "0"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["current_value"] == "0.00"
    assert "equity" not in response.data
    assert "account_number" not in response.data
    assert "financial_institution" not in response.data


def test_old_rows_survive_a_save_that_sends_them_back(filer_session):
    client, session = filer_session
    old = AssetInfo.objects.create(
        session=session,
        asset_type="vehicle",
        description="2015 Civic",
        current_value=Decimal("4000.00"),
    )
    sent = client.get(_url(session)).data["assets"]
    assert sent[0]["ab_line"] is None

    response = client.patch(_url(session), {"assets": sent}, format="json")

    assert response.status_code == 200
    old.refresh_from_db()
    assert (old.ab_line, old.asset_type, old.description) == (None, "vehicle", "2015 Civic")
    assert old.current_value == Decimal("4000.00")
    assert AssetInfo.objects.count() == 1


def _stored(session, **fields):
    return AssetInfo.objects.create(session=session, asset_type="other", **fields)


def test_moving_a_row_to_a_line_that_lacks_its_kind_is_a_400(filer_session):
    client, session = filer_session
    row = _stored(session, ab_line="17", details='{"kind": "checking"}')

    response = client.patch(f"/api/intake/assets/{row.pk}/", {"ab_line": "21"}, format="json")

    assert response.status_code == 400
    row.refresh_from_db()
    assert row.ab_line == "17"


def test_a_nested_row_sent_with_only_a_new_line_cannot_lose_its_kind_slot(filer_session):
    client, session = filer_session
    row = _stored(session, ab_line="17", details='{"kind": "checking"}')

    response = client.patch(
        _url(session), {"assets": [{"id": row.pk, "ab_line": "21"}]}, format="json"
    )

    assert response.status_code == 400
    row.refresh_from_db()
    assert row.ab_line == "17"


def test_a_figure_alone_clears_the_stored_unknown_flag(filer_session):
    client, session = filer_session
    row = _stored(session, ab_line="6", details='{"value_unknown": true}')

    response = client.patch(
        f"/api/intake/assets/{row.pk}/", {"current_value": "5.00"}, format="json"
    )

    assert response.status_code == 200
    row.refresh_from_db()
    assert row.current_value == Decimal("5.00")
    assert row.get_details()["value_unknown"] is False


def test_a_nested_figure_alone_clears_the_stored_unknown_flag(filer_session):
    client, session = filer_session
    row = _stored(session, ab_line="6", details='{"value_unknown": true}')

    response = client.patch(
        _url(session), {"assets": [{"id": row.pk, "current_value": "5.00"}]}, format="json"
    )

    assert response.status_code == 200
    row.refresh_from_db()
    assert row.get_details()["value_unknown"] is False


def test_per_item_update_cannot_strip_a_rows_line(filer_session):
    client, session = filer_session
    row = _stored(session, ab_line="6")

    response = client.patch(f"/api/intake/assets/{row.pk}/", {"ab_line": None}, format="json")

    assert response.status_code == 400
    row.refresh_from_db()
    assert row.ab_line == "6"
