"""
Schedules G and H: the filer's name heads every page, and line 1 answers Yes only when the
filer listed a contract or lease (G) or a codebtor (H).

Business intent: a page without the filer's name can be separated from the filing, and
line 1's answer tells the trustee whether to read on. DigniFi derives it from the lists
the filer saved, Yes with rows and No without (step 2 spec Appendix A.10, owner Q8).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.registry import build_parts
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import Codebtor, DebtorInfo, ExecutoryContract, IntakeSession
from apps.intake.tests.builders import (
    answer_claims,
    complete_codebtor,
    complete_contract,
    complete_debt,
)

User = get_user_model()


def _contract(session):
    ExecutoryContract.objects.create(
        session=session, counterparty_name="Lakeview Apartments", contract_type="lease"
    )


def _codebtor(session):
    Codebtor.objects.create(session=session, name="Pat Doe", relationship="relative")


# Form → how the filer lists one of what its line 1 asks about.
LISTS = {"schedule_g": _contract, "schedule_h": _codebtor}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemagh", password="pass")
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
        first_name="Jane",
        middle_name="",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


def _printed(session, form_type):
    """What the drawn form prints in each widget."""
    values = resolve(load_schema(form_type), session)
    return read_drawn(form_type, PDFFormFiller().fill(form_type, values))


@pytest.mark.parametrize("form_type", LISTS)
def test_the_filers_name_heads_every_page(session, form_type):
    widgets = _printed(session, form_type)

    # One field with a widget on each page: both pages show the name.
    named = {w.page for w in widgets if w.full_name == "Debtor 1" and w.value == "Jane Doe"}
    assert named == {1, 2}
    # A single filer's packet: the spouse's line stays blank.
    assert [w.value for w in widgets if w.full_name == "Debtor 2"] == [""]


@pytest.mark.parametrize("listed,ticks", [(True, {"/yes"}), (False, {"/no"})])
@pytest.mark.parametrize("form_type", LISTS)
def test_line_1_answers_yes_only_when_the_filer_listed_one(session, form_type, listed, ticks):
    if listed:
        LISTS[form_type](session)

    widgets = _printed(session, form_type)

    assert {w.state for w in widgets if w.full_name == "check1" and w.state != "/Off"} == ticks


def _parts_drawn(session, form_type):
    """(the parts, what the drawn form and its copies print), the copies read as their pages."""
    document = build_parts(form_type, session)
    pdf = PDFFormFiller().fill(form_type, document)
    return document["parts"], read_drawn(form_type, pdf, document["parts"])


def _at(drawn, name, copy=None, page=None):
    """What one box prints, on the form's own page (copy None) or on a copy."""
    values = [
        w.value
        for w in drawn
        if w.full_name == name and w.copy == copy and (page is None or w.page == page)
    ]
    assert len(values) == 1, (name, copy, values)
    return values[0]


def _tick(drawn, name, copy=None):
    """The state of the one box of this name that is ticked, else "/Off"."""
    states = {w.state for w in drawn if w.full_name == name and w.copy == copy} - {"/Off"}
    assert len(states) <= 1, (name, states)
    return states.pop() if states else "/Off"


def test_every_contract_prints_its_name_address_and_purpose(session):
    complete_contract(
        session,
        counterparty_name="Demo Lessor One",
        street_2="Suite 4",
        description="Apartment lease",
    )
    complete_contract(session, counterparty_name="Demo Lessor Two", description="Car lease")

    _, drawn = _parts_drawn(session, "schedule_g")

    for n, (name, purpose, street) in enumerate(
        [
            ("Demo Lessor One", "Apartment lease", "1 Demo Street, Suite 4"),
            ("Demo Lessor Two", "Car lease", "1 Demo Street"),
        ],
        start=1,
    ):
        assert _at(drawn, f"Company Name 2.{n}") == name
        assert _at(drawn, f"Street 2.{n}") == street
        assert _at(drawn, f"City 2.{n}") == "Demoville"
        assert _at(drawn, f"State 2.{n}") == "IL"
        assert _at(drawn, f"Zip 2.{n}") == "60601"
        assert _at(drawn, f"Contact Info 2.{n}") == purpose


def test_a_fourteenth_contract_continues_on_a_copy_numbered_14(session):
    for n in range(1, 15):
        complete_contract(session, counterparty_name=f"Demo Lessor {n}")

    parts, drawn = _parts_drawn(session, "schedule_g")

    assert [p["kind"] for p in parts] == ["form", "copy"]
    assert _at(drawn, "fill 2.6", copy=1) == "14"
    assert _at(drawn, "Company Name 2.6", copy=1) == "Demo Lessor 14"
    assert _at(drawn, "fill 2.10") == "10"
    assert _at(drawn, "fill_27.0") == "3"
    assert (_at(drawn, "fill_27.1.0"), _at(drawn, "fill_27.1.1")) == ("2", "3")
    assert (_at(drawn, "fill_27.1.0", copy=1), _at(drawn, "fill_27.1.1", copy=1)) == ("3", "3")


