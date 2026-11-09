"""The household list and the spouse's income decide the means test (3e1 spec §4.4, §5.3, §9).

Business intent: 11 U.S.C. § 707(b) compares the household's income with the median for the
household's size. A filer living with their spouse counts the spouse's income too (122A-1
column B), and line 13 counts everyone living with the filer, so a roommate can move the
median. 122A-2 line 5 counts everyone the filer claims or supports, which sizes the expense
allowances. Until the Income step is answered there is no household to size, so the means test
refuses with the step's first gap rather than giving anyone a household of one.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.eligibility.cmi import IncomeStepGap
from apps.eligibility.models import MeansTest
from apps.eligibility.services.expense_deduction_calculator import ExpenseDeductionCalculator
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.models import GeneratedForm
from apps.intake.models import (
    DebtorInfo,
    ExpenseInfo,
    Household,
    IncomeInfo,
    IntakeSession,
    SpouseIncome,
)
from apps.intake.tests.builders import (
    answer_asset_lines,
    answer_claims,
    answer_household,
    answer_income_detail,
)
from apps.users.models import User

MARRIAGE = "Answer the question about marriage on the Income step."
HOUSEHOLD_LIST = (
    "List the people in your home and the people you support on the Income step, "
    "or tell us no one does."
)

# Household rows as stored. Y, Y: lives with the filer, and claimed or supported.
SPOUSE_45 = {
    "relationship": "spouse",
    "age": 45,
    "lives_with_you": True,
    "claimed_or_supported": True,
    "spouse_is_dependent": False,
}
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
SON_7 = {"relationship": "son", "age": 7, "lives_with_you": True, "claimed_or_supported": True}
SON_8 = {"relationship": "son", "age": 8, "lives_with_you": True, "claimed_or_supported": True}
DAUGHTER_5 = {
    "relationship": "daughter",
    "age": 5,
    "lives_with_you": True,
    "claimed_or_supported": True,
}
ROOMMATE_29 = {
    "relationship": "roommate",
    "age": 29,
    "lives_with_you": True,
    "claimed_or_supported": False,
}
SON_19_ELSEWHERE_SUPPORTED = {
    "relationship": "son",
    "age": 19,
    "lives_with_you": False,
    "claimed_or_supported": True,
}

# (marriage answer, household list, the filer's wages, the spouse's wages or None)
PRIYA = ("married_together", [SPOUSE_45, DAUGHTER_10, SON_7], "12000.00", "1800.00")
DESHAWN = ("married_together", [SPOUSE_44], "3500.00", "1000.00")
SARAH = ("not_married", [ROOMMATE_29], "2000.00", None)  # roommate: lives with her, not claimed
MARIA = ("not_married", [SON_8, DAUGHTER_5], "3200.00", None)


@pytest.fixture
def filer(db):
    """(client, session): a filer signed in, with a new intake in ILND.

    The real ILND data, as test_form_views.py loads it. On 2026-10-16 its medians for one to
    four people are 73,180, 93,934, 113,625 and 137,902.
    """
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    district = District.objects.get(code="ilnd")
    user = User.objects.create_user(username="household", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, IntakeSession.objects.create(user=user, district=district)


def _url(session):
    return f"/api/intake/sessions/{session.pk}/"


def _ten(wages):
    """All ten Income step amounts typed: the wages, and $0 for the other nine."""
    return {
        **dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00")),
        "monthly_gross_wages": Decimal(wages),
    }


def _answer(session, marital_status, members, wages, spouse_wages=None, detail=None):
    IncomeInfo.objects.create(session=session, **_ten(wages))
    answer_household(
        session,
        marital_status=marital_status,
        members=members,
        spouse_income=None if spouse_wages is None else _ten(spouse_wages),
        **(detail or {}),
    )


def _debtor(session, **fields):
    return DebtorInfo.objects.create(
        session=session,
        **{
            "first_name": "Test",
            "last_name": "User",
            "ssn": "900112222",
            "date_of_birth": date(1990, 1, 1),
            "phone": "312-555-0100",
            "email": "test@example.com",
            "street_address": "1 Main St",
            "city": "Chicago",
            "state": "IL",
            "zip_code": "60601",
            **fields,
        },
    )


# ── The means test reads the household ──────────────────────────────────


def test_a_filer_living_with_their_spouse_is_compared_to_the_median_on_both_incomes(filer):
    client, session = filer
    _answer(session, *PRIYA)
    result = MeansTestCalculator(session).calculate()
    assert result["cmi"] == Decimal("13800.00")
    assert result["details"]["annualized_cmi"] == 165600.0
    assert result["median_income_threshold"] == Decimal("137902.00")
    assert (result["passes_means_test"], result["above_median_calculated"]) == (False, True)


def test_sarahs_roommate_counts_in_her_household_and_her_median_follows(filer):
    client, session = filer
    _answer(session, *SARAH)
    result = MeansTestCalculator(session).calculate()
    assert (result["family_size"], result["median_income_threshold"]) == (2, Decimal("93934.00"))


def test_deshawns_means_test_counts_his_and_his_wifes_income(filer):
    client, session = filer
    _answer(session, *DESHAWN)
    result = MeansTestCalculator(session).calculate()
    assert (result["cmi"], result["details"]["annualized_cmi"]) == (Decimal("4500.00"), 54000.0)
    assert "qualifies_for_fee_waiver" not in result


@pytest.mark.parametrize("answered,refusal", [(False, MARRIAGE), (True, HOUSEHOLD_LIST)])
def test_no_intake_completed_before_3e1_is_given_a_household_of_one(filer, answered, refusal):
    client, session = filer
    # income saved before 3e1, by hand: no Household; `answered` sets not_married, else null
    IncomeInfo.objects.create(
        session=session,
        marital_status="not_married" if answered else None,
        monthly_gross_wages=Decimal("3000.00"),
    )
    with pytest.raises(IncomeStepGap) as refused:
        MeansTestCalculator(session).calculate()
    assert str(refused.value) == refusal
    assert not MeansTest.objects.filter(session=session).exists()


def test_calculate_means_test_returns_the_first_income_step_gap(filer):
    client, session = filer
    # pre-3e1, by hand
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
    response = client.post(f"{_url(session)}calculate_means_test/")
    assert (response.status_code, response.data["error"]) == (400, MARRIAGE)


# ── Intakes completed before 3e1 refuse in plain words (spec §9.2) ──────


def _completed_before_3e1(session):
    """An intake completed before 3e1, by hand: no marriage answer and no Household."""
    session.status = "completed"
    session.save()
    _debtor(session, ssn="900-12-3456")
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
    ExpenseInfo.objects.create(session=session)
    answer_asset_lines(session)  # the Assets step is finished, so the Income step's gap speaks
    answer_claims(session, no_debts=True)  # so is the claims step


REFUSED = {"error": MARRIAGE, "step": "income_info"}
ENTRIES_UNANSWERED = (
    "Tell us about any business or rental property on the Income step, or say you have none."
)


def _422(response):
    # A wrongly drawn PDF is a plain HttpResponse, with no .data: show its status instead.
    assert response.status_code == 422, (response.status_code, getattr(response, "data", None))
    return response.data


def test_an_intake_completed_before_3e1_refuses_to_generate_and_names_the_income_step(filer):
    client, session = filer
    _completed_before_3e1(session)
    form = GeneratedForm.objects.create(
        session=session, form_type="form_106dec", status="generated", generated_by=session.user
    )
    # the whole call: no form_type in the body
    assert (
        _422(client.post("/api/forms/generate_all/", {"session_id": session.pk}, format="json"))
        == REFUSED
    )
    assert _422(client.get("/api/forms/packet/", {"session": session.pk})) == REFUSED
    # one form: the body names it
    one = {"form_type": "form_106dec", **REFUSED}
    assert (
        _422(
            client.post(
                "/api/forms/generate/",
                {"session_id": session.pk, "form_type": "form_106dec"},
                format="json",
            )
        )
        == one
    )
    assert _422(client.post(f"/api/forms/{form.pk}/regenerate/")) == one
    assert _422(client.get(f"/api/forms/{form.pk}/download/")) == one


def test_a_filed_form_with_no_stored_values_refuses_like_an_unfiled_one(filer):
    client, session = filer
    _completed_before_3e1(session)
    # Review Focus 4: filed before 3e1 with field_values "" draws from the current intake,
    # so step survives
    form = GeneratedForm.objects.create(
        session=session,
        form_type="form_106dec",
        status="filed",
        field_values="",
        generated_by=session.user,
    )
    assert _422(client.get(f"/api/forms/{form.pk}/download/")) == {
        "form_type": "form_106dec",
        **REFUSED,
    }


def _completed_before_3e2(session):
    """By hand: 3e1's answers, none of 3e2's (no list, no "now different", no assistance)."""
    session.status = "completed"
    session.save()
    _debtor(session, ssn="900-12-3456")
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
    ExpenseInfo.objects.create(session=session, expenses_include_others=None)
    answer_household(
        session,
        income_now_different=None,
        business_and_rental=None,
        assistance_answer=None,
        payroll_tax=None,
    )


def test_an_intake_completed_before_3e2_refuses_every_forms_call_with_the_income_step(filer):
    client, session = filer
    _completed_before_3e2(session)
    form = GeneratedForm.objects.create(
        session=session, form_type="form_106dec", status="generated", generated_by=session.user
    )
    refused = {"error": ENTRIES_UNANSWERED, "step": "income_info"}  # the list comes first (§8.1)
    one = {"form_type": "form_106dec", **refused}
    assert (
        _422(client.post("/api/forms/generate_all/", {"session_id": session.pk}, format="json"))
        == refused
    )
    assert _422(client.get("/api/forms/packet/", {"session": session.pk})) == refused
    assert (
        _422(
            client.post(
                "/api/forms/generate/",
                {"session_id": session.pk, "form_type": "form_106dec"},
                format="json",
            )
        )
        == one
    )
    assert _422(client.post(f"/api/forms/{form.pk}/regenerate/")) == one
    assert _422(client.get(f"/api/forms/{form.pk}/download/")) == one


# ── The session read returns the two counts (spec §4.4) ─────────────────


@pytest.mark.parametrize(
    "household,counts",
    [(MARIA, (3, 3)), (DESHAWN, (2, 2)), (SARAH, (2, 1))],
    ids=["maria", "deshawn", "sarah"],
)
def test_the_session_read_returns_the_households_counts(filer, household, counts):
    client, session = filer
    _answer(session, *household)
    got = client.get(_url(session)).data["household"]
    assert (got["family_size"], got["fee_waiver_household_size"]) == counts


def test_the_counts_are_null_while_a_gap_remains_and_a_bare_session_reads_without_error(filer):
    client, session = filer
    url = _url(session)
    assert client.get(url).data["household"] is None
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("2000.00")
    )
    Household.objects.create(session=session, county="Cook")  # step 1 saved, list never answered
    got = client.get(url).data["household"]
    assert (got["family_size"], got["fee_waiver_household_size"]) == (None, None)


@pytest.mark.parametrize(
    "household",
    [
        (None, [], "2000.00", None),  # the list says no one, the marriage question unanswered
        ("married_together", [SPOUSE_44], "3500.00", None),  # no spouse's income entered
        ("not_married", [], "2000.00", None, {"income_now_different": None}),
    ],
    ids=["marriage_unanswered", "spouse_income_not_entered", "now_different_unanswered"],
)
def test_the_counts_are_null_while_another_income_step_gap_remains(filer, household):
    # The list is answered, so both counts could be worked out; the means test would still
    # refuse, so neither is shown (spec §4.4).
    client, session = filer
    _answer(session, *household)
    got = client.get(_url(session)).data["household"]
    assert got["members"] is not None
    assert (got["family_size"], got["fee_waiver_household_size"]) == (None, None)


def test_a_patch_that_answers_the_income_step_returns_its_counts_in_the_reply(filer):
    client, session = filer
    url = _url(session)
    # Review Focus 1. Stored by hand before this PATCH, as autosave leaves them: the gaps'
    # old answers.
    Household.objects.create(session=session, county="Cook")
    answer_income_detail(
        IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3500.00"))
    )
    answer_income_detail(SpouseIncome.objects.create(session=session))
    reply = client.patch(
        url,
        {
            "income_info": {"marital_status": "married_together"},
            "household": {"members": [SPOUSE_44]},
            "spouse_income": {"monthly_gross_wages": "1000.00"},
        },
        format="json",
    )
    assert reply.status_code == 200
    assert (
        reply.data["household"]["family_size"],
        reply.data["household"]["fee_waiver_household_size"],
    ) == (2, 2)


# ── The expense allowances (122A-2 line 5) and the stored details ───────
#
# The line 5 cases also store DebtorInfo.household_size=3 and $1,200 of food. Food is the
# lesser of 1,200 and the IRS food figure for the size: 713, 904, 1,088 and 1,289 for 1 to 4
# people, so a size read from line 13 or from the debtor box gives a different food figure.


@pytest.mark.parametrize(
    "household,size,food",
    [
        (PRIYA, 4, "1200"),
        (SARAH, 1, "713"),  # line 13 is 2
        (("not_married", [SON_19_ELSEWHERE_SUPPORTED], "2000.00", None), 2, "904"),  # line 13 is 1
    ],
    ids=["priya", "a_roommate_lives_there_but_isnt_claimed", "a_child_supported_elsewhere"],
)
def test_the_expense_allowances_use_line_5s_count(filer, household, size, food):
    client, session = filer
    _answer(session, *household)
    _debtor(session, household_size=3)  # the old box, which no count reads
    ExpenseInfo.objects.create(session=session, food_and_groceries=Decimal("1200"))
    result = ExpenseDeductionCalculator(session).calculate()
    assert (result.family_size, result.national_food_allowance) == (size, Decimal(food))


def test_the_expense_calculator_counts_the_spouses_income(filer):
    # Disposable income is the CMI less the allowances and priority debts. The allowances read
    # the household's size, the debtor's age and the district, never the CMI, and there are
    # no priority debts here: so only the CMI can move it, by exactly the spouse's 1,800.00.
    client, session = filer
    _answer(session, *PRIYA)  # spouse wages 1800.00, the other nine typed $0
    ExpenseInfo.objects.create(session=session, food_and_groceries=Decimal("1200"))
    with_spouse = ExpenseDeductionCalculator(session).calculate()
    # The same household, the spouse's ten all typed $0 (all None would be the spouse-income gap).
    answer_household(
        session,
        marital_status=PRIYA[0],
        members=PRIYA[1],
        spouse_income=dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00")),
    )
    without = ExpenseDeductionCalculator(session).calculate()
    assert (with_spouse.family_size, with_spouse.allowable_expenses) == (
        without.family_size,
        without.allowable_expenses,
    )
    assert with_spouse.disposable_income - without.disposable_income == Decimal("1800.00")


@pytest.mark.parametrize(
    "household,family_size,spouse_cmi",
    [(PRIYA, 4, 1800.0), (SARAH, 2, None)],
    ids=["priya", "sarah"],
)
def test_the_means_test_stores_the_marriage_answer_line_13_and_column_b(
    filer, household, family_size, spouse_cmi
):
    client, session = filer
    _answer(session, *household)
    details = MeansTestCalculator(session).calculate()["details"]
    assert (details["marital_status"], details["family_size"], details["spouse_cmi"]) == (
        household[0],
        family_size,
        spouse_cmi,
    )
    assert "number_of_dependents" not in details
