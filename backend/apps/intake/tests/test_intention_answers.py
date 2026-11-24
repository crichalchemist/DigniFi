"""The filer's Form 108 choices are their own, kept by debt id and lease id (4e, R-SHAPE).

Business intent: a choice is saved against the creditor it was made for and never moves onto
another one; a save keeps only the ids still in scope (a confirmed secured debt, a lease that
isn't residential), so a draft, an unsecured debt or a residential lease never carries a choice
(R-PRUNE); the PATCH's own debts are written before the prune reads them (R-SAVE-ORDER); a bad
body names its key, never what was typed; and a change reopens a completed intake.
"""

import datetime
import json

import pytest

from apps.intake.models import AssetInfo, ExemptionAnswers, ExemptionClaim, IntentionAnswers
from apps.intake.tests.builders import answer_intentions, complete_contract, complete_debt


def _url(session):
    return f"/api/intake/sessions/{session.pk}/"


def _patch(client, session, body):
    return client.patch(_url(session), {"intention_answers": body}, format="json")


def _stored(session):
    return IntentionAnswers.objects.get(session=session).get_answers()


def _secured(session, **over):
    return complete_debt(session, is_secured=True, **over)


def test_a_choice_saves_by_debt_id_and_reads_back(filer):
    client, session = filer
    debt = _secured(session, creditor_name="Demo Auto Finance")
    body = {"secured": {str(debt.pk): {"intention": "retain_reaffirm"}}}
    response = _patch(client, session, body)
    assert response.status_code == 200
    assert _stored(session) == body
    read = client.get(_url(session)).json()["intention_answers"]
    assert read["secured"] == body["secured"]
    assert read["answered_on"] is not None


def test_each_top_key_sent_replaces_its_object_and_a_null_clears_it(filer):
    client, session = filer
    car = _secured(session, creditor_name="Demo Auto Finance")
    home = _secured(session, creditor_name="Demo Mortgage")
    lease = complete_contract(session, lease_kind="vehicle", description="Demo car lease")
    first = {
        "secured": {
            str(car.pk): {"intention": "retain_explain", "explain": "Demo words"},
            str(home.pk): {"intention": "surrender"},
        },
        "leases": {str(lease.pk): {"assumed": "yes"}},
    }
    assert _patch(client, session, first).status_code == 200
    # The secured object is replaced whole: the home's choice goes, the car's explain goes.
    second = {"secured": {str(car.pk): {"intention": "retain_redeem"}}}
    assert _patch(client, session, second).status_code == 200
    assert _stored(session) == {**second, "leases": first["leases"]}
    assert _patch(client, session, {"leases": None}).status_code == 200
    assert _stored(session) == second


def _lease_set(session):
    """The three leases Form 108 asks about, whatever else a case adds."""
    return [
        complete_contract(session, lease_kind=None, description="Demo lease, kind unanswered"),
        complete_contract(session, lease_kind="vehicle", description="Demo car lease"),
        complete_contract(session, lease_kind="other", description="Demo other lease"),
    ]


def _draft_secured(session, other):
    return "secured", _secured(session, is_draft=True, creditor_name="Demo Scanned Lender").pk


def _unsecured(session, other):
    return "secured", complete_debt(session, creditor_name="Demo Card Services").pk


def _residential(session, other):
    return "leases", complete_contract(session, lease_kind="residential").pk


def _other_sessions_debt(session, other):
    return "secured", _secured(other, creditor_name="Demo Stranger Lender").pk


def _deleted_debt(session, other):
    debt = _secured(session, creditor_name="Demo Gone Lender")
    pk = debt.pk
    debt.delete()
    return "secured", pk


@pytest.mark.parametrize(
    "out_of_scope",
    [_draft_secured, _unsecured, _residential, _other_sessions_debt, _deleted_debt],
    ids=["draft", "unsecured", "residential", "other_session", "deleted"],
)
def test_a_save_prunes_ids_that_are_no_longer_in_scope(filer, other_session, out_of_scope):
    # A choice kept for a row Form 108 never prints would wait to land on whatever row the id
    # names next: a scanned draft confirmed later, or a debt made secured by mistake.
    client, session = filer
    kept_debt = _secured(session, creditor_name="Demo Auto Finance")
    leases = _lease_set(session)
    key, stray = out_of_scope(session, other_session)
    body = {
        "secured": {str(kept_debt.pk): {"intention": "retain_redeem"}},
        "leases": {str(lease.pk): {"assumed": "no"} for lease in leases},
    }
    body[key] = {
        **body[key],
        str(stray): {"intention": "surrender"} if key == "secured" else {"assumed": "yes"},
    }
    assert _patch(client, session, body).status_code == 200
    stored = _stored(session)
    assert str(stray) not in stored[key]
    assert set(stored["leases"]) == {str(lease.pk) for lease in leases}
    assert set(stored["secured"]) == {str(kept_debt.pk)}


