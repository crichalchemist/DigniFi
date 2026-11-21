"""
The field index names every widget of each AO template (spec §5.1).

Schemas, the filler and the oracle all address widgets through it, so each
widget must be found by its full name, with the export state a filler writes.
"""

import pytest
from django.conf import settings

from apps.forms.field_index import export_state, index_path, load_index, option_text

PETITION = "form_b101.pdf"


def test_export_states_are_decoded_the_way_pypdf_reads_them():
    assert export_state("Chapter#207") == "/Chapter 7"
    assert export_state("On") == "/On"


def test_a_radio_group_is_one_full_name_with_a_kid_per_state():
    # Form 101 line 9's No and Yes are the two kids of one radio group.
    radio = load_index(PETITION)["bankruptcy within the"]
    assert {w.type for w in radio} == {"RadioButton"}
    assert {w.page for w in radio} == {3}
    assert sorted(export_state(w.on_state) for w in radio) == ["/No", "/Yes"]


def test_the_chapter_box_is_two_names_on_two_pages():
    # 11/26 prints the chapter twice under two names: the cover and line 7 on page 3.
    index = load_index(PETITION)
    for name, page in (("Chapter 7", 1), ("Chapter 7_2", 3)):
        (box,) = index[name]
        assert (box.type, box.page, export_state(box.on_state)) == ("CheckBox", page, "/On")


def test_a_text_box_is_found_by_its_full_name():
    (first_name,) = load_index(PETITION)["First name"]
    assert first_name.type == "Text"
    assert first_name.on_state is None


def test_the_index_is_read_from_the_directory_the_image_copies_it_to():
    # Dockerfile.heroku copies data/forms/field_index/*.index.json to this directory.
    path = index_path(PETITION)
    assert path == settings.FORM_INDEX_DIRECTORY / "form_b101.index.json"
    assert path.is_file()


def test_a_template_without_an_index_cannot_be_loaded():
    with pytest.raises(FileNotFoundError):
        load_index("no_such_template.pdf")


def test_a_boxs_answer_reads_as_the_words_the_form_prints_beside_it():
    # Schedule J line 2, row a: "Does dependent live with you?" has one box per answer.
    assert option_text("form_b106j.pdf", "check2a", "/yes") == "Yes"
    assert option_text("form_b106j.pdf", "check2a", "/no") == "No"
    with pytest.raises(KeyError):
        option_text("form_b106j.pdf", "check2a", "/maybe")
    assert {w.option_text for w in load_index("form_b106j.pdf")["Dependant age 2a"]} == {""}
