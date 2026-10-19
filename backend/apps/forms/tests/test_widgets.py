"""
Every widget of each AO template has one address, its page and tag (spec §4.2).

The engine finds a template widget's index row by page and rectangle, so a value
meant for one of two same-name boxes lands on that box. The template's print
buttons never print, a stacked duplicate prints its value once, and each box is
laid out the way pypdf will draw it.
"""

from collections import Counter
from pathlib import Path

import pypdf
import pytest
from django.conf import settings
from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.forms.field_index import load_index
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.widgets import (
    TemplateMismatch,
    field_of,
    parse_key,
    qualified_name,
    template_widgets,
    widget_for,
)

SCHEDULE_D = "form_b106d.pdf"


def _templates():
    return sorted({load_schema(form_type).template_filename for form_type in get_all_form_types()})


def _all_widgets():
    return [widget for template in _templates() for widget in template_widgets(template)]


def _named(template, full_name):
    return [w for w in template_widgets(template) if w.full_name == full_name]


def test_every_template_widget_matches_one_index_row():
    total = 0
    for template in _templates():
        widgets = template_widgets(template)
        rows = [row for rows in load_index(template).values() for row in rows]
        assert sorted(w.key for w in widgets) == sorted(
            f"{row.full_name}@{row.page}:{row.tag}" for row in rows
        )
        reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template)
        found = []
        for number, page in enumerate(reader.pages, start=1):
            for annot in page.get("/Annots") or []:
                annotation = annot.get_object()
                if annotation.get("/Subtype") != "/Widget":
                    continue
                widget = widget_for(template, number, annotation, float(page.mediabox.top))
                # The rect is the only thing matched: the name proves it found the right row.
                assert widget.full_name == qualified_name(field_of(annotation))
                found.append(widget.key)
        assert sorted(found) == sorted(w.key for w in widgets)
        total += len(widgets)
    assert total == 3003


def test_only_the_print_buttons_are_left_unprinted():
    widgets = _all_widgets()
    unprinted = [w for w in widgets if not w.printed]
    assert len(unprinted) == 67
    assert unprinted == [w for w in widgets if w.kind == "Button"]
    # Flagged not to show on screen but to print: it prints, as from the fillable form.
    (hidden,) = _named(
        SCHEDULE_D, "be notified for any debts in Part 1 do not fill out or submit this page.1"
    )
    assert (hidden.page, hidden.printed, hidden.drawn) == (3, True, True)


SCHEDULE_D_STACKED = {
    "4_3",
    "Contingent_3",
    "Unliquidated_3",
    "Disputed_3",
    "An agreement you made such as mortgage or secured_3",
    "Statutory lien such as tax lien mechanics lien_3",
    "Judgment lien from a lawsuit_3",
    "Other including a right to offset_3",
}


def test_schedule_d_page_2_has_eight_stacked_pairs():
    # One widget of each pair, all of them Schedule D's, and none on any other template.
    stacked = [w for w in _all_widgets() if w.stacked]
    assert sorted(w.full_name for w in stacked) == sorted(SCHEDULE_D_STACKED)
    assert set(stacked) <= set(template_widgets(SCHEDULE_D))
    for name in SCHEDULE_D_STACKED:
        first, second = _named(SCHEDULE_D, name)
        # The pair's second widget by tag number is left out; the first one prints the value.
        assert (first.page, second.page) == (2, 2)
        assert int(first.tag[1:]) < int(second.tag[1:])
        assert (first.drawn, second.drawn) == (True, False)


def test_box_layout_is_read_as_the_template_sets_it():
    # Schedule D's account boxes keep their cell count (MaxLen) on the parent field.
    assert [(w.page, w.comb, w.max_len) for w in _named(SCHEDULE_D, "account number")] == [
        (1, True, 4),
        (3, True, 4),
    ]
    # Form 121 prints the SSN one digit to a cell.
    (ssn,) = _named("form_b121.pdf", "Debtor1a.SSNum")
    assert (ssn.comb, ssn.max_len) == (True, 11)
    # pypdf pads text by the field's border: 103B's 3 pt borders give a margin of 3.
    fee_waiver = template_widgets("form_b103b.pdf")
    assert len([w for w in fee_waiver if w.kind == "Text" and w.margin == 3]) == 14
    # A border on a kid widget alone is one pypdf never reads.
    assert [w.margin for w in _named("form_b103b.pdf", "Debtor.Name1")] == [1, 1]
    # Amounts are right-aligned ...
    (wages,) = _named("form_b106i.pdf", "Amount 2 Debtor 1")
    assert wages.align == 2
    # ... including where /Q 2 sits on the kid widget alone, which pypdf reads only from
    # the field: undefined_166's two widgets, and T8 but not T7 of 24.2's pair.
    assert [w.align for w in _named("form_b106ab.pdf", "undefined_166")] == [2, 2]
    ira = _named("form_b106ab.pdf", "24.2 Interest in an education IRA")
    assert [(w.tag, w.align) for w in ira] == [("T7", 0), ("T8", 2)]


class _Built(Exception):
    """What from_text_annotation handed TextStreamAppearance, raised by the stand-in below."""

    def __init__(self, layout, kwargs):
        self.layout = layout
        self.kwargs = kwargs


