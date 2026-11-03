"""Form 101 line 8 and 103B's own answers, kept on one encrypted record (3f spec §4, §6.5).

Business intent: how the filer will pay the filing fee is the filer's own answer. Nothing
starts answered, a save changes only what it sends, and a choice moved off the waiver keeps
the waiver answers for a return. Every answer is filer data, so it is ciphertext in the table.
The court's limit and the filer's own figure are shown beside the question as information
only: when either can't be worked out the page says why, and the answer still saves. Saving
never sends a completed intake back to be completed again, and another filer's session is
never found.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.districts.models import District, PovertyGuideline
from apps.forms.services.derivations import DERIVATIONS
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.intake.models import FilingFee, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household
from apps.users.models import User

ANSWER_FIELDS = (
    "payment_choice",
    "income_change_answer",
    "income_change_explanation",
    "installments_explanation",
    "others_covered_answer",
    "others_covered_who",
    "expense_change_answer",
    "expense_change_explanation",
)
# Maria's line 5, approved by the owner (spec §10); the text limits are measured with it.
LINE_5_DRAFT = (
    "I support two children on what I earn. After rent, food, the car and the children's "
    "costs, there is not enough left each month to pay the fee, even in parts."
)
ROOMMATE = {
    "relationship": "roommate",
    "age": 29,
    "lives_with_you": True,
    "claimed_or_supported": False,
}
# Every answer given, for the ciphertext check: (value, a piece that must not show in the table).
ANSWERS = {
    "payment_choice": ("installments", "installments"),
    "income_change_answer": ("yes", None),
    "income_change_explanation": ("My hours at the store drop in December.", "December"),
    "installments_explanation": (LINE_5_DRAFT, "children"),
    "others_covered_answer": ("yes", None),
    "others_covered_who": ("My mother, who stays with us each summer.", "mother"),
    "expense_change_answer": ("yes", None),
    "expense_change_explanation": ("My rent goes up $90 in March.", "March"),
}


def _filer(username):
    user = User.objects.create_user(username=username, password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def sarah(db):
    """A completed intake shaped like Sarah's (spec §10): not married, a roommate she doesn't
    support, $2,000.00 in wages less $250.00 taken out of pay, and no line 8 answer yet."""
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    client, user = _filer("filer")
    session = IntakeSession.objects.create(
        user=user, district=district, status="completed", current_step=9
    )
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("2000.00")
    )
    answer_household(
        session, members=[ROOMMATE], payroll_tax=Decimal("250.00"), payment_choice=None
    )
    return client, session


def _url(session):
    return f"/api/intake/sessions/{session.pk}/filing-fee/"


def _put(client, session, body):
    return client.put(_url(session), body, format="json")


def _sample(length):
    """Maria's line 5, repeated and cut at length."""
    text = LINE_5_DRAFT + " "
    return (text * (length // len(text) + 1))[:length]


def test_nothing_is_answered_until_the_filer_answers(sarah):
    client, session = sarah
    body = client.get(_url(session)).json()
    assert set(body) == {*ANSWER_FIELDS, "information", "information_gap"}
    assert {name: body[name] for name in ANSWER_FIELDS} == {
        "payment_choice": None,
        "income_change_answer": None,
        "income_change_explanation": "",
        "installments_explanation": "",
        "others_covered_answer": None,
        "others_covered_who": "",
        "expense_change_answer": None,
        "expense_change_explanation": "",
    }
    assert not FilingFee.objects.filter(session=session).exists()  # reading stores nothing


def test_the_court_limit_and_the_filers_own_figure_are_shown_beside_the_question(sarah):
    client, session = sarah
    body = client.get(_url(session)).json()
    guideline = PovertyGuideline.objects.get(effective_date=date(2026, 1, 15))
    # Exactly these four keys: the two figures and where the limit comes from, never a verdict.
    assert body["information"] == {
        "family_size": 1,
        "limit_monthly": "1995.00",
        "guideline": {
            "year": 2026,
            "effective_date": "2026-01-15",
            "source_url": guideline.source_url,
        },
        "family_income_monthly": "1750.00",
    }
    assert body["information_gap"] is None


def test_the_figure_shown_is_the_family_and_total_form_103b_prints(sarah):
    client, session = sarah
    information = client.get(_url(session)).json()["information"]
    assert information["family_size"] == int(DERIVATIONS["fee_waiver_family_size"](session))
    assert Decimal(information["family_income_monthly"]) == Decimal(
        DERIVATIONS["fee_waiver_income_total"](session)
    )


def test_a_save_changes_only_the_answers_it_sends_and_a_withdrawn_waiver_keeps_its_answers(sarah):
    client, session = sarah
    first = _put(
        client,
        session,
        {
            "payment_choice": "waiver",
            "income_change_answer": "no",
            "installments_explanation": LINE_5_DRAFT,
        },
    )
    assert first.status_code == 200
    assert first.json()["payment_choice"] == "waiver"
    assert first.json()["information"]["limit_monthly"] == "1995.00"  # the reply is the GET body

    moved = _put(client, session, {"payment_choice": "pay_in_full"}).json()
    assert (moved["payment_choice"], moved["income_change_answer"]) == ("pay_in_full", "no")
    assert moved["installments_explanation"] == LINE_5_DRAFT

    back = _put(client, session, {"payment_choice": "waiver"}).json()
    assert (back["income_change_answer"], back["installments_explanation"]) == ("no", LINE_5_DRAFT)


def test_a_yes_or_no_answer_can_be_left_unanswered_again(sarah):
    client, session = sarah
    _put(client, session, {"others_covered_answer": "yes"})
    reply = _put(client, session, {"others_covered_answer": None})
    assert reply.status_code == 200
    assert FilingFee.objects.get(session=session).others_covered_answer is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("payment_choice", "monthly"),
        ("payment_choice", None),  # a filer changes the answer; nothing takes it back
        ("payment_choice", ""),
        ("income_change_answer", "maybe"),
        ("others_covered_answer", True),
        ("expense_change_answer", ""),
        ("others_covered_who", None),
    ],
)
def test_an_answer_no_question_on_the_page_can_have_is_refused_and_nothing_is_stored(
    sarah, field, value
):
    client, session = sarah
    reply = _put(client, session, {field: value})
    assert reply.status_code == 400
    assert field in reply.json()
    assert not FilingFee.objects.filter(session=session).exists()


