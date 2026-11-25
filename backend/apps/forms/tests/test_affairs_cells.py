"""
Form 107 lines 1-12 print the filer's own answers as the form reads them (4f-i, D§5.2).

An amount prints to the cent or blank, a date only as MM/DD/YYYY, a last 4 only as four digits,
and every word a computed cell adds is the form's own: a malformed answer stays stored as typed
and prints blank, never 0.00 and never a guess, and line 6's rows print only under the branch of
Form 101 line 16 they were given for.
"""

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.field_index import export_state, load_index, option_text
from apps.forms.services.answer_records import (
    AFFAIRS_CELLS,
    AFFAIRS_COMPUTED_CELLS,
    AFFAIRS_LIST_CELLS,
    PAID_FOR_WORDS,
    WHAT_HAPPENED_WORDS,
    affairs_statement,
    branch_of,
    record_value,
)
from apps.forms.services.derivations import PREDICATES
from apps.forms.services.explain_split import split_at_box, split_explain
from apps.forms.services.fill_resolver import is_money_binding
from apps.intake.models import FinancialAffairsAnswers, IntakeSession
from apps.intake.tests.builders import answer_financial_affairs, answer_petition

User = get_user_model()

FORM_107 = "b_107_0425-form.pdf"


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="testuser", password="pw")
    d = District.objects.create(
        code="ilnd",
        name="N.D. Ill.",
        court_name="x",
        state="IL",
        filing_fee_chapter_7="338.00",
    )
    return IntakeSession.objects.create(user=user, district=d, status="in_progress", current_step=1)


def _stub(record, answers):
    return SimpleNamespace(**{record: SimpleNamespace(get_answers=lambda: answers)})


def _reread(s):
    return IntakeSession.objects.get(pk=s.pk)


def test_the_printed_cell_table_is_the_records():
    assert AFFAIRS_LIST_CELLS == FinancialAffairsAnswers.LIST_CELLS


def test_every_stored_and_computed_cell_has_its_own_printer():
    # A printer built in a loop that caught the last cell would print one cell in every box.
    for key, cells in AFFAIRS_LIST_CELLS.items():
        assert set(AFFAIRS_CELLS[key]) == {*cells, *AFFAIRS_COMPUTED_CELLS.get(key, ())}, key
    row = {"street": "1 Demo St", "city": "Joliet", "from": "01/02/2025", "to": "03/04/2026"}
    printed = {cell: AFFAIRS_CELLS["l2_rows"][cell](row) for cell in ("street", "from", "to")}
    assert printed == {"street": "1 Demo St", "from": "01/02/2025", "to": "03/04/2026"}


@pytest.mark.parametrize(
    "typed,printed",
    [
        ("1250.5", "1250.50"),
        ("0", "0.00"),
        ("", ""),
        ("12.345", ""),
        ("-5", ""),
        ("1,200", ""),
        ("10000000000", ""),
        ("٣", ""),
    ],
)
def test_an_affairs_amount_prints_to_the_cent_and_a_malformed_one_prints_blank(typed, printed):
    assert AFFAIRS_CELLS["l6_rows"]["paid"]({"paid": typed}) == printed


@pytest.mark.parametrize(
    "typed,printed",
    [
        ("09/02/2026", "09/02/2026"),
        ("9/2/2026", ""),
        ("13/40/2026", ""),
        ("02/30/2026", ""),
        ("", ""),
    ],
)
def test_an_affairs_date_prints_only_as_mm_dd_yyyy(typed, printed):  # R-12
    assert AFFAIRS_CELLS["l2_rows"]["from"]({"from": typed}) == printed


def test_last_4_prints_only_four_digits():
    assert [
        AFFAIRS_CELLS["l11_rows"]["last_4"]({"last_4": v}) for v in ("1234", "123", "12345", "12a4")
    ] == ["1234", "", "", ""]


