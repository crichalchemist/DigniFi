"""The court's List of Creditors in the packet (3c6 spec §10, rulings R3, R4, R7, R8, R13).

Business intent: every filer's packet holds the court's own two-page list, with the filer's name
and chapter 7 and one entry per name and address the schedules print, in the court's boxes, and
an entry the form can't print sends the filer to the step that holds it.
"""

from datetime import date
from decimal import Decimal

import pymupdf
import pytest
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.registry import build_parts, packet
from apps.forms.schema import load_schema
from apps.forms.services import text_fit
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.forms.services.widgets import template_widgets
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_household,
    complete_codebtor,
    complete_contract,
    complete_debt,
)
from apps.users.models import User

FORM = "list_of_creditors"
LEFT_1 = [f"creditor1.0.{i}" for i in range(5)]
RIGHT_1 = [f"creditor2.0.{i}" for i in range(5)]


@pytest.fixture
def user(db):
    return User.objects.create_user(username="lister", email="lister@example.com", password="pw")


@pytest.fixture
def api_client(user):
    api = APIClient()
    api.force_authenticate(user=user)
    return api


@pytest.fixture
def district(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


def _session(user, district, county="Cook"):
    session = IntakeSession.objects.create(user=user, district=district, status="completed")
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("3000.00")
    )
    answer_household(session, county=county)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        middle_name="",
        ssn="900-12-3456",
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


@pytest.fixture
def session(user, district):
    return _session(user, district)


def _debts(session, count):
    for i in range(1, count + 1):
        complete_debt(session, creditor_name=f"Demo Lender {i}", street_address=f"{i} Demo Way")


def _drawn(session):
    document = build_parts(FORM, session)
    pdf = PDFFormFiller().fill(FORM, document)
    return document, pdf, read_drawn(FORM, pdf, document["parts"])


def _values(drawn):
    return {(w.full_name, w.page, w.copy): w.value for w in drawn}


def test_every_packet_holds_the_list_of_creditors(session):
    forms = packet(session)
    assert FORM in forms
    assert forms.index(FORM) == forms.index("form_121") + 1


def test_a_filer_with_no_creditors_gets_a_list_with_their_name_and_chapter_7(session):
    _, _, drawn = _drawn(session)
    values = _values(drawn)
    assert values[("Debtor1.Name", 1, None)] == "Jane Doe"
    assert values[("Debtor1.Name", 2, None)] == "Jane Doe"
    assert values[("chapter", 1, None)] == "7"
    # Debtor 2's name, the case number and the read-only "Debtor 1 and Debtor 2" label are
    # never bound: binding one prints a value here and fails this.
    for name in ("Debtor2.Name", "Case number1", "Debtor1andDebtor2"):
        boxes = [v for (full_name, _, _), v in values.items() if full_name == name]
        assert boxes and set(boxes) == {""}, name
    assert [w.value for w in drawn if w.full_name.startswith("creditor")] == [""] * 30


def test_each_entry_prints_in_its_own_box_column_by_column(session):
    _debts(session, 12)
    _, _, drawn = _drawn(session)
    by_name = {(w.full_name, w.page): w.value for w in drawn if w.full_name.startswith("creditor")}
    page_2_left = [f"creditor1.0.5.{i}" for i in range(2)]
    boxes = [*((n, 1) for n in LEFT_1), *((n, 1) for n in RIGHT_1)]
    boxes += [(n, 2) for n in page_2_left]
    # The debts print in the order Schedule E/F lists them (name, ignoring case), and the
    # boxes fill down the left column, then the right, then page 2's left.
    names = sorted(f"Demo Lender {i}" for i in range(1, 13))
    expected = [f"{n} {n.split()[-1]} Demo Way Demoville, IL 60601" for n in names]
    assert [by_name[box] for box in boxes] == expected
    assert sum(1 for v in by_name.values() if v) == 12


