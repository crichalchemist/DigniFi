"""The in-app result says only what the form's arithmetic gives, in one of four outcomes, and
never a verdict."""

import logging
from dataclasses import replace
from datetime import date
from decimal import Decimal as D

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.dated_tables import NoTableInForce
from apps.districts.means_standards import NoMeansTestTable
from apps.districts.models import District
from apps.eligibility.cmi import MEMBER_UNANSWERED, IncomeStepGap, income_step_gaps
from apps.eligibility.means_inputs import read_inputs, read_tables
from apps.eligibility.means_lines import SKIPPED, work_out
from apps.eligibility.models import MeansTest
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.eligibility.tests.test_means_inputs import PRIYAS_ANSWERS
from apps.intake.models import DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household
from apps.users.models import User


def _session(wages):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    user = User.objects.create_user(username=f"outcome{wages}", password="pw")
    session = IntakeSession.objects.create(user=user, district=District.objects.get(code="ilnd"))
    IncomeInfo.objects.create(
        session=session,
        **{
            **dict.fromkeys(IncomeInfo.SOURCE_FIELDS, D("0.00")),
            "monthly_gross_wages": D(wages),
        },
    )
    answer_household(session)
    DebtorInfo.objects.create(
        session=session,
        first_name="Demo",
        last_name="Filer",
        ssn="900112222",
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="demo@example.com",
        street_address="1 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return IntakeSession.objects.get(pk=session.pk)


@pytest.fixture
def session_at_3000(db):
    return _session("3000.00")


@pytest.fixture
def session_at_9000(db):
    return _session("9000.00")


@pytest.fixture
def api_client(session_at_9000):
    client = APIClient()
    client.force_authenticate(user=session_at_9000.user)
    return client


def test_a_filer_at_or_below_the_median_is_told_so_and_passes(session_at_3000):
    result = MeansTestCalculator(session_at_3000).calculate()
    assert (result["outcome"], result["passes_means_test"], result["tables_gap"]) == (
        "at_or_below_median",
        True,
        None,
    )
    assert result["details"]["tables"] == []


def test_an_above_median_filer_cant_be_worked_out_until_the_page_asks_its_questions(
    session_at_9000,
):
    result = MeansTestCalculator(session_at_9000).calculate()
    assert (result["outcome"], result["passes_means_test"]) == ("cannot_work_out", None)
    assert [t["name"] for t in result["details"]["tables"]] == [
        "IRS expense standards",
        "Bankruptcy Code dollar amounts",
    ]
    assert MeansTest.objects.get(session=session_at_9000).outcome == "cannot_work_out"


def test_an_above_median_session_with_no_debtor_info_still_gets_an_outcome(session_at_9000):
    DebtorInfo.objects.filter(session=session_at_9000).delete()
    session = IntakeSession.objects.get(pk=session_at_9000.pk)
    assert not ExpenseInfo.objects.filter(session=session).exists()
    result = MeansTestCalculator(session).calculate()
    assert (result["outcome"], result["passes_means_test"]) == ("cannot_work_out", None)


@pytest.mark.parametrize(
    "line_16, line_24, line_39d, outcome, passes",
    [
        (D("2300.00"), D("7096.00"), D("57444.00"), "presumption", False),
        (D("3200.00"), D("7996.00"), D("3444.00"), "no_presumption", True),
    ],
)
def test_a_worked_out_result_is_the_comparisons_and_passes_follows_it(
    session_at_9000, monkeypatch, line_16, line_24, line_39d, outcome, passes
):
    # The session boundary only: the real reader, with the page's answers merged in (what 3h2
    # will store).
    def reader(session):
        return replace(read_inputs(session), **{**PRIYAS_ANSWERS, "line_16": line_16})

    monkeypatch.setattr("apps.eligibility.models.read_inputs", reader)
    # 122A-2 reads no Schedule J figure (§7.11)
    assert not ExpenseInfo.objects.filter(session=session_at_9000).exists()
    lines = work_out(reader(session_at_9000), read_tables()[0])
    assert lines.lines["24"] == line_24
    assert lines.lines["32"] == D("850.00")
    assert lines.lines["36"] == D("96.60")
    assert lines.lines["35"] is SKIPPED
    assert lines.lines["39d"] == line_39d
    assert lines.outcome == outcome

    result = MeansTestCalculator(session_at_9000).calculate()
    assert (result["outcome"], result["passes_means_test"]) == (outcome, passes)
    assert MeansTest.objects.get(session=session_at_9000).outcome == outcome


def test_a_missing_median_table_still_refuses_and_is_never_cannot_work_out(
    session_at_9000, monkeypatch
):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2027, 4, 1))
    with pytest.raises(NoTableInForce) as refused:
        MeansTestCalculator(session_at_9000).calculate()
    assert not isinstance(refused.value, NoMeansTestTable)


