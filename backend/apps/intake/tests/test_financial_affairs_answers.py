"""Form 107 lines 1 to 12 are the filer's own answers, saved by line (4f-i, D§3).

Business intent: each line's answer is stored as the filer typed it, never as a boolean, a
number or a value they didn't send; a picked debt that is gone loses only its link, never the
row or the name typed beside it (R-9), and the prune sees the same PATCH's debts (R-14); the
line 4 year label is stamped once and never moves while an amount it labels is stored, so a
save after January 1 can't relabel last year's income (R-4); line 6's answer never travels
without the branch it was asked under (R-5); a bad body names its key, never what was typed;
and a change reopens a completed intake.
"""

import datetime
import json

import pytest

from apps.forms.services.answer_records import branch_of
from apps.intake.models import FinancialAffairsAnswers, IntakeSession
from apps.intake.tests.builders import answer_financial_affairs, answer_petition, complete_debt


def _url(session):
    return f"/api/intake/sessions/{session.pk}/"


def _patch(client, session, body):
    return client.patch(_url(session), {"financial_affairs": body}, format="json")


def _walk(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)
    else:
        yield value


def _stored(session):
    return FinancialAffairsAnswers.objects.get(session=session).get_answers()


def _record(session):
    return FinancialAffairsAnswers.objects.get(session=session)


def _status(session):
    return IntakeSession.objects.get(pk=session.pk).status


def _complete(session):
    session.status = "completed"
    session.save()


def _on(monkeypatch, day):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: day)


def test_line_answers_save_by_line_and_read_back(filer):
    client, session = filer
    body = {
        "l2_answer": "no",
        "l9_answer": "yes",
        "l9_rows": [{"_key": "new-1", "case_title": "Demo v. Demo", "status": "pending"}],
    }
    reply = _patch(client, session, body)
    assert reply.status_code == 200
    read = reply.data["financial_affairs"]
    assert read["l9_rows"] == [{"case_title": "Demo v. Demo", "status": "pending"}]  # _key dropped
    assert (read["l2_answer"], read["answered_on"], read["fill_year"]) == (
        "no",
        "2026-10-16",
        2026,
    )
    assert client.get(_url(session)).data["financial_affairs"] == read


def test_a_session_with_no_record_reads_only_the_date_and_this_year(filer):
    client, session = filer
    assert client.get(_url(session)).data["financial_affairs"] == {
        "answered_on": None,
        "fill_year": 2026,
    }


def test_each_key_sent_replaces_its_value_whole_and_null_clears_it(filer):
    client, session = filer
    two = [{"name": "Demo Bank"}, {"name": "Demo Card Services"}]
    assert _patch(client, session, {"l2_answer": "no", "l6_rows": two}).status_code == 200
    assert len(_stored(session)["l6_rows"]) == 2
    assert _patch(client, session, {"l6_rows": [{"name": "Demo Bank"}]}).status_code == 200
    assert len(_stored(session)["l6_rows"]) == 1
    assert _stored(session)["l2_answer"] == "no"  # a key not sent is kept
    assert _patch(client, session, {"l2_answer": None}).status_code == 200
    assert "l2_answer" not in _stored(session)


def _scanned_draft(session, other):
    return complete_debt(session, is_draft=True, creditor_name="Demo Scanned Lender").pk


def _other_sessions_debt(session, other):
    return complete_debt(other, creditor_name="Demo Stranger Lender").pk


def _deleted_debt(session, other):
    debt = complete_debt(session, creditor_name="Demo Gone Lender")
    pk = debt.pk
    debt.delete()
    return pk


def _deleted_in_the_same_patch(session, other):
    return complete_debt(session, creditor_name="Demo Gone Lender").pk


GONE = {
    "scanned_draft": _scanned_draft,
    "other_sessions_debt": _other_sessions_debt,
    "deleted_debt": _deleted_debt,
    "deleted_in_the_same_patch": _deleted_in_the_same_patch,
}


