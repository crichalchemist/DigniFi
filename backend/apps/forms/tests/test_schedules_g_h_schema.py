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
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import Codebtor, DebtorInfo, ExecutoryContract, IntakeSession

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


@pytest.mark.parametrize("form_type", LISTS)
def test_each_schedule_answers_from_its_own_list_only(session, form_type):
    # A lease is no codebtor, and a codebtor no lease.
    for other, list_one in LISTS.items():
        if other != form_type:
            list_one(session)

    assert resolve(load_schema(form_type), session).get("check1") == "/no"
