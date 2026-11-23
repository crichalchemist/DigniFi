"""What Schedule I lines 1, 11 and 13 and Schedule J line 24 still lack, in Complete's list (4c).

Business intent: Schedule I prints each of these as a box the filer must tick, so Complete waits
for the three Yes/No questions (a gate), while a missing employment answer or employer name
prints its box blank and only shows on Review and the dashboard (a detail). A stored answer the
step hides behind a later No is no gap: the form doesn't print it. None of these answers reaches
the means test or the household counts, so an unanswered Schedule I never moves them.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.eligibility.cmi import income_step_gaps
from apps.eligibility.services import MeansTestCalculator
from apps.forms.services.fee_waiver import fee_waiver_family, fee_waiver_income
from apps.intake import schedule_i
from apps.intake.completion import (
    EXPENSES_INCLUDE_OTHERS_UNANSWERED,
    EXPENSES_STEP_NEVER_SAVED,
    TAKE_HOME_PAY_NOT_ENTERED,
    Gap,
    completion_gaps,
)
from apps.intake.filing_fee import filing_fee_information
from apps.intake.models import (
    DebtorInfo,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
    ScheduleIAnswers,
)
from apps.intake.petition import GATE_HAZARD
from apps.intake.schedule_i import (
    DETAIL_EMPLOYER,
    DETAIL_EMPLOYMENT,
    DETAIL_J24,
    DETAIL_LINE_11_AMOUNT,
    DETAIL_LINE_13,
    DETAIL_SPOUSE_EMPLOYER,
    DETAIL_SPOUSE_EMPLOYMENT,
    DETAIL_TOO_LONG,
    GATE_J24,
    GATE_LINE_11,
    GATE_LINE_13,
    married_together,
    schedule_i_step_gaps,
)
from apps.intake.tests.builders import (
    SCHEDULE_I_DEFAULTS,
    answer_household,
    answer_petition,
    answer_schedule_i,
)
from apps.users.models import User

SPOUSE_44 = {
    "relationship": "spouse",
    "age": 44,
    "lives_with_you": True,
    "claimed_or_supported": True,
    "spouse_is_dependent": False,
}
DAUGHTER_10 = {
    "relationship": "daughter",
    "age": 10,
    "lives_with_you": True,
    "claimed_or_supported": True,
}
SPOUSE_WAGES = {
    **dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00")),
    "monthly_gross_wages": Decimal("1000.00"),
}
LIMITS = ScheduleIAnswers.TEXT_LIMITS
LABELS = ScheduleIAnswers.TEXT_LABELS


def _too_long(key, form="Schedule I"):
    return DETAIL_TOO_LONG.format(label=LABELS[key], form=form)


def _over(key):
    # One digit past the key's cap: stored as typed, listed too long.
    return "8" * (LIMITS[key] + 1)


@pytest.fixture
def district(db):
    # The real ILND data: the means test's median table is in force on the pinned date.
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


@pytest.fixture
def filer(district):
    user = User.objects.create_user(username="filer", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _session(user, district, *, status="in_progress", **household):
    """An intake with everything Complete asks answered: answer_household's defaults (Schedule
    I's included), the Expenses row and Form 101's answers."""
    session = IntakeSession.objects.create(
        user=user, district=district, status=status, current_step=9
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Demo",
        last_name="Filer",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        street_address="100 Demo St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3500.00"))
    answer_household(session, **household)
    ExpenseInfo.objects.create(session=session, expenses_include_others="no")
    answer_petition(session)
    return session


@pytest.fixture
def finished(filer, district):
    _, user = filer
    return _session(user, district)


@pytest.fixture
def married(filer, district):
    _, user = filer
    return _session(
        user,
        district,
        marital_status="married_together",
        members=[SPOUSE_44, DAUGHTER_10],
        spouse_income=SPOUSE_WAGES,
    )


def _messages(gaps):
    return [str(g) for g in gaps]


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


def _clear(session, *keys):
    answer_schedule_i(session, **dict.fromkeys(keys))


def test_a_session_with_no_record_lists_every_gate(filer, district):
    # Every intake saved before 4c has no record: each question reads as unanswered.
    _, user = filer
    session = IntakeSession.objects.create(user=user, district=district)
    assert not ScheduleIAnswers.objects.filter(session=session).exists()

    gaps = schedule_i_step_gaps(session)

    assert [(g.step, g.kind, str(g)) for g in gaps] == [
        ("income_info", Gap.DETAIL, DETAIL_EMPLOYMENT),
        ("income_info", Gap.GATE, GATE_LINE_11),
        ("income_info", Gap.GATE, GATE_LINE_13),
        ("expense_info", Gap.GATE, GATE_J24),
    ]


def test_the_gaps_come_in_one_fixed_order(married):
    # 4c-R2: employment, the spouse's, the employer, the spouse's employer, line 11, line 13, the
    # too-long texts in the record's order; line 24's own after them, on the Expenses step.
    _clear(married, *SCHEDULE_I_DEFAULTS, "spouse_employment_status")
    answer_schedule_i(
        married,
        occupation=_over("occupation"),  # hidden while the status is unanswered: not measured
        spouse_employment_status="employed",
        spouse_occupation=_over("spouse_occupation"),
        line_11_answer="yes",
        line_11_text=_over("line_11_text"),
        line_13_answer="yes",
        schedule_j_line_24_answer="yes",
    )
    assert [(g.step, str(g)) for g in schedule_i_step_gaps(married)] == [
        ("income_info", DETAIL_EMPLOYMENT),
        ("income_info", DETAIL_SPOUSE_EMPLOYER),
        ("income_info", DETAIL_LINE_11_AMOUNT),
        ("income_info", DETAIL_LINE_13),
        ("income_info", _too_long("spouse_occupation")),
        ("income_info", _too_long("line_11_text")),
        ("expense_info", DETAIL_J24),
    ]

    _clear(married, *ScheduleIAnswers.KEYS)
    answer_schedule_i(
        married,
        employment_status="employed",
        occupation=_over("occupation"),
        schedule_j_line_24_answer="yes",
        schedule_j_line_24_text=_over("schedule_j_line_24_text"),
    )
    assert [(g.step, str(g)) for g in schedule_i_step_gaps(married)] == [
        ("income_info", DETAIL_SPOUSE_EMPLOYMENT),
        ("income_info", DETAIL_EMPLOYER),
        ("income_info", GATE_LINE_11),
        ("income_info", GATE_LINE_13),
        ("income_info", _too_long("occupation")),
        ("expense_info", _too_long("schedule_j_line_24_text", "Schedule J")),
    ]

    # In Complete's list the step 2 gaps follow the Income step's own and come before take-home
    # pay, which comes before the Expenses step.
    married.income_info.assistance_answer = None
    married.income_info.payroll_tax = None
    married.income_info.save()
    messages = _messages(completion_gaps(_fresh(married)))
    last_income = _messages(income_step_gaps(_fresh(married)))[-1]
    at = messages.index(last_income)
    assert messages[at + 1 : at + 6] == [
        DETAIL_SPOUSE_EMPLOYMENT,
        DETAIL_EMPLOYER,
        GATE_LINE_11,
        GATE_LINE_13,
        _too_long("occupation"),
    ]
    assert messages[at + 6] == TAKE_HOME_PAY_NOT_ENTERED


def test_the_filers_employment_details_come_before_the_spouses(married):
    # 4c-R2's pairs side by side: your status before the spouse's, then your employer before the
    # spouse's. A status unanswered and a missing employer exclude each other, so two states.
    _clear(married, "employment_status", "spouse_employment_status")
    assert [str(g) for g in schedule_i_step_gaps(married)] == [
        DETAIL_EMPLOYMENT,
        DETAIL_SPOUSE_EMPLOYMENT,
    ]

    answer_schedule_i(
        married,
        employment_status="employed",
        employer_name="  ",
        spouse_employment_status="employed",
        spouse_employer_name="",
    )
    assert [str(g) for g in schedule_i_step_gaps(married)] == [
        DETAIL_EMPLOYER,
        DETAIL_SPOUSE_EMPLOYER,
    ]


def test_each_gap_has_its_kind_from_the_one_table(finished, monkeypatch):
    # The three Yes/No questions are the only gates (D1); the rest let Complete through.
    _clear(finished, *ScheduleIAnswers.KEYS)
    gaps = schedule_i_step_gaps(finished)
    assert [str(g) for g in gaps if g.kind == Gap.GATE] == [GATE_LINE_11, GATE_LINE_13, GATE_J24]
    assert [str(g) for g in gaps if g.kind == Gap.DETAIL] == [DETAIL_EMPLOYMENT]
    assert set(schedule_i.KIND_OF.values()) == {Gap.GATE, Gap.DETAIL}

    # One line of the table moves a gap from detail to gate, and a gate names no form.
    monkeypatch.setitem(schedule_i.KIND_OF, "employment_status", Gap.GATE)
    (employment,) = [g for g in schedule_i_step_gaps(finished) if str(g) == DETAIL_EMPLOYMENT]
    assert (employment.kind, employment.forms) == (Gap.GATE, ())


def test_the_spouse_gaps_show_only_for_a_spouse_at_home(filer, district):
    _, user = filer
    alone = _session(user, district)
    answer_schedule_i(alone, spouse_employment_status="employed")
    assert schedule_i_step_gaps(alone) == []
    assert married_together(alone) is False

    alone.income_info.marital_status = "married_together"
    alone.income_info.save()
    assert married_together(alone) is True
    assert _messages(schedule_i_step_gaps(alone)) == [DETAIL_SPOUSE_EMPLOYER]

    _clear(alone, "spouse_employment_status")
    gaps = schedule_i_step_gaps(alone)
    assert [(g.step, g.kind, str(g), g.forms) for g in gaps] == [
        ("income_info", Gap.DETAIL, DETAIL_SPOUSE_EMPLOYMENT, ("schedule_i",))
    ]


def test_employed_with_no_employer_name_is_a_detail(finished):
    answer_schedule_i(finished, employment_status="employed", employer_name="   ")

    gaps = schedule_i_step_gaps(finished)

    assert [(g.step, g.kind, str(g), g.forms) for g in gaps] == [
        ("income_info", Gap.DETAIL, DETAIL_EMPLOYER, ("schedule_i",))
    ]
    answer_schedule_i(finished, employer_name="Demo Pharmacy")
    assert schedule_i_step_gaps(finished) == []


def test_not_employed_with_no_occupation_is_no_gap(finished):
    # The spec names no gap for a blank occupation, address or tenure (S:276).
    answer_schedule_i(finished, employment_status="not_employed", occupation="")
    assert schedule_i_step_gaps(finished) == []
    answer_schedule_i(finished, employment_status="employed", employer_name="Demo Hotel")
    assert schedule_i_step_gaps(finished) == []


def test_line_11_yes_with_no_amount_names_form_103b_only_under_the_waiver(finished):
    # 103B line 8 copies line 11's amount, but only a waiver filer's packet holds 103B (4c-R12).
    answer_schedule_i(finished, line_11_answer="yes", line_11_text="Demo relative pays rent")

    (paying,) = schedule_i_step_gaps(finished)
    assert (paying.step, paying.kind, str(paying), paying.forms) == (
        "income_info",
        Gap.DETAIL,
        DETAIL_LINE_11_AMOUNT,
        ("schedule_i",),
    )

    finished.filing_fee.payment_choice = "waiver"
    finished.filing_fee.save()
    (waiving,) = schedule_i_step_gaps(_fresh(finished))
    assert (str(waiving), waiving.forms) == (DETAIL_LINE_11_AMOUNT, ("schedule_i", "form_103b"))

    # A typed 0 is an amount.
    answer_schedule_i(finished, line_11_amount="0")
    assert schedule_i_step_gaps(finished) == []


def test_a_text_over_its_cap_is_a_too_long_detail_naming_its_form(married):
    answer_schedule_i(
        married,
        employment_status="employed",
        employer_name="Demo Logistics",
        employer_city=_over("employer_city"),
        spouse_employment_status="employed",
        spouse_employer_name="Demo Grocery",
        spouse_time_employed=_over("spouse_time_employed"),
        line_13_answer="yes",
        line_13_text=_over("line_13_text"),
        schedule_j_line_24_answer="yes",
        schedule_j_line_24_text=_over("schedule_j_line_24_text"),
    )
    # At its cap, a text is no gap.
    answer_schedule_i(married, occupation="8" * LIMITS["occupation"])

    gaps = schedule_i_step_gaps(married)

    assert [(g.step, g.kind, str(g), g.forms) for g in gaps] == [
        ("income_info", Gap.DETAIL, _too_long("employer_city"), ("schedule_i",)),
        ("income_info", Gap.DETAIL, _too_long("spouse_time_employed"), ("schedule_i",)),
        ("income_info", Gap.DETAIL, _too_long("line_13_text"), ("schedule_i",)),
        (
            "expense_info",
            Gap.DETAIL,
            _too_long("schedule_j_line_24_text", "Schedule J"),
            ("schedule_j",),
        ),
    ]
    assert _too_long("employer_city") == (
        "Your answer for Employer's city is too long for its box on Schedule I."
    )


def test_a_text_over_its_cap_kept_under_a_no_is_not_measured(filer, district):
    # Only where its box prints (4c-R5): a text the step hides prints nothing, so its length is
    # no gap.
    _, user = filer
    session = _session(user, district)
    answer_schedule_i(
        session,
        employment_status="not_employed",
        employer_name=_over("employer_name"),
        time_employed=_over("time_employed"),
        spouse_employment_status="employed",
        spouse_occupation=_over("spouse_occupation"),  # no spouse at home
        line_11_answer="no",
        line_11_text=_over("line_11_text"),
        line_13_answer="no",
        line_13_text=_over("line_13_text"),
        schedule_j_line_24_answer="no",
        schedule_j_line_24_text=_over("schedule_j_line_24_text"),
    )
    assert schedule_i_step_gaps(session) == []

    # Your occupation prints only once your status is answered, as the spouse's does.
    _clear(session, "employment_status")
    answer_schedule_i(session, occupation=_over("occupation"))
    assert _messages(schedule_i_step_gaps(session)) == [DETAIL_EMPLOYMENT]


def test_line_24s_gate_shows_while_the_expenses_step_was_never_saved(filer, district):
    # The record is not the Expenses row: both gaps link to the Expenses step (4c-R2).
    _, user = filer
    session = _session(user, district)
    session.expense_info.delete()
    _clear(session, "schedule_j_line_24_answer")

    messages = _messages(completion_gaps(_fresh(session)))

    at = messages.index(EXPENSES_STEP_NEVER_SAVED)
    assert messages[at + 1] == GATE_J24
    assert [g.step for g in completion_gaps(_fresh(session)) if str(g) == GATE_J24] == [
        "expense_info"
    ]


def test_answers_kept_under_a_no_raise_no_gap(married):
    # An employer under Not employed, a line 11 text or amount and the line 13 and 24 texts under
    # No, and the spouse's block after the marriage answer changed: kept, never a gap.
    answer_schedule_i(
        married,
        employment_status="not_employed",
        employer_street="200 Demo Ave",
        line_11_answer="no",
        line_11_text="",
        line_11_amount="",
        line_13_answer="no",
        line_13_text="   ",
        schedule_j_line_24_answer="no",
        schedule_j_line_24_text="",
        spouse_employment_status="employed",
    )
    married.income_info.marital_status = "married_separately"
    married.income_info.save()

    assert schedule_i_step_gaps(married) == []


def test_complete_refuses_an_unanswered_line_11_and_lets_a_missing_employer_through(
    filer, finished
):
    client, _ = filer
    url = f"/api/intake/sessions/{finished.pk}/complete/"
    answer_schedule_i(finished, line_11_answer=None, employment_status="employed")

    refused = client.post(url)

    assert refused.status_code == 400
    assert refused.data["errors"] == [{"step": "income_info", "message": GATE_LINE_11}]

    answer_schedule_i(finished, line_11_answer="no")
    completed = client.post(url)
    assert completed.status_code == 200, completed.data
    assert _fresh(finished).status == "completed"
    # The employer left blank is still listed, as a detail Schedule I prints blank.
    assert [(g.kind, str(g)) for g in completion_gaps(_fresh(finished))] == [
        (Gap.DETAIL, DETAIL_EMPLOYER)
    ]


def test_line_24s_gaps_sit_after_the_expenses_steps(finished):
    finished.expense_info.expenses_include_others = None
    finished.expense_info.save()
    _clear(finished, "schedule_j_line_24_answer")
    answer_petition(finished, hazard_answer=None)

    messages = _messages(completion_gaps(_fresh(finished)))

    at = messages.index(EXPENSES_INCLUDE_OTHERS_UNANSWERED)
    assert messages[at : at + 3] == [EXPENSES_INCLUDE_OTHERS_UNANSWERED, GATE_J24, GATE_HAZARD]


def test_an_unanswered_schedule_i_leaves_the_means_test_and_household_reads_alone(filer, married):
    # Review Focus 2: no 4c answer reaches CMI, the means test, 103B lines 1 and 2, the filing-fee
    # page's income figure or the household's family size (S:274), so taking every answer away
    # changes none of them. The answers taken away are ones that would move those reads if they
    # leaked: $5,000 a month from others would lift this household of 3 above the median.
    client, _ = filer
    answer_schedule_i(
        married,
        employment_status="employed",
        occupation="Demo clerk",
        employer_name="Demo Employer Inc",
        spouse_employment_status="employed",
        spouse_employer_name="Demo Spouse Employer LLC",
        line_11_answer="yes",
        line_11_text="Demo relative pays the rent",
        line_11_amount="5000.00",
        line_13_answer="yes",
        line_13_text="Demo raise expected next spring",
    )

    def reads():
        session = _fresh(married)
        result = MeansTestCalculator(session).calculate()
        household = client.get(f"/api/intake/sessions/{married.pk}/").data["household"]
        information, _ = filing_fee_information(session)
        return {
            "outcome": result["outcome"],
            "cmi": result["cmi"],
            "family_size": household["family_size"],
            "fee_waiver_household_size": household["fee_waiver_household_size"],
            "103b_line_1": fee_waiver_family(session).total,
            "103b_line_2": fee_waiver_income(session).total,
            "family_income_monthly": information["family_income_monthly"],
            "income_step_gaps": _messages(income_step_gaps(session)),
        }

    before = reads()
    ScheduleIAnswers.objects.filter(session=married).delete()
    after = reads()

    assert GATE_LINE_11 in _messages(schedule_i_step_gaps(_fresh(married)))
    assert before == after
    assert before["family_size"] == 3
    assert before["103b_line_1"] == 3
    assert before["103b_line_2"] == Decimal("4500.00")
    assert before["family_income_monthly"] == "4500.00"
    assert before["outcome"] == "at_or_below_median"
    assert before["income_step_gaps"] == []


@pytest.mark.parametrize("marital_status", ["not_married", "married_together"])
def test_the_builder_default_leaves_no_gap(filer, district, marital_status):
    _, user = filer
    together = marital_status == "married_together"
    session = _session(
        user,
        district,
        marital_status=marital_status,
        members=[SPOUSE_44] if together else [],
        spouse_income=SPOUSE_WAGES if together else None,
    )

    assert schedule_i_step_gaps(session) == []
    assert completion_gaps(_fresh(session)) == []
    expected = dict(SCHEDULE_I_DEFAULTS)
    if together:
        expected["spouse_employment_status"] = "not_employed"
    assert session.schedule_i_answers.get_answers() == expected


def test_the_builders_default_gives_way_to_a_stored_answer(finished):
    # PF-4c-G: a second answer_household keeps what a test stored; an explicit mapping is applied
    # whole, and None leaves the record alone.
    answer_schedule_i(finished, line_11_answer="yes", line_11_amount="25.00")

    answer_household(finished)
    assert finished.schedule_i_answers.get_answers()["line_11_answer"] == "yes"

    answer_household(finished, schedule_i={"line_11_answer": "no", "line_11_amount": None})
    stored = finished.schedule_i_answers.get_answers()
    assert (stored["line_11_answer"], "line_11_amount" in stored) == ("no", False)

    answer_household(finished, schedule_i=None)
    assert finished.schedule_i_answers.get_answers() == stored
