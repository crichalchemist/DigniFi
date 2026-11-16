"""A page answer that would not print whole in a 122A-2 box is refused when it is saved, never at Generate."""

from apps.forms.services.means_fit import (
    LINE_3_PURPOSE,
    LINE_43_EXPLANATION_LINES,
    LOAN_CREDITOR,
    LOAN_PROPERTY,
    TEMPLATE,
    VEHICLE_DESCRIPTION,
    box_refusal,
    explanation_refusal,
    fits_every,
)
from apps.forms.services.widgets import template_widgets
from apps.intake.means_test import (
    MEANS_EXPLANATION_LETTER,
    MEANS_EXPLANATION_TOO_LONG,
    MEANS_LETTER,
    MEANS_TOO_LONG,
)

# Measured with text_fit at 6 pt: 95.0 pt wide, so wider than line 34's creditor boxes
# (89.5 pt, less padding) and narrower than 33d's (about 120.6 pt).
CREDITOR_BETWEEN = "Demo Prairie Credit Union of Illinois"


def test_a_spouse_vehicle_description_is_held_to_line_34s_property_box():
    assert fits_every("2019 Toyota Sienna LE", VEHICLE_DESCRIPTION)  # 62.7 pt at 6 pt
    assert not fits_every("2019 Toyota Sienna LE minivan", VEHICLE_DESCRIPTION)  # 85.0 pt
    assert fits_every("2019 Toyota Sienna LE minivan", ("Describe Vehicle 1 1",))


def test_a_creditor_that_fits_33d_but_not_line_34_is_refused():
    assert fits_every(CREDITOR_BETWEEN, ("undefined_71",))
    assert not fits_every(CREDITOR_BETWEEN, LOAN_CREDITOR)


def test_every_named_box_is_a_drawn_widget_of_the_template():
    widgets = template_widgets(TEMPLATE)
    names = {*LINE_3_PURPOSE, *VEHICLE_DESCRIPTION, *LOAN_CREDITOR, *LOAN_PROPERTY}
    for name in names:
        drawn = [w for w in widgets if w.full_name == name and w.drawn]
        assert len(drawn) == 1, name


def test_a_letter_the_form_cant_print_never_fits():
    assert not fits_every("□", LINE_3_PURPOSE)


def test_a_refusal_says_whether_a_letter_or_the_length_is_the_trouble():
    assert box_refusal("Demo Lễ Bank", LOAN_CREDITOR) == MEANS_LETTER
    assert box_refusal(CREDITOR_BETWEEN, LOAN_CREDITOR) == MEANS_TOO_LONG
    assert box_refusal("Demo Bank", LOAN_CREDITOR) is None


def test_the_longest_aid_draft_saves():
    prose = " ".join(["Demo prose about what changed and why it matters to us."] * 8)[:450]
    labels = (
        "What happened:",
        "How it changes my monthly expenses or income:",
        "Other choices I looked at:",
        "Papers I will give my case trustee:",
    )
    draft = "\n".join(f"{label}\n{prose}" for label in labels)
    assert explanation_refusal(draft) is None


def test_an_explanation_past_36_sheet_lines_is_refused():
    text = "\n".join(["Demo line"] * (LINE_43_EXPLANATION_LINES + 1))
    assert explanation_refusal(text) == MEANS_EXPLANATION_TOO_LONG
    assert explanation_refusal("\n".join(["Demo line"] * LINE_43_EXPLANATION_LINES)) is None


def test_an_explanation_with_a_word_wider_than_its_column_is_refused():
    assert explanation_refusal("W" * 80) == MEANS_EXPLANATION_TOO_LONG


def test_an_explanation_with_a_letter_the_form_cant_print_is_refused():
    assert explanation_refusal("Demo □ explanation") == MEANS_EXPLANATION_LETTER
