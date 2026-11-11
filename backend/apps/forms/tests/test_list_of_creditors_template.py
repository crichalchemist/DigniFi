"""
The court's List of Creditors template and its index (3c6 R1, R2).

Business intent: the list a filer prints is the court's own two pages, so the template is the
court's bytes and every box is indexed under the court's own name, by a tool that can be run
again, never by hand.
"""

import importlib.util

from django.conf import settings

from apps.forms.services import sheets
from apps.forms.services.text_fit import font_for
from apps.forms.services.widgets import template_widgets

ROOT = settings.BASE_DIR.parent
TOOL = ROOT / "data/forms/field_index/tools/build_list_of_creditors.py"
INDEX_DIR = ROOT / "data/forms/field_index"
PDF_DIR = ROOT / "data/forms/pdfs"
TEMPLATE = "ilnb_list_of_creditors.pdf"


def _tool():
    spec = importlib.util.spec_from_file_location("build_list_of_creditors", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _tool()


def test_the_index_is_what_the_tool_reads_off_the_template():
    # R2: the index is never hand-edited; the tool reads it off the committed template.
    committed = (INDEX_DIR / "ilnb_list_of_creditors.index.json").read_text()
    assert committed == tool.dumps(tool.index_rows(PDF_DIR / TEMPLATE))


def test_every_box_of_the_court_list_is_indexed_under_the_courts_own_name():
    widgets = template_widgets(TEMPLATE)  # matches each widget to one index row
    names = {w.full_name for w in widgets}
    assert len(widgets) == 36
    assert {"Debtor1.Name", "Debtor2.Name", "Case number1", "chapter", "Debtor1andDebtor2"} <= names
    assert {f"creditor1.0.{i}" for i in range(5)} | {f"creditor2.0.{i}" for i in range(5)} <= names
    assert {f"creditor{c}.0.5.{i}" for c in (1, 2) for i in range(10)} <= names
    assert [w.kind for w in widgets if w.full_name == "chapter"] == ["ComboBox"]


def test_the_list_prints_its_letters_in_the_forms_own_encoding():
    # The creditor boxes draw Times-Roman; both fonts must carry the shared /Differences.
    for font in ("/Helv", "/TiRo"):
        assert font_for(TEMPLATE, font).encoding == sheets._font().encoding
