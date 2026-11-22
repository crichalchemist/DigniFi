"""
Form 101A's schema and the landlord caps (forms step 4b2, R1, R10).

Business intent: Form 101A prints the filer's own landlord answer and nothing sworn, and each
landlord text stops at the width of the box that prints it on this form.
"""

import hashlib
import importlib.util
import json
from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.registry import build_field_values
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.services.widgets import template_widgets
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household, answer_petition, finish_intake

User = get_user_model()

ROOT = settings.BASE_DIR.parent
TOOL = ROOT / "data/forms/field_index/tools/build_form_101a.py"
INDEX_DIR = ROOT / "data/forms/field_index"
SCHEMAS = ROOT / "data/forms/schemas"
PDF_DIR = ROOT / "data/forms/pdfs"
TEMPLATE = "form_b101a_fillable.pdf"
LANDLORD = {
    "landlord_name": "Demo Property Holdings LLC",
    "landlord_street": "100 Demo St Apt 2",
    "landlord_city": "Chicago",
    "landlord_state": "IL",
    "landlord_zip": "60601",
}


def _tool():
    spec = importlib.util.spec_from_file_location("build_form_101a", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _tool()


def _index():
    return json.loads((INDEX_DIR / "form_b101a_fillable.index.json").read_text())


def test_the_schema_its_rows_and_its_caps_are_what_the_tool_writes():
    index = _index()
    digest = hashlib.sha256((PDF_DIR / TEMPLATE).read_bytes()).hexdigest()
    assert (SCHEMAS / "form_101a.json").read_text() == tool.dumps(tool.schema(index, digest))
    assert (SCHEMAS / "form_101a.limits.json").read_text() == tool.dumps(tool.limits(index))
    rows = tool.addendum_rows(index)
    assert len(rows) == 7
    assert tool.ADDENDUM.read_text() == tool.merged_text(tool.ADDENDUM.read_text(), rows)


def test_form_101a_binds_seven_boxes_and_nothing_sworn():
    # Never a No the filer didn't give, and nothing sworn (spec 5.3, B58).
    fields = json.loads((SCHEMAS / "form_101a.json").read_text())["fields"]
    names = {f["pdf_field"] for f in fields}
    assert names == {
        "Debtor 1",
        "Bankruptcy District Information",
        "Name of landlord",
        "Landlord Street address",
        "Landlord City",
        "Landlord State",
        "Landlord ZIP Code_5",
    }
    assert len(fields) == 7
    never = {
        "Check Box12",
        "Check Box13",
        "undefined_38",
        "undefined_39",
        "Date",
        "Date_2",
        "Debtor 2",
        "Case number",
    }
    assert not names & never


def test_the_landlord_caps_are_measured_on_form_101as_boxes():
    limits = json.loads((SCHEMAS / "form_101a.limits.json").read_text())
    assert limits["limits"] == {
        "landlord_name": 65,
        "landlord_street": 65,
        "landlord_city": 35,
        "landlord_state": 2,
        "landlord_zip": 13,
    }
    assert set(limits["labels"]) == set(limits["limits"])
    assert "cell_labels" not in limits


def test_the_state_cap_is_the_boxs_max_len():
    # The width formula gives 4 for two capitals in this box, but the box refuses a third
    # character (/MaxLen 2), so the cap is the smaller.
    (box,) = [w for w in template_widgets(TEMPLATE) if w.full_name == "Landlord State"]
    cap = json.loads((SCHEMAS / "form_101a.limits.json").read_text())["limits"]["landlord_state"]
    assert box.max_len == 2 == cap


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="fit101a", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session,
        first_name="Demo",
        middle_name="Q",
        last_name="Filer",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="demo@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(session=session)
    return session


def _printed_form_101a(session):
    """Every drawn widget of Form 101A by full name, each its own (value, state)."""
    values = build_field_values("form_101a", session)
    drawn = {(w.page, w.tag) for w in template_widgets(TEMPLATE) if w.drawn}
    shown = {}
    for widget in read_drawn("form_101a", PDFFormFiller().fill("form_101a", values)):
        if (widget.page, widget.tag) in drawn:
            shown.setdefault(widget.full_name, []).append((widget.value, widget.state))
    return shown


@pytest.mark.django_db
def test_form_101a_prints_the_caption_and_the_landlord_and_nothing_sworn(session):
    answer_household(session)
    finish_intake(session)
    answer_petition(session, rents_residence="yes", eviction_judgment="yes", **LANDLORD)

    shown = _printed_form_101a(session)

    # Each box holds its own answer: five distinct values, so a swapped pair fails.
    assert shown["Debtor 1"] == [("Demo Q Filer", "")]
    assert shown["Bankruptcy District Information"] == [("Northern District of Illinois", "")]
    assert shown["Name of landlord"] == [("Demo Property Holdings LLC", "")]
    assert shown["Landlord Street address"] == [("100 Demo St Apt 2", "")]
    assert shown["Landlord City"] == [("Chicago", "")]
    assert shown["Landlord State"] == [("IL", "")]
    assert shown["Landlord ZIP Code_5"] == [("60601", "")]
    # The certification boxes, the signing dates, Debtor 2 and the case number stay blank:
    # never a No the filer didn't give, and nothing sworn.
    for box in ("Check Box12", "Check Box13"):
        assert shown[box] and all(state == "/Off" for _, state in shown[box]), box
    for box in ("undefined_38", "undefined_39", "Date", "Date_2", "Debtor 2", "Case number"):
        assert shown[box], box
        assert all(value == "" and state in ("", "/Off") for value, state in shown[box]), box