@pytest.mark.parametrize(
    "gone", ["scanned_draft", "other_sessions_debt", "deleted_debt", "deleted_in_the_same_patch"]
)
def test_a_picked_debt_id_is_pruned_when_it_names_no_confirmed_debt_of_the_session(
    filer, other_session, gone
):
    # A link kept to a debt Form 107 can't name would print another creditor's details later;
    # the row and the name the filer typed stay, so nothing they wrote is lost.
    client, session = filer
    kept = complete_debt(session, creditor_name="Demo Card Services")
    stray = GONE[gone](session, other_session)
    rows = [
        {"debt_id": str(stray), "name": "Demo Gone Bank", "paid": "100.00"},
        {"debt_id": str(kept.pk), "name": "Demo Card Services", "paid": "50.00"},
    ]
    body = {"financial_affairs": {"l6_rows": rows}}
    if gone == "deleted_in_the_same_patch":
        body["debts"] = [{"id": kept.pk}]  # the stray's row is left out, so it is deleted
    assert client.patch(_url(session), body, format="json").status_code == 200
    stored_rows = _stored(session)["l6_rows"]
    assert stored_rows[0] == {"name": "Demo Gone Bank", "paid": "100.00"}  # only debt_id went
    assert stored_rows[1]["debt_id"] == str(kept.pk)


def test_the_year_label_never_moves_while_an_amount_it_labels_is_stored(filer, monkeypatch):
    # Line 4 asks for "this year" and "last year": relabelling stored figures after January 1
    # would swear last year's income was this year's.
    client, session = filer
    assert _patch(client, session, {"l4_current_wages": "1200"}).status_code == 200
    assert _stored(session)["l4_year"] == 2026
    _on(monkeypatch, datetime.date(2027, 1, 5))
    assert _patch(client, session, {"l9_answer": "no"}).status_code == 200
    assert _stored(session)["l4_year"] == 2026
    assert _patch(client, session, {"l4_current_wages": "1300"}).status_code == 200
    assert _stored(session)["l4_year"] == 2026
    cleared = dict.fromkeys(FinancialAffairsAnswers.L4_AMOUNT_KEYS, None)
    assert _patch(client, session, cleared).status_code == 200
    assert "l4_year" not in _stored(session)
    assert _patch(client, session, {"l4_last_wages": "900"}).status_code == 200
    assert _stored(session)["l4_year"] == 2027


def test_continue_after_new_year_resends_the_whole_body_and_moves_nothing(filer, monkeypatch):
    # Continue always sends the whole step body; the stored values come back unchanged, so the
    # year and the date of the last change stay where they were (COV-3).
    client, session = filer
    first = {"l4_answer": "yes", "l4_current_wages": "1200", "l9_answer": "no"}
    assert _patch(client, session, first).status_code == 200
    _complete(session)
    _on(monkeypatch, datetime.date(2027, 1, 5))
    body = {k: v for k, v in _stored(session).items() if k != "l4_year"}
    assert _patch(client, session, body).status_code == 200
    assert _stored(session)["l4_year"] == 2026
    assert _record(session).answered_on == "2026-10-16"
    assert _status(session) == "in_progress"  # any intake-data PATCH reopens (B44)


def test_line_4_amounts_kept_under_a_no_still_pin_the_year(filer):
    # An amount kept behind Show under a No can come back on a Yes: its label must stay with it.
    client, session = filer
    assert (
        _patch(client, session, {"l4_answer": "yes", "l4_current_wages": "1200"}).status_code == 200
    )
    assert _patch(client, session, {"l4_answer": "no"}).status_code == 200
    assert _stored(session)["l4_year"] == 2026
    assert _patch(client, session, {"l4_current_wages": None}).status_code == 200
    assert "l4_year" not in _stored(session)


def test_deleting_the_six_line_4_amounts_with_no_line_5_amount_removes_the_year(filer):
    client, session = filer
    amounts = dict.fromkeys(FinancialAffairsAnswers.L4_AMOUNT_KEYS, "100")
    assert _patch(client, session, {"l4_answer": "yes", **amounts}).status_code == 200
    assert _stored(session)["l4_year"] == 2026
    deleted = dict.fromkeys(FinancialAffairsAnswers.L4_AMOUNT_KEYS, None)
    assert _patch(client, session, deleted).status_code == 200
    assert "l4_year" not in _stored(session)


def test_a_line_5_amount_alone_stamps_the_year(filer):
    # Line 5 shares line 4's year columns (P7).
    client, session = filer
    body = {"l5_answer": "yes", "l5_last_rows": [{"source": "Demo", "amount": "50"}]}
    assert _patch(client, session, body).status_code == 200
    assert _stored(session)["l4_year"] == 2026


def test_a_sent_year_or_fill_year_is_ignored(filer):
    client, session = filer
    assert _patch(client, session, {"l4_current_wages": "1200"}).status_code == 200
    before = _record(session)
    _complete(session)
    echo = {"l4_year": 1999, "fill_year": 1999, "answered_on": "1999-01-01"}
    assert _patch(client, session, echo).status_code == 200
    after = _record(session)
    assert after.get_answers() == before.get_answers()
    assert after.answered_on == before.answered_on
    assert _status(session) == "completed"


