# ruff: noqa: F811
"""The builder answers every page question, so a test of an above-median session can reach the
gate's last step."""

from decimal import Decimal

import pytest

from apps.districts.dated_tables import fill_date
from apps.eligibility.means_inputs import read_inputs, read_tables
from apps.eligibility.means_lines import MISSING, work_out
from apps.forms.tests.test_means_hold import (  # noqa: F401, F811
    above,
    district,
    session_with_debtor,
    user,
)
from apps.intake.models import IntakeSession
from apps.intake.tests.builders import answer_means_test, linked_loan, linked_row


def _car_and_loan(session):
    car = linked_row(session, "3")
    loan = linked_loan(session, car, Decimal("450.00"))
    return car, loan


@pytest.mark.django_db
def test_the_builder_answers_every_question_the_calculator_reads(above):
    _car_and_loan(above)

    answer_means_test(above)

    tables, _ = read_tables(fill_date())
    lines = work_out(read_inputs(above), tables)
    assert [key for key, value in lines.lines.items() if value is MISSING] == []
    assert lines.outcome in ("no_presumption", "presumption")


@pytest.mark.django_db
def test_the_builder_answers_the_spouse_block_only_under_married_together(above):
    answer_means_test(above)
    single = IntakeSession.objects.get(pk=above.pk).means_test_answers.get_answers()
    assert (single.get("line_3_answer"), single.get("spouse_vehicles_answer")) == (None, None)
    assert single.get("spouse_loans_answer") is None

    income = above.income_info
    income.marital_status = "married_together"
    income.save()
    answer_means_test(above)

    married = IntakeSession.objects.get(pk=above.pk).means_test_answers.get_answers()
    assert (
        married["line_3_answer"],
        married["spouse_vehicles_answer"],
        married["spouse_loans_answer"],
    ) == ("no", "no", "no")


@pytest.mark.django_db
def test_over_replaces_an_answer_and_debts_merges_per_debt(above):
    _, loan = _car_and_loan(above)

    answer_means_test(above, line_16="2300.00", debts={loan.pk: {"payments_left": "37"}})

    stored = IntakeSession.objects.get(pk=above.pk)
    assert stored.means_test_answers.get_answers()["line_16"] == "2300.00"
    answers = type(loan).objects.get(pk=loan.pk).means_answers
    assert (answers.payments_left, answers.payment_changes) == ("37", "no")

    answer_means_test(above, line_16=None)

    stored = IntakeSession.objects.get(pk=above.pk)
    assert stored.means_test_answers.get_answers()["line_16"] is None
    assert type(loan).objects.get(pk=loan.pk).means_answers.payments_left == "60_or_more"


@pytest.mark.django_db
def test_the_session_a_test_holds_reads_the_answers_the_builder_wrote(above):
    _car_and_loan(above)
    assert read_inputs(above).line_16 is None

    answer_means_test(above, line_16="2300.00")

    assert read_inputs(above).line_16 == Decimal("2300.00")


@pytest.mark.django_db
def test_over_refuses_a_key_the_page_doesnt_ask(above):
    _car_and_loan(above)

    with pytest.raises(KeyError):
        answer_means_test(above, not_a_question="yes")
    with pytest.raises(KeyError):
        answer_means_test(above, debts={999999: {"payments_left": "37"}})


@pytest.mark.django_db
def test_a_misspelled_per_debt_answer_is_refused_not_silently_dropped(above):
    _car, loan = _car_and_loan(above)

    with pytest.raises(KeyError):
        answer_means_test(above, debts={loan.pk: {"payments_lft": "37"}})

    assert getattr(above, "means_test_answers", None) is None