def test_entries_past_thirty_continue_on_a_copy_of_page_2(session):
    _debts(session, 30)
    complete_contract(session, counterparty_name="Demo Lease Co")
    document = build_parts(FORM, session)
    form, *copies = document["parts"]
    assert form["kind"] == "form"
    assert form["fixes"] == {
        name: {"step": "debts"}
        for name in [*LEFT_1, *RIGHT_1]
        + [f"creditor1.0.5.{i}" for i in range(10)]
        + [f"creditor2.0.5.{i}" for i in range(10)]
    }
    assert len(copies) == 1
    copy = copies[0]
    assert copy["kind"] == "copy" and copy["page"] == 2
    assert copy["values"]["Debtor1.Name"] == "Jane Doe"
    assert "Demo Lease Co" in copy["values"]["creditor1.0.5.0"]
    assert copy["fixes"] == {"creditor1.0.5.0": {"step": "contracts"}}

    pdf = PDFFormFiller().fill(FORM, document)
    drawn = read_drawn(FORM, pdf, document["parts"])
    on_copy = {w.full_name: w.value for w in drawn if w.copy == 1}
    assert on_copy["Debtor1.Name"] == "Jane Doe"
    assert "Demo Lease Co" in on_copy["creditor1.0.5.0"]
    assert [v for k, v in on_copy.items() if k.startswith("creditor") and v] == [
        on_copy["creditor1.0.5.0"]
    ]


def _heading(session):
    pdf = PDFFormFiller().fill(FORM, build_parts(FORM, session))
    page = pymupdf.open("pdf", pdf)[0]
    clip = pymupdf.Rect(0, 60, page.rect.width, 130)
    return page.get_pixmap(dpi=144, clip=clip).samples


def test_a_western_filer_gets_the_courts_page_as_published(user, district):
    western = _session(user, district, county="Winnebago")
    eastern = _session(user, district, county="Cook")
    assert _heading(western) == _heading(eastern)
    for session in (western, eastern):
        _, _, drawn = _drawn(session)
        assert all("DIVISION" not in w.value.upper() for w in drawn)


def _long_debt(session):
    complete_debt(session, creditor_name="W" * 60)


def _long_contract(session):
    complete_contract(session, counterparty_name="W" * 60)


def _long_codebtor(session):
    complete_debt(session)
    complete_codebtor(session, name="W" * 60)


@pytest.mark.parametrize(
    "make, step",
    [
        (_long_debt, "debts"),
        (_long_contract, "contracts"),
        (_long_codebtor, "codebtors"),
    ],
)
def test_an_entry_too_long_names_the_step_it_came_from(api_client, session, make, step):
    make(session)
    response = api_client.post(
        "/api/forms/generate/", {"session_id": session.id, "form_type": FORM}, format="json"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.data
    assert response.data["step"] == step
    assert "Name and address" in response.data["error"]


def test_a_creditor_box_is_measured_in_the_courts_times_roman(session):
    # W is 944 units in Times-Roman and Helvetica alike, so a run of W can't tell the two
    # apart. A run of i is 278 units in Times and 222 in Helvetica: it fits the box at 6 pt
    # in Helvetica and not in Times, so only a check measuring in the box's own font refuses it.
    template = load_schema(FORM).template_filename
    box = next(w for w in template_widgets(template) if w.full_name == "creditor1.0.0")
    room = box.width - 4 * box.margin
    count = int(room * 1000 / (222 * text_fit.MIN_SIZE))
    assert count * 222 * text_fit.MIN_SIZE / 1000 <= room < count * 278 * text_fit.MIN_SIZE / 1000
    font = text_fit.font_for(template, box.font)
    reverse_cmap = text_fit.reverse_cmap_for(template, box.font)
    word = "i" * count
    assert text_fit._width(font, reverse_cmap, word, text_fit.MIN_SIZE) > room
    complete_debt(session, creditor_name=word)
    with pytest.raises(ValueTooLong):
        PDFFormFiller().check(FORM, build_parts(FORM, session))