def test_line_6_answer_and_branch_travel_together(filer):
    # Line 6's question differs by branch: an answer kept without the branch it was asked under
    # could print under the other question.
    client, session = filer
    refused = _patch(client, session, {"l6_answer": "yes"})
    assert refused.status_code == 400 and "l6_answer" in str(refused.data)
    assert _patch(client, session, {"l6_branch": "other"}).status_code == 400
    assert not FinancialAffairsAnswers.objects.filter(session=session).exists()
    ok = _patch(client, session, {"l6_answer": "yes", "l6_branch": "consumer"})
    assert ok.status_code == 200
    assert _patch(client, session, {"l6_answer": None, "l6_branch": None}).status_code == 200
    assert "l6_answer" not in _stored(session) and "l6_branch" not in _stored(session)


@pytest.mark.parametrize(
    ("body", "typed"),
    [
        ({"l13_answer": "no"}, None),
        ({"l2_answer": "maybe"}, "maybe"),
        ({"l2_answer": True}, None),
        ({"l6_rows": {}}, None),
        ({"l6_rows": ["x"]}, None),
        ({"l6_rows": [{"nmae": "Demo"}]}, "nmae"),
        ({"l10_rows": [{"repossessed": "no"}]}, None),
        ({"l10_rows": [{"repossessed": True}]}, None),
        ({"l9_rows": [{"status": "open"}]}, "open"),
        ({"l6_rows": [{"debt_id": 7}]}, None),
        ({"l6_rows": [{"debt_id": "0"}]}, None),
        ({"l6_rows": [{"name": "D" * 501}]}, "D" * 501),
        ({"l12_statement": [{"text": "D" * 2001}]}, "D" * 2001),
        ({"l6_rows": [{"paid": "1" * 33}]}, "1" * 33),
        ({"l2_rows": [{"city": "Demo"}] * 101}, "Demo"),
        ({"l2_rows": [{"city": "\ud800"}]}, None),
    ],
    ids=[
        "unknown_key",
        "yes_no_outside_its_set",
        "yes_no_boolean",
        "list_not_a_list",
        "row_not_an_object",
        "unknown_cell",
        "tick_not_yes",
        "tick_boolean",
        "status_outside_its_set",
        "debt_id_number",
        "debt_id_zero",
        "text_over_500",
        "statement_over_2000",
        "amount_over_32",
        "over_100_rows",
        "lone_surrogate",
    ],
)
def test_an_unknown_key_wrong_type_or_value_over_its_ceiling_is_a_400_naming_the_key_not_the_value(
    filer, body, typed
):
    # Stored, any of these would make a Form 107 box raise or print what the filer never said.
    client, session = filer
    # JSON text, which can carry the lone surrogate the test renderer can't encode.
    text = json.dumps({"financial_affairs": body})
    refused = client.patch(_url(session), data=text, content_type="application/json")
    assert refused.status_code == 400
    assert next(iter(body)) in refused.json()["financial_affairs"][0]  # the key is named
    if typed is not None:
        assert typed not in refused.content.decode()  # no sent value echoed
    assert not FinancialAffairsAnswers.objects.filter(session=session).exists()
    # No "no digit in the reply" check: the messages carry "107", "1-12" and "l13_answer".


def test_a_malformed_date_or_amount_is_stored_as_typed(filer):
    # Shapes are flagged by the gaps and print blank, never refused (B47): the filer's words stay.
    client, session = filer
    body = {
        "l6_answer": "yes",
        "l6_branch": "consumer",
        "l6_rows": [{"name": "Demo Bank", "date_1": "13/40/2026", "paid": "12.345"}],
    }
    assert _patch(client, session, body).status_code == 200
    assert _stored(session)["l6_rows"][0]["date_1"] == "13/40/2026"
    assert _stored(session)["l6_rows"][0]["paid"] == "12.345"


def _every_list():
    """One row of every list, each cell holding a value it may take."""
    rows = {}
    for key, cells in FinancialAffairsAnswers.LIST_CELLS.items():
        row = {}
        for cell in cells:
            if cell in FinancialAffairsAnswers.TICK_CELLS:
                row[cell] = "yes"
            elif cell == "status":
                row[cell] = "concluded"
            elif cell == "debt_id":
                continue  # no debt to pick; a pruned id would prove nothing here
            else:
                row[cell] = "Demo"
        rows[key] = [row]
    return rows


