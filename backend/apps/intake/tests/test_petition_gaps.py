"""What Form 101's questions still lack is listed in the filer's words (4b spec §7.1).

Business intent: an unanswered question blocks Complete (a gate), while an answer the form
would print blank is only a detail, and no question is ever answered for the filer.
"""

import json

from apps.intake import petition
from apps.intake.models import PetitionAnswers
from apps.intake.petition import (
    DETAIL_BUSINESS,
    DETAIL_EIN,
    DETAIL_HAZARD,
    DETAIL_ITIN,
    DETAIL_MAILING,
    DETAIL_OTHER_NAMES,
    DETAIL_OTHER_SSN,
    DETAIL_PENDING_CASE,
    DETAIL_PRIOR_CASE,
    DETAIL_PRIOR_DATE,
    DETAIL_TOO_LONG,
    DETAIL_VENUE,
    DETAIL_VENUE_REASON,
    GATE_EVICTION,
    GATE_HAZARD,
    GATE_RENTS,
    STEP_1_GATES,
    petition_step_gaps,
)

NO = {key: "no" for key in (*STEP_1_GATES, "hazard_answer", "rents_residence")}


def _gaps(session, answers):
    PetitionAnswers.objects.update_or_create(
        session=session, defaults={"answers": json.dumps(answers)}
    )
    session.refresh_from_db()
    return [(g.step, g.kind, str(g)) for g in petition_step_gaps(session)]


def test_a_session_with_no_record_lists_the_seven_step_1_gates_then_the_hazard_and_rent_gates(
    filer,
):
    _, session = filer
    gaps = petition_step_gaps(session)
    assert [(g.step, g.kind, str(g)) for g in gaps[:7]] == [
        ("debtor_info", "gate", petition._GATE_SENTENCE[key]) for key in STEP_1_GATES
    ]
    assert [(g.step, g.kind, str(g)) for g in gaps[7:]] == [
        ("debtor_info", "detail", DETAIL_VENUE),
        ("assets", "gate", GATE_HAZARD),
        ("contracts", "gate", GATE_RENTS),
    ]
    assert len(gaps) == 7 + 1 + 1 + 1


def test_every_no_lists_nothing(filer):
    _, session = filer
    assert _gaps(session, {**NO, "venue_choice": "lived_here"}) == []


def test_a_yes_with_nothing_under_it_is_a_detail_not_a_gate(filer):
    _, session = filer
    base = {**NO, "venue_choice": "lived_here"}
    cases = {
        "other_names_answer": DETAIL_OTHER_NAMES,
        "itin_answer": DETAIL_ITIN,
        "other_ssn_answer": DETAIL_OTHER_SSN,
        "mailing_answer": DETAIL_MAILING,
        "sole_proprietor_answer": DETAIL_BUSINESS,
        "hazard_answer": DETAIL_HAZARD,
    }
    for key, sentence in cases.items():
        gaps = _gaps(session, {**base, key: "yes"})
        assert [(kind, text) for _, kind, text in gaps] == [("detail", sentence)], key
    other = _gaps(session, {**base, "venue_choice": "other"})
    assert [text for _, _, text in other] == [DETAIL_VENUE_REASON]


def test_the_eviction_gate_asks_only_under_a_rent_yes(filer):
    _, session = filer
    base = {**NO, "venue_choice": "lived_here"}
    assert _gaps(session, base) == []
    assert _gaps(session, {**base, "rents_residence": "yes"}) == [
        ("contracts", "gate", GATE_EVICTION)
    ]


def test_a_prior_case_row_needs_its_district_and_date(filer):
    _, session = filer
    base = {**NO, "venue_choice": "lived_here", "prior_bankruptcy_answer": "yes"}
    rows = [{"district": "Demo", "filed_on": None}]
    assert [t for _, _, t in _gaps(session, {**base, "prior_cases": rows})] == [DETAIL_PRIOR_CASE]
    ok = [{"district": "Demo", "filed_on": "03/04/2019"}]
    assert _gaps(session, {**base, "prior_cases": ok}) == []
    pending = {**NO, "venue_choice": "lived_here", "pending_case_answer": "yes"}
    assert [t for _, _, t in _gaps(session, {**pending, "pending_cases": [{"debtor": ""}]})] == [
        DETAIL_PENDING_CASE
    ]


def test_a_malformed_date_is_a_detail(filer):
    _, session = filer
    base = {**NO, "venue_choice": "lived_here", "prior_bankruptcy_answer": "yes"}
    rows = [{"district": "Demo", "filed_on": "13/45/2020"}]
    assert [t for _, _, t in _gaps(session, {**base, "prior_cases": rows})] == [DETAIL_PRIOR_DATE]


def test_nothing_of_4d_or_4i_is_listed(filer):
    _, session = filer
    answers = {**NO, "venue_choice": "lived_here"}
    assert "debt_nature" not in answers and "credit_counseling" not in answers
    assert _gaps(session, answers) == []


def test_every_detail_names_the_forms_that_print_it_blank(filer, monkeypatch):
    _, session = filer
    monkeypatch.setattr(PetitionAnswers, "TEXT_LIMITS", {"business_name": 3})
    monkeypatch.setattr(PetitionAnswers, "TEXT_LABELS", {"business_name": "Name of business"})
    every_yes = {key: "yes" for key in (*STEP_1_GATES, "hazard_answer", "rents_residence")}
    answers = {
        **every_yes,
        "venue_choice": "other",
        "ein": "12",
        "business_name": "Demo Business",
        "prior_cases": [{"district": "Demo", "filed_on": "13/45/2020"}, {"filed_on": None}],
        "pending_cases": [{"debtor": ""}],
    }
    PetitionAnswers.objects.create(session=session, answers=json.dumps(answers))
    session.refresh_from_db()
    gaps = petition_step_gaps(session)
    texts = [str(g) for g in gaps]
    for sentence in (DETAIL_VENUE_REASON, DETAIL_OTHER_NAMES, DETAIL_ITIN, DETAIL_OTHER_SSN):
        assert sentence in texts
    assert DETAIL_EIN in texts and DETAIL_MAILING in texts and DETAIL_HAZARD in texts
    for gap in gaps:
        if gap.kind == "detail":
            assert "form_101" in gap.forms
        else:
            assert gap.forms == ()
    by_text = {str(g): g for g in gaps}
    assert "form_121" in by_text[DETAIL_ITIN].forms
    assert "form_121" in by_text[DETAIL_OTHER_SSN].forms
    assert [str(g) for g in gaps if g.kind == "gate"] == [GATE_EVICTION]


def test_a_too_long_text_names_its_box_in_plain_words(filer, monkeypatch):
    _, session = filer
    monkeypatch.setattr(PetitionAnswers, "TEXT_LIMITS", {"business_name": 10})
    monkeypatch.setattr(PetitionAnswers, "TEXT_LABELS", {"business_name": "Name of business"})
    answers = {
        **NO,
        "venue_choice": "lived_here",
        "sole_proprietor_answer": "yes",
        "business_name": "A" * 11,
    }
    gaps = _gaps(session, answers)
    expected = DETAIL_TOO_LONG.format(label="Name of business")
    assert gaps == [("debtor_info", "detail", expected)]
    assert "{" not in expected
