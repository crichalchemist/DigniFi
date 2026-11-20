"""Form 101's asked answers are the filer's own and are stored only as typed (4b spec §7.1).

Business intent: a sworn No is never written for a filer who did not give it, the ITIN and the
other Social Security number never leave the server, and a change reopens a completed intake.
"""

import datetime
import json

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.intake.models import PetitionAnswers
from apps.intake.petition import petition_step_gaps


def _url(session):
    return f"/api/intake/sessions/{session.pk}/"


def _patch(client, session, body):
    return client.patch(_url(session), {"petition_answers": body}, format="json")


def _stored(session):
    return PetitionAnswers.objects.get(session=session).get_answers()


def _walk(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)
    else:
        yield value


def test_petition_answers_set_only_the_keys_sent(filer):
    client, session = filer
    assert _patch(client, session, {"mailing_answer": "no", "ein": "123456789"}).status_code == 200
    second = _patch(client, session, {"hazard_answer": "yes"})
    assert second.status_code == 200
    assert _stored(session) == {
        "mailing_answer": "no",
        "ein": "123456789",
        "hazard_answer": "yes",
    }
    assert _patch(client, session, {"ein": None}).status_code == 200
    assert "ein" not in _stored(session)


def test_an_unknown_key_is_refused_by_name_and_nothing_is_saved(filer):
    client, session = filer
    response = _patch(client, session, {"landlord": "x", "mailing_answer": "no"})
    assert response.status_code == 400
    assert response.json() == {"petition_answers": ["Not a petition answer: landlord."]}
    assert not PetitionAnswers.objects.filter(session=session).exists()


def test_a_yes_no_key_takes_only_yes_or_no(filer):
    client, session = filer
    refused = _patch(client, session, {"mailing_answer": "maybe"})
    assert refused.status_code == 400
    assert refused.json() == {"petition_answers": ["Check the answer for mailing_answer."]}
    assert _patch(client, session, {"mailing_answer": "yes"}).status_code == 200


def test_no_key_stores_a_boolean(filer):
    client, session = filer
    for key in PetitionAnswers.KEYS:
        if key in PetitionAnswers.LIST_KEYS:
            continue
        assert _patch(client, session, {key: True}).status_code == 400, key
    for key, cells in PetitionAnswers.LIST_KEYS.items():
        response = _patch(client, session, {key: [{cells[0]: True}]})
        assert response.status_code == 400, key
    assert not PetitionAnswers.objects.filter(session=session).exists()
    # A refusal after a good save leaves the stored record without a boolean.
    assert _patch(client, session, {"mailing_answer": "no"}).status_code == 200
    assert _patch(client, session, {"prior_cases": [{"district": True}]}).status_code == 400
    assert not [v for v in _walk(_stored(session)) if isinstance(v, bool)]


def test_a_list_key_takes_a_list_of_rows_with_its_own_keys(filer):
    client, session = filer
    assert _patch(client, session, {"prior_cases": {"district": "x"}}).status_code == 400
    assert _patch(client, session, {"prior_cases": [{"when": "x"}]}).status_code == 400
    rows = [{"district": f"Demo {n}", "filed_on": "01/02/2020"} for n in range(4)]
    assert _patch(client, session, {"prior_cases": rows}).status_code == 200


def test_a_rows_browser_key_is_accepted_and_never_stored(filer):
    client, session = filer
    response = _patch(client, session, {"prior_cases": [{"district": "Demo", "_key": "k1"}]})
    assert response.status_code == 200
    assert "_key" not in PetitionAnswers.objects.get(session=session).answers
    assert "_key" not in json.dumps(response.json()["petition_answers"])
    assert "_key" not in json.dumps(client.get(_url(session)).json()["petition_answers"])


def test_an_enumerated_key_takes_only_its_set(filer):
    client, session = filer
    refused = _patch(client, session, {"venue_choice": "maybe"})
    assert refused.status_code == 400
    assert refused.json() == {"petition_answers": ["Check the answer for venue_choice."]}
    assert _patch(client, session, {"venue_choice": "other"}).status_code == 200


def test_a_third_other_name_is_refused(filer):
    client, session = filer
    row = {"first": "Demo", "last": "Name"}
    assert _patch(client, session, {"other_names": [row, row]}).status_code == 200
    refused = _patch(client, session, {"other_names": [row, row, row]})
    assert refused.status_code == 400
    assert refused.json() == {"petition_answers": ["Check the answer for other_names."]}