def test_every_box_is_measured_the_way_pypdf_draws_it(monkeypatch):
    # The stand-in records what pypdf would build each text and combo box from, then stops.
    def built(self, layout=None, *args, **kwargs):
        raise _Built(layout, kwargs)

    monkeypatch.setattr(TextStreamAppearance, "__init__", built)
    differences = set()
    compared = 0
    for template in _templates():
        writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
        acro_form = writer.root_object["/AcroForm"]
        for number, page in enumerate(writer.pages, start=1):
            for annot in page.get("/Annots") or []:
                annotation = annot.get_object()
                if annotation.get("/Subtype") != "/Widget":
                    continue
                widget = widget_for(template, number, annotation, float(page.mediabox.top))
                if widget.kind not in ("Text", "ComboBox"):
                    continue
                with pytest.raises(_Built) as seen:
                    TextStreamAppearance.from_text_annotation(
                        writer, page, False, acro_form, field_of(annotation), annotation
                    )
                layout, kwargs = seen.value.layout, seen.value.kwargs
                factor = 2 if layout.border_style in ("/B", "/I") else 1
                pypdf_reads = {
                    "font": kwargs["font_name"],
                    "size": float(kwargs["font_size"]),
                    "align": int(kwargs["alignment"]),
                    "comb": kwargs["is_comb"],
                    "multiline": kwargs["is_multiline"],
                    "max_len": kwargs["max_length"],
                    "margin": max(float(layout.border_width) * factor, 1),
                    "width": float(layout.rectangle.width),
                    "height": float(layout.rectangle.height),
                }
                ours = {
                    "font": widget.font,
                    "size": widget.size,
                    "align": widget.align,
                    "comb": widget.comb,
                    "multiline": widget.multiline,
                    "max_len": widget.max_len if widget.comb else None,  # pypdf's use of MaxLen
                    "margin": widget.margin,
                    "width": widget.width,
                    "height": widget.height,
                }
                differences |= {(widget.key, k) for k in ours if ours[k] != pypdf_reads[k]}
                compared += 1
    assert compared == 2053 + 18
    # Only what pypdf doesn't read from where the template puts it, and the drawing hands
    # over: MaxLen on the parent field (R4), /Q on the kid widget alone (R26).
    assert differences == {
        ("account number@1:T32", "max_len"),
        ("account number@3:T33", "max_len"),
        ("24.2 Interest in an education IRA@7:T8", "align"),
        ("undefined_166@10:T34", "align"),
        ("undefined_166@10:T35", "align"),
    }


def test_text_boxes_start_at_the_templates_font_and_size():
    text = [w for w in _all_widgets() if w.kind == "Text"]
    assert Counter((w.font, w.size) for w in text) == {
        ("/Helv", 10.0): 1959,
        ("/Helv", 9.0): 65,
        ("/Helv", 12.0): 19,
        ("/Helv", 0.0): 10,  # auto size
    }
    assert (sum(w.comb for w in text), sum(w.multiline for w in text)) == (51, 94)


def test_a_box_lists_its_on_states_and_a_combo_its_options():
    # 103B line 3's Yes and No boxes also draw an /Off appearance; it isn't a state to tick.
    line_3 = _named("form_b103b.pdf", "check 3")
    assert sorted(w.states for w in line_3) == [("/no",), ("/yes",)]
    assert {w.font for w in line_3} == {""}
    (district,) = _named("form_b121.pdf", "Bankruptcy District Information")
    assert "Northern District of Illinois" in district.options
    assert (district.font, district.states) == ("/Helv", ())


def test_a_values_key_names_a_full_name_or_one_widget():
    assert parse_key("Debtor 1") == ("Debtor 1", None, None)
    assert parse_key("Assistance 8f@2:T49") == ("Assistance 8f", 2, "T49")
    (_, second) = _named("form_b106i.pdf", "Assistance 8f")
    assert second.key == "Assistance 8f@2:T49"
    assert parse_key(second.key) == (second.full_name, second.page, second.tag)


@pytest.mark.parametrize("key", ["x@2", "x@a:T1", "x@2:", "x@:T1", "x@2:7", "@2:T1", ""])
def test_a_malformed_values_key_is_refused(key):
    with pytest.raises(ValueError):
        parse_key(key)


def test_an_annotation_the_template_lacks_is_a_mismatch():
    stray = DictionaryObject(
        {NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (1, 1, 2, 2)])}
    )
    with pytest.raises(TemplateMismatch, match=r"form_b106d\.pdf page 2"):
        widget_for(SCHEDULE_D, 2, stray, 792.0)


def _drop_a_row(rows):
    rows.remove(next(row for row in rows if row["page"] == 2))


def _add_a_row_with_no_widget(rows):
    rows.append(
        {**next(row for row in rows if row["page"] == 2), "tag": "T999", "rect": [1, 1, 2, 2]}
    )


def _add_a_row_past_the_last_page(rows):
    rows.append({**next(row for row in rows if row["page"] == 2), "page": 9, "tag": "T1"})


@pytest.mark.parametrize(
    "change, page",
    [(_drop_a_row, 2), (_add_a_row_with_no_widget, 2), (_add_a_row_past_the_last_page, 9)],
)
def test_an_index_that_doesnt_match_its_template_one_to_one_is_refused(index_copy, change, page):
    index_copy(SCHEDULE_D, change)
    with pytest.raises(TemplateMismatch, match=rf"form_b106d\.pdf page {page}:"):
        template_widgets(SCHEDULE_D)
