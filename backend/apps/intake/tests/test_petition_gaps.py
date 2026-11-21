"""What Form 101's questions still lack is listed in the filer's words (4b spec §7.1).

Business intent: an unanswered question blocks Complete (a gate), while an answer the form
would print blank is only a detail, and no question is ever answered for the filer.
"""

import json

import pytest

from apps.intake.models import PetitionAnswers
from apps.intake.petition import (
    CELL_LABELS,
    DETAIL_BUSINESS,
    DETAIL_EIN,
    DETAIL_HAZARD,
    DETAIL_ITIN,
    DETAIL_MAILING,
    DETAIL_OTHER_NAMES,
    DETAIL_OTHER_SSN,
    DETAIL_PENDING_CASE,
    DETAIL_PENDING_DATE,
    DETAIL_PRIOR_CASE,
    DETAIL_PRIOR_DATE,
    DETAIL_TOO_LONG,
    DETAIL_TOO_LONG_ROW,
    DETAIL_VENUE,
    DETAIL_VENUE_REASON,
    GATE_EVICTION,
    GATE_HAZARD,
    GATE_ITIN,
    GATE_MAILING,
    GATE_OTHER_NAMES,
    GATE_OTHER_SSN,
    GATE_PENDING_CASE,
    GATE_PRIOR_BANKRUPTCY,
    GATE_RENTS,
    GATE_SOLE_PROPRIETOR,
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


# Each step-1 question with the sentence that asks it, written out so a sentence moved to
# another question (say the ITIN's to the other number's) is caught.
STEP_1_GATE_SENTENCES = [
    ("other_names_answer", GATE_OTHER_NAMES),
    ("itin_answer", GATE_ITIN),
    ("other_ssn_answer", GATE_OTHER_SSN),
    ("mailing_answer", GATE_MAILING),
    ("prior_bankruptcy_answer", GATE_PRIOR_BANKRUPTCY),
    ("pending_case_answer", GATE_PENDING_CASE),
    ("sole_proprietor_answer", GATE_SOLE_PROPRIETOR),
]


def test_a_session_with_no_record_lists_the_seven_step_1_gates_then_the_hazard_and_rent_gates(
    filer,
):
    _, session = filer
    gaps = petition_step_gaps(session)
    assert [(g.step, g.kind, str(g)) for g in gaps[:7]] == [
        ("debtor_info", "gate", sentence) for _, sentence in STEP_1_GATE_SENTENCES
    ]
    assert [(g.step, g.kind, str(g)) for g in gaps[7:]] == [
        ("debtor_info", "detail", DETAIL_VENUE),
        ("assets", "gate", GATE_HAZARD),
        ("contracts", "gate", GATE_RENTS),
    ]
    assert len(gaps) == 7 + 1 + 1 + 1


def test_each_step_1_question_left_open_is_asked_in_its_own_words(filer):
    _, session = filer
    for key, sentence in STEP_1_GATE_SENTENCES:
        answers = {**NO, "venue_choice": "lived_here"}
        del answers[key]
        assert _gaps(session, answers) == [("debtor_info", "gate", sentence)], key


def test_the_other_reason_gap_asks_only_for_the_reason(filer):
    # FR-venue: it names no other answer to pick, since line 6's first answer is a sworn
    # statement about where the filer lived (UPL §II.4).
    _, session = filer
    assert _gaps(session, {**NO, "venue_choice": "other"}) == [
        ("debtor_info", "detail", "Explain your other reason for filing here.")
    ]


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


def test_a_yes_to_an_earlier_or_pending_case_with_no_row_is_a_detail(filer):
    _, session = filer
    prior = {**NO, "venue_choice": "lived_here", "prior_bankruptcy_answer": "yes"}
    pending = {**NO, "venue_choice": "lived_here", "pending_case_answer": "yes"}
    for rows in ({"prior_cases": []}, {"prior_cases": [{}]}, {}):
        assert [t for _, _, t in _gaps(session, {**prior, **rows})] == [DETAIL_PRIOR_CASE]
    for rows in ({"pending_cases": []}, {"pending_cases": [{}]}, {}):
        assert [t for _, _, t in _gaps(session, {**pending, **rows})] == [DETAIL_PENDING_CASE]


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
            assert gap.forms
        else:
            assert gap.forms == ()
    by_text = {str(g): g for g in gaps}
    assert by_text[DETAIL_ITIN].forms == ("form_101", "form_121")
    # Form 101 has no box for the other number, so only Form 121 prints it blank.
    assert by_text[DETAIL_OTHER_SSN].forms == ("form_121",)
    assert by_text[DETAIL_EIN].forms == ("form_101",)
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


def test_a_yes_to_other_names_is_answered_by_a_business_name_alone(filer):
    _, session = filer
    base = {**NO, "venue_choice": "lived_here", "other_names_answer": "yes"}
    named = {**base, "other_business_names": [{"name": "Demo Trading Co"}]}
    assert _gaps(session, named) == []
    assert [t for _, _, t in _gaps(session, base)] == [DETAIL_OTHER_NAMES]


def test_the_details_come_in_one_fixed_order(filer, monkeypatch):
    _, session = filer
    monkeypatch.setattr(PetitionAnswers, "TEXT_LIMITS", {"business_city": 3})
    monkeypatch.setattr(PetitionAnswers, "TEXT_LABELS", {"business_city": "City of business"})
    every_yes = {key: "yes" for key in (*STEP_1_GATES, "hazard_answer", "rents_residence")}
    answers = {
        **every_yes,
        "venue_choice": "other",
        "ein": "12",
        "business_city": "Springfield",
        "prior_cases": [{"district": "Demo", "filed_on": "13/45/2020"}, {"filed_on": None}],
        "pending_cases": [{"debtor": ""}],
    }
    PetitionAnswers.objects.create(session=session, answers=json.dumps(answers))
    session.refresh_from_db()
    assert [str(g) for g in petition_step_gaps(session)] == [
        DETAIL_VENUE_REASON,
        DETAIL_OTHER_NAMES,
        DETAIL_ITIN,
        DETAIL_OTHER_SSN,
        DETAIL_MAILING,
        DETAIL_BUSINESS,
        DETAIL_EIN,
        DETAIL_PRIOR_CASE,
        DETAIL_PRIOR_DATE,
        DETAIL_PENDING_CASE,
        DETAIL_TOO_LONG.format(label="City of business"),
        DETAIL_HAZARD,
        GATE_EVICTION,
    ]


def test_a_too_long_answer_to_another_steps_question_is_not_listed_here(filer, monkeypatch):
    _, session = filer
    monkeypatch.setattr(
        PetitionAnswers,
        "TEXT_LIMITS",
        {"preparer_name": 3, "debt_nature_text": 3, "landlord_name": 3},
    )
    answers = {
        **NO,
        "venue_choice": "lived_here",
        "preparer_name": "A" * 10,
        "debt_nature_text": "B" * 10,
        "landlord_name": "C" * 10,
    }
    assert _gaps(session, answers) == []


def test_the_owner_approved_gate_and_pending_date_sentences_are_exact():
    assert GATE_HAZARD == (
        "Say whether any property you own poses a hazard or needs attention right away."
    )
    assert GATE_OTHER_SSN == (
        "Say whether you have used any other Social Security number. Answer Yes or No."
    )
    assert DETAIL_PENDING_DATE == (
        "A date is written as MM/DD/YYYY. Check the date of the pending case."
    )


def test_a_malformed_pending_date_is_a_detail_under_yes_and_nothing_under_no(filer):
    _, session = filer
    base = {**NO, "venue_choice": "lived_here"}
    rows = [{"debtor": "Demo Partner", "filed_on": "2025-01-15"}]
    yes = {**base, "pending_case_answer": "yes", "pending_cases": rows}
    assert [t for _, _, t in _gaps(session, yes)] == [DETAIL_PENDING_DATE]
    assert _gaps(session, {**base, "pending_cases": rows}) == []
    blank = [{"debtor": "Demo Partner", "filed_on": ""}]
    assert _gaps(session, {**yes, "pending_cases": blank}) == []


def test_a_too_long_text_under_a_no_is_not_listed(filer, monkeypatch):
    # A box hidden under a No prints nothing, so a line about its length would be false.
    _, session = filer
    monkeypatch.setattr(PetitionAnswers, "TEXT_LIMITS", {"business_name": 3, "hazard_what": 3})
    monkeypatch.setattr(PetitionAnswers, "TEXT_LABELS", {})
    long = {"business_name": "Demo Business", "hazard_what": "Leaking tank"}
    base = {"venue_choice": "lived_here", **long}
    gated = ("sole_proprietor_answer", "hazard_answer")
    unanswered = {k: v for k, v in NO.items() if k not in gated}
    for state in (NO, unanswered):
        gaps = [t for _, k, t in _gaps(session, {**base, **state}) if "too long" in t]
        assert gaps == []
    yes = {**NO, "sole_proprietor_answer": "yes", "hazard_answer": "yes"}
    texts = [t for _, _, t in _gaps(session, {**base, **yes})]
    assert DETAIL_TOO_LONG.format(label="business name") in texts
    assert DETAIL_TOO_LONG.format(label="hazard what") in texts


@pytest.mark.parametrize(
    "itin,listed",
    [("812345678", True), ("912345678", False), ("9-12-34-5678", False), ("91234567", True)],
)
def test_an_itin_is_nine_digits_starting_with_9(filer, itin, listed):
    _, session = filer
    answers = {**NO, "venue_choice": "lived_here", "itin_answer": "yes", "itin": itin}
    texts = [t for _, _, t in _gaps(session, answers)]
    assert (DETAIL_ITIN in texts) is listed


def _too_long(label):
    return DETAIL_TOO_LONG.format(label=label)


def _row_too_long(label, noun, n):
    return DETAIL_TOO_LONG_ROW.format(label=label, noun=noun, n=n)


def test_capitals_under_a_cap_that_dont_fit_the_box_are_named_too_long(filer):
    # PF2-1: the cap counts digit-wide letters, so wide capitals under it can still be refused
    # at Generate; Review names them first, in the same sentence as an answer over its cap.
    _, session = filer
    cap = PetitionAnswers.TEXT_LIMITS["business_name"]
    base = {**NO, "venue_choice": "lived_here", "sole_proprietor_answer": "yes"}
    label = _too_long(PetitionAnswers.TEXT_LABELS["business_name"])
    assert _gaps(session, {**base, "business_name": "W" * cap}) == [
        ("debtor_info", "detail", label)
    ]
    assert _gaps(session, {**base, "business_name": "Demo Cleaning Services"}) == []


def test_an_answer_over_its_cap_and_too_wide_is_listed_once(filer):
    _, session = filer
    cap = PetitionAnswers.TEXT_LIMITS["business_name"]
    answers = {
        **NO,
        "venue_choice": "lived_here",
        "sole_proprietor_answer": "yes",
        "business_name": "W" * (cap + 1),
    }
    label = _too_long(PetitionAnswers.TEXT_LABELS["business_name"])
    assert _gaps(session, answers) == [("debtor_info", "detail", label)]


def test_a_too_wide_answer_under_a_no_is_not_listed(filer):
    # The measured line is gated by the same predicate as the character one (PF2-3).
    _, session = filer
    cap = PetitionAnswers.TEXT_LIMITS["hazard_what"]
    answers = {**NO, "venue_choice": "lived_here", "hazard_what": "W" * cap}
    assert _gaps(session, answers) == []


def test_too_wide_texts_and_cells_come_after_the_step_1_details_in_one_order(filer):
    # The step's texts in their order, then its row cells by line (2, 9, 10), then step 5's.
    _, session = filer
    answers = {
        **NO,
        "venue_choice": "lived_here",
        "mailing_answer": "yes",
        "mailing_city": "W" * PetitionAnswers.TEXT_LIMITS["mailing_city"],
        "prior_bankruptcy_answer": "yes",
        "prior_cases": [{"district": "W" * 40, "filed_on": "01/02/2020"}],
        "other_names_answer": "yes",
        "other_names": [{"first": "W" * 60}],
        "hazard_answer": "yes",
        "hazard_what": "W" * PetitionAnswers.TEXT_LIMITS["hazard_what"],
    }
    assert _gaps(session, answers) == [
        ("debtor_info", "detail", _too_long(PetitionAnswers.TEXT_LABELS["mailing_city"])),
        ("debtor_info", "detail", _row_too_long(CELL_LABELS["other_names"]["first"], "name", 1)),
        ("debtor_info", "detail", _row_too_long(CELL_LABELS["prior_cases"]["district"], "case", 1)),
        ("assets", "detail", _too_long(PetitionAnswers.TEXT_LABELS["hazard_what"])),
    ]


def test_a_too_wide_row_cell_names_the_forms_of_its_list(filer):
    _, session = filer
    answers = {
        **NO,
        "venue_choice": "lived_here",
        "pending_case_answer": "yes",
        "pending_cases": [{"debtor": "W" * 60}],
    }
    PetitionAnswers.objects.create(session=session, answers=json.dumps(answers))
    session.refresh_from_db()
    (gap,) = petition_step_gaps(session)
    assert (str(gap), gap.forms) == (
        _row_too_long(CELL_LABELS["pending_cases"]["debtor"], "case", 1),
        ("form_101",),
    )
