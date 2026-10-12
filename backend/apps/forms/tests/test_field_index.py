"""
The field index names every widget of each AO template (spec §5.1).

Schemas, the filler and the oracle all address widgets through it, so each
widget must be found by its full name, with the export state a filler writes.
"""

import pytest
from django.conf import settings

from apps.forms.field_index import export_state, index_path, load_index

PETITION = "form_b_101_0624_fillable_clean.pdf"


def test_export_states_are_decoded_the_way_pypdf_reads_them():
    assert export_state("Chapter#207") == "/Chapter 7"
    assert export_state("On") == "/On"


def test_a_checkbox_group_is_one_full_name_with_a_widget_per_option():
    # Form 101 prints the chapter boxes twice: the page 1 header and Part 1 on page 3.
    chapter = load_index(PETITION)["Check Box1"]
    assert {w.type for w in chapter} == {"CheckBox"}
    assert {w.page for w in chapter} == {1, 3}
    assert [export_state(w.on_state) for w in chapter].count("/Chapter 7") == 2


def test_a_text_box_is_found_by_its_full_name():
    (first_name,) = load_index(PETITION)["Debtor1.First name"]
    assert first_name.type == "Text"
    assert first_name.on_state is None


def test_the_index_is_read_from_the_directory_the_image_copies_it_to():
    # Dockerfile.heroku copies data/forms/field_index/*.index.json to this directory.
    path = index_path(PETITION)
    assert path == settings.FORM_INDEX_DIRECTORY / "form_b_101_0624_fillable_clean.index.json"
    assert path.is_file()


def test_a_template_without_an_index_cannot_be_loaded():
    with pytest.raises(FileNotFoundError):
        load_index("no_such_template.pdf")