def test_a_blank_sixth_row_shows_the_courts_own_number(session):
    # B41: a row with no contract leaves its number box alone, and the form's own "6" shows.
    for n in range(1, 6):
        complete_contract(session, counterparty_name=f"Demo Lessor {n}")

    parts, drawn = _parts_drawn(session, "schedule_g")

    assert "fill 2.6" not in parts[0]["values"]
    assert _at(drawn, "fill 2.6") == ""


def test_a_codebtor_prints_the_lines_it_shares(session):
    secured = complete_debt(
        session,
        creditor_name="Demo Bank",
        is_secured=True,
        collateral_description="Demo",
        lien={"kinds": ["agreement"], "other": ""},
    )
    complete_debt(session, creditor_name="Demo Card Services")
    contract = complete_contract(session)
    links = [
        {"kind": "debt", "id": secured.pk},
        {"kind": "debt", "id": session.debts.order_by("pk").last().pk},
        {"kind": "contract", "id": contract.pk},
    ]
    complete_codebtor(session, links=links)

    _, drawn = _parts_drawn(session, "schedule_h")

    assert _tick(drawn, "check schedule line D 3.1") == "/yes"
    assert _tick(drawn, "check schedule line E/F 3.1") == "/yes"
    assert _tick(drawn, "check schedule line G 3.1") == "/yes"
    assert _at(drawn, "Schedule line D 3.1") == "2.1"
    assert _at(drawn, "Schedule line E/F 3.1") == "4.1"
    assert _at(drawn, "Schedule line G 3.1") == "2.1"
    assert _at(drawn, "Codebtor Name 3.1") == "Demo Codebtor"


def test_a_codebtor_with_more_lines_than_a_box_holds_takes_a_further_row(session):
    for n in range(3):
        complete_debt(session, creditor_name=f"Demo Card {n}")
    links = [{"kind": "debt", "id": d.pk} for d in session.debts.order_by("pk")]
    complete_codebtor(session, links=links)

    _, drawn = _parts_drawn(session, "schedule_h")

    assert _at(drawn, "Schedule line E/F 3.1") == "4.1, 4.2"
    assert _at(drawn, "Schedule line E/F 3.2") == "4.3"
    for n in (1, 2):
        assert _at(drawn, f"Codebtor Name 3.{n}") == "Demo Codebtor"
        assert _at(drawn, f"Codebtor Street 3.{n}") == "1 Demo Street"
    assert _tick(drawn, "check schedule line E/F 3.2") == "/yes"
    assert _tick(drawn, "check schedule line D 3.2") == "/Off"
    assert _tick(drawn, "check schedule line G 3.2") == "/Off"


def test_a_twelfth_codebtor_row_continues_on_a_copy(session):
    debt = complete_debt(session)
    for n in range(1, 13):
        complete_codebtor(
            session, links=[{"kind": "debt", "id": debt.pk}], name=f"Demo Codebtor {n}"
        )

    parts, drawn = _parts_drawn(session, "schedule_h")

    assert [p["kind"] for p in parts] == ["form", "copy"]
    assert _at(drawn, "fill 3.4", copy=1) == "12"
    assert _at(drawn, "Codebtor Name 3.4", copy=1) == "Demo Codebtor 12"


H2 = {
    "community_lived": "yes",
    "community_state": "Arizona",
    "community_spouse_name": "Demo Spouse",
    "community_spouse_street_address": "2 Demo Street",
    "community_spouse_city": "Demoville",
    "community_spouse_state": "IL",
    "community_spouse_zip_code": "60602",
}


def test_h_line_2_prints_the_spouse_under_both_yes(session):
    answer_claims(session, community_spouse_lived_with="yes", **H2)

    _, drawn = _parts_drawn(session, "schedule_h")

    assert _tick(drawn, "check2") == "/yes"
    assert _tick(drawn, "check3") == "/yes"
    assert {
        name: _at(drawn, name)
        for name in (
            "Community state",
            "Spouse Name",
            "Spouse Street",
            "Spouse City",
            "Spouse State",
            "Spouse Zip",
        )
    } == {
        "Community state": "Arizona",
        "Spouse Name": "Demo Spouse",
        "Spouse Street": "2 Demo Street",
        "Spouse City": "Demoville",
        "Spouse State": "IL",
        "Spouse Zip": "60602",
    }


def test_h_line_2_prints_no_spouse_under_a_no(session):
    answer_claims(session, community_spouse_lived_with="no", **H2)

    _, drawn = _parts_drawn(session, "schedule_h")

    assert _tick(drawn, "check2") == "/yes"
    assert _tick(drawn, "check3") == "/no"
    for name in (
        "Community state",
        "Spouse Name",
        "Spouse Street",
        "Spouse City",
        "Spouse State",
        "Spouse Zip",
    ):
        assert _at(drawn, name) == ""


@pytest.mark.parametrize("form_type", LISTS)
def test_each_schedule_answers_from_its_own_list_only(session, form_type):
    # A lease is no codebtor, and a codebtor no lease.
    for other, list_one in LISTS.items():
        if other != form_type:
            list_one(session)

    assert resolve(load_schema(form_type), session).get("check1") == "/no"
