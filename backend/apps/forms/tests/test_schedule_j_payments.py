"""Schedule J prints each linked payment on the line the form asks for (3c4 spec §8.1)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.text_fit import fit
from apps.forms.services.widgets import template_widgets
from apps.intake.claims import OTHER_PROPERTY_WORDS, SPILL_WORDS, VEHICLE_WORDS
from apps.intake.models import ExpenseInfo, Household, IntakeSession
from apps.intake.tests.builders import linked_lease, linked_loan, linked_row

User = get_user_model()

BOXES = ("4", "5", "17a", "17b", "17c", "17d", "Other 17c", "Other 17d", "20a")


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="paymentsj", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    household = Household(session=session)
    household.store_members([])
    household.save()
    return session


def _printed(session):
    values = resolve(load_schema("schedule_j"), session)
    return {box: values.get(box) for box in BOXES}


def test_each_linked_payment_prints_on_its_line(session):
    ExpenseInfo.objects.create(session=session, rent_or_mortgage=Decimal("1000.00"))
    home = linked_row(session, "1", lives_here="yes")
    linked_loan(session, home, 1200, home_payment_line="first")
    linked_loan(session, home, 250, home_payment_line="additional")
    rental = linked_row(session, "1", lives_here="no")
    linked_loan(session, rental, 800)
    for payment in (10, 20, 30, 40):
        linked_loan(session, linked_row(session, "3"), payment)
    linked_loan(session, linked_row(session, "6"), 5)

    assert _printed(session) == {
        "4": "2200.00",
        "5": "250.00",
        "17a": "10.00",
        "17b": "20.00",
        "17c": "30.00",
        "Other 17c": "Vehicle 3",
        "17d": "45.00",
        "Other 17d": "Other secured payments",
        "20a": "800.00",
    }


def test_a_vehicle_lease_on_the_home_prints_on_line_4(session):
    ExpenseInfo.objects.create(session=session, rent_or_mortgage=Decimal("100.00"))
    home = linked_row(session, "4", lives_here="yes")
    linked_lease(session, home, 700)

    printed = _printed(session)

    assert printed["4"] == "800.00"
    assert printed["17a"] is None


def test_a_line_with_no_payment_prints_blank_and_so_do_its_words(session):
    ExpenseInfo.objects.create(session=session)
    linked_row(session, "3")

    assert _printed(session) == dict.fromkeys(BOXES)


@pytest.mark.parametrize("box", ["Other 17c", "Other 17d"])
@pytest.mark.parametrize("word", [*VEHICLE_WORDS, OTHER_PROPERTY_WORDS, SPILL_WORDS])
def test_the_specify_words_fit_their_box_whole(box, word):
    template = load_schema("schedule_j").template_filename
    widget = next(w for w in template_widgets(template) if w.full_name == box)

    assert fit(widget, template, word) == (word, 10.0)
