"""
Form 122A-2's line 43 on the full path: the box, the four pointers and the attached sheet.

Business intent: a special circumstance is sworn to, so it prints only where the form reaches
line 43, a pointer must name the very sheet row that holds its explanation, an explanation
prints whole and never cut mid-word, and line 43 never moves a box that states the result.
"""

# ruff: noqa: F811
from decimal import Decimal

import pytest

from apps.districts.dated_tables import fill_date
from apps.eligibility.means_inputs import read_inputs, read_tables
from apps.eligibility.means_lines import work_out
from apps.forms.registry import build_parts
from apps.forms.services.means_fit import explanation_refusal
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.means_rows import CIRCUMSTANCES, answer_page, overflowing_session
from apps.forms.tests.pdf_readback import read_drawn, read_sheet_part
from apps.forms.tests.test_form_122a2_rows import LINE_43, _sheet_part
from apps.forms.tests.test_means_hold import district, user  # noqa: F401  (fixtures)
from apps.intake.models import IntakeSession
from apps.intake.tests.builders import complete_debt

POINTERS_AND_AMOUNTS = {name for boxes in LINE_43 for name in boxes}


@pytest.fixture
def session(user, district):
    return overflowing_session(user, district)


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


def _drawn(session):
    """(the document, its PDF, what the drawn form prints in each widget)."""
    document = build_parts("form_122a2", _fresh(session))
    pdf = PDFFormFiller().fill("form_122a2", document)
    return document, pdf, read_drawn("form_122a2", pdf, document["parts"])


def _printed(drawn, name):
    values = {w.value for w in drawn if w.full_name == name}
    assert len(values) == 1, (name, values)
    return values.pop()


def _tick(drawn, name):
    states = {w.state for w in drawn if w.full_name == name} - {"/Off"}
    assert len(states) <= 1, (name, states)
    return states.pop() if states else "/Off"


def _39c(session):
    tables, _ = read_tables(fill_date())
    return work_out(read_inputs(_fresh(session)), tables).lines["39c"]


def _no_presumption_by_line_16(session):
    # the builder leaves line 16 at 0.00, so this line 16 leaves 39c at -100.00
    return answer_page(session, over={"line_16": str(_39c(session) + Decimal("100.00"))})


def _no_presumption_by_line_42(session):
    # 39c at 200.00 puts 39d at 12,000.00, in the middle band, and 60,000.00 of unsecured debt
    # puts line 41b at 15,000.00, above it: line 42 is No.
    complete_debt(session, amount_owed=Decimal("60000.00"))
    return answer_page(session, over={"line_16": str(_39c(session) - Decimal("200.00"))})


@pytest.mark.parametrize(
    ("setup", "box", "reached"),
    [
        pytest.param(lambda s: s, "/Yes", True, id="a presumption, answered Yes"),
        pytest.param(
            lambda s: answer_page(s, over={"line_43_answer": "no"}),
            "/No",
            False,
            id="a presumption, answered No",
        ),
        pytest.param(_no_presumption_by_line_16, "/Off", False, id="no presumption at line 40"),
        pytest.param(_no_presumption_by_line_42, "/Off", False, id="no presumption at line 42"),
    ],
)
def test_check_box_16_prints_only_where_the_form_reaches_line_43(session, setup, box, reached):
    session = setup(session)

    document, _, drawn = _drawn(session)

    assert _tick(drawn, "CheckBox16") == box
    # a Yes prints four pointers and amounts and a sheet; every other case prints none of them
    printed = [_printed(drawn, name) for name in sorted(POINTERS_AND_AMOUNTS)]
    assert all(printed) is reached
    assert any(printed) is reached
    assert (_sheet_part(document, "43") is not None) is reached


def test_the_pointer_names_its_sheet_row(session):
    document, pdf, drawn = _drawn(session)
    (page,) = read_sheet_part(pdf, _sheet_part(document, "43"))

    assert _printed(drawn, "undefined_113") == "See line 43.1 on the attached sheet."
    assert _printed(drawn, "undefined_119") == "See line 43.4 on the attached sheet."
    assert page.rows == tuple(
        (f"43.{n}", explanation, amount) for n, (explanation, amount) in enumerate(CIRCUMSTANCES, 1)
    )

    # circumstance 1 removed: pointers 1 to 4 now name the former 2 to 5, and the sheet agrees
    kept = CIRCUMSTANCES[1:]
    session = answer_page(
        session,
        over={
            "line_43_circumstances": [
                {"explanation": explanation, "amount": amount} for explanation, amount in kept
            ]
        },
    )
    document, pdf, drawn = _drawn(session)
    (page,) = read_sheet_part(pdf, _sheet_part(document, "43"))

    assert page.rows == tuple(
        (f"43.{n}", explanation, amount) for n, (explanation, amount) in enumerate(kept, 1)
    )
    for n, ((pointer, amount_box), (_, amount)) in enumerate(zip(LINE_43, kept, strict=True), 1):
        assert _printed(drawn, pointer) == f"See line 43.{n} on the attached sheet."
        assert _printed(drawn, amount_box) == amount


def test_a_long_explanation_prints_whole_wrapped_at_its_spaces(session):
    # distinct words, so a word cut in two or two lines swapped shows as a different list
    explanation = " ".join(f"word{n:03d}" for n in range(200))
    assert explanation_refusal(explanation) is None
    circumstances = [{"explanation": explanation, "amount": "10.00"}] + [
        {"explanation": text, "amount": amount} for text, amount in CIRCUMSTANCES[1:]
    ]
    session = answer_page(session, over={"line_43_circumstances": circumstances})

    document, pdf, _ = _drawn(session)
    (page,) = read_sheet_part(pdf, _sheet_part(document, "43"))

    wrapped = page.lines[0][1]
    assert len(wrapped) > 1
    assert [word for line in wrapped for word in line.split()] == explanation.split()
    assert page.rows[0] == ("43.1", explanation, "10.00")
    assert (page.crossing, page.overlapping) == ((), ())


def test_line_43_never_changes_a_printed_box(session):
    _, _, with_circumstances = _drawn(session)
    without = answer_page(session, over={"line_43_answer": "no", "line_43_circumstances": []})
    _, _, without_circumstances = _drawn(without)

    def boxes(drawn):
        return {
            (w.full_name, w.page, w.tag): (w.value, w.state)
            for w in drawn
            if w.full_name != "CheckBox16" and w.full_name not in POINTERS_AND_AMOUNTS
        }

    assert boxes(with_circumstances) == boxes(without_circumstances)
    assert _tick(with_circumstances, "CheckBox16") == "/Yes"
    assert _tick(without_circumstances, "CheckBox16") == "/No"