def test_a_save_of_one_key_drops_the_other_keys_ids_that_left_scope(filer):
    # The prune covers the whole record, not only the key sent: a debt made unsecured since its
    # choice was saved loses it at the next save of the step.
    client, session = filer
    debt = _secured(session, creditor_name="Demo Auto Finance")
    lease = complete_contract(session, lease_kind="vehicle", description="Demo car lease")
    _patch(client, session, {"secured": {str(debt.pk): {"intention": "surrender"}}})
    debt.is_secured = False
    debt.save()
    assert (
        _patch(client, session, {"leases": {str(lease.pk): {"assumed": "no"}}}).status_code == 200
    )
    assert _stored(session) == {"secured": {}, "leases": {str(lease.pk): {"assumed": "no"}}}


def test_one_patch_dropping_a_secured_debt_and_keying_a_choice_to_it_stores_none(filer):
    client, session = filer
    gone = _secured(session, creditor_name="Demo Gone Lender")
    stays = _secured(session, creditor_name="Demo Auto Finance")
    response = client.patch(
        _url(session),
        {
            "debts": [{"id": stays.pk}],
            "intention_answers": {"secured": {str(gone.pk): {"intention": "surrender"}}},
        },
        format="json",
    )
    assert response.status_code == 200
    assert _stored(session) == {"secured": {}}


def test_one_patch_making_a_debt_secured_keeps_the_choice_sent_with_it(filer):
    client, session = filer
    debt = complete_debt(session, creditor_name="Demo Auto Finance")
    response = client.patch(
        _url(session),
        {
            "debts": [{"id": debt.pk, "is_secured": True}],
            "intention_answers": {"secured": {str(debt.pk): {"intention": "retain_redeem"}}},
        },
        format="json",
    )
    assert response.status_code == 200
    assert _stored(session) == {"secured": {str(debt.pk): {"intention": "retain_redeem"}}}


SECRET = "Demo private words"


@pytest.mark.parametrize(
    ("body", "named", "typed"),
    [
        ({"plans": {"1": {"intention": "surrender"}}}, "plans", "surrender"),
        ({"secured": {"{debt}": {"colour": "Demo hue"}}}, "secured", "Demo hue"),
        ({"secured": {"{debt}": {"intention": "keep"}}}, "secured", "keep"),
        ({"secured": {"{debt}": {"intention": None}}}, "secured", "null"),
        ({"leases": {"{lease}": {"assumed": "maybe"}}}, "leases", "maybe"),
        ({"leases": {"{lease}": {"intention": "surrender"}}}, "leases", "surrender"),
        (
            {"secured": {"{debt}": {"intention": "retain_explain", "explain": "x" * 501}}},
            "secured",
            "x" * 501,
        ),
        (
            {"secured": {str(n): {"intention": "surrender"} for n in range(1, 102)}},
            "secured",
            "surrender",
        ),
        ({"secured": {"0": {"intention": "surrender"}}}, "secured", "0"),
        ({"secured": {"abc": {"intention": "surrender"}}}, "secured", "abc"),
        ({"secured": {"{debt}": {"explain": "\ud800"}}}, "secured", "\\ud800"),
        ({"secured": []}, "secured", "[]"),
        ({"secured": {"{debt}": None}}, "secured", "null"),
    ],
    ids=[
        "unknown_top_key",
        "unknown_entry_key",
        "unknown_intention",
        "null_intention",
        "unknown_assumed",
        "intention_on_a_lease",
        "explain_over_500",
        "over_100_ids",
        "id_zero",
        "id_not_digits",
        "lone_surrogate",
        "not_an_object",
        "null_entry",
    ],
)
def test_an_unknown_key_wrong_type_or_value_over_its_ceiling_is_a_400_naming_the_key_not_the_value(
    filer, body, named, typed
):
    # Stored, any of these would make a Form 108 box raise or print a choice the filer never
    # made. The body goes as JSON text, which can carry the lone surrogate.
    client, session = filer
    debt = _secured(session, creditor_name="Demo Auto Finance")
    lease = complete_contract(session, lease_kind="vehicle", description="Demo car lease")
    text = json.dumps({"intention_answers": body})
    text = text.replace("{debt}", str(debt.pk)).replace("{lease}", str(lease.pk))
    refused = client.patch(_url(session), data=text, content_type="application/json")
    assert refused.status_code == 400
    message = refused.json()["intention_answers"][0]
    assert named in message
    assert typed not in refused.content.decode()
    # No id is echoed, nor any digit of one.
    assert not any(ch.isdigit() for ch in refused.content.decode())
    assert not IntentionAnswers.objects.filter(session=session).exists()


