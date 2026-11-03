"""Only the server marks an intake complete, and an edit after that reopens it (spec §5.3).

Business intent: forms are prepared only from an intake the filer completed, because only
then does an empty list mean "the filer said none". The browser can't claim that state
(DIG-151). Changing intake data after Complete sets the intake back to in progress, so the
filer presses Complete again, which re-runs its checks. Form answers, SOFA and the filing
fee are not intake data and never reopen it.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.eligibility.cmi import LEGACY_RENTAL as LEGACY
from apps.eligibility.cmi import SPOUSE_LEGACY_RENTAL as SPOUSE_LEGACY
from apps.eligibility.cmi import income_step_gaps
from apps.eligibility.services import MeansTestCalculator
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
    SpouseIncome,
)
from apps.intake.tests.builders import answer_household, answer_income_detail
from apps.users.models import User

FINISH = "Finish your intake before preparing your forms."


@pytest.fixture
def district(db):
    # The real ILND data: its name is one of the court forms' district choices, and preparing
    # forms works the means test out against its median income.
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


@pytest.fixture
def filer(district):
    user = User.objects.create_user(username="filer", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def completed(filer, district):
    """An intake the filer completed, with the three sections Complete requires."""
    _, user = filer
    session = IntakeSession.objects.create(
        user=user, district=district, status="completed", current_step=9
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(
        session=session,
        marital_status="not_married",
        monthly_gross_wages=Decimal("3000.00"),
    )
    answer_household(session)
    ExpenseInfo.objects.create(session=session, expenses_include_others="no")
    return session


def _session_url(session, action=""):
    return f"/api/intake/sessions/{session.pk}/{action}"


def _status(session):
    return IntakeSession.objects.get(pk=session.pk).status


def _complete_again(session):
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")


# ── Who marks an intake complete ──────────────────────────────────────


def test_browser_cannot_mark_intake_complete(filer, district):
    client, _ = filer
    claimed = {"status": "completed", "current_step": 9}

    created = client.post(
        "/api/intake/sessions/", {"district": district.id, **claimed}, format="json"
    )
    assert created.status_code == 201
    session = IntakeSession.objects.get(pk=created.data["session"]["id"])
    assert (session.status, session.current_step) == ("started", 1)

    patched = client.patch(_session_url(session), claimed, format="json")
    assert patched.status_code == 200
    session.refresh_from_db()
    assert (session.status, session.current_step) == ("started", 1)

    # update_step's nested data can't carry them either.
    stepped = client.post(
        _session_url(session, "update_step/"),
        {"current_step": 3, "data": claimed},
        format="json",
    )
    assert stepped.status_code == 200
    session.refresh_from_db()
    assert (session.status, session.current_step) == ("in_progress", 3)


_MISSING = object()


@pytest.mark.parametrize(
    "step",
    [0, 10, -1, "3", 3.0, 2.5, True, None, _MISSING],
    ids=["0", "10", "-1", "string", "float", "fraction", "bool", "null", "missing"],
)
def test_wizard_step_must_be_one_of_the_wizard_steps(filer, completed, step):
    # A step the wizard doesn't have is a client fault, not something the filer can fix.
    client, _ = filer
    body = {} if step is _MISSING else {"current_step": step}

    response = client.post(_session_url(completed, "update_step/"), body, format="json")

    assert response.status_code == 400
    assert "current_step" in response.data
    completed.refresh_from_db()
    assert (completed.status, completed.current_step) == ("completed", 9)


def test_filer_who_leaves_every_expense_blank_can_complete(filer, district):
    # DIG-153: a body with no amounts still creates the record with its $0 defaults. The server
    # drops the read-only total sent here. The wizard sends all 13 amounts, a blank box as 0.
    # Line 3 is answered, which Complete asks for (3e2).
    # Line 3 is answered, which Complete asks for (3e2).
    client, user = filer
    session = IntakeSession.objects.create(user=user, district=district, current_step=4)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",
        date_of_birth=date(1990, 1, 15),
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("0.00"))
    answer_household(session)

    saved = client.patch(
        _session_url(session),
        {"expense_info": {"total_monthly_expenses": 0, "expenses_include_others": "no"}},
        format="json",
    )

    assert saved.status_code == 200
    expenses = ExpenseInfo.objects.get(session=session)
    assert expenses.calculate_total_monthly_expenses() == 0
    assert client.post(_session_url(session, "complete/")).status_code == 200
    assert _status(session) == "completed"


# ── Complete names the step that fixes each gap (forms step 3a1 spec §4.2) ──

NOT_FINISHED = "Please complete all required sections before finalizing"
NAME_AND_ADDRESS = "Enter your name and address on the Your Information step."
NINE_DIGIT_SSN = "Enter your 9-digit Social Security number on the Your Information step."
INCOME_BY_SOURCE = "Enter your income by source on the Income step."
ENTRIES_UNANSWERED = (
    "Tell us about any business or rental property on the Income step, or say you have none."
)
ENTRY_UNANSWERED = "Answer every question for each business or rental property on the Income step."
NOW_DIFFERENT_UNANSWERED = (
    "Answer whether your income is now different from the six-month average, on the Income step."
)
CURRENT_NOT_GIVEN = (
    "Enter your income now on the Income step, or change your answer about whether it is different."
)
ASSISTANCE_UNANSWERED = (
    "Answer whether you receive other government assistance, on the Income step."
)
ASSISTANCE_KIND_MISSING = "Say what government assistance you receive on the Income step."
CASH_AMOUNT_MISSING = "Enter how much cash assistance you receive a month, on the Income step."
SPOUSE_ENTRIES_UNANSWERED = (
    "Tell us about any business or rental property your spouse has on the Income step, "
    "or say your spouse has none."
)
SPOUSE_ENTRY_UNANSWERED = (
    "Answer every question for each of your spouse's businesses or rental properties "
    "on the Income step."
)
SPOUSE_NOW_DIFFERENT_UNANSWERED = (
    "Answer whether your spouse's income is now different from the six-month average, "
    "on the Income step."
)
SPOUSE_CURRENT_NOT_GIVEN = (
    "Enter your spouse's income now on the Income step, "
    "or change your spouse's answer about whether it is different."
)
SPOUSE_ASSISTANCE_UNANSWERED = (
    "Answer whether your spouse receives other government assistance, on the Income step."
)
SPOUSE_ASSISTANCE_KIND_MISSING = (
    "Say what government assistance your spouse receives on the Income step."
)
SPOUSE_CASH_AMOUNT_MISSING = (
    "Enter how much cash assistance your spouse receives a month, on the Income step."
)
TAKE_HOME_PAY_NOT_ENTERED = (
    "Enter what is taken out of your pay on the Take-home pay step. "
    "If nothing is, enter $0 in one box."
)
SPOUSE_TAKE_HOME_PAY_NOT_ENTERED = (
    "Enter what is taken out of your spouse's pay on the Take-home pay step. "
    "If nothing is, enter $0 in one box."
)
EXPENSES_INCLUDE_OTHERS_UNANSWERED = (
    "Answer whether your expenses include anyone else's, on the Expenses step."
)
EXPENSES_STEP = "Go through the Expenses step, even if you have no expenses to enter."
SCANNED_DEBTS = "Check the debts read from your documents on the Amounts Owed step."


def _no_debtor(session):
    session.debtor_info.delete()


def _eight_digit_ssn(session):
    session.debtor_info.ssn = "90012345"
    session.debtor_info.save()


def _income_boxes_all_empty(session):
    session.income_info.monthly_gross_wages = None
    session.income_info.save()


def _expenses_step_never_saved(session):
    session.expense_info.delete()


def _scanned_debt(session):
    # What an upload creates: a draft the filer hasn't checked on the Amounts Owed step yet.
    return DebtInfo.objects.create(
        session=session,
        creditor_name="Larkfield General Hospital",
        debt_type="medical",
        amount_owed=Decimal("2000.00"),
        data_source="uploaded_document",
        is_draft=True,
    )


# ── Complete names each county, household and spouse gap (3e1 spec §9.1) ──

COUNTY = "Choose your county on the Your Information step."
MARRIAGE = "Answer the question about marriage on the Income step."
SPOUSE_FILING = (
    "DigniFi prepares forms for one person filing alone. "
    "Check your answer about marriage on the Income step."
)
HOUSEHOLD_LIST = (
    "List the people in your home and the people you support on the Income step, "
    "or tell us no one does."
)
HOUSEHOLD_ROW = "Answer every question for each person on your household list on the Income step."
MISMATCH = (
    "Your household list and your answer about marriage don't match. "
    "Check both on the Income step."
)
SPOUSE_INCOME = (
    "Enter your spouse's income by source on the Income step. "
    "If your spouse has no income, enter $0 in one box."
)

# Household rows as stored. Y, Y: lives with the filer, and claimed or supported.
SPOUSE_44 = {
    "relationship": "spouse",
    "age": 44,
    "lives_with_you": True,
    "claimed_or_supported": True,
    "spouse_is_dependent": False,
}
SON_8 = {"relationship": "son", "age": 8, "lives_with_you": True, "claimed_or_supported": True}


def _marry(session, answer):
    session.income_info.marital_status = answer
    session.income_info.save()


def _household_list(session, rows):
    session.household.store_members([dict(r) for r in rows])
    session.household.save()


def _spouse_typed(session):
    row = SpouseIncome(session=session, monthly_gross_wages=Decimal("0.00"))
    answer_income_detail(row)


def _no_county(session):
    # household.county = None
    session.household.county = None
    session.household.save()


def _marriage_unanswered(session):
    _marry(session, None)


def _spouse_filing_with_you(session):
    # married_spouse_filing
    _marry(session, "married_spouse_filing")


def _household_list_unanswered(session):
    # members None
    session.household.store_members(None)
    session.household.save()


def _a_row_half_answered(session):
    # son 8, lives_with_you None
    _household_list(session, [{**SON_8, "lives_with_you": None}])


def _a_spouse_row_but_not_married(session):
    # [SPOUSE_44] under not_married
    _household_list(session, [SPOUSE_44])


def _living_together_with_twenty_others_and_no_spouse(session):
    # Review Focus 3: 20 answered non-spouse rows, spouse typed $0
    _marry(session, "married_together")
    _household_list(session, [SON_8] * 20)
    _spouse_typed(session)


def _spouse_income_not_entered(session):
    # married_together, [SPOUSE_44], SpouseIncome with no amounts
    _marry(session, "married_together")
    _household_list(session, [SPOUSE_44])
    answer_income_detail(SpouseIncome(session=session))  # the 3e2 answers given: one gap open


def _legacy_rental(session):
    # Wages stay $3,000, so only the legacy gap and the unanswered list are open
    session.income_info.monthly_rental_income = Decimal("900.00")
    session.income_info.store_entries(None)
    session.income_info.save()


def _spouse_legacy_rental(session):
    _marry(session, "married_together")
    _household_list(session, [SPOUSE_44])
    row = SpouseIncome(session=session, monthly_rental_income=Decimal("700.00"))
    answer_income_detail(row, business_and_rental=None)


@pytest.mark.parametrize(
    "gap,step,message",
    [
        (_no_debtor, "debtor_info", NAME_AND_ADDRESS),
        (_eight_digit_ssn, "debtor_info", NINE_DIGIT_SSN),
        (_income_boxes_all_empty, "income_info", INCOME_BY_SOURCE),
        (_expenses_step_never_saved, "expense_info", EXPENSES_STEP),
        (_scanned_debt, "debts", SCANNED_DEBTS),
        (_no_county, "debtor_info", COUNTY),
        (_marriage_unanswered, "income_info", MARRIAGE),
        (_spouse_filing_with_you, "income_info", SPOUSE_FILING),
        (_household_list_unanswered, "income_info", HOUSEHOLD_LIST),
        (_a_row_half_answered, "income_info", HOUSEHOLD_ROW),
        (_a_spouse_row_but_not_married, "income_info", MISMATCH),
        (_living_together_with_twenty_others_and_no_spouse, "income_info", MISMATCH),
        (_spouse_income_not_entered, "income_info", SPOUSE_INCOME),
        (_legacy_rental, "income_info", [LEGACY, ENTRIES_UNANSWERED]),
        (_spouse_legacy_rental, "income_info", [SPOUSE_LEGACY, SPOUSE_ENTRIES_UNANSWERED]),
    ],
    ids=[
        "no_name_and_address",
        "eight_digit_ssn",
        "no_income_by_source",
        "no_expenses_step",
        "unconfirmed_scanned_debt",
        "no_county",
        "marriage_unanswered",
        "spouse_filing_with_you",
        "household_list_unanswered",
        "a_row_half_answered",
        "a_spouse_row_but_not_married",
        "living_together_with_twenty_others_and_no_spouse",
        "spouse_income_not_entered",
        "legacy_rental",
        "spouse_legacy_rental",
    ],
)
def test_complete_names_every_new_gap_by_its_step(filer, completed, gap, step, message):
    # The filer reads why on Review, with a way to the step that fixes it (DIG-181).
    client, _ = filer
    completed.status = "in_progress"
    completed.save()
    gap(completed)

    response = client.post(_session_url(completed, "complete/"))

    messages = message if isinstance(message, list) else [message]
    assert response.status_code == 400
    assert response.data == {
        "message": NOT_FINISHED,
        "errors": [{"step": step, "message": m} for m in messages],
    }
    assert _status(completed) == "in_progress"


def test_a_rental_figure_saved_as_one_amount_names_the_legacy_gap_not_income_not_entered(
    filer, completed
):
    # Its only income was the legacy figure, so "income not entered" stays unnamed (§4.7). The
    # list is unanswered too, and that is its own gap (3e2 spec §8).
    IncomeInfo.objects.filter(session=completed).update(monthly_gross_wages=None)
    completed.income_info.refresh_from_db()
    _legacy_rental(completed)
    messages = [str(g) for g in income_step_gaps(completed)]
    assert messages[0] == LEGACY
    assert INCOME_BY_SOURCE not in messages


def test_a_rental_figure_saved_as_one_amount_refuses_the_means_test_and_the_forms(filer, completed):
    client, _ = filer
    _legacy_rental(completed)  # status stays "completed"
    means = client.post(_session_url(completed, "calculate_means_test/"))
    assert (means.status_code, means.data["error"]) == (400, LEGACY)
    forms = client.get("/api/forms/packet/", {"session": completed.pk})
    assert (forms.status_code, forms.data["error"], forms.data["step"]) == (
        422,
        LEGACY,
        "income_info",
    )
    client.patch(
        _session_url(completed), {"income_info": {"business_and_rental": []}}, format="json"
    )
    assert LEGACY not in [
        str(g) for g in income_step_gaps(IntakeSession.objects.get(pk=completed.pk))
    ]


def test_complete_lists_every_gap_in_wizard_order(filer, district):
    client, user = filer
    session = IntakeSession.objects.create(user=user, district=district, current_step=9)
    _scanned_debt(session)

    response = client.post(_session_url(session, "complete/"))

    assert response.status_code == 400
    assert response.data["errors"] == [
        {"step": "debtor_info", "message": NAME_AND_ADDRESS},
        {"step": "debtor_info", "message": COUNTY},
        {"step": "income_info", "message": MARRIAGE},
        {"step": "income_info", "message": HOUSEHOLD_LIST},
        {"step": "income_info", "message": INCOME_BY_SOURCE},
        {"step": "income_info", "message": ENTRIES_UNANSWERED},
        {"step": "income_info", "message": NOW_DIFFERENT_UNANSWERED},
        {"step": "income_info", "message": ASSISTANCE_UNANSWERED},
        {"step": "expense_info", "message": EXPENSES_STEP},
        {"step": "debts", "message": SCANNED_DEBTS},
    ]
    assert _status(session) == "started"


# ── Complete names each 3e2 income, take-home pay and line 3 gap (3e2 spec §8) ──


def _entry(**changes):
    return {
        "kind": "business",
        "description": "Rideshare and delivery driving",
        "gross": "1000.00",
        "expenses": "200.00",
        "current_gross": None,
        "current_expenses": None,
        **changes,
    }


def _set(row, **fields):
    for name, value in fields.items():
        setattr(row, name, value)
    row.save()


def _store(row, entries):
    row.store_entries(entries)
    row.save()


def _list_unanswered(row):
    _store(row, None)


def _entry_without_gross(row):
    _store(row, [_entry(gross=None)])


def _description_of_only_spaces(row):
    _store(row, [_entry(description="   ")])


def _entry_without_current_amounts_while_now_different(row):
    _store(row, [_entry()])
    _set(row, income_now_different="yes", current_monthly_gross_wages=Decimal("3000.00"))


def _now_different_unanswered(row):
    _set(row, income_now_different=None)


def _now_different_with_no_current_figure(row):
    _set(row, income_now_different="yes")


def _assistance_unanswered(row):
    _set(row, assistance_answer=None)


def _assistance_with_no_kind(row):
    _set(row, assistance_answer="yes", cash_assistance_kind="", noncash_assistance_kind="")


def _an_amount_beside_an_empty_kind(row):
    _set(
        row,
        assistance_answer="yes",
        cash_assistance_kind="TANF",
        cash_assistance_amount=Decimal("100.00"),
        noncash_assistance_kind="",
        noncash_assistance_value=Decimal("350.00"),
    )


def _cash_kind_with_no_amount(row):
    _set(row, assistance_answer="yes", cash_assistance_kind="TANF", cash_assistance_amount=None)


def _pay_with_every_deduction_blank(row):
    _set(row, payroll_tax=None)


NEW_INCOME_GAPS = [
    (_list_unanswered, "ENTRIES_UNANSWERED"),
    (_entry_without_gross, "ENTRY_UNANSWERED"),
    (_description_of_only_spaces, "ENTRY_UNANSWERED"),
    (_entry_without_current_amounts_while_now_different, "ENTRY_UNANSWERED"),
    (_now_different_unanswered, "NOW_DIFFERENT_UNANSWERED"),
    (_now_different_with_no_current_figure, "CURRENT_NOT_GIVEN"),
    (_assistance_unanswered, "ASSISTANCE_UNANSWERED"),
    (_assistance_with_no_kind, "ASSISTANCE_KIND_MISSING"),
    (_an_amount_beside_an_empty_kind, "ASSISTANCE_KIND_MISSING"),
    (_cash_kind_with_no_amount, "CASH_AMOUNT_MISSING"),
]
NEW_INCOME_GAP_IDS = [
    "list_unanswered",
    "entry_without_gross",
    "description_of_only_spaces",
    "entry_without_current_amounts_while_now_different",
    "now_different_unanswered",
    "now_different_with_no_current_figure",
    "assistance_unanswered",
    "assistance_with_no_kind",
    "an_amount_beside_an_empty_kind",
    "cash_kind_with_no_amount",
]


def _complete_refused(client, session):
    session.status = "in_progress"
    session.save()
    response = client.post(_session_url(session, "complete/"))
    assert response.status_code == 400
    assert response.data["message"] == NOT_FINISHED
    return response.data["errors"]


@pytest.mark.parametrize("gap,name", NEW_INCOME_GAPS, ids=NEW_INCOME_GAP_IDS)
def test_complete_names_each_new_income_gap_by_its_step(filer, completed, gap, name):
    client, _ = filer
    gap(completed.income_info)

    assert _complete_refused(client, completed) == [
        {"step": "income_info", "message": globals()[name]}
    ]


@pytest.mark.parametrize("gap,name", NEW_INCOME_GAPS, ids=NEW_INCOME_GAP_IDS)
def test_complete_names_each_spouse_gap_in_the_spouses_words(filer, completed, gap, name):
    client, _ = filer
    _marry(completed, "married_together")
    _household_list(completed, [SPOUSE_44])
    spouse = SpouseIncome(session=completed, monthly_gross_wages=Decimal("1000.00"))
    answer_income_detail(spouse)
    gap(spouse)

    assert _complete_refused(client, completed) == [
        {"step": "income_info", "message": globals()["SPOUSE_" + name]}
    ]


def test_complete_names_pay_with_every_deduction_blank_by_the_take_home_pay_step(filer, completed):
    client, _ = filer
    _pay_with_every_deduction_blank(completed.income_info)

    assert _complete_refused(client, completed) == [
        {"step": "take_home_pay", "message": TAKE_HOME_PAY_NOT_ENTERED}
    ]


def test_complete_names_the_spouses_pay_with_every_deduction_blank(filer, completed):
    client, _ = filer
    _marry(completed, "married_together")
    _household_list(completed, [SPOUSE_44])
    spouse = SpouseIncome(session=completed, monthly_gross_wages=Decimal("1000.00"))
    answer_income_detail(spouse, payroll_tax=None)

    assert _complete_refused(client, completed) == [
        {"step": "take_home_pay", "message": SPOUSE_TAKE_HOME_PAY_NOT_ENTERED}
    ]


def test_complete_names_schedule_j_line_3_unanswered_by_the_expenses_step(filer, completed):
    client, _ = filer
    _set(completed.expense_info, expenses_include_others=None)

    assert _complete_refused(client, completed) == [
        {"step": "expense_info", "message": EXPENSES_INCLUDE_OTHERS_UNANSWERED}
    ]


def test_complete_lists_every_new_gap_in_wizard_order(filer, completed):
    client, _ = filer
    _marry(completed, "married_together")
    _household_list(completed, [SPOUSE_44])
    _list_unanswered(completed.income_info)
    _now_different_unanswered(completed.income_info)
    _assistance_unanswered(completed.income_info)
    _pay_with_every_deduction_blank(completed.income_info)
    spouse = SpouseIncome(session=completed, monthly_gross_wages=Decimal("1000.00"))
    answer_income_detail(spouse, payroll_tax=None)
    _list_unanswered(spouse)
    _now_different_unanswered(spouse)
    _assistance_with_no_kind(spouse)
    _set(completed.expense_info, expenses_include_others=None)

    assert _complete_refused(client, completed) == [
        {"step": "income_info", "message": ENTRIES_UNANSWERED},
        {"step": "income_info", "message": NOW_DIFFERENT_UNANSWERED},
        {"step": "income_info", "message": ASSISTANCE_UNANSWERED},
        {"step": "income_info", "message": SPOUSE_ENTRIES_UNANSWERED},
        {"step": "income_info", "message": SPOUSE_NOW_DIFFERENT_UNANSWERED},
        {"step": "income_info", "message": SPOUSE_ASSISTANCE_KIND_MISSING},
        {"step": "take_home_pay", "message": TAKE_HOME_PAY_NOT_ENTERED},
        {"step": "take_home_pay", "message": SPOUSE_TAKE_HOME_PAY_NOT_ENTERED},
        {"step": "expense_info", "message": EXPENSES_INCLUDE_OTHERS_UNANSWERED},
    ]


def _unknown_noncash_value(session):
    _set(
        session.income_info,
        assistance_answer="yes",
        noncash_assistance_kind="SNAP (food stamps)",
        noncash_assistance_value=None,
    )


def _no_pay_and_no_deductions(session):
    _set(session.income_info, monthly_gross_wages=Decimal("0.00"), payroll_tax=None)


def _entry_current_amounts_blank_while_not_different(session):
    _store(session.income_info, [_entry()])


def _spouse_gaps_while_living_apart(session):
    _marry(session, "married_separately")
    SpouseIncome.objects.create(session=session)


@pytest.mark.parametrize(
    "answers",
    [
        _unknown_noncash_value,
        _no_pay_and_no_deductions,
        _entry_current_amounts_blank_while_not_different,
        _spouse_gaps_while_living_apart,
    ],
    ids=[
        "unknown_noncash_value",
        "no_pay_and_no_deductions",
        "entry_current_amounts_blank_while_not_different",
        "spouse_gaps_while_living_apart",
    ],
)
def test_these_are_not_gaps(filer, completed, answers):
    client, _ = filer
    answers(completed)
    completed.status = "in_progress"
    completed.save()

    response = client.post(_session_url(completed, "complete/"))

    assert response.status_code == 200
    assert _status(completed) == "completed"


def test_the_take_home_pay_gap_never_stops_the_means_test(filer, completed):
    # Take-home pay is Complete's alone: the preview and the forms don't read it.
    client, _ = filer
    _pay_with_every_deduction_blank(completed.income_info)

    assert income_step_gaps(completed) == []
    MeansTestCalculator(completed).calculate()
    response = client.post(_session_url(completed, "calculate_means_test/"))
    assert response.status_code == 200


def test_saving_the_amounts_owed_step_confirms_a_scanned_debt_so_complete_passes(filer, completed):
    # An upload after Complete reopens the intake (DIG-163). Until the filer saves the Amounts
    # Owed step, the scanned debt is on no form, so Complete sends them there first.
    client, _ = filer
    completed.status = "in_progress"
    completed.save()
    typed = DebtInfo.objects.create(
        session=completed,
        creditor_name="Brightwater Card Services",
        debt_type="credit_card",
        amount_owed=Decimal("1000.00"),
    )
    scanned = _scanned_debt(completed)

    refused = client.post(_session_url(completed, "complete/"))
    assert refused.status_code == 400
    assert refused.data["errors"] == [{"step": "debts", "message": SCANNED_DEBTS}]

    # Continue on Amounts Owed sends every row the step shows, each with its id.
    saved = client.patch(
        _session_url(completed),
        {
            "debts": [
                {
                    "id": row.pk,
                    "creditor_name": row.creditor_name,
                    "debt_type": row.debt_type,
                    "amount_owed": str(row.amount_owed),
                }
                for row in (typed, scanned)
            ]
        },
        format="json",
    )
    assert saved.status_code == 200

    scanned.refresh_from_db()  # the same row, now confirmed
    assert scanned.is_draft is False
    assert client.post(_session_url(completed, "complete/")).status_code == 200
    assert resolve(load_schema("schedule_e_f"), completed)["Total_6j"] == "3000.00"


# ── An edit after Complete reopens the intake ─────────────────────────


def test_editing_a_completed_intake_asks_for_complete_again(filer, completed):
    client, _ = filer
    generate = {"session_id": completed.pk, "form_type": "form_106dec"}

    edited = client.patch(
        _session_url(completed), {"debtor_info": {"first_name": "Janet"}}, format="json"
    )
    assert edited.status_code == 200
    assert edited.data["status"] == "in_progress"
    assert _status(completed) == "in_progress"

    refused = client.post("/api/forms/generate/", generate, format="json")
    assert refused.status_code == 422
    assert refused.data["error"] == FINISH

    assert client.post(_session_url(completed, "complete/")).status_code == 200
    assert client.post("/api/forms/generate/", generate, format="json").status_code == 200


@pytest.mark.parametrize(
    "section,value",
    [
        ("debtor_info", {"first_name": "Janet"}),
        ("income_info", {"monthly_gross_wages": "3100.00", "monthly_tips": None}),
        ("expense_info", {"rent_or_mortgage": 900}),
        ("debts", [{"creditor_name": "Chase", "debt_type": "credit_card", "amount_owed": 500}]),
        (
            "assets",
            [{"asset_type": "bank_account", "description": "Checking", "current_value": 800}],
        ),
        ("household", {"county": "Cook"}),
        ("spouse_income", {"monthly_gross_wages": "100.00"}),
    ],
)
def test_saving_an_intake_step_after_complete_reopens_it(filer, completed, section, value):
    client, _ = filer

    response = client.patch(_session_url(completed), {section: value}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "in_progress"
    assert _status(completed) == "in_progress"


def test_a_refused_save_leaves_a_completed_intake_complete(filer, completed):
    client, _ = filer

    response = client.patch(_session_url(completed), {"debtor_info": {"ssn": "123"}}, format="json")

    assert response.status_code == 400
    assert _status(completed) == "completed"


@pytest.mark.parametrize("step", [5, 9])
def test_moving_between_wizard_steps_after_complete_reopens_it(filer, completed, step):
    # Take-home pay made the wizard nine steps long: Review, the last, is step 9
    client, _ = filer

    response = client.post(
        _session_url(completed, "update_step/"), {"current_step": step}, format="json"
    )

    assert response.status_code == 200
    completed.refresh_from_db()
    assert completed.current_step == step
    assert _status(completed) == "in_progress"


@pytest.mark.parametrize(
    "endpoint,row",
    [
        ("contracts", {"counterparty_name": "Oak Street Apartments", "contract_type": "lease"}),
        ("codebtors", {"name": "Sam Doe", "relationship": "relative"}),
    ],
)
def test_adding_or_removing_a_contract_or_codebtor_after_complete_reopens_it(
    filer, completed, endpoint, row
):
    client, _ = filer
    url = _session_url(completed, f"{endpoint}/")

    added = client.post(url, row, format="json")
    assert added.status_code == 201
    assert _status(completed) == "in_progress"

    _complete_again(completed)
    removed = client.delete(f"{url}{added.data['id']}/")
    assert removed.status_code == 204
    assert _status(completed) == "in_progress"


@pytest.mark.parametrize(
    "endpoint,row",
    [
        ("contracts", {"counterparty_name": "Oak Street Apartments", "contract_type": "lease"}),
        ("codebtors", {"name": "Sam Doe", "relationship": "relative"}),
    ],
)
def test_saving_the_contracts_or_codebtors_list_after_complete_reopens_it(
    filer, completed, endpoint, row
):
    # Continue on steps 7 and 8 saves the whole list (DIG-147).
    client, _ = filer

    response = client.put(_session_url(completed, f"{endpoint}/"), [row], format="json")

    assert response.status_code == 200
    assert _status(completed) == "in_progress"


@pytest.mark.parametrize(
    "endpoint,row,change",
    [
        (
            "debts",
            {"creditor_name": "Chase", "debt_type": "credit_card", "amount_owed": "500.00"},
            {"amount_owed": "650.00"},
        ),
        (
            "assets",
            {"asset_type": "bank_account", "description": "Checking", "current_value": "800.00"},
            {"current_value": "950.00"},
        ),
    ],
)
def test_per_item_debt_and_asset_writes_after_complete_reopen_it(
    filer, completed, endpoint, row, change
):
    client, _ = filer
    url = f"/api/intake/{endpoint}/"

    created = client.post(url, {"session": completed.pk, **row}, format="json")
    assert created.status_code == 201
    assert _status(completed) == "in_progress"

    _complete_again(completed)
    updated = client.patch(f"{url}{created.data['id']}/", change, format="json")
    assert updated.status_code == 200
    assert _status(completed) == "in_progress"

    _complete_again(completed)
    deleted = client.delete(f"{url}{created.data['id']}/")
    assert deleted.status_code == 204
    assert _status(completed) == "in_progress"
    assert not AssetInfo.objects.filter(session=completed).exists()
    assert not DebtInfo.objects.filter(session=completed).exists()


def test_moving_a_debt_to_another_intake_reopens_both(filer, completed, district):
    client, user = filer
    other = IntakeSession.objects.create(user=user, district=district, status="completed")
    debt = DebtInfo.objects.create(
        session=completed, creditor_name="Chase", debt_type="credit_card", amount_owed=500
    )

    response = client.patch(f"/api/intake/debts/{debt.pk}/", {"session": other.pk}, format="json")

    assert response.status_code == 200
    assert (_status(completed), _status(other)) == ("in_progress", "in_progress")


def test_a_write_that_loaded_the_intake_before_complete_still_reopens_it(completed):
    # An upload loads the session, then reads the file for several seconds. The filer can press
    # Complete meanwhile, so the copy the upload holds still says in progress.
    IntakeSession.objects.filter(pk=completed.pk).update(status="in_progress")
    loaded_before_complete = IntakeSession.objects.get(pk=completed.pk)
    _complete_again(completed)

    loaded_before_complete.reopen()

    assert _status(completed) == "in_progress"
    # A full save of the copy afterwards (as the session PATCH does) keeps it in progress
    assert loaded_before_complete.status == "in_progress"


# ── What is not intake data ───────────────────────────────────────────


def test_form_answers_sofa_and_the_filing_fee_leave_a_completed_intake_complete(filer, completed):
    client, _ = filer

    answers = client.post(
        _session_url(completed, "answers/bulk/"),
        {
            "answers": [
                {"form_type": "form_101", "binding": "answer:form_101.q1", "value": "Yes"},
                {"form_type": "form_107", "binding": "sofa.has_prior_income", "value": "True"},
            ]
        },
        format="json",
    )
    sofa = client.patch(
        f"/api/intake/sofa-report/{completed.pk}/", {"has_business": False}, format="json"
    )
    filing_fee = client.put(
        _session_url(completed, "filing-fee/"), {"payment_choice": "waiver"}, format="json"
    )

    assert (answers.status_code, sofa.status_code, filing_fee.status_code) == (200, 200, 200)
    assert _status(completed) == "completed"