def test_a_missing_122a2_table_is_cannot_work_out_with_the_table_named(
    session_at_9000, api_client, monkeypatch
):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2026, 7, 14))
    response = api_client.post(f"/api/intake/sessions/{session_at_9000.pk}/calculate_means_test/")
    assert response.status_code == 200
    result = response.data["means_test_result"]
    assert (result["outcome"], result["tables_gap"]) == ("cannot_work_out", "IRS expense standards")


def test_a_below_median_filer_never_reads_the_122a2_tables(session_at_3000, monkeypatch, caplog):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2026, 7, 14))
    with caplog.at_level(logging.ERROR):
        result = MeansTestCalculator(session_at_3000).calculate()
    assert result["outcome"] == "at_or_below_median" and caplog.records == []


def test_the_calculate_reply_carries_the_outcome_and_no_sentence(session_at_3000):
    assert set(MeansTestCalculator(session_at_3000).calculate()) == {
        "passes_means_test",
        "cmi",
        "median_income_threshold",
        "family_size",
        "details",
        "means_test_id",
        "outcome",
        "tables_gap",
    }


def test_the_session_summary_carries_the_outcome(session_at_9000, api_client):
    api_client.post(f"/api/intake/sessions/{session_at_9000.pk}/calculate_means_test/")
    response = api_client.get(f"/api/intake/sessions/{session_at_9000.pk}/summary/")
    assert response.data["means_test"] == {"passes": None, "outcome": "cannot_work_out"}


def test_a_row_saved_before_3h1_reads_as_not_worked_out_until_the_next_calculation(
    session_at_9000,
):
    row = MeansTest.objects.create(
        session=session_at_9000,
        district=session_at_9000.district,
        median_income_threshold=D("73180.00"),
        calculated_cmi=D("9000.00"),
        passes_means_test=False,
        outcome=None,
    )
    assert str(row) == f"Means Test {row.id} - not worked out yet"
    MeansTestCalculator(IntakeSession.objects.get(pk=session_at_9000.pk)).calculate()
    row.refresh_from_db()
    assert str(row) == f"Means Test {row.id} - cannot_work_out"


def test_a_household_row_left_unanswered_is_refused_in_the_income_steps_words_before_any_line(
    session_at_9000, api_client, monkeypatch
):
    household = session_at_9000.household
    household.store_members(
        [
            {
                "relationship": "son",
                "age": 8,
                "lives_with_you": True,
                "claimed_or_supported": None,
            }
        ]
    )
    household.save()

    def never(*args, **kwargs):
        raise AssertionError("a 122A-2 figure was worked out before the Income step's gaps")

    monkeypatch.setattr("apps.eligibility.models.read_inputs", never)
    monkeypatch.setattr("apps.eligibility.models.work_out", never)
    with pytest.raises(IncomeStepGap):
        MeansTestCalculator(IntakeSession.objects.get(pk=session_at_9000.pk)).calculate()
    response = api_client.post(f"/api/intake/sessions/{session_at_9000.pk}/calculate_means_test/")
    assert response.status_code == 400
    sentence = str(income_step_gaps(IntakeSession.objects.get(pk=session_at_9000.pk))[0])
    assert response.data["error"] == sentence
    # The first gap is the row's own, not some other gap that happened to come first
    assert sentence == MEMBER_UNANSWERED
