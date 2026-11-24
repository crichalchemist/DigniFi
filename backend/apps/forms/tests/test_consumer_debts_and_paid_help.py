"""
The filer's answers about consumer debts and paid help print on every form that asks
(step 2 spec §3 Q7 and Q12, §6.3).

Business intent: whether the debts are primarily consumer debts (Form 101 line 16a,
106Sum line 7, 107 line 6) and whether the filer paid someone who is not a lawyer to
help with the forms (101 Part 7, 106Dec, 107 Part 12, with that person's name) are the
filer's own sworn answers. DigniFi never answers them. Each form prints exactly what
the filer said, and a question the filer hasn't answered stays blank. Form 103B lines
17-19 ask three different payment questions, and each prints its own answer.

Until 4d and 4i ask these questions once, the answers live in two stores: Form 101 reads
`PetitionAnswers` and the other forms read `FormAnswer`. The tests plant the answer in
each form's own store, so they show that each form prints its store's answer, not that
the two stores agree.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.derivations import ANSWER_BOX_RULES
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import DebtorInfo, FormAnswer, IncomeInfo, IntakeSession, PetitionAnswers
from apps.intake.tests.builders import answer_household

User = get_user_model()

# Form → (box, state its "yes" ticks, state its "no" ticks), each state from the index. Form 101
# (11/26) asks each as two single boxes: ((its Yes box, its No box), the one state each ticks).
CONSUMER_DEBTS = {
    "form_101": (("Yes Go to line 17", "No Go to line 16b"), "/On"),
    "form_106sum": ("check7", "/consumer", "/not consumer"),
    "form_107": ("check6", "/yes", "/no"),
}
PAID_HELP = {
    "form_101": (("Yes Name of Person", "No_10"), "/On"),
    "form_106dec": ("check1", "/yes", "/no"),
    "form_107": ("check30", "/yes", "/no"),
}
HELPER_NAME = {
    "form_101": "undefined_22",
    "form_106dec": "Name of person payed to help file",
    "form_107": "Name of person agreed to pay",
}
# Form 103B line → (its answer key, its box).
PAYMENT_LINES = {
    "17": ("paid_anyone_for_services", "check_17"),
    "18": ("promised_to_pay_for_services", "check_18"),
    "19": ("someone_paid_on_your_behalf", "check_19"),
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="filer_answers", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        middle_name="",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    # 106Sum line 8 prints CMI, which needs income entered by source.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
    # Line 16 left unanswered (4d's builder default answers consumer): each test plants its own.
    answer_household(session, debt_nature=None)
    return session


def _answer(session, key, value, form_type="form_101"):
    FormAnswer.objects.create(session=session, form_type=form_type, field_key=key, value=value)


# The petition's own record of the answers 106Sum, 106Dec and 107 still read from FormAnswer
# rows until 4d and 4i: key → (PetitionAnswers key, the stored value of a "yes" / "no").
PETITION_ANSWER = {
    "primarily_consumer_debts": ("debt_nature", {"yes": "consumer", "no": "business"}),
    "paid_non_attorney_preparer": ("paid_preparer", {"yes": "yes", "no": "no"}),
}


def _says(session, form_type, key, value):
    """The filer's answer, stored where the form reads it: Form 101's record, or the shared row."""
    if form_type != "form_101":
        _answer(session, key, value)
        return
    petition_key, stored = PETITION_ANSWER.get(key, (key, None))
    record, _ = PetitionAnswers.objects.get_or_create(session=session)
    record.merge({petition_key: stored[value] if stored else value})
    record.save()
    session.refresh_from_db()  # drops the record the session cached before this save


def _boxes(entry):
    """(yes box, yes state, no box, no state) of a table entry."""
    if isinstance(entry[0], tuple):
        (yes_box, no_box), state = entry
        return yes_box, state, no_box, state
    box, yes, no = entry
    return box, yes, box, no


def _shows(filled, form_type, entry, answer):
    """What the form prints in the box of its Yes and the box of its No, for one answer."""
    yes_box, yes, no_box, no = _boxes(entry)
    if yes_box == no_box:
        return filled.get(yes_box), {yes if answer == "yes" else no}
    own, other = (yes_box, no_box) if answer == "yes" else (no_box, yes_box)
    # Only the box of the filer's own answer is ticked; the other prints nothing.
    assert filled.get(other) == set(), (form_type, other)
    return filled.get(own), {yes if answer == "yes" else no}


def _filled(session, form_type):
    """Box → what the drawn form prints in it: the ticked states, or the text."""
    values = resolve(load_schema(form_type), session)
    shows = {}
    for widget in read_drawn(form_type, PDFFormFiller().fill(form_type, values)):
        seen = shows.setdefault(widget.full_name, set())
        if widget.state:
            if widget.state != "/Off":
                seen.add(widget.state)
        elif widget.value:
            seen.add(widget.value)
    return shows


@pytest.mark.slow
@pytest.mark.parametrize("answer", ["yes", "no"])
@pytest.mark.parametrize("form_type", CONSUMER_DEBTS)
def test_the_consumer_debts_answer_ticks_the_same_answer_on_every_form_that_asks(
    session, form_type, answer
):
    _says(session, form_type, "primarily_consumer_debts", answer)
    shown, expected = _shows(
        _filled(session, form_type), form_type, CONSUMER_DEBTS[form_type], answer
    )
    assert shown == expected


@pytest.mark.parametrize("form_type", CONSUMER_DEBTS)
def test_only_the_filers_own_answer_can_tick_consumer_debts(form_type):
    # The answer decides whether the means test applies, and DigniFi never gives it for
    # the filer: the box is held for legal review, which fills it only from an answer.
    box = _boxes(CONSUMER_DEBTS[form_type])[0]
    field = next((f for f in load_schema(form_type).fields if f.pdf_field == box), None)
    assert field is not None, f"{box!r} is not bound on {form_type}"
    if form_type == "form_101":
        # Form 101 ticks its Yes box through a rule that fires on the filer's own "consumer".
        assert (field.source, field.legal_review) == ("derived", True)
        assert field.rule in ANSWER_BOX_RULES
    else:
        assert (field.source, field.legal_review) == ("asked", True)


@pytest.mark.slow
@pytest.mark.parametrize("form_type", PAID_HELP)
def test_a_filer_who_paid_a_non_lawyer_says_so_and_names_them_on_every_form_that_asks(
    session, form_type
):
    _says(session, form_type, "paid_non_attorney_preparer", "yes")
    _says(session, form_type, "preparer_name", "Pat Helper")
    filled = _filled(session, form_type)
    shown, expected = _shows(filled, form_type, PAID_HELP[form_type], "yes")
    assert shown == expected
    assert filled.get(HELPER_NAME[form_type]) == {"Pat Helper"}


@pytest.mark.slow
@pytest.mark.parametrize("form_type", PAID_HELP)
def test_a_filer_who_paid_no_one_says_no_and_names_no_one(session, form_type):
    _says(session, form_type, "paid_non_attorney_preparer", "no")
    filled = _filled(session, form_type)
    shown, expected = _shows(filled, form_type, PAID_HELP[form_type], "no")
    assert shown == expected
    assert filled.get(HELPER_NAME[form_type]) == set()


@pytest.mark.slow
def test_form_107_names_the_helper_the_filer_named_once_for_every_form(session):
    # A separate Form 107 answer could name someone the petition doesn't.
    _answer(session, "Name_of_person_agreed_to_pay", "Someone Else", form_type="form_107")
    _answer(session, "preparer_name", "Pat Helper")
    assert _filled(session, "form_107").get("Name of person agreed to pay") == {"Pat Helper"}


@pytest.mark.parametrize("yes_line", PAYMENT_LINES)
def test_each_form_103b_payment_question_prints_its_own_answer(session, yes_line):
    # Lines 17-19 ask three different things, so a "yes" to one ticks Yes on that line only.
    for line, (key, _) in PAYMENT_LINES.items():
        _answer(session, key, "yes" if line == yes_line else "no", form_type="form_103b")
    filled = _filled(session, "form_103b")
    assert {line: filled.get(box) for line, (_, box) in PAYMENT_LINES.items()} == {
        line: {"/yes" if line == yes_line else "/no"} for line in PAYMENT_LINES
    }


# Form 101 line 9 and Form 103B line 20 ask the same question: (the answer's box and its Yes
# state, then each case's district, when and case number boxes), from each form's index, all on
# page 3. Form 101's "District" is also the court on page 1, so a box is read on its page.
PRIOR_CASES = {
    "form_101": (
        ("bankruptcy within the", "/Yes"),
        (("District", "When", "Case number"), ("District_2", "When_2", "Case number_2")),
    ),
    "form_103b": (
        ("check_20", "/yes"),
        (("undefined_37", "When", "Case number_2"), ("District", "When_2", "Case number_3")),
    ),
}


@pytest.mark.slow
def test_the_prior_cases_print_the_same_on_form_101_and_103b(session):
    # One answer, stored once in the petition record, prints the same on both forms that ask.
    cases = [
        {"district": "Demo Northern Illinois", "filed_on": "03/02/2018", "case_number": "18-01"},
        {"district": "Demo Central Illinois", "filed_on": "11/20/2019", "case_number": "19-02"},
    ]
    record, _ = PetitionAnswers.objects.get_or_create(session=session)
    record.merge({"prior_bankruptcy_answer": "yes", "prior_cases": cases})
    record.save()
    session.refresh_from_db()
    for form_type, ((answer_box, yes), rows) in PRIOR_CASES.items():
        values = resolve(load_schema(form_type), session)
        on_page_3 = {}
        for widget in read_drawn(form_type, PDFFormFiller().fill(form_type, values)):
            if widget.page == 3 and widget.state not in (None, "", "/Off"):
                on_page_3.setdefault(widget.full_name, set()).add(widget.state)
            elif widget.page == 3 and not widget.state:
                on_page_3.setdefault(widget.full_name, set()).add(widget.value)
        assert on_page_3.get(answer_box) == {yes}, form_type
        printed = [tuple(on_page_3.get(box) for box in row) for row in rows]
        assert printed == [
            ({case["district"]}, {case["filed_on"]}, {case["case_number"]}) for case in cases
        ], form_type


@pytest.mark.slow
def test_a_question_the_filer_has_not_answered_prints_nothing(session):
    boxes = {
        "form_101": [
            *CONSUMER_DEBTS["form_101"][0],
            *PAID_HELP["form_101"][0],
            HELPER_NAME["form_101"],
        ],
        "form_103b": [box for _, box in PAYMENT_LINES.values()],
        "form_106dec": ["check1", HELPER_NAME["form_106dec"]],
        "form_106sum": [CONSUMER_DEBTS["form_106sum"][0]],
        "form_107": ["check6", "check30", HELPER_NAME["form_107"]],
    }
    for form_type, names in boxes.items():
        filled = _filled(session, form_type)
        # A box name that is no box on the form reads None here, not blank.
        assert {box: filled.get(box) for box in names} == {box: set() for box in names}