def test_an_echoed_answered_on_alone_saves_nothing_and_reopens_nothing(filer):
    client, session = filer
    session.status = "completed"
    session.save()
    for body in ({}, {"answered_on": "2026-01-01"}):
        assert _patch(client, session, body).status_code == 200
        session.refresh_from_db()
        assert session.status == "completed"
    assert not IntentionAnswers.objects.filter(session=session).exists()


def test_saving_choices_reopens_a_completed_intake(filer):
    client, session = filer
    debt = _secured(session, creditor_name="Demo Auto Finance")
    session.status = "completed"
    session.save()
    body = {"secured": {str(debt.pk): {"intention": "undecided"}}}
    assert _patch(client, session, body).status_code == 200
    session.refresh_from_db()
    assert session.status == "in_progress"


def test_answered_on_moves_only_when_an_answer_changes(filer, monkeypatch):
    client, session = filer
    debt = _secured(session, creditor_name="Demo Auto Finance")
    today = {"day": datetime.date(2026, 11, 24)}
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: today["day"])
    body = {"secured": {str(debt.pk): {"intention": "retain_redeem"}}}
    assert _patch(client, session, body).status_code == 200
    today["day"] = datetime.date(2026, 11, 25)
    assert _patch(client, session, {**body, "answered_on": "1999-01-01"}).status_code == 200
    assert IntentionAnswers.objects.get(session=session).answered_on == "2026-11-24"
    changed = {"secured": {str(debt.pk): {"intention": "retain_reaffirm"}}}
    assert _patch(client, session, changed).status_code == 200
    record = IntentionAnswers.objects.get(session=session)
    assert record.answered_on == "2026-11-25"
    assert "answered_on" not in record.get_answers()
    read = client.get(_url(session)).json()["intention_answers"]
    assert read == {**changed, "answered_on": "2026-11-25"}


def test_with_no_record_the_read_carries_only_answered_on(filer):
    client, session = filer
    assert client.get(_url(session)).json()["intention_answers"] == {"answered_on": None}


def test_the_session_read_carries_each_secured_debts_exempt_state(filer):
    client, session = filer
    couch = AssetInfo.objects.create(session=session, ab_line="6", description="Demo couch")
    ExemptionAnswers.objects.create(session=session, line_1="state_and_federal")
    ExemptionClaim.objects.create(session=session, asset=couch, other_law="Demo law")
    listed = _secured(session, creditor_name="Demo Furniture Credit", secured_by=couch)
    draft = _secured(session, is_draft=True, creditor_name="Demo Scanned Lender")
    unsecured = complete_debt(session, creditor_name="Demo Card Services")
    exempt = client.get(_url(session)).json()["intention_exempt"]
    assert exempt == {str(listed.pk): "listed", str(draft.pk): "no_property"}
    assert str(unsecured.pk) not in exempt


def test_a_patch_reply_carries_the_exempt_state_of_a_debt_it_made_secured(filer):
    # The wizard takes the state from the reply (Ruling F1), so a debt made secured in this save
    # must have one there, not only after a reload.
    client, session = filer
    debt = complete_debt(session, creditor_name="Demo Auto Finance")
    response = client.patch(
        _url(session), {"debts": [{"id": debt.pk, "is_secured": True}]}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["intention_exempt"] == {str(debt.pk): "no_property"}


def test_the_exempt_state_is_read_only(filer):
    client, session = filer
    debt = _secured(session, creditor_name="Demo Auto Finance")
    session.status = "completed"
    session.save()
    response = client.patch(
        _url(session), {"intention_exempt": {str(debt.pk): "listed"}}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["intention_exempt"] == {str(debt.pk): "no_property"}
    session.refresh_from_db()
    assert session.status == "completed"


def test_the_builder_stores_what_a_save_would(filer):
    # Later tasks build their sessions with it, so it must keep the save's scope and its
    # None-leaves-alone, {}-clears rule.
    _, session = filer
    debt = _secured(session, creditor_name="Demo Auto Finance")
    lease = complete_contract(session, lease_kind="vehicle", description="Demo car lease")
    unsecured = complete_debt(session, creditor_name="Demo Card Services")
    answer_intentions(
        session,
        secured={
            str(debt.pk): {"intention": "retain_redeem"},
            str(unsecured.pk): {"intention": "surrender"},
        },
        leases={str(lease.pk): {"assumed": "undecided"}},
    )
    assert _stored(session) == {
        "secured": {str(debt.pk): {"intention": "retain_redeem"}},
        "leases": {str(lease.pk): {"assumed": "undecided"}},
    }
    answer_intentions(session, leases={})
    assert _stored(session) == {
        "secured": {str(debt.pk): {"intention": "retain_redeem"}},
        "leases": {},
    }
