"""
Form 101 line 8 is the filer's own answer, so Form 103B is in the packet exactly when they ask
for the fee waiver, and nothing routes on a computed result (3f spec §7, U:375–381). A petition
with no answer, or a waiver application with a question unanswered, is refused with a link to the
page that asks it, never filled with a guess (§4, §7).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.models import MeansTest
from apps.forms.registry import PreconditionMissing, build_field_values, packet
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.intake.models import DebtorInfo, FilingFee, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household

User = get_user_model()

PAGE = "/filing-fee"
CHOOSE = "Choose how you will pay the filing fee."
MARIA_LINE_5 = (
    "I support two children on what I earn. After rent, food, the car and the children's "
    "costs, there is not enough left each month to pay the fee, even in parts."
)
WAIVER = {
    "income_change_answer": "no",
    "installments_explanation": MARIA_LINE_5,
    "others_covered_answer": "no",
    "expense_change_answer": "no",
}
LINES_4_TO_9 = ("Check 4", "4 type", "5 Type", "Check 7", "undefined_8", "Check 9", "undefined_10")


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        court_name="U.S. Bankruptcy Court, N.D. Ill.",
        state="IL",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session,
        first_name="Sarah",
        last_name="Chen",
        ssn="900-55-0005",
        date_of_birth=date(1995, 1, 20),
        street_address="1520 N Damen Ave Apt 2F",
        city="Chicago",
        state="IL",
        zip_code="60622",
    )
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("2000.00")
    )
    answer_household(session, payroll_tax=Decimal("250.00"), payment_choice=None)  # no line 8 yet
    return session


def _line_8(session, payment_choice, **answers):
    """Store the filer's filing-fee answers, and return the session read afresh (no cached row)."""
    FilingFee.objects.update_or_create(
        session=session, defaults={"payment_choice": payment_choice, **answers}
    )
    return IntakeSession.objects.get(pk=session.pk)


# ── The packet ────────────────────────────────────────────────────────


def test_103b_is_in_the_packet_exactly_when_the_filer_asks_for_the_waiver(session):
    # No record yet, then each answer in turn: asking, moving off, and asking again.
    held = ["form_103b" in packet(session)]
    for choice in (None, "installments", "waiver", "pay_in_full", "waiver"):
        held.append("form_103b" in packet(_line_8(session, choice)))
    assert held == [False, False, False, True, False, True]


def test_a_waiver_filer_above_the_median_still_gets_103b(session):
    # The filer chooses; the packet never second-guesses the choice on a computed figure.
    MeansTest.objects.create(
        session=session,
        district=session.district,
        calculated_cmi=Decimal("12000.00"),
        median_income_threshold=Decimal("134366.00"),
        passes_means_test=False,
    )
    forms = packet(_line_8(session, "waiver", **WAIVER))
    assert {"form_103b", "form_122a2"} <= set(forms)


# ── Form 101 line 8 ───────────────────────────────────────────────────


@pytest.mark.parametrize("stored", [False, True], ids=["no_row", "row_with_no_answer"])
def test_the_petition_is_refused_until_the_filer_chooses_how_to_pay_the_fee(session, stored):
    if stored:
        session = _line_8(session, None)
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_101", session)
    assert (str(refused.value), refused.value.step, refused.value.page) == (CHOOSE, None, PAGE)


def test_the_petition_names_a_missing_county_before_the_fee(session):
    # A guard (ruling R29): it passes before Step 3, and fails if the fee check runs first.
    household = session.household
    household.county = None
    household.save()
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_101", session)
    assert (str(refused.value), refused.value.step, refused.value.page) == (
        "Choose your county on the Your Information step.",
        "debtor_info",
        None,
    )


@pytest.mark.parametrize(
    "choice,state",
    [
        ("pay_in_full", "/Pay entirely"),
        ("installments", "/Pay in installments"),
        ("waiver", "/Request fees waived"),
    ],
)
def test_the_petition_ticks_only_the_filers_own_way_to_pay_the_fee(session, choice, state):
    values = build_field_values("form_101", _line_8(session, choice, **WAIVER))
    assert values["Check Box7"] == state
    PDFFormFiller().check("form_101", values)  # the state is one of the box's own


# ── Form 103B's own questions ─────────────────────────────────────────


@pytest.mark.parametrize(
    "answers,sentence",
    [
        (
            {"income_change_answer": None},
            "Answer whether you expect your family's income to go up or down by more than 10% in the next 6 months.",
        ),
        (
            {"income_change_answer": "yes", "income_change_explanation": ""},
            "Explain how you expect your family's income to change.",
        ),
        (
            {"income_change_answer": "yes", "income_change_explanation": "  \n "},
            "Explain how you expect your family's income to change.",
        ),
        (
            {"installments_explanation": "   "},  # line 5 typed as only spaces
            "Tell the court why you can't pay the filing fee in installments.",
        ),
        (
            {"installments_explanation": " \t\n"},
            "Tell the court why you can't pay the filing fee in installments.",
        ),
        (
            {"others_covered_answer": None},
            "Answer whether your expenses cover anyone not counted in your family.",
        ),
        (
            {"others_covered_answer": "yes", "others_covered_who": ""},
            "Say who else your expenses cover.",
        ),
        (
            {"expense_change_answer": None},
            "Answer whether you expect your expenses to go up or down by more than 10% in the next 6 months.",
        ),
        (
            {"expense_change_answer": "yes", "expense_change_explanation": " "},
            "Explain how you expect your expenses to change.",
        ),
    ],
)
def test_103b_is_refused_with_a_link_to_the_filing_fee_page_until_each_question_is_answered(
    session, answers, sentence
):
    session = _line_8(session, "waiver", **{**WAIVER, **answers})
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_103b", session)
    assert (str(refused.value), refused.value.step, refused.value.page) == (sentence, None, PAGE)


