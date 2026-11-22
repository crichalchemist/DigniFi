"""Form 101's asked answers are the filer's own and are stored only as typed (4b spec §7.1).

Business intent: a sworn No is never written for a filer who did not give it, the ITIN and the
other Social Security number never leave the server, and a change reopens a completed intake.
"""

import datetime
import json

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.intake.models import PetitionAnswers, _read_text_limits
from apps.intake.petition import (
    DETAIL_ITIN,
    DETAIL_ITIN_NINE,
    DETAIL_OTHER_SSN,
    petition_step_gaps,
)


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


def test_a_short_other_ssn_is_listed_for_form_121_alone(filer):
    # Form 101 has no box for the other Social Security number (PF2-T7-7).
    client, session = filer
    body = {"other_ssn_answer": "yes", "other_ssn": "90055"}
    assert _patch(client, session, body).status_code == 200
    session.refresh_from_db()
    gap = next(g for g in petition_step_gaps(session) if str(g) == DETAIL_OTHER_SSN)
    assert (gap.step, gap.kind, gap.forms) == ("debtor_info", "detail", ("form_121",))


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


def test_a_stored_other_ssn_never_comes_back_in_any_reply(filer):
    client, session = filer
    body = {
        "itin_answer": "yes",
        "itin": "900701234",
        "other_ssn_answer": "yes",
        "other_ssn": "900554321",
    }
    response = _patch(client, session, body)
    assert response.status_code == 200
    assert _stored(session)["other_ssn"] == "900554321"
    read = client.get(_url(session))
    for reply in (response, read):
        answers = reply.json()["petition_answers"]
        assert "other_ssn" not in answers and "itin" not in answers
        assert answers["other_ssn_saved"] is True and answers["itin_saved"] is True
        assert b"900554321" not in reply.content
        assert b"900701234" not in reply.content


def _raw_patch(client, session, text):
    """A PATCH body sent as typed JSON text, so it can carry what a test renderer can't."""
    return client.patch(_url(session), data=text, content_type="application/json")


def test_half_of_a_surrogate_pair_is_refused_and_the_session_still_reads(filer):
    # A browser can cut a pasted emoji in half at a box's maxLength. Stored, it would make
    # every later read of the session fail to render, so it is refused before any write.
    client, session = filer
    text = json.dumps({"petition_answers": {"venue_reason": "ok \ud83d"}})
    refused = _raw_patch(client, session, text)
    assert refused.status_code == 400
    assert refused.json() == {"petition_answers": ["Check the answer for venue_reason."]}
    cell = json.dumps({"petition_answers": {"prior_cases": [{"district": "Demo \udc00"}]}})
    assert _raw_patch(client, session, cell).status_code == 400
    assert not PetitionAnswers.objects.filter(session=session).exists()
    assert client.get(_url(session)).status_code == 200


def test_a_list_holds_at_most_twenty_rows(filer):
    client, session = filer
    rows = [{"district": f"Demo {n}", "filed_on": "01/02/2020"} for n in range(21)]
    for key in ("prior_cases", "pending_cases"):
        refused = _patch(client, session, {key: rows if key == "prior_cases" else [{}] * 21})
        assert refused.status_code == 400, key
        assert refused.json() == {"petition_answers": [f"Check the answer for {key}."]}
    assert _patch(client, session, {"prior_cases": rows[:20]}).status_code == 200


def test_a_row_cell_over_the_ceiling_or_a_row_that_is_not_an_object_is_refused(filer):
    client, session = filer
    long_cell = [{"district": "x" * (PetitionAnswers.TEXT_CEILING + 1)}]
    assert _patch(client, session, {"prior_cases": long_cell}).status_code == 400
    assert _patch(client, session, {"prior_cases": ["Demo"]}).status_code == 400
    assert _patch(client, session, {"other_names": [["Demo", "Name"]]}).status_code == 400
    assert not PetitionAnswers.objects.filter(session=session).exists()
    at_ceiling = [{"district": "x" * PetitionAnswers.TEXT_CEILING}]
    assert _patch(client, session, {"prior_cases": at_ceiling}).status_code == 200