def test_a_dashed_itin_is_stored_as_typed_and_not_a_gap(filer):
    client, session = filer
    assert _patch(client, session, {"itin_answer": "yes", "itin": "900-70-1234"}).status_code == 200
    assert _stored(session)["itin"] == "900-70-1234"
    session.refresh_from_db()
    assert "Type your 9-digit ITIN, or change your answer to No." not in [
        str(g) for g in petition_step_gaps(session)
    ]


def test_a_seven_digit_itin_is_stored_and_listed_as_a_detail(filer):
    client, session = filer
    assert _patch(client, session, {"itin_answer": "yes", "itin": "9007123"}).status_code == 200
    session.refresh_from_db()
    gap = next(g for g in petition_step_gaps(session) if str(g).startswith("Type your 9-digit"))
    assert (gap.step, gap.kind, gap.forms) == ("debtor_info", "detail", ("form_101", "form_121"))


def test_the_itin_and_other_ssn_never_come_back(filer):
    client, session = filer
    body = {"itin_answer": "yes", "itin": "900701234", "other_ssn_answer": "no"}
    response = _patch(client, session, body)
    assert response.status_code == 200
    read = client.get(_url(session))
    answers = read.json()["petition_answers"]
    assert "itin" not in answers and "other_ssn" not in answers
    assert answers["itin_saved"] is True
    assert answers["other_ssn_saved"] is False
    assert b"900701234" not in read.content
    assert b"900701234" not in response.content


def test_an_echoed_read_never_changes_a_stored_itin(filer):
    client, session = filer
    _patch(client, session, {"itin_answer": "yes", "itin": "900701234"})
    echoed = client.get(_url(session)).json()["petition_answers"]
    # The browser leaves the two read-only booleans out of a body.
    echoed = {k: v for k, v in echoed.items() if not k.endswith("_saved")}
    assert _patch(client, session, echoed).status_code == 200
    assert _stored(session)["itin"] == "900701234"
    refused = _patch(client, session, {"itin": "saved"})
    assert refused.status_code == 400
    assert refused.json() == {"petition_answers": ["Check the answer for itin."]}
    refused = _patch(client, session, {"itin_saved": True})
    assert refused.status_code == 400
    assert refused.json() == {"petition_answers": ["Not a petition answer: itin_saved."]}


def test_a_text_over_the_ceiling_is_refused(filer):
    client, session = filer
    assert _patch(client, session, {"venue_reason": "x" * 501}).status_code == 400
    assert _patch(client, session, {"venue_reason": "x" * 500}).status_code == 200


def test_answered_on_is_stamped_and_read_only(filer, monkeypatch):
    client, session = filer
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: datetime.date(2026, 11, 19))
    response = _patch(client, session, {"mailing_answer": "no", "answered_on": "1999-01-01"})
    assert response.status_code == 400  # a body key that is not an answer is refused by name
    assert _patch(client, session, {"mailing_answer": "no"}).status_code == 200
    assert PetitionAnswers.objects.get(session=session).answered_on == "2026-11-19"
    top = client.patch(
        _url(session),
        {"petition_answers": {"hazard_answer": "no"}, "answered_on": "x"},
        format="json",
    )
    assert top.status_code == 200
    assert PetitionAnswers.objects.get(session=session).answered_on == "2026-11-19"


def test_a_petition_save_reopens_a_completed_intake(filer):
    client, session = filer
    session.status = "completed"
    session.save()
    assert _patch(client, session, {"mailing_answer": "no"}).status_code == 200
    session.refresh_from_db()
    assert session.status == "in_progress"


def test_the_record_rides_on_the_session_read(filer):
    client, session = filer
    _patch(client, session, {"mailing_answer": "no"})
    with CaptureQueriesContext(connection) as queries:
        response = client.get(_url(session))
    assert response.json()["petition_answers"]["mailing_answer"] == "no"
    # select_related joins it: no query of its own reads the record's table.
    assert [q for q in queries if 'FROM "petition_answers"' in q["sql"]] == []


@pytest.mark.parametrize("key", PetitionAnswers.RADIO_KEYS)
def test_every_radio_key_is_a_yes_no_key(key):
    assert key in PetitionAnswers.YES_NO_KEYS
