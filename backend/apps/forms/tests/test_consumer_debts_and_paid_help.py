"""
The filer's answers about consumer debts and paid help print on every form that asks
(step 2 spec §3 Q7 and Q12, §6.3).

Business intent: whether the debts are primarily consumer debts (Form 101 line 16a,
106Sum line 7, 107 line 6) and whether the filer paid someone who is not a lawyer to
help with the forms (101 Part 7, 106Dec, 107 Part 12, with that person's name) are the
filer's own sworn answers. DigniFi never answers them. Each form prints exactly what
the filer said, all of them say the same, and a question the filer hasn't answered
stays blank. Form 103B lines 17-19 ask three different payment questions, and each
prints its own answer.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import DebtorInfo, FormAnswer, IncomeInfo, IntakeSession

User = get_user_model()

# Form → (box, state its "yes" ticks, state its "no" ticks), each state from the index.
CONSUMER_DEBTS = {
    "form_101": ("Check Box18", "/Yes", "/No"),
    "form_106sum": ("check7", "/consumer", "/not consumer"),
    "form_107": ("check6", "/yes", "/no"),
}
PAID_HELP = {
    "form_101": ("Check Box26", "/Yes", "/no"),
    "form_106dec": ("check1", "/yes", "/no"),
    "form_107": ("check30", "/yes", "/no"),
}
HELPER_NAME = {
    "form_101": "Name of person payed to help file",
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
    return session


def _answer(session, key, value, form_type="form_101"):
    FormAnswer.objects.create(session=session, form_type=form_type, field_key=key, value=value)


def _filled(session, form_type):
    """Box → what a viewer sees in it once the form is filled: the ticked states, or the text."""
    values = resolve(load_schema(form_type), session)
    shows = {}
    for widget in read_widgets(PDFFormFiller().fill(form_type, values)):
        seen = shows.setdefault(widget.full_name, set())
        if widget.state is not None:
            if widget.state != "/Off":
                seen.add(widget.state)
        elif widget.value:
            seen.add(widget.value)
    return shows


@pytest.mark.parametrize("answer", ["yes", "no"])
@pytest.mark.parametrize("form_type", CONSUMER_DEBTS)
def test_the_consumer_debts_answer_ticks_the_same_answer_on_every_form_that_asks(
    session, form_type, answer
):
    _answer(session, "primarily_consumer_debts", answer)
    box, yes, no = CONSUMER_DEBTS[form_type]
    assert _filled(session, form_type).get(box) == {yes if answer == "yes" else no}


@pytest.mark.parametrize("form_type", CONSUMER_DEBTS)
def test_only_the_filers_own_answer_can_tick_consumer_debts(form_type):
    # The answer decides whether the means test applies, and DigniFi never gives it for
    # the filer: the box is held for legal review, which fills it only from an answer.
    box = CONSUMER_DEBTS[form_type][0]
    field = next((f for f in load_schema(form_type).fields if f.pdf_field == box), None)
    assert field is not None, f"{box!r} is not bound on {form_type}"
    assert (field.source, field.legal_review) == ("asked", True)


@pytest.mark.parametrize("form_type", PAID_HELP)
def test_a_filer_who_paid_a_non_lawyer_says_so_and_names_them_on_every_form_that_asks(
    session, form_type
):
    _answer(session, "paid_non_attorney_preparer", "yes")
    _answer(session, "preparer_name", "Pat Helper")
    box, yes, _ = PAID_HELP[form_type]
    filled = _filled(session, form_type)
    assert filled.get(box) == {yes}
    assert filled.get(HELPER_NAME[form_type]) == {"Pat Helper"}


@pytest.mark.parametrize("form_type", PAID_HELP)
def test_a_filer_who_paid_no_one_says_no_and_names_no_one(session, form_type):
    _answer(session, "paid_non_attorney_preparer", "no")
    box, _, no = PAID_HELP[form_type]
    filled = _filled(session, form_type)
    assert filled.get(box) == {no}
    assert filled.get(HELPER_NAME[form_type]) == set()


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


def test_a_question_the_filer_has_not_answered_prints_nothing(session):
    boxes = {
        "form_101": ["Check Box18", "Check Box26", HELPER_NAME["form_101"]],
        "form_103b": [box for _, box in PAYMENT_LINES.values()],
        "form_106dec": ["check1", HELPER_NAME["form_106dec"]],
        "form_106sum": ["check7"],
        "form_107": ["check6", "check30", HELPER_NAME["form_107"]],
    }
    for form_type, names in boxes.items():
        filled = _filled(session, form_type)
        # A box name that is no box on the form reads None here, not blank.
        assert {box: filled.get(box) for box in names} == {box: set() for box in names}