def test_an_echoed_read_never_changes_a_stored_itin(filer):
    client, session = filer
    _patch(client, session, {"itin_answer": "yes", "itin": "900701234"})
    echoed = client.get(_url(session)).json()["petition_answers"]
    assert _patch(client, session, echoed).status_code == 200  # the read PATCHed back whole
    assert _stored(session)["itin"] == "900701234"
    refused = _patch(client, session, {"itin": "saved"})
    assert refused.status_code == 400
    assert refused.json() == {"petition_answers": ["Check the answer for itin."]}
    ignored = _patch(client, session, {"itin_saved": False, "other_ssn_saved": True})
    assert ignored.status_code == 200
    assert _stored(session)["itin"] == "900701234"
    assert "itin_saved" not in _stored(session) and "other_ssn_saved" not in _stored(session)


def test_a_text_over_the_ceiling_is_refused(filer):
    client, session = filer
    assert _patch(client, session, {"venue_reason": "x" * 501}).status_code == 400
    assert _patch(client, session, {"venue_reason": "x" * 500}).status_code == 200


def test_answered_on_is_stamped_and_read_only(filer, monkeypatch):
    client, session = filer
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: datetime.date(2026, 11, 19))
    response = _patch(client, session, {"mailing_answer": "no", "answered_on": "1999-01-01"})
    assert response.status_code == 200  # a body carrying it is ignored
    assert PetitionAnswers.objects.get(session=session).answered_on == "2026-11-19"
    assert "answered_on" not in _stored(session)
    top = client.patch(
        _url(session),
        {"petition_answers": {"hazard_answer": "no"}, "answered_on": "x"},
        format="json",
    )
    assert top.status_code == 200
    assert PetitionAnswers.objects.get(session=session).answered_on == "2026-11-19"


def test_answered_on_moves_only_when_an_answer_changes(filer, monkeypatch):
    client, session = filer
    today = {"day": datetime.date(2026, 11, 19)}
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: today["day"])
    assert _patch(client, session, {"mailing_answer": "no"}).status_code == 200
    today["day"] = datetime.date(2026, 11, 20)
    assert _patch(client, session, {"mailing_answer": "no", "ein": None}).status_code == 200
    assert PetitionAnswers.objects.get(session=session).answered_on == "2026-11-19"
    assert _patch(client, session, {"mailing_answer": "yes"}).status_code == 200
    assert PetitionAnswers.objects.get(session=session).answered_on == "2026-11-20"


def test_a_body_with_no_answer_in_it_saves_nothing_and_leaves_a_completed_intake_complete(
    filer,
):
    client, session = filer
    session.status = "completed"
    session.save()
    for body in ({}, {"itin_saved": True, "other_ssn_saved": False, "answered_on": "x"}):
        assert _patch(client, session, body).status_code == 200
        session.refresh_from_db()
        assert session.status == "completed"
    assert not PetitionAnswers.objects.filter(session=session).exists()


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


def test_a_missing_caps_file_fails_loudly(settings, tmp_path):
    # Read at import: without it every text would lose its cap with no sign of it.
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    with pytest.raises(FileNotFoundError):
        _read_text_limits()


@pytest.mark.parametrize("key", PetitionAnswers.RADIO_KEYS)
def test_every_radio_key_is_a_yes_no_key(key):
    assert key in PetitionAnswers.YES_NO_KEYS


@pytest.mark.parametrize(
    "itin,saved,listed",
    [
        ("", False, True),
        ("9007012", False, True),
        ("666701234", False, True),
        ("912345678", True, False),
        # Arabic-Indic digits are no ITIN: the forms' font can't print them (F16)
        ("9\u0660\u0667\u0660\u0661\u0662\u0663\u0664\u0665", False, True),
    ],
)
def test_itin_saved_means_it_will_print_and_no_detail_is_listed(filer, itin, saved, listed):
    client, session = filer
    response = _patch(client, session, {"itin_answer": "yes", "itin": itin})
    assert response.status_code == 200
    read = client.get(_url(session)).json()["petition_answers"]
    assert read["itin_saved"] is saved
    session.refresh_from_db()
    texts = [str(g) for g in petition_step_gaps(session)]
    assert (DETAIL_ITIN in texts or DETAIL_ITIN_NINE in texts) is listed


@pytest.mark.parametrize(
    "other,saved",
    [
        ("", False),
        ("9007012", False),
        ("666701234", True),
        ("\u0669\u0660\u0660\u0667\u0660\u0661\u0662\u0663\u0664", False),
    ],
)
def test_other_ssn_saved_only_when_it_is_nine_digits(filer, other, saved):
    client, session = filer
    assert _patch(client, session, {"other_ssn": other}).status_code == 200
    read = client.get(_url(session)).json()["petition_answers"]
    assert read["other_ssn_saved"] is saved
