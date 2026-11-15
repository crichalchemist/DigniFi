# ruff: noqa: F811
"""The 122A-2 page reads and saves its answers for the filer alone, under the session's lock, and
never reopens a completed intake."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.districts.means_standards import NoMeansTestTable
from apps.eligibility.cmi import income_step_gaps
from apps.forms.tests.test_means_hold import (  # noqa: F401, F811
    above,
    district,
    session_with_debtor,
    user,
)
from apps.intake.means_page import (
    DEBT_NAMED_TWICE,
    NOT_A_COUNTED_DEBT,
    NOT_A_LINE_11_VEHICLE,
    NOT_AN_OPEN_DEBT,
)
from apps.intake.means_test import ANSWER_KEYS
from apps.intake.models import (
    ExpenseInfo,
    IntakeSession,
    MeansTestAnswers,
    SecuredDebtAnswers,
)
from apps.intake.tests.builders import (
    answer_household,
    answer_means_test,
    complete_debt,
    linked_loan,
    linked_row,
)

User = get_user_model()

STAMP = "2026-10-16"
STALE = "2026-09-30"
# the calculator's lines for the `filer` fixture with every page answer "No" (line 35 is skipped
# under No, so it reads null)
EXPECTED_LINES = {"line_7g": "90.00", "line_8": "691.00", "line_35": None, "line_39c": "5074.00"}


@dataclass
class Filer:
    client: APIClient
    session: IntakeSession
    car: object
    loan: object


@pytest.fixture
def filer(user, above):
    client = APIClient()
    client.force_authenticate(user=user)
    car = linked_row(above, "3", description="Demo car")
    loan = linked_loan(above, car, Decimal("450.00"), creditor_name="Demo Auto Finance")
    return Filer(client, above, car, loan)


def _url(session):
    return f"/api/intake/sessions/{session.pk}/means-test/"


def _get(filer):
    return filer.client.get(_url(filer.session))


def _put(filer, body):
    return filer.client.put(_url(filer.session), body, format="json")


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


def _stored(session):
    """Everything the endpoint stores, read fresh, for a 'nothing changed' check."""
    record = MeansTestAnswers.objects.filter(session=session).first()
    per_debt = sorted(
        (
            row.debt_id,
            row.payments_left,
            row.payment_changes,
            row.total_60_months,
            row.taxes_or_insurance,
            row.necessary_for_support,
            row.cure,
        )
        for row in SecuredDebtAnswers.objects.filter(debt__session=session)
    )
    return (
        (
            None
            if record is None
            else (
                record.answers,
                record.debts_answered_on,
                record.next_spouse_vehicle_id,
                record.next_spouse_loan_id,
            )
        ),
        per_debt,
    )


def _answered_on(session):
    return MeansTestAnswers.objects.get(session=session).debts_answered_on


def _set_answered_on(session, day):
    record = MeansTestAnswers.objects.get(session=session)
    record.debts_answered_on = day
    record.save()


def _debt_body(loan, **over):
    return {
        "id": loan.pk,
        "payments_left": "60_or_more",
        "payment_changes": "no",
        "total_60_months": None,
        "taxes_or_insurance": "no",
        "necessary_for_support": None,
        "cure": None,
    } | over


def _stored_loan(**over):
    """A spouse loan as the record stores it (strings), not as a PUT sends it."""
    return {
        "ref": "spouse-1",
        "on_amounts_owed": "no",
        "debt": None,
        "creditor": "Demo Lender",
        "secured_by": "home",
        "property": None,
        "payment": "100.00",
        "payments_left": "12",
        "payment_changes": "no",
        "total_60_months": "3600.00",
        "taxes_or_insurance": "no",
        "necessary_for_support": None,
        "cure": None,
    } | over


def _sent_loan(**over):
    """The same loan as a PUT sends it."""
    return _stored_loan(payments_left=12) | over


def _put_body(page):
    """What the page sends back from a GET (Task 10's toPutBody): every key of `answers`, and
    each of `debts` as its id and per-debt answers, nulls and all. The GET's display keys
    (ref, creditor, property, monthly_payment, secured_by, on_home) are refused on a PUT."""
    keys = (
        "payments_left",
        "payment_changes",
        "total_60_months",
        "taxes_or_insurance",
        "necessary_for_support",
        "cure",
    )
    return {
        **page["answers"],
        "debts": [{"id": debt["id"], **{key: debt[key] for key in keys}} for debt in page["debts"]],
    }


def _other_filers_rows(district):
    other = User.objects.create_user(username="otherfiler", password="pw")
    session = IntakeSession.objects.create(user=other, district=district, status="completed")
    car = linked_row(session, "3", description="Other car")
    loan = linked_loan(session, car, Decimal("100.00"))
    card = complete_debt(session)
    return other, session, car, loan, card


def _married(session):
    answer_household(
        session,
        marital_status="married_together",
        members=[
            {
                "relationship": "spouse",
                "age": 40,
                "lives_with_you": True,
                "claimed_or_supported": False,
                "spouse_is_dependent": False,
            }
        ],
        spouse_income={"monthly_gross_wages": Decimal("0.00")},
    )


@pytest.mark.django_db
def test_an_above_median_filer_reads_their_vehicles_debts_and_every_answer_unanswered(filer):
    page = _get(filer).json()

    assert page["applies"] is True
    assert page["applies_gap"] is None
    assert page["married_together"] is False
    assert page["vehicles"] == [
        {"ref": f"asset-{filer.car.pk}", "name": "Demo car", "leased": False}
    ]
    assert page["debts"] == [
        {
            "id": filer.loan.pk,
            "ref": f"debt-{filer.loan.pk}",
            "creditor": "Demo Auto Finance",
            "property": "Demo car",
            "monthly_payment": "450.00",
            "secured_by": f"asset-{filer.car.pk}",
            "on_home": False,
            "payments_left": None,
            "payment_changes": None,
            "total_60_months": None,
            "taxes_or_insurance": None,
            "necessary_for_support": None,
            "cure": None,
        }
    ]
    assert set(page["answers"]) == set(ANSWER_KEYS)
    for key, value in page["answers"].items():
        if key in ("line_3_rows", "spouse_vehicles", "spouse_loans", "line_43_circumstances"):
            assert value == []
        elif key == "vehicle_claims":
            assert value == {}
        elif key == "vehicle_choice":
            assert value == [None, None]
        else:
            assert value is None, key
    assert page["debt_lines"] == {f"debt-{filer.loan.pk}": None}
    assert page["fill_date"] == "2026-10-16"
    assert page["debts_answered_on"] is None
    assert page["information"]["multiplier"] == "6.9"
    assert page["amounts_owed_loans"] == []
    assert page["gap"] is None


@pytest.mark.django_db
def test_the_loans_line_shows_once_the_car_is_claimed(filer):
    reply = _put(filer, {"vehicle_claims": {f"asset-{filer.car.pk}": "yes"}})

    assert reply.status_code == 200
    assert reply.json()["debt_lines"] == {f"debt-{filer.loan.pk}": "13b"}


@pytest.mark.django_db
def test_a_below_median_filer_reads_applies_false(filer):
    income = filer.session.income_info
    income.monthly_gross_wages = Decimal("1000.00")
    income.save()

    page = _get(filer).json()

    assert page["applies"] is False
    assert page["applies_gap"] is None
    assert page["debt_lines"] is None
    assert page["information"] is None


@pytest.mark.django_db
def test_an_unfinished_intake_gets_applies_null_with_the_income_steps_sentence(filer):
    answer_household(filer.session, members=None)
    sentence = str(income_step_gaps(_fresh(filer.session))[0])

    reply = _get(filer)

    assert reply.status_code == 200
    page = reply.json()
    assert page["applies"] is None
    assert page["applies_gap"] == sentence
    assert sentence
    assert page["debt_lines"] is None


@pytest.mark.django_db
def test_the_figures_beside_lines_follow_the_map(filer, monkeypatch):
    income = filer.session.income_info
    income.payroll_tax = Decimal("0")
    income.payroll_insurance = Decimal("620.00")
    income.payroll_support = None
    income.save()
    ExpenseInfo.objects.create(
        session=filer.session,
        childcare=Decimal("1200.00"),
        vehicle_insurance=Decimal("0"),
        expenses_include_others="no",
    )

    info = _get(filer).json()["information"]

    assert info["schedule_i"]["you"]["5a"] == "0.00"
    assert info["schedule_i"]["you"]["5e"] == "620.00"
    assert "5f" not in info["schedule_i"]["you"]
    assert info["schedule_i"]["spouse"] is None
    assert info["schedule_j"]["8"] == "1200.00"
    assert "15c" not in info["schedule_j"]
    assert info["line_30_people"] == 1
    assert info["line_30_cap"] == "30.00"

    def no_table(on=None):
        raise NoMeansTestTable("IRS expense standards", date(2026, 10, 16))

    monkeypatch.setattr("apps.intake.means_page.read_tables", no_table)
    page = _get(filer).json()
    assert page["information"] is None
    assert page["information_gap"] == "no_table"
    assert page["applies"] is True


@pytest.mark.django_db
def test_every_information_figure_comes_from_the_column_the_sentence_names(filer):
    # One distinct value in every mapped column, so a swapped key or column changes the dict.
    from apps.districts.dated_tables import fill_date
    from apps.districts.means_standards import section_104_in_force
    from apps.eligibility.means_inputs import read_tables

    _married(filer.session)
    income = _fresh(filer.session).income_info
    for n, column in enumerate(
        (
            "payroll_tax",
            "payroll_mandatory_retirement",
            "payroll_retirement_loan",
            "payroll_insurance",
            "payroll_support",
            "payroll_union_dues",
        ),
        start=1,
    ):
        setattr(income, column, Decimal(f"{n}.11"))
    income.save()
    spouse = _fresh(filer.session).spouse_income
    for n, column in enumerate(
        (
            "payroll_tax",
            "payroll_mandatory_retirement",
            "payroll_retirement_loan",
            "payroll_insurance",
            "payroll_support",
            "payroll_union_dues",
        ),
        start=1,
    ):
        setattr(spouse, column, Decimal(f"{n + 10}.22"))
    spouse.save()
    ExpenseInfo.objects.create(
        session=filer.session,
        food_and_groceries=Decimal("101.01"),
        childcare=Decimal("102.01"),
        clothing=Decimal("103.01"),
        medical_expenses=Decimal("104.01"),
        charitable_contributions=Decimal("105.01"),
        vehicle_insurance=Decimal("106.01"),
        insurance_not_deducted=Decimal("107.01"),
        taxes_not_deducted=Decimal("108.01"),
        child_support_paid=Decimal("109.01"),
        expenses_include_others="no",
    )

    answer_means_test(filer.session)
    info = _get(filer).json()["information"]
    tables, _ = read_tables(fill_date())
    limits = section_104_in_force(fill_date())

    assert info["schedule_i"] == {
        "you": {
            "5a": "1.11",
            "5b": "2.11",
            "5d": "3.11",
            "5e": "4.11",
            "5f": "5.11",
            "5g": "6.11",
        },
        "spouse": {
            "5a": "11.22",
            "5b": "12.22",
            "5d": "13.22",
            "5e": "14.22",
            "5f": "15.22",
            "5g": "16.22",
        },
    }
    assert info["schedule_j"] == {
        "7": "101.01",
        "8": "102.01",
        "9": "103.01",
        "11": "104.01",
        "14": "105.01",
        "15c": "106.01",
        "15d": "107.01",
        "16": "108.01",
        "18": "109.01",
    }
    assert info["limits"]["unsecured"] == str(
        limits.chapter_13_unsecured_limit.quantize(Decimal("0.01"))
    )
    assert info["limits"]["secured"] == str(
        limits.chapter_13_secured_limit.quantize(Decimal("0.01"))
    )
    assert info["limits"]["unsecured"] != info["limits"]["secured"]
    assert info["line_15_cap"] == str(tables.public_transport.quantize(Decimal("0.01")))
    assert info["line_29_per_child"] == str(tables.education_per_child.quantize(Decimal("0.01")))
    # the calculator's own lines, pinned whole (values read off the worked-out page)
    assert {k: info[k] for k in ("line_7g", "line_8", "line_35", "line_39c")} == EXPECTED_LINES


@pytest.mark.django_db
def test_a_filer_with_no_expenses_row_has_no_schedule_j_figures(filer):
    assert _get(filer).json()["information"]["schedule_j"] == {}


@pytest.mark.django_db
def test_a_spouses_schedule_i_figures_show_only_under_married_together(filer):
    _married(filer.session)
    spouse = _fresh(filer.session).spouse_income
    spouse.payroll_union_dues = Decimal("12.00")
    spouse.save()

    page = _get(filer).json()

    assert page["applies_gap"] is None
    assert page["married_together"] is True
    assert page["information"]["schedule_i"]["spouse"] == {
        "5a": "0.00",  # answer_household stores payroll_tax $0 for the spouse too
        "5g": "12.00",
    }


@pytest.mark.django_db
def test_line_36s_totals_are_schedule_e_f_and_schedule_d(filer):
    complete_debt(
        filer.session,
        creditor_name="Demo Tax Office",
        debt_type="taxes",
        amount_owed=Decimal("3000.00"),
        priority_answer="taxes",
        priority_amount=Decimal("3000.00"),
        nonpriority_amount=Decimal("0.00"),
        past_due_amount=Decimal("3000.00"),
    )
    complete_debt(filer.session, amount_owed=Decimal("500.00"))
    answers = {
        "line_36_answer": "yes",
        "line_36_payment": "1000.00",
    }
    reply = _put(filer, answers).json()["information"]

    assert reply["totals"] == {"unsecured": "3500.00", "secured": "500.00"}
    assert reply["limits"]["effective_date"]
    assert reply["line_36_product"] == "69.00"


@pytest.mark.django_db
def test_a_save_sets_only_the_keys_sent_and_replies_with_the_page(filer):
    assert _stored(filer.session)[0] is None

    first = _put(filer, {"line_16": "12.00", "debts": [_debt_body(filer.loan, payments_left=5)]})

    assert first.status_code == 200
    body = first.json()
    # a first-ever save replies with the answers it just stored
    assert body["answers"]["line_16"] == "12.00"
    assert body["debts"][0]["payments_left"] == 5
    assert set(body) == set(_get(filer).json())

    assert _put(filer, {"line_17": "20.00"}).status_code == 200
    answers = _get(filer).json()["answers"]
    assert (answers["line_16"], answers["line_17"]) == ("12.00", "20.00")


@pytest.mark.django_db
def test_a_debts_only_save_creates_the_record(filer):
    assert _put(filer, {"debts": [_debt_body(filer.loan, payments_left=3)]}).status_code == 200

    assert MeansTestAnswers.objects.filter(session=filer.session).exists()


@pytest.mark.django_db
def test_a_save_never_reopens_a_completed_intake(filer):
    assert filer.session.status == "completed"

    assert _put(filer, {"line_16": "1.00"}).status_code == 200

    assert _fresh(filer.session).status == "completed"


@pytest.mark.django_db
def test_another_filers_session_is_not_found(filer, district):
    other = User.objects.create_user(username="intruder", password="pw")
    client = APIClient()
    client.force_authenticate(user=other)

    assert client.get(_url(filer.session)).status_code == 404
    assert client.put(_url(filer.session), {"line_16": "1.00"}, format="json").status_code == 404
    assert _stored(filer.session)[0] is None


@pytest.mark.django_db
def test_a_save_refuses_a_reference_to_a_row_that_isnt_this_sessions(filer, district):
    _, _, other_car, other_loan, other_card = _other_filers_rows(district)
    card = complete_debt(filer.session)
    other_ref = f"asset-{other_car.pk}"
    cases = [
        (
            {"debts": [_debt_body(other_loan)]},
            {"debts": {"0": {"id": [NOT_A_COUNTED_DEBT]}}},
        ),
        ({"debts": [_debt_body(card)]}, {"debts": {"0": {"id": [NOT_A_COUNTED_DEBT]}}}),
        (
            {"debts": [{**_debt_body(filer.loan), "id": 999999}]},
            {"debts": {"0": {"id": [NOT_A_COUNTED_DEBT]}}},
        ),
        (
            {"vehicle_claims": {other_ref: "yes"}},
            {"vehicle_claims": {other_ref: [NOT_A_LINE_11_VEHICLE]}},
        ),
        (
            {"spouse_loans": [{"ref": "new-1", "on_amounts_owed": "yes", "debt": filer.loan.pk}]},
            {"spouse_loans": {"0": {"debt": [NOT_AN_OPEN_DEBT]}}},
        ),
        (
            {"spouse_loans": [{"ref": "new-1", "on_amounts_owed": "yes", "debt": other_card.pk}]},
            {"spouse_loans": {"0": {"debt": [NOT_AN_OPEN_DEBT]}}},
        ),
        (
            {
                "spouse_loans": [
                    {"ref": "new-1", "on_amounts_owed": "yes", "debt": card.pk},
                    {"ref": "new-2", "on_amounts_owed": "yes", "debt": card.pk},
                ]
            },
            {"spouse_loans": {"1": {"debt": [DEBT_NAMED_TWICE]}}},
        ),
        (
            {"spouse_loans": [{"ref": "new-1", "on_amounts_owed": "no", "secured_by": other_ref}]},
            {"spouse_loans": {"0": {"secured_by": [NOT_A_LINE_11_VEHICLE]}}},
        ),
        (
            {"vehicle_choice": [other_ref, f"asset-{filer.car.pk}"]},
            {"vehicle_choice": [NOT_A_LINE_11_VEHICLE]},
        ),
        (
            {
                "spouse_vehicles": [{"ref": "spouse-7", "description": "Demo truck"}],
                "spouse_loans": [
                    {"ref": "new-1", "on_amounts_owed": "no", "secured_by": "spouse-7"}
                ],
            },
            {"spouse_loans": {"0": {"secured_by": [NOT_A_LINE_11_VEHICLE]}}},
        ),
    ]
    before = _stored(filer.session)

    for body, errors in cases:
        reply = _put(filer, body)
        assert reply.status_code == 400, body
        assert reply.json() == errors
        assert _stored(filer.session) == before


@pytest.mark.django_db
def test_a_spouse_loan_with_no_debt_is_never_refused(filer):
    typed = {
        "ref": "new-1",
        "on_amounts_owed": "no",
        "debt": None,
        "creditor": "Demo Lender",
        "secured_by": "home",
    }

    assert _put(filer, {"spouse_loans": [typed]}).status_code == 200
    second = {**typed, "ref": "new-2", "creditor": "Another Demo Lender"}
    assert _put(filer, {"spouse_loans": [typed, second]}).status_code == 200


@pytest.mark.django_db
def test_new_spouse_rows_get_ids_and_the_loans_naming_them_follow(filer):
    _married(filer.session)
    first = _put(
        filer,
        {
            "spouse_vehicles_answer": "yes",
            "spouse_vehicles": [
                {"ref": "new-2", "description": "Demo van", "leased": "no"},
                {"ref": "new-1", "description": "Demo truck", "leased": "no", "claimed": "yes"},
            ],
            "spouse_loans_answer": "yes",
            "spouse_loans": [
                {"ref": "new-1", "on_amounts_owed": "no", "secured_by": "new-1", "creditor": "A"}
            ],
            "vehicle_choice": ["new-1", f"asset-{filer.car.pk}"],
        },
    )

    assert first.status_code == 200
    answers = first.json()["answers"]
    # the rows come back in the order sent, each with its id
    assert [row["description"] for row in answers["spouse_vehicles"]] == ["Demo van", "Demo truck"]
    assert [row["ref"] for row in answers["spouse_vehicles"]] == ["spouse-1", "spouse-2"]
    assert answers["spouse_loans"][0]["ref"] == "spouse-1"
    assert answers["spouse_loans"][0]["secured_by"] == "spouse-2"
    assert answers["vehicle_choice"] == ["spouse-2", f"asset-{filer.car.pk}"]

    kept = _put(
        filer,
        {"spouse_vehicles": [{"ref": "spouse-2", "description": "Demo truck", "leased": "no"}]},
    )
    assert kept.json()["answers"]["spouse_vehicles"][0]["ref"] == "spouse-2"

    later = _put(
        filer, {"spouse_vehicles": [{"ref": "new-1", "description": "Demo bus", "leased": "no"}]}
    )
    # an id is never reused
    assert later.json()["answers"]["spouse_vehicles"][0]["ref"] == "spouse-3"


@pytest.mark.django_db
def test_changing_a_debt_answer_stamps_the_day(filer):
    answer_means_test(filer.session)
    _set_answered_on(filer.session, STALE)

    _put(filer, {"debts": [_debt_body(filer.loan, payments_left=12)]})
    assert _answered_on(filer.session) == STAMP

    _set_answered_on(filer.session, STALE)
    answer_means_test(filer.session, spouse_loans_answer="yes", spouse_loans=[_stored_loan()])
    _set_answered_on(filer.session, STALE)
    record = MeansTestAnswers.objects.get(session=filer.session)
    record.next_spouse_loan_id = 2
    record.save()
    changed = _sent_loan(total_60_months="3700.00")
    assert _put(filer, {"spouse_loans": [changed]}).status_code == 200
    assert _answered_on(filer.session) == STAMP

    _set_answered_on(filer.session, STALE)
    # a new loan that sends no per-debt answer changes nothing
    bare = {"ref": "new-1", "on_amounts_owed": "no", "creditor": "Demo"}
    assert _put(filer, {"spouse_loans": [changed, bare]}).status_code == 200
    assert _answered_on(filer.session) == STALE

    # a new loan that sends one does
    answered = {**bare, "payments_left": 3}
    assert _put(filer, {"spouse_loans": [changed, answered]}).status_code == 200
    assert _answered_on(filer.session) == STAMP


@pytest.mark.django_db
def test_a_continue_that_changes_no_debt_answer_keeps_the_stale_notice(filer):
    answer_means_test(filer.session, spouse_loans_answer="yes", spouse_loans=[_stored_loan()])
    _set_answered_on(filer.session, STALE)
    same = _debt_body(filer.loan)

    assert _put(filer, {"debts": [same]}).status_code == 200
    assert _answered_on(filer.session) == STALE
    assert _put(filer, {"line_16": "5.00"}).status_code == 200
    assert _answered_on(filer.session) == STALE
    assert _put(filer, {"debts": [{"id": filer.loan.pk}]}).status_code == 200
    assert _answered_on(filer.session) == STALE
    # a spouse loan sent back as stored, and its amount typed without the cents
    assert _put(filer, {"spouse_loans": [_sent_loan()]}).status_code == 200
    assert _answered_on(filer.session) == STALE
    assert _put(filer, {"spouse_loans": [_sent_loan(total_60_months="3600")]}).status_code == 200
    assert _answered_on(filer.session) == STALE
    # a loan left out of the list changes nothing either
    assert _put(filer, {"spouse_loans": []}).status_code == 200
    assert _answered_on(filer.session) == STALE


@pytest.mark.django_db
def test_the_result_turns_once_the_last_input_under_39d_is_answered(filer):
    answer_means_test(filer.session, line_16=None)

    assert _get(filer).json()["outcome"] == "cannot_work_out"

    reply = _put(filer, {"line_16": "0.00"}).json()

    assert reply["outcome"] in ("no_presumption", "presumption")
    packet = filer.client.get(f"/api/forms/packet/?session={filer.session.pk}").json()
    assert packet["outcome"] == reply["outcome"]


@pytest.mark.django_db
def test_changing_the_spouse_vehicles_answer_to_no_saves_with_a_loan_still_naming_the_row(filer):
    _married(filer.session)
    stored = _stored_loan(on_amounts_owed="no", secured_by="spouse-1")
    answer_means_test(
        filer.session,
        spouse_vehicles_answer="yes",
        spouse_vehicles=[
            {"ref": "spouse-1", "description": "Demo truck", "leased": "no", "claimed": "yes"}
        ],
        spouse_loans_answer="yes",
        spouse_loans=[stored],
    )

    reply = _put(
        filer, {"spouse_vehicles_answer": "no", "spouse_loans": [_sent_loan(secured_by="spouse-1")]}
    )

    assert reply.status_code == 200
    assert _get(filer).json()["answers"]["spouse_loans"][0]["secured_by"] is None


@pytest.mark.django_db
def test_a_spouse_loan_row_replaces_the_stored_row_whole(filer):
    card = complete_debt(filer.session)
    answer_means_test(
        filer.session,
        spouse_loans_answer="yes",
        spouse_loans=[_stored_loan(on_amounts_owed="yes", debt=card.pk, secured_by="home")],
    )

    reply = _put(
        filer,
        {"spouse_loans": [{"ref": "spouse-1", "secured_by": f"asset-{filer.car.pk}"}]},
    )

    assert reply.status_code == 200
    loans = MeansTestAnswers.objects.get(session=filer.session).get_answers()["spouse_loans"]
    # nothing of the stored Yes survives, so no merged check of it is needed
    assert loans == [{"ref": "spouse-1", "secured_by": f"asset-{filer.car.pk}"}]


@pytest.mark.django_db
def test_answers_stay_stored_when_the_form_stops_applying(filer):
    answer_means_test(filer.session, line_16="123.00")
    before = _stored(filer.session)
    income = filer.session.income_info
    income.monthly_gross_wages = Decimal("1000.00")
    income.save()

    page = _get(filer).json()

    assert page["applies"] is False
    assert page["debt_lines"] is None
    assert page["answers"]["line_16"] == "123.00"
    assert _stored(filer.session) == before


@pytest.mark.django_db
def test_a_save_after_the_intake_changed_sends_back_what_the_get_gave_and_succeeds(filer):
    _married(filer.session)
    card = complete_debt(filer.session, creditor_name="Demo Card")
    car_ref = f"asset-{filer.car.pk}"
    answer_means_test(
        filer.session,
        vehicle_claims={car_ref: "yes"},
        vehicle_choice=[car_ref, "spouse-1"],
        spouse_vehicles_answer="yes",
        spouse_vehicles=[
            {"ref": "spouse-1", "description": "Demo truck", "leased": "no", "claimed": "yes"}
        ],
        spouse_loans_answer="yes",
        spouse_loans=[
            _stored_loan(on_amounts_owed="yes", debt=card.pk, secured_by="home", creditor=None)
        ],
        debts={
            filer.loan.pk: {"payments_left": "10", "total_60_months": "4500.00", "cure": "0.00"}
        },
    )
    # the filer then deletes the car and lists the card as secured
    filer.car.delete()
    card.is_secured = True
    card.save()

    page = _get(filer).json()
    assert page["answers"]["vehicle_claims"] == {}
    assert page["answers"]["vehicle_choice"] == [None, "spouse-1"]
    assert page["answers"]["spouse_loans"][0]["debt"] is None

    reply = _put(filer, _put_body(page))

    assert reply.status_code == 200, reply.content
