"""Schedule I's line 1, 11 and 13 answers and Schedule J's line 24 are the filer's own (4c).

Business intent: an answer is stored only as the filer typed it, a stale tab never erases one, a
change reopens a completed intake, and the pay stub's employer name is shown, never saved over
the filer's own answer.
"""

import datetime
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured

from apps.documents.models import IngestedAggregate
from apps.intake.models import ScheduleIAnswers, _read_schedule_i_limits

ROOT = Path(django_settings.BASE_DIR).parent
TOOL = ROOT / "data/forms/field_index/tools/build_schedule_i_limits.py"
LIMITS_DIR = ROOT / "data/forms/schemas"


def _url(session):
    return f"/api/intake/sessions/{session.pk}/"


def _patch(client, session, body):
    return client.patch(_url(session), {"schedule_i_answers": body}, format="json")


def _stored(session):
    return ScheduleIAnswers.objects.get(session=session).get_answers()


def test_a_patch_sets_only_the_keys_sent(filer):
    client, session = filer
    first = {"employment_status": "employed", "employer_name": "Demo Pharmacy"}
    assert _patch(client, session, first).status_code == 200
    assert _patch(client, session, {"line_13_answer": "no"}).status_code == 200
    assert _stored(session) == {**first, "line_13_answer": "no"}


def test_a_null_removes_a_key(filer):
    client, session = filer
    _patch(client, session, {"employer_name": "Demo Pharmacy", "line_11_answer": "no"})
    assert _patch(client, session, {"employer_name": None}).status_code == 200
    assert _stored(session) == {"line_11_answer": "no"}


def test_an_unknown_key_is_refused_by_name_and_nothing_is_saved(filer):
    client, session = filer
    response = _patch(client, session, {"employer": "x", "line_13_answer": "no"})
    assert response.status_code == 400
    assert response.json() == {"schedule_i_answers": ["Not a Schedule I answer: employer."]}
    assert not ScheduleIAnswers.objects.filter(session=session).exists()


def test_a_text_over_500_characters_is_refused(filer):
    client, session = filer
    refused = _patch(client, session, {"line_13_text": "x" * 501})
    assert refused.status_code == 400
    assert refused.json() == {"schedule_i_answers": ["Check the answer for line_13_text."]}
    assert _patch(client, session, {"line_13_text": "x" * 500}).status_code == 200


@pytest.mark.parametrize("amount", ["-1", "1e3", "abc", "10000000000.00", 12, "", "12."])
def test_an_amount_that_is_not_a_plain_decimal_at_or_above_zero_is_refused(filer, amount):
    # Stored, any of these would make the line 11 and line 12 boxes fail at Generate.
    client, session = filer
    refused = _patch(client, session, {"line_11_amount": amount})
    assert refused.status_code == 400
    assert refused.json() == {"schedule_i_answers": ["Check the answer for line_11_amount."]}
    assert not ScheduleIAnswers.objects.filter(session=session).exists()
    assert _patch(client, session, {"line_11_amount": "9999999999.99"}).status_code == 200


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("employment_status", "unemployed"),
        ("spouse_employment_status", "self_employed"),
        ("line_13_answer", "maybe"),
        ("line_11_answer", True),
        ("occupation", 12),
        ("employer_name", {"a": 1}),
        ("line_13_text", "\ud800"),
    ],
)
def test_an_answer_no_box_can_print_is_refused_and_nothing_is_saved(filer, key, value):
    # Stored, a stranger choice or yes/no would make its box raise UnmappedChoice at Generate, a
    # text that isn't a string can't be measured or printed, and half of a surrogate pair can't
    # be written as UTF-8, so every later read of the session would fail. The body goes as JSON
    # text, which can carry the lone surrogate a test renderer can't encode.
    client, session = filer
    text = json.dumps({"schedule_i_answers": {key: value}})
    refused = client.patch(_url(session), data=text, content_type="application/json")
    assert refused.status_code == 400
    assert refused.json() == {"schedule_i_answers": [f"Check the answer for {key}."]}
    assert not ScheduleIAnswers.objects.filter(session=session).exists()


def test_a_text_over_its_cap_is_stored(filer):
    # The cap is the box's width, not a refusal: the gap list names the text (B47).
    client, session = filer
    over = "x" * (ScheduleIAnswers.TEXT_LIMITS["employer_state"] + 1)
    assert _patch(client, session, {"employer_state": over}).status_code == 200
    assert _stored(session) == {"employer_state": over}


def test_answered_on_takes_the_fill_date_only_when_an_answer_changes(filer, monkeypatch):
    client, session = filer
    today = {"day": datetime.date(2026, 11, 22)}
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: today["day"])
    assert _patch(client, session, {"line_11_answer": "no"}).status_code == 200
    today["day"] = datetime.date(2026, 11, 23)
    body = {"line_11_answer": "no", "line_13_text": None}
    assert _patch(client, session, body).status_code == 200
    assert ScheduleIAnswers.objects.get(session=session).answered_on == "2026-11-22"
    assert _patch(client, session, {"line_11_answer": "yes"}).status_code == 200
    assert ScheduleIAnswers.objects.get(session=session).answered_on == "2026-11-23"
    read = client.get(_url(session)).json()["schedule_i_answers"]
    assert read == {"line_11_answer": "yes", "answered_on": "2026-11-23"}


def test_a_body_with_no_answer_saves_nothing_and_reopens_nothing(filer):
    client, session = filer
    session.status = "completed"
    session.save()
    for body in ({}, {"answered_on": "2026-01-01"}):
        assert _patch(client, session, body).status_code == 200
        session.refresh_from_db()
        assert session.status == "completed"
    assert not ScheduleIAnswers.objects.filter(session=session).exists()