def test_a_case_status_prints_only_as_one_of_the_forms_three():
    printed = [
        AFFAIRS_CELLS["l9_rows"]["status"]({"status": v})
        for v in ("pending", "on_appeal", "concluded", "closed", "")
    ]
    assert printed == ["pending", "on_appeal", "concluded", "", ""]


def test_a_folded_name_and_address_cell_prints_the_parts_given():
    row = {
        "name": "Demo Bank",
        "street": "1 Demo St",
        "street_2": "Suite 2",
        "city": "Chicago",
        "state": "IL",
        "zip": "60601",
    }
    assert (
        AFFAIRS_CELLS["l6_rows"]["name_and_address"](row)
        == "Demo Bank, 1 Demo St, Suite 2, Chicago, IL 60601"
    )
    assert (
        AFFAIRS_CELLS["l6_rows"]["name_and_address"]({"name": "Demo Bank", "zip": "60601"})
        == "Demo Bank, 60601"
    )
    assert (
        AFFAIRS_CELLS["l2_rows"]["address"]({"street": "1 Demo St", "city": "Joliet"})
        == "1 Demo St, Joliet"
    )


def test_a_court_cell_prints_its_name_street_and_city_line():
    row = {
        "court_name": "Demo County Court",
        "court_street": "50 Demo Ave",
        "court_city": "Joliet",
        "court_state": "IL",
        "court_zip": "60432",
    }
    assert (
        AFFAIRS_CELLS["l9_rows"]["court"](row) == "Demo County Court, 50 Demo Ave, Joliet, IL 60432"
    )


def test_the_dates_cell_prints_only_the_dates_the_form_can_read():
    row = {"date_1": "01/05/2026", "date_2": "2/1/2026", "date_3": "03/05/2026"}
    assert AFFAIRS_CELLS["l7_rows"]["dates"](row) == "01/05/2026, 03/05/2026"


def test_the_payment_words_follow_the_ticks_in_the_forms_order():
    row = {"other": "yes", "car": "yes", "other_text": "storage unit"}
    assert AFFAIRS_CELLS["l6_rows"]["paid_for"](row) == "Car, Other: storage unit"
    assert AFFAIRS_CELLS["l6_rows"]["paid_for"]({"other": "yes", "other_text": " "}) == "Other"
    assert (
        AFFAIRS_CELLS["l10_rows"]["what_happened"]({"garnished": "yes", "repossessed": "yes"})
        == "Property was repossessed. Property was garnished."
    )


@pytest.mark.parametrize(
    "cell,box",
    [
        ("mortgage", "check mortgage 1"),
        ("car", "check car 1"),
        ("credit_card", "check credit card 1"),
        ("loan", "check loan 1"),
        ("vendors", "check vendors 1"),
        ("other", "check other 1"),
    ],
)
def test_the_payment_tick_words_are_the_forms_own(cell, box):
    state = next(w for w in load_index(FORM_107)[box]).on_state
    assert PAID_FOR_WORDS[cell] == option_text(FORM_107, box, export_state(state))


@pytest.mark.parametrize(
    "cell,box",
    [
        ("repossessed", "check10a1"),
        ("foreclosed", "check10a2"),
        ("garnished", "check10a3"),
        ("attached", "check10a4"),
    ],
)
def test_the_what_happened_words_are_the_forms_own(cell, box):
    assert WHAT_HAPPENED_WORDS[cell] == option_text(FORM_107, box, "/yes")


def test_the_word_tables_keep_the_forms_order():
    assert list(PAID_FOR_WORDS) == ["mortgage", "car", "credit_card", "loan", "vendors", "other"]
    assert list(WHAT_HAPPENED_WORDS) == ["repossessed", "foreclosed", "garnished", "attached"]


def test_a_tick_prints_true_only_for_yes():
    assert [AFFAIRS_CELLS["l6_rows"]["car"]({"car": v}) for v in ("yes", "no", "")] == [
        "true",
        "",
        "",
    ]