def test_103b_names_the_first_unanswered_line_in_the_forms_order(session):
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_103b", _line_8(session, "waiver"))
    assert str(refused.value).startswith("Answer whether you expect your family's income")


@pytest.mark.parametrize(
    "left_blank,sentence",
    [
        (
            {
                "installments_explanation": "",
                "others_covered_answer": None,
                "expense_change_answer": None,
            },
            "Tell the court why you can't pay the filing fee in installments.",
        ),
        (
            {"others_covered_answer": None, "expense_change_answer": None},
            "Answer whether your expenses cover anyone not counted in your family.",
        ),
    ],
)
def test_with_several_lines_unanswered_103b_names_the_earliest_on_the_form(
    session, left_blank, sentence
):
    # The filer fixes one line at a time, so the refusal must point at the line
    # they reach first on the form, not whichever gap the code checks first.
    session = _line_8(session, "waiver", **{**WAIVER, **left_blank})
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_103b", session)
    assert str(refused.value) == sentence


def test_103b_with_no_filing_fee_row_is_refused_in_words_never_an_attribute_error(session):
    assert not FilingFee.objects.filter(session=session).exists()
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_103b", session)
    assert str(refused.value).startswith("Answer whether you expect your family's income")


def test_103b_prints_a_waiver_filers_own_answers_to_lines_4_5_7_and_9(session):
    values = build_field_values("form_103b", _line_8(session, "waiver", **WAIVER))
    assert {box: values.get(box) for box in LINES_4_TO_9} == {
        "Check 4": "/no",
        "4 type": None,
        "5 Type": MARIA_LINE_5,
        "Check 7": "/On",  # the template's No box exports On (field index, Check 7 T4)
        "undefined_8": None,
        "Check 9": "/no",
        "undefined_10": None,
    }
    PDFFormFiller().check("form_103b", values)  # Maria's line 5 fits its box


YESES = {
    "income_change_answer": "yes",
    "income_change_explanation": "My hours are being cut in March.",
    "others_covered_answer": "yes",
    "others_covered_who": "My mother, who lives with her sister.",
    "expense_change_answer": "yes",
    "expense_change_explanation": "My rent goes up $200 in June.",
}
EXPLANATIONS = ("4 type", "undefined_8", "undefined_10")


def test_each_yes_prints_with_what_the_filer_wrote_beside_it(session):
    values = build_field_values("form_103b", _line_8(session, "waiver", **{**WAIVER, **YESES}))
    assert {box: values.get(box) for box in LINES_4_TO_9} == {
        "Check 4": "/yes",
        "4 type": "My hours are being cut in March.",
        "5 Type": MARIA_LINE_5,
        "Check 7": "/yes",
        "undefined_8": "My mother, who lives with her sister.",
        "Check 9": "/yes",
        "undefined_10": "My rent goes up $200 in June.",
    }


def test_an_explanation_kept_after_the_answer_changes_to_no_does_not_print(session):
    yes = build_field_values("form_103b", _line_8(session, "waiver", **{**WAIVER, **YESES}))
    assert all(yes.get(box) for box in EXPLANATIONS)
    # The page keeps the texts stored when each answer moves to No (spec §4).
    no = {
        "income_change_answer": "no",
        "others_covered_answer": "no",
        "expense_change_answer": "no",
    }
    values = build_field_values(
        "form_103b", _line_8(session, "waiver", **{**WAIVER, **YESES, **no})
    )
    assert (values["Check 4"], values["Check 7"], values["Check 9"]) == ("/no", "/On", "/no")
    assert [values.get(box) for box in EXPLANATIONS] == [None] * 3
    stored = FilingFee.objects.get(session=session)
    assert (
        stored.income_change_explanation,
        stored.others_covered_who,
        stored.expense_change_explanation,
    ) == (
        YESES["income_change_explanation"],
        YESES["others_covered_who"],
        YESES["expense_change_explanation"],
    )  # still stored, only not printed


def test_line_5_prints_without_the_spaces_around_it(session):
    session = _line_8(
        session, "waiver", **{**WAIVER, "installments_explanation": "  I have no savings.\n"}
    )
    assert build_field_values("form_103b", session)["5 Type"] == "I have no savings."


def test_an_unanswered_waiver_question_ticks_no_box(session):
    # resolve() alone, without 103B's requires(): only line 5 is answered, and no other
    # answer is guessed onto the page.
    session = _line_8(session, "waiver", installments_explanation="I have no savings.")
    values = resolve(load_schema("form_103b"), session)
    assert [box for box in LINES_4_TO_9 if box in values] == ["5 Type"]
