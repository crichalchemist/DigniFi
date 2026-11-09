import pytest

from apps.intake.models import ClaimAnswers, DebtInfo, IntakeSession


def _url(session, action=""):
    return f"/api/intake/sessions/{session.pk}/{action}"


def _draft(session):
    return DebtInfo.objects.create(
        session=session,
        creditor_name="Demo Scanned Bill",
        debt_type="medical",
        amount_owed="200.00",
        is_draft=True,
    )


def test_claim_answers_set_only_the_keys_sent(filer):
    client, session = filer
    first = client.patch(
        _url(session),
        {"claim_answers": {"contracts_answer": "yes", "community_state": "Illinois"}},
        format="json",
    )
    assert first.status_code == 200
    assert first.data["claim_answers"] == {"contracts_answer": "yes", "community_state": "Illinois"}

    second = client.patch(
        _url(session), {"claim_answers": {"codebtors_answer": "no"}}, format="json"
    )
    expected = {
        "contracts_answer": "yes",
        "community_state": "Illinois",
        "codebtors_answer": "no",
    }
    assert second.data["claim_answers"] == expected
    assert client.get(_url(session)).data["claim_answers"] == expected


def test_a_fresh_session_reads_no_claim_answers_and_no_row(filer):
    client, session = filer
    assert client.get(_url(session)).data["claim_answers"] == {}
    assert not ClaimAnswers.objects.filter(session=session).exists()


def test_a_null_clears_a_claim_answer(filer):
    client, session = filer
    client.patch(_url(session), {"claim_answers": {"no_debts": True}}, format="json")
    cleared = client.patch(_url(session), {"claim_answers": {"no_debts": None}}, format="json")
    assert cleared.status_code == 200
    assert "no_debts" not in cleared.data["claim_answers"]
    assert "no_debts" not in ClaimAnswers.objects.get(session=session).get_answers()

    never_set = client.patch(
        _url(session), {"claim_answers": {"community_lived": None}}, format="json"
    )
    assert never_set.status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"nope": "yes"},
        {"contracts_answer": "maybe"},
        {"no_debts": False},
        {"no_debts": "true"},
        {"community_state": "x" * 101},
        {"community_spouse_state": "ILL"},
        {"community_spouse_outside_us": "yes"},
        {"community_spouse_name": 5},
    ],
    ids=[
        "unknown_key",
        "bad_choice",
        "no_debts_false",
        "no_debts_string",
        "too_long",
        "state_three_letters",
        "outside_us_string",
        "name_number",
    ],
)
def test_an_unknown_claim_key_or_value_is_refused(filer, body):
    client, session = filer
    response = client.patch(_url(session), {"claim_answers": body}, format="json")
    assert response.status_code == 400
    assert not ClaimAnswers.objects.filter(session=session).exists()
    if body == {"contracts_answer": "maybe"}:
        assert "maybe" not in response.content.decode()


def test_one_bad_claim_key_saves_none_of_the_good_ones(filer):
    client, session = filer
    response = client.patch(
        _url(session),
        {"claim_answers": {"contracts_answer": "yes", "codebtors_answer": "maybe"}},
        format="json",
    )
    assert response.status_code == 400
    assert not ClaimAnswers.objects.filter(session=session).exists()


def test_a_spouse_state_is_stored_in_capitals(filer):
    client, session = filer
    response = client.patch(
        _url(session), {"claim_answers": {"community_spouse_state": "il"}}, format="json"
    )
    assert response.data["claim_answers"]["community_spouse_state"] == "IL"
    assert ClaimAnswers.objects.get(session=session).get_answers()["community_spouse_state"] == "IL"


def test_saving_claim_answers_reopens_a_completed_intake(filer):
    client, session = filer
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")
    response = client.patch(
        _url(session), {"claim_answers": {"contracts_answer": "no"}}, format="json"
    )
    assert response.data["status"] == "in_progress"
    session.refresh_from_db()
    assert session.status == "in_progress"

    IntakeSession.objects.filter(pk=session.pk).update(status="completed")
    put = client.put(
        _url(session),
        {"district": session.district_id, "claim_answers": {"contracts_answer": "yes"}},
        format="json",
    )
    assert put.status_code == 200
    assert put.data["status"] == "in_progress"
    session.refresh_from_db()
    assert session.status == "in_progress"


def test_claim_answers_cannot_be_saved_on_another_filers_intake(filer, other_session):
    client, _ = filer
    response = client.patch(
        _url(other_session), {"claim_answers": {"contracts_answer": "no"}}, format="json"
    )
    assert response.status_code == 404
    assert not ClaimAnswers.objects.filter(session=other_session).exists()


def test_continue_to_step_7_confirms_every_draft(filer):
    client, session = filer
    draft = _draft(session)
    before = client.post(_url(session, "update_step/"), {"current_step": 6}, format="json")
    assert before.status_code == 200
    draft.refresh_from_db()
    assert draft.is_draft is True

    after = client.post(_url(session, "update_step/"), {"current_step": 7}, format="json")
    assert after.data["session"]["debts"][0]["is_draft"] is False
    draft.refresh_from_db()
    assert draft.is_draft is False


def test_continue_to_step_7_saves_the_rows_it_carries_before_confirming(filer):
    client, session = filer
    draft = _draft(session)
    response = client.post(
        _url(session, "update_step/"),
        {
            "current_step": 7,
            "data": {
                "debts": [
                    {
                        "id": draft.pk,
                        "creditor_name": "Demo Scanned Bill",
                        "debt_type": "medical",
                        "amount_owed": "600.00",
                    }
                ]
            },
        },
        format="json",
    )
    assert response.status_code == 200
    draft.refresh_from_db()
    assert str(draft.amount_owed) == "600.00"
    assert draft.is_draft is False
    assert response.data["session"]["debts"][0]["is_draft"] is False


def test_an_autosaved_debts_patch_leaves_a_draft_a_draft(filer):
    client, session = filer
    draft = _draft(session)
    response = client.patch(
        _url(session),
        {
            "debts": [
                {
                    "id": draft.pk,
                    "creditor_name": "Demo Scanned Bill",
                    "debt_type": "medical",
                    "amount_owed": "200.00",
                }
            ]
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.data["debts"][0]["is_draft"] is True
    draft.refresh_from_db()
    assert draft.is_draft is True
