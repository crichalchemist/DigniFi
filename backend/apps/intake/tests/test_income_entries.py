"""The business and rental entries' arithmetic (3e2 spec §4.2).

Business intent: each kind's net is that person's gross sum less their expenses sum. CMI never
counts a loss, because the U.S. Trustee's guidance says the net "cannot be a negative number"
(owner answer 1, C-12), and a loss never crosses kinds or people (§4.2).
"""

from decimal import Decimal
from types import SimpleNamespace

from apps.intake.income import (
    current_given,
    deductions_blank,
    floored_net,
    has_entry_figures,
    is_entry_answered,
    kind_net,
    kind_sums,
    schedule_i_field,
    schedule_i_line4,
)
from apps.intake.models import IncomeInfo


def _e(kind, gross, expenses, current_gross=None, current_expenses=None):
    return {
        "id": 1,
        "kind": kind,
        "description": "x",
        "gross": gross,
        "expenses": expenses,
        "current_gross": current_gross,
        "current_expenses": current_expenses,
    }


def test_a_loss_on_one_entry_nets_against_a_profit_on_another_of_the_same_kind():
    entries = [_e("business", "1000.00", "200.00"), _e("business", "300.00", "600.00")]
    assert kind_sums(entries, "business") == (Decimal("1300.00"), Decimal("800.00"))
    assert floored_net(entries, "business") == Decimal("500.00")


def test_a_kinds_net_below_zero_counts_as_zero_and_never_touches_the_other_kind():
    entries = [_e("business", "100.00", "400.00"), _e("rental", "1200.00", "200.00")]
    assert kind_net(entries, "business") == Decimal("-300.00")
    assert floored_net(entries, "business") == Decimal("0.00")
    assert floored_net(entries, "rental") == Decimal("1000.00")


def test_the_current_figures_have_their_own_net():
    entries = [_e("rental", "1200.00", "200.00", current_gross="500.00", current_expenses="900.00")]
    assert floored_net(entries, "rental", current=True) == Decimal("0.00")
    assert floored_net(entries, "rental") == Decimal("1000.00")


def test_a_blank_amount_counts_as_zero_and_no_list_nets_zero():
    assert kind_sums([_e("business", None, "50.00")], "business") == (
        Decimal("0"),
        Decimal("50.00"),
    )
    assert floored_net(None, "business") == Decimal("0.00")
    assert not has_entry_figures([_e("business", None, None)])
    assert has_entry_figures([_e("rental", "0.00", None)])


def test_schedule_i_uses_the_current_figures_only_while_the_answer_is_yes():
    for answer, field in [
        ("yes", "current_monthly_tips"),
        ("no", "monthly_tips"),
        (None, "monthly_tips"),
    ]:
        row = SimpleNamespace(income_now_different=answer)
        assert schedule_i_field(row, "monthly_tips") == field


def _row(**given):
    """A row by duck type: every Income step column None, then what the test gives."""
    columns = (
        IncomeInfo.SOURCE_FIELDS
        + IncomeInfo.CURRENT_FIELDS
        + IncomeInfo.DEDUCTION_FIELDS
        + ("income_now_different",)
    )
    row = SimpleNamespace(
        CURRENT_FIELDS=IncomeInfo.CURRENT_FIELDS,
        DEDUCTION_FIELDS=IncomeInfo.DEDUCTION_FIELDS,
        **dict.fromkeys(columns),
    )
    row.get_entries = lambda: given.pop("entries", None) or []
    row.__dict__.update(given)
    return row


def test_a_description_of_only_spaces_is_an_unanswered_question():  # Review Focus 5
    entry = {
        "kind": "business",
        "description": "   ",
        "gross": "100.00",
        "expenses": "0.00",
        "current_gross": None,
        "current_expenses": None,
    }
    assert is_entry_answered(entry, current=False) is False
    assert is_entry_answered(
        {**entry, "description": "Rideshare and delivery driving"}, current=False
    )


def test_an_entrys_current_amounts_are_asked_only_while_income_is_now_different():
    entry = {
        "kind": "rental",
        "description": "Duplex",
        "gross": "900.00",
        "expenses": "300.00",
        "current_gross": None,
        "current_expenses": None,
    }
    assert is_entry_answered(entry, current=False) is True
    assert is_entry_answered(entry, current=True) is False
    given = {**entry, "current_gross": "0.00", "current_expenses": "0.00"}
    assert is_entry_answered(given, current=True) is True


def test_a_current_figure_counts_as_given_from_a_box_or_from_an_entry():
    entry = {"id": 1, "kind": "business", "current_gross": None, "current_expenses": "0.00"}
    assert current_given(_row()) is False
    assert current_given(_row(current_monthly_tips=Decimal("0"))) is True
    assert current_given(_row(entries=[entry])) is True


def test_line_4_reads_the_figures_schedule_i_uses_and_counts_a_blank_as_zero():
    row = _row(
        monthly_gross_wages=Decimal("3000"),
        monthly_overtime=Decimal("200"),
        current_monthly_gross_wages=Decimal("1000"),
    )
    assert schedule_i_line4(row) == Decimal("3200")  # not answered: the averages
    row.income_now_different = "no"
    assert schedule_i_line4(row) == Decimal("3200")
    row.income_now_different = "yes"
    assert schedule_i_line4(row) == Decimal("1000")


def test_deductions_count_as_blank_only_when_all_eight_are():
    assert deductions_blank(_row()) is True
    assert deductions_blank(_row(payroll_union_dues=Decimal("0"))) is False