@pytest.mark.parametrize(
    "key,value",
    [("monthly_take_home_pay", "1750.00"), ("information", None), ("session", 1)],
)
def test_a_key_that_is_not_a_filing_fee_answer_is_refused_by_name_and_nothing_is_stored(
    sarah, key, value
):
    client, session = sarah
    reply = _put(client, session, {"payment_choice": "waiver", key: value})
    assert reply.status_code == 400
    assert set(reply.json()) == {key}
    assert not FilingFee.objects.filter(session=session).exists()


@pytest.mark.parametrize("field", sorted(FilingFee.TEXT_LIMITS))
def test_a_text_is_kept_up_to_its_limit_and_refused_past_it(sarah, field):
    client, session = sarah
    limit = FilingFee.TEXT_LIMITS[field]
    assert _put(client, session, {field: _sample(limit)}).status_code == 200
    assert getattr(FilingFee.objects.get(session=session), field) == _sample(limit).strip()
    assert _put(client, session, {field: _sample(limit + 1)}).status_code == 400


@pytest.mark.parametrize(
    "field,box,limit",
    [
        ("income_change_explanation", "4 type", 520),
        ("installments_explanation", "5 Type", 520),
        ("others_covered_who", "undefined_8", 420),
        ("expense_change_explanation", "undefined_10", 420),
    ],
)
def test_the_longest_text_the_page_takes_fits_its_box_on_form_103b(field, box, limit):
    assert FilingFee.TEXT_LIMITS[field] == limit
    PDFFormFiller().check("form_103b", {box: _sample(limit)})  # fits, at some size down to 6 pt
    with pytest.raises(ValueTooLong):
        # The next ten characters don't: the limit is the box's, rounded down to ten.
        PDFFormFiller().check("form_103b", {box: _sample(limit + 10)})


def test_a_filing_fee_save_never_sends_a_completed_intake_back(sarah):
    client, session = sarah
    assert _put(client, session, {"payment_choice": "pay_in_full"}).status_code == 200
    session.refresh_from_db()
    assert session.status == "completed"


def test_an_intake_reopened_with_an_income_gap_shows_no_figures_and_still_saves_the_answer(sarah):
    client, session = sarah
    reopened = client.patch(
        f"/api/intake/sessions/{session.pk}/",
        {"income_info": {"income_now_different": None}},
        format="json",
    )
    assert reopened.status_code == 200
    session.refresh_from_db()
    assert session.status == "in_progress"

    body = client.get(_url(session)).json()
    assert (body["information"], body["information_gap"]) == (None, "income")

    saved = _put(client, session, {"payment_choice": "waiver"})
    assert saved.status_code == 200
    assert (saved.json()["payment_choice"], saved.json()["information_gap"]) == ("waiver", "income")
    assert FilingFee.objects.get(session=session).payment_choice == "waiver"


def test_with_no_poverty_table_in_force_the_page_says_so_logs_and_still_saves_the_answer(
    sarah, monkeypatch, caplog
):
    client, session = sarah
    # The day before the 2026 guideline was published: none of DigniFi's rows is in force.
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2026, 1, 14))
    body = client.get(_url(session)).json()
    assert (body["information"], body["information_gap"]) == (None, "no_table")
    assert [r.getMessage() for r in caplog.records if r.name == "apps.districts.dated_tables"] == [
        "No HHS poverty guidelines table in force on 2026-01-14 for district -"
    ]

    assert _put(client, session, {"payment_choice": "installments"}).status_code == 200
    assert FilingFee.objects.get(session=session).payment_choice == "installments"


def test_another_filers_session_is_not_found(sarah):
    _, session = sarah
    stranger, _ = _filer("stranger")
    assert stranger.get(_url(session)).status_code == 404
    assert _put(stranger, session, {"payment_choice": "waiver"}).status_code == 404
    assert not FilingFee.objects.filter(session=session).exists()


@pytest.mark.parametrize("field", ANSWER_FIELDS)
def test_every_filing_fee_answer_is_ciphertext_in_the_table(sarah, field):
    client, session = sarah
    body = {name: value for name, (value, _) in ANSWERS.items()}
    assert _put(client, session, body).status_code == 200
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {field} FROM filing_fees WHERE session_id = %s", [session.pk])
        raw = cursor.fetchone()[0]
    plain = ANSWERS[field][1]
    assert raw.startswith("gAAAAA") and (plain is None or plain not in raw)  # a Fernet token


def test_the_shared_test_household_pays_in_full_so_forms_tests_meet_no_new_refusal(sarah):
    _, session = sarah
    answer_household(session, members=[ROOMMATE], payroll_tax=Decimal("250.00"))
    assert FilingFee.objects.get(session=session).payment_choice == "pay_in_full"
    answer_household(session, payment_choice=None)  # leaves the stored answer alone
    assert FilingFee.objects.get(session=session).payment_choice == "pay_in_full"
