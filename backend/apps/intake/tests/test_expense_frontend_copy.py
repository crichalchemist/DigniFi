"""
The Expenses step asks Schedule J's amounts in the form's own words, and the browser keeps its own
copy of the server's names and of the words the backfill wrote. A word that drifts from the form
tells the filer one thing on the step and another on the form; a name spelled differently makes
every save of the step drop an amount silently (DRF ignores unknown keys).
"""

import json
import re
from pathlib import Path

import pypdf
import pytest

from apps.intake.models import ExpenseInfo
from apps.intake.tests.test_petition_frontend_copy import FRONTEND, PDFS

INDEX = PDFS.parent / "field_index" / "form_b106j.index.json"
MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0047_label_combined_expense_figures.py"
)
LEGACY_TOTAL = FRONTEND / "components" / "wizard" / "steps" / "expenses" / "legacyTotal.ts"

# Each amount's line on Schedule J
LINE_OF = {
    "rent_or_mortgage": "4",
    "real_estate_taxes": "4a",
    "home_insurance": "4b",
    "home_maintenance": "4c",
    "hoa_dues": "4d",
    "electricity_heat_gas": "6a",
    "water_sewer_garbage": "6b",
    "phone_internet_cable": "6c",
    "utilities": "6d",
    "food_and_groceries": "7",
    "childcare": "8",
    "clothing": "9",
    "personal_care": "10",
    "medical_expenses": "11",
    "vehicle_maintenance": "12",
    "entertainment": "13",
    "charitable_contributions": "14",
    "life_insurance": "15a",
    "health_insurance": "15b",
    "vehicle_insurance": "15c",
    "insurance_not_deducted": "15d",
    "taxes_not_deducted": "16",
    "child_support_paid": "18",
    "support_others": "19",
    "other_property_taxes": "20b",
    "other_property_insurance": "20c",
    "other_property_upkeep": "20d",
    "other_property_hoa_dues": "20e",
    "other_expenses": "21",
}
SPECIFY_BOX_OF = {
    "utilities_specify": "Other 6d",
    "insurance_specify": "Other 15d",
    "taxes_specify": "Other 16",
    "support_others_specify": "Other 19",
    "other_expenses_specify": "Other 21",
}


@pytest.fixture(autouse=True)
def _frontend_is_here():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")


_ENTRY = re.compile(r"(\w+):\s*(?:'((?:\\'|[^'])*)'|\"((?:\\\"|[^\"])*)\")")


def _dict(source: str, name: str) -> dict[str, str]:
    """A formText.ts record's entries. Comment lines go first (a comment quoting words would parse
    as a key), and what the parser finds is compared to the server's list by the tests."""
    match = re.search(rf"^export const {name}\b[^=]*=\s*\{{(.*?)^\}};", source, re.M | re.S)
    assert match, f"formText.ts has no {name}"
    body = "\n".join(
        line for line in match.group(1).splitlines() if not line.lstrip().startswith("//")
    )
    return {
        key: (single or double).replace("\\'", "'").replace('\\"', '"')
        for key, single, double in _ENTRY.findall(body)
    }


def _string(source: str, name: str) -> str:
    match = re.search(
        rf"^export const {name}\b[^=]*=\s*(?:'(.*?)'|\"(.*?)\");", source, re.M | re.S
    )
    assert match, f"formText.ts has no {name}"
    return match.group(1) or match.group(2)


def _squeeze(text: str) -> str:
    return "".join(text.replace("’", "'").split())


@pytest.fixture(scope="module")
def layer() -> str:
    reader = pypdf.PdfReader(PDFS / "form_b106j.pdf")
    return _squeeze("".join(reader.pages[i].extract_text() for i in range(3)))


@pytest.fixture(scope="module")
def form_text() -> str:
    return (FRONTEND / "constants" / "formText.ts").read_text()


def test_the_browser_lists_the_servers_expense_names_in_order():
    api = (FRONTEND / "types" / "api.ts").read_text()

    def names(const):
        match = re.search(rf"^export const {const} = \[(.*?)\] as const;", api, re.M | re.S)
        assert match, f"api.ts has no {const}"
        return re.findall(r"'(\w+)'", match.group(1))

    assert names("EXPENSE_FIELDS") == list(ExpenseInfo.AMOUNT_FIELDS)
    assert names("EXPENSE_SPECIFY_FIELDS") == list(ExpenseInfo.SPECIFY_FIELDS)
    assert len(ExpenseInfo.AMOUNT_FIELDS) == 29 and len(ExpenseInfo.SPECIFY_FIELDS) == 5


def test_each_expense_line_is_quoted_after_its_line_number(form_text, layer):
    words = _dict(form_text, "EXPENSE_LINE_WORDS")
    # The parser can't miss an entry silently
    assert list(words) == list(ExpenseInfo.AMOUNT_FIELDS)
    assert list(LINE_OF) == list(ExpenseInfo.AMOUNT_FIELDS)
    for field, text in words.items():
        quote = f"{LINE_OF[field]}.{_squeeze(text)}"
        assert quote in layer, f"{field}: {LINE_OF[field]}. {text!r} is not on Schedule J"


def test_the_line_6_and_line_15_headings_are_the_forms_own(form_text, layer):
    assert f"6.{_squeeze(_string(form_text, 'LINE_6_GROUP_HEADING'))}" in layer
    assert f"15.{_squeeze(_string(form_text, 'LINE_15_GROUP_HEADING'))}" in layer


def test_each_specify_label_is_the_index_label_of_its_box(form_text):
    words = _dict(form_text, "EXPENSE_SPECIFY_WORDS")
    assert list(words) == list(ExpenseInfo.SPECIFY_FIELDS)
    labels = {row["full_name"]: row["label"] for row in json.loads(INDEX.read_text())}
    for field, text in words.items():
        assert (
            labels[SPECIFY_BOX_OF[field]] == text
        ), f"{field}: {text!r} is not the label of {SPECIFY_BOX_OF[field]}"


def test_the_step_looks_for_the_words_the_backfill_wrote():
    # The information line shows only for the exact words 0047 stored as the filer's own text
    browser = LEGACY_TOTAL.read_text()
    migration = MIGRATION.read_text()
    for field, constant, words in (
        ("utilities_specify", "UTILITIES_WORDS", "Utilities (combined)"),
        ("insurance_specify", "INSURANCE_WORDS", "Insurance (combined)"),
    ):
        # the browser keys the words by the field; the migration defines the words once and
        # assigns that constant to the field in its forward step
        assert re.search(rf"^\s*{field}:\s*'{re.escape(words)}',", browser, re.M)
        assert re.search(rf'^{constant} = "{re.escape(words)}"$', migration, re.M)
        assert re.search(rf"^\s+row\.{field} = {constant}$", migration, re.M)