def test_line_12s_statement_reads_only_under_its_yes():
    assert affairs_statement({"l12_answer": "no", "l12_statement": [{"text": "Demo"}]}) == []
    assert affairs_statement({"l12_answer": "yes", "l12_statement": [{"text": "  "}]}) == []
    stub = _stub(
        "financial_affairs",
        {"l12_answer": "yes", "l12_statement": [{"text": "Demo note"}, {"text": ""}]},
    )
    assert record_value(stub, "affairs.l12_statement[].text") == ["Demo note"]


@pytest.mark.parametrize("debt_nature", [None, "consumer", "business", "neither"])
@pytest.mark.parametrize("branch", ["consumer", "other"])
@pytest.mark.parametrize("answer", ["yes", "no"])
def test_line_6_rows_print_only_under_the_branch_they_were_given(
    debt_nature, branch, answer, session
):  # R-5
    answer_petition(session, debt_nature=debt_nature)
    answer_financial_affairs(session, l6_answer=answer, l6_branch=branch)
    expected = answer == "yes" and debt_nature is not None and branch_of(debt_nature) == branch
    assert PREDICATES["affairs_l6_rows"](_reread(session)) is expected


def test_a_line_6_yes_with_no_branch_prints_no_row(session):  # Ruling T1-PAIR
    answer_petition(session, debt_nature="consumer")
    answer_financial_affairs(session, l6_answer="yes", l6_branch=None)
    assert PREDICATES["affairs_l6_rows"](_reread(session)) is False


@pytest.mark.parametrize("line", [2, 5, 7, 8, 9, 10, 11])
def test_a_lines_rows_print_only_under_its_yes(line, session):
    name = f"affairs_l{line}_rows"
    assert PREDICATES[name](session) is False  # no record
    answer_financial_affairs(session, **{f"l{line}_answer": "no"})
    assert PREDICATES[name](_reread(session)) is False
    answer_financial_affairs(session, **{f"l{line}_answer": "yes"})
    assert PREDICATES[name](_reread(session)) is True


def test_a_case_title_too_long_for_its_first_box_continues_in_the_second():  # R-15
    # Case title1 9a is one line, 111.4 pt wide (index rect [101.5, 193.9, 212.9, 208.5]):
    # about 37 letters at 6 pt, so this 80-letter title overflows it.
    title = "Demo Holdings Limited Partnership v. Demonstration Property Management Company"
    first = AFFAIRS_CELLS["l9_rows"]["case_title_1"]({"case_title": title})
    second = AFFAIRS_CELLS["l9_rows"]["case_title_2"]({"case_title": title})
    assert first and second and f"{first} {second}" == title  # split at a word
    assert (
        AFFAIRS_CELLS["l9_rows"]["case_title_1"]({"case_title": "Demo v. Demo"}) == "Demo v. Demo"
    )
    assert AFFAIRS_CELLS["l9_rows"]["case_title_2"]({"case_title": "Demo v. Demo"}) == ""


def test_an_unknown_affairs_list_or_cell_on_lines_1_to_12_raises():  # R-48
    for binding in (
        "affairs.l1_rows[].street",
        "affairs.l6_rows[].nmae",
        "affairs.l12_statement[].words",
    ):
        with pytest.raises(ValueError, match="unrecognized binding"):
            record_value(SimpleNamespace(), binding)  # no record: still refused


def test_an_affairs_money_cell_can_be_totalled():
    assert is_money_binding("affairs.l6_rows[].paid")
    assert is_money_binding("affairs.l10_rows[].value")
    assert not is_money_binding("affairs.l6_rows[].name")


def test_split_explain_still_splits_form_108s_words_as_before():
    words = "My brother Mateo, the co-owner, keeps paying the loan."
    assert split_explain(words) == split_at_box(words, "form_b108.pdf", "Explain1 1a")