def test_a_write_reopens_a_completed_intake(filer):
    client, session = filer
    session.status = "completed"
    session.save()
    assert _patch(client, session, {"line_13_answer": "no"}).status_code == 200
    session.refresh_from_db()
    assert session.status == "in_progress"


def test_a_patch_without_the_key_leaves_the_record_alone(filer):
    # A stale tab's step save carries no schedule_i_answers key; it must erase nothing.
    client, session = filer
    answers = {"employment_status": "employed", "employer_name": "Demo Pharmacy"}
    _patch(client, session, answers)
    record = ScheduleIAnswers.objects.get(session=session)
    response = client.patch(_url(session), {"household": {"county": "Cook"}}, format="json")
    assert response.status_code == 200
    again = ScheduleIAnswers.objects.get(session=session)
    assert again.get_answers() == answers
    assert again.answered_on == record.answered_on


def test_an_echoed_answered_on_is_ignored(filer, monkeypatch):
    client, session = filer
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: datetime.date(2026, 11, 22))
    body = {"line_13_answer": "no", "answered_on": "1999-01-01"}
    assert _patch(client, session, body).status_code == 200
    record = ScheduleIAnswers.objects.get(session=session)
    assert record.answered_on == "2026-11-22"
    assert "answered_on" not in record.get_answers()


def test_the_session_read_carries_the_pay_stub_employer_name(filer):
    client, session = filer
    IngestedAggregate.objects.create(
        session=session, ingest_key="paystub.employer_name", value=" Demo Pharmacy "
    )
    IngestedAggregate.objects.create(session=session, ingest_key="paystub.gross", value="2000")
    assert client.get(_url(session)).json()["paystub_employer_name"] == "Demo Pharmacy"


def test_with_no_pay_stub_the_employer_name_reads_empty(filer):
    client, session = filer
    read = client.get(_url(session)).json()
    assert read["paystub_employer_name"] == ""
    assert read["schedule_i_answers"] == {"answered_on": None}


def test_the_pay_stub_name_is_read_only(filer):
    client, session = filer
    IngestedAggregate.objects.create(
        session=session, ingest_key="paystub.employer_name", value="Demo Pharmacy"
    )
    session.status = "completed"
    session.save()
    response = client.patch(_url(session), {"paystub_employer_name": "Someone Else"}, format="json")
    assert response.status_code == 200
    assert response.json()["paystub_employer_name"] == "Demo Pharmacy"
    assert IngestedAggregate.objects.get(session=session).value == "Demo Pharmacy"
    assert not ScheduleIAnswers.objects.filter(session=session).exists()
    session.refresh_from_db()
    assert session.status == "completed"


def _tool():
    spec = importlib.util.spec_from_file_location("build_schedule_i_limits", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_caps_are_measured_on_schedule_i_and_j_boxes():
    built = _tool().limits()
    stored = json.loads((LIMITS_DIR / "schedule_i.limits.json").read_text())
    assert stored == built
    limits = stored["limits"]
    assert set(limits) == set(ScheduleIAnswers.TEXT_KEYS)
    assert set(stored["labels"]) == set(ScheduleIAnswers.TEXT_KEYS)
    assert "employer_state" in limits and "employer_zip" in limits
    for key in ScheduleIAnswers.TEXT_KEYS:
        if key.startswith("spouse_"):
            assert limits[key] == limits[key.removeprefix("spouse_")], key
    # The record reads the same file at import.
    assert ScheduleIAnswers.TEXT_LIMITS == limits
    assert ScheduleIAnswers.TEXT_LABELS == stored["labels"]


def test_a_missing_limits_file_fails_at_import(settings, tmp_path):
    # Read at import: without it every text would lose its cap with no sign of it.
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    with pytest.raises(FileNotFoundError):
        _read_schedule_i_limits()


@pytest.mark.parametrize(
    "body",
    [{}, {"limits": {}, "labels": {}}, {"limits": {"occupation": 44}}, {"labels": {"x": "y"}}],
)
def test_a_limits_file_with_no_limits_or_no_labels_is_improperly_configured(
    settings, tmp_path, body
):
    (tmp_path / "schedule_i.limits.json").write_text(json.dumps(body))
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    with pytest.raises(ImproperlyConfigured):
        _read_schedule_i_limits()


@pytest.mark.parametrize("part", ["limits", "labels"])
def test_a_limits_key_the_record_does_not_ask_is_improperly_configured(settings, tmp_path, part):
    # A misspelt key would leave the real key with no cap, and nothing would say so.
    shutil.copy(LIMITS_DIR / "schedule_i.limits.json", tmp_path)
    path = tmp_path / "schedule_i.limits.json"
    data = json.loads(path.read_text())
    data[part]["employer_nmae"] = 44 if part == "limits" else "Employer's name"
    path.write_text(json.dumps(data))
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    with pytest.raises(ImproperlyConfigured):
        _read_schedule_i_limits()


@pytest.mark.parametrize("part", ["limits", "labels"])
def test_a_text_the_limits_file_leaves_out_is_improperly_configured(settings, tmp_path, part):
    # A text with no cap would drop out of the too-long check, and nothing would say so until
    # the suite ran: the server refuses to start instead.
    shutil.copy(LIMITS_DIR / "schedule_i.limits.json", tmp_path)
    path = tmp_path / "schedule_i.limits.json"
    data = json.loads(path.read_text())
    del data[part]["line_13_text"]
    path.write_text(json.dumps(data))
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    with pytest.raises(ImproperlyConfigured, match="line_13_text"):
        _read_schedule_i_limits()