def test_no_answer_is_stored_as_a_boolean(filer):
    client, session = filer
    answers = dict.fromkeys(FinancialAffairsAnswers.YES_NO_KEYS, "yes")
    body = {**answers, "l6_branch": "other", "l4_current_wages": "1200", **_every_list()}
    assert _patch(client, session, body).status_code == 200
    assert set(_stored(session)) == set(FinancialAffairsAnswers.KEYS) - set(
        FinancialAffairsAnswers.L4_AMOUNT_KEYS[1:]
    )
    for refused in (
        {"l2_answer": True},
        {"l10_rows": [{"repossessed": True}]},
        {"l6_rows": [{"debt_id": True}]},
        {"l4_current_wages": False},
        {"l6_branch": True, "l6_answer": "yes"},
    ):
        assert _patch(client, session, refused).status_code == 400, refused
    assert not [v for v in _walk(_stored(session)) if isinstance(v, bool)]


def test_saving_line_answers_reopens_a_completed_intake(filer):
    client, session = filer
    _complete(session)
    assert _patch(client, session, {"l2_answer": "no"}).status_code == 200
    assert _status(session) == "in_progress"


def test_an_echoed_answered_on_alone_saves_nothing_and_reopens_nothing(filer):
    client, session = filer
    _complete(session)
    for body in ({}, {"answered_on": "2026-01-01"}):
        assert _patch(client, session, body).status_code == 200
        assert _status(session) == "completed"
    assert not FinancialAffairsAnswers.objects.filter(session=session).exists()


def test_answered_on_moves_only_when_the_stored_answers_change(filer, monkeypatch):
    client, session = filer
    kept = complete_debt(session, creditor_name="Demo Card Services")
    gone = complete_debt(session, creditor_name="Demo Gone Lender")
    body = {
        "l7_answer": "yes",
        "l7_rows": [
            {"debt_id": str(gone.pk), "name": "Demo Gone Lender"},
            {"debt_id": str(kept.pk), "name": "Demo Card Services"},
        ],
    }
    _on(monkeypatch, datetime.date(2026, 11, 24))
    assert _patch(client, session, body).status_code == 200
    _on(monkeypatch, datetime.date(2026, 11, 25))
    assert _patch(client, session, body).status_code == 200
    assert _record(session).answered_on == "2026-11-24"
    # The shape Continue sends: the debts list without the picked row and the unchanged body.
    _on(monkeypatch, datetime.date(2026, 11, 26))
    both = {"debts": [{"id": kept.pk}], "financial_affairs": body}
    assert client.patch(_url(session), both, format="json").status_code == 200
    record = _record(session)
    assert "debt_id" not in record.get_answers()["l7_rows"][0]
    assert record.answered_on == "2026-11-26"


def test_a_blank_cell_is_stored_as_absent(filer):
    # The blank shapes a browser row can carry are absent, never a 400 (D§3 "yes or absent").
    client, session = filer
    body = {
        "l6_answer": "yes",
        "l6_branch": "consumer",
        "l6_rows": [
            {
                "_key": "new-1",
                "name": "Demo Bank",
                "debt_id": None,
                "car": "",
                "mortgage": None,
                "street": "",
            }
        ],
        "l9_answer": "yes",
        "l9_rows": [{"case_title": "Demo v. Demo", "status": ""}],
    }
    assert _patch(client, session, body).status_code == 200
    assert _stored(session)["l6_rows"] == [{"name": "Demo Bank", "street": ""}]
    assert _stored(session)["l9_rows"] == [{"case_title": "Demo v. Demo"}]


def test_branch_of_follows_line_16():
    assert [branch_of(v) for v in ("consumer", "business", "neither", None, "", "x")] == [
        "consumer",
        "other",
        "other",
        None,
        None,
        None,
    ]


def test_the_builder_derives_a_lone_line_6_answers_branch(filer, other_session):  # R-47
    client, session = filer
    answer_petition(session, debt_nature="consumer")
    answer_financial_affairs(session, l6_answer="no")
    assert _stored(session)["l6_branch"] == "consumer"
    answer_petition(session, debt_nature="business")
    answer_financial_affairs(session, l6_answer="yes")
    assert _stored(session)["l6_branch"] == "other"
    answer_financial_affairs(session, l6_answer=None)
    assert "l6_answer" not in _stored(session) and "l6_branch" not in _stored(session)

    answer_petition(other_session, debt_nature=None)
    with pytest.raises(ValueError, match="answer debt_nature first"):
        answer_financial_affairs(other_session, l6_answer="no")
    with pytest.raises(ValueError):
        answer_financial_affairs(session, l6_branch="consumer")
